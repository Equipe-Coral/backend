"""
Configurações do Blockchain Service.
Carrega variáveis de ambiente e define constantes.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações do serviço de blockchain."""

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001

    # Database Settings (para tracking de transações)
    DATABASE_URL: str = "postgresql://coral_user:senha123@localhost:5433/coral_blockchain"

    # Blockchain Settings - Ethereum Sepolia Testnet
    SEPOLIA_RPC_URL: str = "https://rpc.sepolia.org"
    ETHEREUM_MAINNET_RPC_URL: str = "https://eth.llamarpc.com"

    # Usar testnet por padrão para desenvolvimento
    USE_TESTNET: bool = True

    # Wallet do backend (custodial) - NUNCA commitar a private key real!
    WALLET_PRIVATE_KEY: str = ""
    WALLET_ADDRESS: str = ""

    # Smart Contract - Deployed on Sepolia
    CONTRACT_ADDRESS: str = "0x883C02985C8eEA78f708dbf5C84A1772a6bfbc6C"

    # Hash salt (deve ser o mesmo do backend principal para consistência)
    CIVIC_ID_SALT: str = "coral_civic_id"

    # Gas Settings
    GAS_LIMIT: int = 200000
    MAX_PRIORITY_FEE_GWEI: float = 2.0  # Sepolia gas prices
    MAX_FEE_GWEI: float = 10.0

    @property
    def rpc_url(self) -> str:
        """Retorna a URL RPC baseada na configuração de testnet."""
        return self.SEPOLIA_RPC_URL if self.USE_TESTNET else self.ETHEREUM_MAINNET_RPC_URL

    @property
    def network_name(self) -> str:
        """Retorna o nome da rede atual."""
        return "sepolia" if self.USE_TESTNET else "ethereum-mainnet"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
