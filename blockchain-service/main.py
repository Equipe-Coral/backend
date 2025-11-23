"""
Blockchain Service - Coral Platform
API FastAPI para tokenização de registros cívicos na blockchain Polygon.

Endpoint principal: POST /blockas
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.config import settings
from src.models import (
    TipoRegistro,
    BlockasRequest,
    BlockasResponse,
    StatusResponse,
    TransactionStatus,
    DemandaPayload,
    ContaPayload,
    ApoioPayload,
    DossiePayload,
    get_db,
    init_db,
    BlockchainRecord,
)
from src.services import HasherService, BlockchainService
from src.services.blockchain import blockchain_service


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    # Startup
    logger.info("Iniciando Blockchain Service...")
    init_db()
    blockchain_service.initialize()

    if blockchain_service.is_configured:
        balance = blockchain_service.get_balance()
        logger.info(f"Wallet balance: {balance} MATIC")
    else:
        logger.warning(
            "Blockchain service não está totalmente configurado. "
            "Configure WALLET_PRIVATE_KEY e CONTRACT_ADDRESS no .env"
        )

    yield

    # Shutdown
    logger.info("Encerrando Blockchain Service...")


app = FastAPI(
    title="Coral Blockchain Service",
    description="Serviço de tokenização de registros cívicos na blockchain Polygon",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serviços
hasher = HasherService()


def parse_payload(tipo: TipoRegistro, dados: dict):
    """Parse do payload baseado no tipo."""
    if tipo == TipoRegistro.DEMANDA:
        return DemandaPayload(**dados)
    elif tipo == TipoRegistro.CONTA:
        return ContaPayload(**dados)
    elif tipo == TipoRegistro.APOIO:
        return ApoioPayload(**dados)
    elif tipo == TipoRegistro.DOSSIE:
        return DossiePayload(**dados)
    else:
        raise ValueError(f"Tipo não suportado: {tipo}")


@app.get("/health")
def health_check():
    """Health check do serviço."""
    return {
        "status": "ok",
        "service": "blockchain-service",
        "network": blockchain_service.network_name,
        "configured": blockchain_service.is_configured,
    }


@app.post("/blockas", response_model=BlockasResponse)
async def blockas(
    request: BlockasRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint principal para tokenização de registros na blockchain.

    Tipos suportados:
    - **demanda**: Prova de existência de uma demanda cidadã
    - **conta**: Registro de ID Cívico (hash do telefone)
    - **apoio**: Registro de apoio a uma demanda
    - **dossie**: Hash de documento/evidência

    O serviço:
    1. Recebe os dados
    2. Hasheia informações sensíveis (telefone -> civic_id)
    3. Gera hash SHA-256 do conjunto de dados
    4. Envia transação para a blockchain Polygon
    5. Retorna tx_hash para acompanhamento

    **Nota**: Nenhum dado pessoal é enviado para a blockchain.
    Apenas hashes são registrados para prova de existência.
    """
    try:
        # Parse do payload específico
        if isinstance(request.dados, dict):
            payload = parse_payload(request.tipo, request.dados)
        else:
            payload = request.dados

        # Preparar dados e gerar hash
        prepared_data, data_hash = hasher.prepare_and_hash(request.tipo, payload)

        # Verificar se já existe registro com este hash
        existing = db.query(BlockchainRecord).filter(
            BlockchainRecord.data_hash == data_hash
        ).first()

        if existing:
            return BlockasResponse(
                success=True,
                tipo=request.tipo,
                data_hash=data_hash,
                tx_hash=existing.tx_hash,
                status=TransactionStatus(existing.status),
                block_number=existing.block_number,
                network=existing.network,
                message="Registro já existe na blockchain"
            )

        # Metadata para o contrato (sem dados sensíveis)
        metadata = json.dumps({
            "tipo": request.tipo.value,
            "version": "1.0",
        })

        # Registrar na blockchain
        status, tx_hash, error = blockchain_service.register_hash(
            data_hash=data_hash,
            tipo=request.tipo.value,
            metadata=metadata,
            db=db,
            original_data=prepared_data
        )

        if status == TransactionStatus.FAILED:
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao registrar na blockchain: {error}"
            )

        return BlockasResponse(
            success=True,
            tipo=request.tipo,
            data_hash=data_hash,
            tx_hash=tx_hash,
            status=status,
            block_number=None,
            network=blockchain_service.network_name,
            message="Transação enviada" if tx_hash else "Registro salvo - aguardando configuração do serviço"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no endpoint /blockas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.get("/blockas/status/{tx_hash}", response_model=StatusResponse)
async def get_transaction_status(
    tx_hash: str,
    db: Session = Depends(get_db)
):
    """
    Consulta o status de uma transação.

    Use o tx_hash retornado pelo endpoint /blockas para verificar
    se a transação foi confirmada na blockchain.
    """
    status, block_number, error = blockchain_service.check_transaction_status(
        tx_hash, db
    )

    # Buscar info adicional do banco
    record = db.query(BlockchainRecord).filter(
        BlockchainRecord.tx_hash == tx_hash
    ).first()

    confirmations = None
    if block_number and blockchain_service.w3:
        current_block = blockchain_service.w3.eth.block_number
        confirmations = current_block - block_number

    return StatusResponse(
        tx_hash=tx_hash,
        status=status,
        block_number=block_number,
        confirmations=confirmations,
        gas_used=record.gas_used if record else None,
        error=error
    )


@app.get("/blockas/verify/{data_hash}")
async def verify_hash(
    data_hash: str,
    db: Session = Depends(get_db)
):
    """
    Verifica se um hash está registrado na blockchain.

    Permite validar que um determinado conjunto de dados
    foi registrado em uma data específica.
    """
    # Verificar no banco local primeiro
    record = db.query(BlockchainRecord).filter(
        BlockchainRecord.data_hash == data_hash
    ).first()

    local_info = None
    if record:
        local_info = {
            "tipo": record.tipo,
            "status": record.status,
            "tx_hash": record.tx_hash,
            "block_number": record.block_number,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "confirmed_at": record.confirmed_at.isoformat() if record.confirmed_at else None,
        }

    # Verificar on-chain
    on_chain, chain_info = blockchain_service.verify_hash_on_chain(data_hash)

    return {
        "data_hash": data_hash,
        "exists_on_chain": on_chain,
        "chain_info": chain_info,
        "local_record": local_info,
    }


@app.get("/blockas/records")
async def list_records(
    tipo: Optional[TipoRegistro] = Query(None, description="Filtrar por tipo"),
    status: Optional[TransactionStatus] = Query(None, description="Filtrar por status"),
    limit: int = Query(50, le=100, description="Limite de registros"),
    offset: int = Query(0, description="Offset para paginação"),
    db: Session = Depends(get_db)
):
    """
    Lista registros de blockchain salvos localmente.

    Útil para auditoria e acompanhamento de transações.
    """
    query = db.query(BlockchainRecord)

    if tipo:
        query = query.filter(BlockchainRecord.tipo == tipo.value)
    if status:
        query = query.filter(BlockchainRecord.status == status.value)

    total = query.count()
    records = query.order_by(
        BlockchainRecord.created_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "records": [
            {
                "id": str(record.id),
                "tipo": record.tipo,
                "data_hash": record.data_hash,
                "tx_hash": record.tx_hash,
                "status": record.status,
                "block_number": record.block_number,
                "network": record.network,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
            for record in records
        ]
    }


@app.get("/blockas/stats")
async def get_stats(db: Session = Depends(get_db)):
    """
    Retorna estatísticas do serviço de blockchain.
    """
    from sqlalchemy import func

    # Contagem por tipo
    by_type = db.query(
        BlockchainRecord.tipo,
        func.count(BlockchainRecord.id)
    ).group_by(BlockchainRecord.tipo).all()

    # Contagem por status
    by_status = db.query(
        BlockchainRecord.status,
        func.count(BlockchainRecord.id)
    ).group_by(BlockchainRecord.status).all()

    total = db.query(func.count(BlockchainRecord.id)).scalar()

    # Info da wallet
    wallet_info = None
    if blockchain_service.is_configured:
        balance = blockchain_service.get_balance()
        wallet_info = {
            "address": blockchain_service.account.address if blockchain_service.account else None,
            "balance_matic": float(balance) if balance else None,
        }

    return {
        "total_records": total,
        "by_type": {tipo: count for tipo, count in by_type},
        "by_status": {status: count for status, count in by_status},
        "network": blockchain_service.network_name,
        "contract_address": settings.CONTRACT_ADDRESS or "Não configurado",
        "wallet": wallet_info,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
