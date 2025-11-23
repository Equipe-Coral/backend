"""
Serviço de integração com blockchain Ethereum (Sepolia testnet).
Responsável por enviar transações e verificar status.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Tuple

from web3 import Web3
from eth_account import Account
from sqlalchemy.orm import Session

from src.config import settings
from src.models.schemas import TransactionStatus
from src.models.database import BlockchainRecord

logger = logging.getLogger(__name__)


# ABI do contrato CivicRegistry (funções essenciais)
CONTRACT_ABI = [
    {
        "inputs": [
            {"name": "_dataHash", "type": "bytes32"},
            {"name": "_tipo", "type": "string"},
            {"name": "_metadata", "type": "string"}
        ],
        "name": "registerRecord",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "_dataHash", "type": "bytes32"}],
        "name": "getRecord",
        "outputs": [
            {"name": "exists", "type": "bool"},
            {"name": "tipo", "type": "string"},
            {"name": "timestamp", "type": "uint256"},
            {"name": "registrar", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "_dataHash", "type": "bytes32"}],
        "name": "verifyRecord",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "dataHash", "type": "bytes32"},
            {"indexed": True, "name": "registrar", "type": "address"},
            {"indexed": False, "name": "tipo", "type": "string"},
            {"indexed": False, "name": "timestamp", "type": "uint256"}
        ],
        "name": "RecordRegistered",
        "type": "event"
    }
]


class BlockchainService:
    """
    Serviço para interação com a blockchain Ethereum (Sepolia).
    Gerencia conexão Web3, envio de transações e verificação de status.
    """

    def __init__(self):
        self.w3: Optional[Web3] = None
        self.account: Optional[Account] = None
        self.contract = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Inicializa conexão com a blockchain.
        Retorna True se bem-sucedido.
        """
        try:
            # Conectar ao RPC
            self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))

            if not self.w3.is_connected():
                logger.error("Falha ao conectar com a blockchain")
                return False

            # Carregar conta do backend
            if settings.WALLET_PRIVATE_KEY:
                self.account = Account.from_key(settings.WALLET_PRIVATE_KEY)
                logger.info(f"Wallet carregada: {self.account.address}")

            # Carregar contrato
            if settings.CONTRACT_ADDRESS:
                self.contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(settings.CONTRACT_ADDRESS),
                    abi=CONTRACT_ABI
                )
                logger.info(f"Contrato carregado: {settings.CONTRACT_ADDRESS}")

            self._initialized = True
            logger.info(f"Blockchain service inicializado na rede: {settings.network_name}")
            return True

        except Exception as e:
            logger.error(f"Erro ao inicializar blockchain service: {e}")
            return False

    @property
    def network_name(self) -> str:
        """Retorna nome da rede atual."""
        return settings.network_name

    @property
    def is_configured(self) -> bool:
        """Verifica se o serviço está totalmente configurado."""
        return bool(
            settings.WALLET_PRIVATE_KEY
            and settings.CONTRACT_ADDRESS
            and self._initialized
        )

    def get_balance(self) -> Optional[float]:
        """Retorna o saldo da wallet em ETH."""
        if not self.account or not self.w3:
            return None
        balance_wei = self.w3.eth.get_balance(self.account.address)
        return self.w3.from_wei(balance_wei, "ether")

    def register_hash(
        self,
        data_hash: str,
        tipo: str,
        metadata: str,
        db: Session,
        original_data: dict
    ) -> Tuple[TransactionStatus, Optional[str], Optional[str]]:
        """
        Registra um hash na blockchain.

        Args:
            data_hash: Hash SHA-256 dos dados (64 chars hex)
            tipo: Tipo de registro (demanda, conta, apoio, dossie)
            metadata: JSON string com metadados adicionais
            db: Sessão do banco de dados
            original_data: Dados originais para persistência local

        Returns:
            Tuple de (status, tx_hash, error_message)
        """
        # Criar registro local primeiro
        record = BlockchainRecord(
            tipo=tipo,
            data_hash=data_hash,
            original_data=original_data,
            network=self.network_name,
            contract_address=settings.CONTRACT_ADDRESS,
            status=TransactionStatus.PENDING.value
        )
        db.add(record)
        db.commit()

        # Se não está configurado, retorna como pending para processamento posterior
        if not self.is_configured:
            logger.warning("Blockchain service não configurado - registro salvo como pending")
            return TransactionStatus.PENDING, None, "Serviço não configurado - aguardando configuração"

        try:
            # Converter hash hex para bytes32
            hash_bytes = bytes.fromhex(data_hash)

            # Construir transação
            nonce = self.w3.eth.get_transaction_count(self.account.address)

            # Estimar gas
            gas_estimate = self.contract.functions.registerRecord(
                hash_bytes,
                tipo,
                metadata
            ).estimate_gas({"from": self.account.address})

            # Construir transação com EIP-1559
            tx = self.contract.functions.registerRecord(
                hash_bytes,
                tipo,
                metadata
            ).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gas": min(gas_estimate + 50000, settings.GAS_LIMIT),
                "maxFeePerGas": self.w3.to_wei(settings.MAX_FEE_GWEI, "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei(settings.MAX_PRIORITY_FEE_GWEI, "gwei"),
            })

            # Assinar e enviar
            signed_tx = self.w3.eth.account.sign_transaction(tx, settings.WALLET_PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            # Atualizar registro
            record.tx_hash = tx_hash_hex
            record.status = TransactionStatus.SUBMITTED.value
            record.submitted_at = datetime.utcnow()
            db.commit()

            logger.info(f"Transação enviada: {tx_hash_hex}")
            return TransactionStatus.SUBMITTED, tx_hash_hex, None

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erro ao enviar transação: {error_msg}")

            record.status = TransactionStatus.FAILED.value
            record.error_message = error_msg
            record.retry_count += 1
            db.commit()

            return TransactionStatus.FAILED, None, error_msg

    def check_transaction_status(
        self, tx_hash: str, db: Session
    ) -> Tuple[TransactionStatus, Optional[int], Optional[str]]:
        """
        Verifica o status de uma transação.

        Returns:
            Tuple de (status, block_number, error_message)
        """
        if not self.w3:
            return TransactionStatus.PENDING, None, "Serviço não inicializado"

        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)

            if receipt is None:
                return TransactionStatus.SUBMITTED, None, None

            # Atualizar registro no banco
            record = db.query(BlockchainRecord).filter(
                BlockchainRecord.tx_hash == tx_hash
            ).first()

            if receipt.status == 1:
                if record:
                    record.status = TransactionStatus.CONFIRMED.value
                    record.block_number = receipt.blockNumber
                    record.gas_used = receipt.gasUsed
                    record.confirmed_at = datetime.utcnow()
                    db.commit()
                return TransactionStatus.CONFIRMED, receipt.blockNumber, None
            else:
                if record:
                    record.status = TransactionStatus.FAILED.value
                    record.error_message = "Transação revertida"
                    db.commit()
                return TransactionStatus.FAILED, None, "Transação revertida"

        except Exception as e:
            return TransactionStatus.SUBMITTED, None, str(e)

    def verify_hash_on_chain(self, data_hash: str) -> Tuple[bool, Optional[dict]]:
        """
        Verifica se um hash existe na blockchain.

        Returns:
            Tuple de (exists, record_info)
        """
        if not self.contract:
            return False, None

        try:
            hash_bytes = bytes.fromhex(data_hash)
            exists, tipo, timestamp, registrar = self.contract.functions.getRecord(
                hash_bytes
            ).call()

            if exists:
                return True, {
                    "tipo": tipo,
                    "timestamp": timestamp,
                    "registrar": registrar,
                }
            return False, None

        except Exception as e:
            logger.error(f"Erro ao verificar hash: {e}")
            return False, None


# Singleton do serviço
blockchain_service = BlockchainService()
