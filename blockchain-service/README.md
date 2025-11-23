# Blockchain Service - Coral Platform

Serviço de integração com blockchain para tokenização de registros cívicos na rede Polygon.

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
│   │   └── blockchain.py     # Serviço Web3 para Polygon
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
  "network": "polygon-amoy",
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
5. Envia transação para smart contract na Polygon
           │
           ▼
6. Atualiza status para "submitted" com tx_hash
           │
           ▼
7. Retorna tx_hash para cliente acompanhar
```

## Smart Contract

O contrato `CivicRegistry.sol` é um registro simples de hashes:

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

### Deploy do Contrato

1. **Compile** o contrato usando Remix, Hardhat ou Foundry
2. **Deploy** na rede Polygon Amoy (testnet) ou Polygon mainnet
3. **Configure** o endereço no `.env`:
   ```
   CONTRACT_ADDRESS=0x...
   ```

## Configuração

### Variáveis de Ambiente

```bash
# Copie o template
cp .env.example .env

# Edite as variáveis
nano .env
```

**Variáveis obrigatórias para produção:**

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | URL do PostgreSQL |
| `WALLET_PRIVATE_KEY` | Private key da wallet (sem 0x) |
| `WALLET_ADDRESS` | Endereço da wallet |
| `CONTRACT_ADDRESS` | Endereço do contrato deployado |

### Wallet

O serviço usa uma wallet **custodial** (gerenciada pelo backend):

1. **Crie uma wallet** usando MetaMask ou qualquer outra ferramenta
2. **Exporte a private key** (nunca commite!)
3. **Deposite MATIC** para pagar gas:
   - Testnet (Amoy): Use faucet https://faucet.polygon.technology/
   - Mainnet: Compre MATIC e transfira

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

### Polygon (estimativas)
- **Gas por transação**: ~50,000-100,000 gas
- **Custo médio**: ~0.001-0.005 MATIC por registro
- **Mainnet**: ~$0.001-0.01 USD por registro

### Otimizações
- Batch de registros (futuro)
- Ajuste dinâmico de gas price
- Retry com backoff exponencial

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

## Roadmap

- [x] Endpoint `/blockas` básico
- [x] Suporte a 4 tipos de registro
- [x] Tracking local de transações
- [x] Verificação on-chain
- [ ] Batch de registros
- [ ] Webhook para notificação de confirmação
- [ ] Dashboard de monitoramento
- [ ] Suporte a múltiplas redes (Base, Arbitrum)

## Troubleshooting

### "Serviço não configurado"
Configure `WALLET_PRIVATE_KEY` e `CONTRACT_ADDRESS` no `.env`

### "Insufficient funds"
Deposite MATIC na wallet do backend

### "Transaction reverted"
Verifique se a wallet está autorizada no contrato (`addRegistrar`)

### "Hash já registrado"
O mesmo conjunto de dados já foi tokenizado anteriormente

## Contribuição

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## Licença

MIT License - Coral Platform
