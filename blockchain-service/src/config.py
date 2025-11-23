"""
Configurações do Blockchain Service.
Carrega variáveis de ambiente e define constantes.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configurações do serviço de blockchain."""

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001

    # Database Settings (para tracking de transações)
    DATABASE_URL: str = "postgresql://coral_user:senha123@localhost:5433/coral_blockchain"

    # Blockchain Settings - Polygon
    POLYGON_RPC_URL: str = "https://polygon-rpc.com"  # Mainnet
    POLYGON_TESTNET_RPC_URL: str = "https://rpc-amoy.polygon.technology"  # Amoy Testnet

    # Usar testnet por padrão para desenvolvimento
    USE_TESTNET: bool = True

    # Wallet do backend (custodial) - NUNCA commitar a private key real!
    WALLET_PRIVATE_KEY: str = ""
    WALLET_ADDRESS: str = ""

    # Smart Contract
    CONTRACT_ADDRESS: str = ""

    # Hash salt (deve ser o mesmo do backend principal para consistência)
    CIVIC_ID_SALT: str = "coral_civic_id"

    # Gas Settings
    GAS_LIMIT: int = 200000
    MAX_PRIORITY_FEE_GWEI: float = 30.0  # Para Polygon
    MAX_FEE_GWEI: float = 50.0

    @property
    def rpc_url(self) -> str:
        """Retorna a URL RPC baseada na configuração de testnet."""
        return self.POLYGON_TESTNET_RPC_URL if self.USE_TESTNET else self.POLYGON_RPC_URL

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
