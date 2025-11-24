# Blockchain Service - Coral Platform

Serviço de integração com blockchain para tokenização de registros cívicos na rede Ethereum (Sepolia testnet).

## Smart Contract Deployado

| Rede | Endereço | Explorer |
|------|----------|----------|
| **Sepolia (testnet)** | `0x883C02985C8eEA78f708dbf5C84A1772a6bfbc6C` | [Blockscout](https://eth-sepolia.blockscout.com/address/0x883C02985C8eEA78f708dbf5C84A1772a6bfbc6C?tab=contract) |

## Visão Geral

Este serviço permite registrar provas de existência de ações cívicas na blockchain, garantindo:

- **Imutabilidade**: Uma vez registrado, o hash não pode ser alterado
- **Transparência**: Qualquer pessoa pode verificar a existência de um registro
- **Privacidade**: Nenhum dado pessoal vai para a blockchain, apenas hashes SHA-256

## Arquitetura

```
blockchain-service/
├── main.py                    # FastAPI app com endpoint /blockas
├── Dockerfile                 # Container Docker
├── requirements.txt           # Dependências Python
├── .env.example              # Template de variáveis de ambiente
├── README.md                 # Esta documentação
├── src/
│   ├── config.py             # Configurações (Pydantic Settings)
│   ├── models/
│   │   ├── schemas.py        # Schemas Pydantic (request/response)
│   │   └── database.py       # SQLAlchemy models para tracking
│   ├── services/
│   │   ├── hasher.py         # Serviço de hashing SHA-256
│   │   └── blockchain.py     # Serviço Web3 para Ethereum
│   └── contracts/
│       └── CivicRegistry.sol # Smart contract Solidity
└── tests/
    └── test_blockas.py       # Testes do endpoint
```

## Tipos de Registro

| Tipo | Descrição | Dados Hasheados |
|------|-----------|-----------------|
| `demanda` | Prova de existência de uma demanda cidadã | demand_id, title, creator_hash, theme, scope_level, timestamp |
| `conta` | Registro de ID Cívico | civic_id (hash do telefone), user_id, timestamp |
| `apoio` | Registro de apoio a uma demanda | demand_id, supporter_hash, timestamp |
| `dossie` | Hash de documento/evidência | demand_id, file_hash, file_name, timestamp |

## Endpoints

### POST /blockas

Endpoint principal para tokenização de registros.

**Request:**
```json
{
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
```

**Response:**
```json
{
  "success": true,
  "tipo": "demanda",
  "data_hash": "a1b2c3d4e5f6789...",
  "tx_hash": "0x1234567890abcdef...",
  "status": "submitted",
  "block_number": null,
  "network": "sepolia",
  "message": "Transação enviada",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### GET /blockas/status/{tx_hash}

Consulta o status de uma transação.

### GET /blockas/verify/{data_hash}

Verifica se um hash existe na blockchain.

### GET /blockas/records

Lista registros salvos localmente (com filtros opcionais).

### GET /blockas/stats

Retorna estatísticas do serviço.

### GET /health

Health check do serviço.

## Fluxo de Tokenização

```
1. Cliente envia POST /blockas com tipo e dados
           │
           ▼
2. Serviço hasheia dados sensíveis (telefone → civic_id)
           │
           ▼
3. Gera hash SHA-256 do conjunto de dados preparados
           │
           ▼
4. Salva registro local no PostgreSQL (status: pending)
           │
           ▼
5. Envia transação para smart contract na Sepolia
           │
           ▼
6. Atualiza status para "submitted" com tx_hash
           │
           ▼
7. Retorna tx_hash para cliente acompanhar
```

## Smart Contract

O contrato `CivicRegistry.sol` está deployado na Sepolia:

**Endereço**: `0x883C02985C8eEA78f708dbf5C84A1772a6bfbc6C`

**Funções principais:**

```solidity
// Registra um novo hash
function registerRecord(
    bytes32 _dataHash,
    string calldata _tipo,
    string calldata _metadata
) external returns (uint256 recordId);

// Verifica se hash existe
function verifyRecord(bytes32 _dataHash) external view returns (bool);

// Consulta informações de um registro
function getRecord(bytes32 _dataHash) external view returns (
    bool exists,
    string memory tipo,
    uint256 timestamp,
    address registrar
);
```

**Verificar contrato no explorer:**
- [Blockscout Sepolia](https://eth-sepolia.blockscout.com/address/0x883C02985C8eEA78f708dbf5C84A1772a6bfbc6C?tab=contract)

## Configuração

### Variáveis de Ambiente

```bash
# Copie o template
cp .env.example .env

# Edite as variáveis
nano .env
```

**Variáveis obrigatórias para produção:**

| Variável | Descrição | Valor Padrão |
|----------|-----------|--------------|
| `DATABASE_URL` | URL do PostgreSQL | - |
| `WALLET_PRIVATE_KEY` | Private key da wallet (sem 0x) | - |
| `WALLET_ADDRESS` | Endereço da wallet | - |
| `CONTRACT_ADDRESS` | Endereço do contrato | `0x883C02985C8eEA78f708dbf5C84A1772a6bfbc6C` |
| `USE_TESTNET` | Usar Sepolia (true) ou mainnet (false) | `true` |

### Wallet

O serviço usa uma wallet **custodial** (gerenciada pelo backend):

1. **Crie uma wallet** usando MetaMask ou qualquer outra ferramenta
2. **Exporte a private key** (nunca commite!)
3. **Deposite ETH (Sepolia)** para pagar gas:
   - Faucet: https://sepoliafaucet.com/
   - Faucet alternativo: https://www.alchemy.com/faucets/ethereum-sepolia

## Execução

### Desenvolvimento Local

```bash
# Instale dependências
pip install -r requirements.txt

# Configure variáveis
cp .env.example .env
# Edite .env com suas configurações

# Execute
python main.py

# Ou com uvicorn
uvicorn main:app --reload --port 8001
```

### Docker

```bash
# Build
docker build -t coral-blockchain-service .

# Run
docker run -p 8001:8001 --env-file .env coral-blockchain-service
```

### Docker Compose (recomendado)

O serviço está configurado no `docker-compose.yml` do projeto principal:

```bash
# Na raiz do projeto backend
docker-compose up -d blockchain-service
```

## Segurança

### O que vai para blockchain:
- Hashes SHA-256 dos dados
- Tipo do registro
- Timestamp

### O que NÃO vai para blockchain:
- Telefones (convertidos para civic_id hash)
- Nomes
- Endereços
- Qualquer dado pessoal identificável

### Boas práticas:
- Nunca commite `WALLET_PRIVATE_KEY`
- Use secrets manager em produção (AWS Secrets, Vault, etc)
- Monitore o saldo da wallet
- Configure alertas para transações falhas

## Custos

### Sepolia (Testnet)
- **Custo**: Gratuito (use faucets para obter ETH de teste)
- **Propósito**: Desenvolvimento e testes

### Ethereum Mainnet (Produção)
- **Gas por transação**: ~50,000-100,000 gas
- **Custo médio**: Depende do gas price atual
- **Recomendação**: Considere L2s como Base ou Arbitrum para custos menores

## Testes

```bash
# Execute testes
pytest tests/ -v

# Com coverage
pytest tests/ --cov=src --cov-report=html
```

## API Documentation

Após iniciar o serviço, acesse:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Exemplo de Uso

```bash
# Registrar uma demanda
curl -X POST http://localhost:8001/blockas \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "demanda",
    "dados": {
      "demand_id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Buracos na Rua das Flores",
      "creator_phone": "+5511999999999",
      "theme": "zeladoria",
      "scope_level": 1
    }
  }'

# Verificar status da transação
curl http://localhost:8001/blockas/status/0x1234...

# Verificar hash on-chain
curl http://localhost:8001/blockas/verify/abc123...
```

## Roadmap

- [x] Endpoint `/blockas` básico
- [x] Suporte a 4 tipos de registro
- [x] Tracking local de transações
- [x] Verificação on-chain
- [x] Deploy na Sepolia
- [ ] Batch de registros
- [ ] Webhook para notificação de confirmação
- [ ] Dashboard de monitoramento
- [ ] Migração para L2 (Base/Arbitrum) em produção

## Troubleshooting

### "Serviço não configurado"
Configure `WALLET_PRIVATE_KEY` no `.env`

### "Insufficient funds"
Deposite ETH (Sepolia) na wallet do backend usando um faucet

### "Transaction reverted"
Verifique se a wallet está autorizada no contrato (`addRegistrar`)

### "Hash já registrado"
O mesmo conjunto de dados já foi tokenizado anteriormente

### "Falha ao conectar com a blockchain"
Verifique a URL do RPC e sua conexão com a internet

## Contribuição

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## Licença

MIT License - Coral Platform
