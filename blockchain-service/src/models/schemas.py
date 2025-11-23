"""
Schemas Pydantic para o endpoint /blockas.
Define os tipos de registro e payloads específicos.
"""

from enum import Enum
from typing import Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class TipoRegistro(str, Enum):
    """Tipos de registro suportados pelo serviço de blockchain."""

    DEMANDA = "demanda"
    CONTA = "conta"
    APOIO = "apoio"
    DOSSIE = "dossie"


class DemandaPayload(BaseModel):
    """Payload para tokenização de uma demanda."""

    demand_id: str = Field(..., description="UUID da demanda")
    title: str = Field(..., description="Título da demanda")
    creator_phone: str = Field(..., description="Telefone do criador (será hasheado)")
    description: Optional[str] = Field(None, description="Descrição da demanda")
    theme: Optional[str] = Field(None, description="Tema da demanda")
    scope_level: Optional[int] = Field(None, description="Nível de escopo (1-3)")


class ContaPayload(BaseModel):
    """Payload para tokenização de uma conta/ID Cívico."""

    phone: str = Field(..., description="Telefone do usuário (será hasheado)")
    user_id: Optional[str] = Field(None, description="UUID do usuário no sistema")


class ApoioPayload(BaseModel):
    """Payload para registro de apoio a uma demanda."""

    demand_id: str = Field(..., description="UUID da demanda apoiada")
    supporter_phone: str = Field(..., description="Telefone do apoiador (será hasheado)")


class DossiePayload(BaseModel):
    """Payload para registro de dossiê/documento."""

    demand_id: str = Field(..., description="UUID da demanda relacionada")
    file_hash: str = Field(..., description="SHA-256 do arquivo/documento")
    file_name: Optional[str] = Field(None, description="Nome do arquivo")
    file_type: Optional[str] = Field(None, description="Tipo MIME do arquivo")


class BlockasRequest(BaseModel):
    """Request body para o endpoint /blockas."""

    tipo: TipoRegistro = Field(..., description="Tipo de registro a ser tokenizado")
    dados: Union[DemandaPayload, ContaPayload, ApoioPayload, DossiePayload] = Field(
        ..., description="Dados específicos do tipo de registro"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tipo": "demanda",
                "dados": {
                    "demand_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "Buracos na Rua das Flores",
                    "creator_phone": "+5511999999999",
                    "description": "Vários buracos causando acidentes",
                    "theme": "zeladoria",
                    "scope_level": 1
                }
            }
        }


class TransactionStatus(str, Enum):
    """Status de uma transação blockchain."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class BlockasResponse(BaseModel):
    """Response do endpoint /blockas."""

    success: bool = Field(..., description="Se a operação foi bem-sucedida")
    tipo: TipoRegistro = Field(..., description="Tipo de registro processado")
    data_hash: str = Field(..., description="Hash SHA-256 dos dados registrados")
    tx_hash: Optional[str] = Field(None, description="Hash da transação na blockchain")
    status: TransactionStatus = Field(..., description="Status da transação")
    block_number: Optional[int] = Field(None, description="Número do bloco (se confirmado)")
    network: str = Field(..., description="Rede blockchain utilizada")
    message: Optional[str] = Field(None, description="Mensagem adicional")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "tipo": "demanda",
                "data_hash": "a1b2c3d4e5f6...",
                "tx_hash": "0x1234567890abcdef...",
                "status": "submitted",
                "block_number": None,
                "network": "polygon-amoy",
                "message": "Transação enviada com sucesso",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class StatusResponse(BaseModel):
    """Response para consulta de status de transação."""

    tx_hash: str
    status: TransactionStatus
    block_number: Optional[int] = None
    confirmations: Optional[int] = None
    gas_used: Optional[int] = None
    error: Optional[str] = None
