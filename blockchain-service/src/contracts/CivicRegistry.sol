// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title CivicRegistry
 * @dev Contrato para registro de provas de existência de ações cívicas.
 *      Parte da plataforma Coral - Democracia Participativa.
 *
 * Este contrato permite:
 * - Registrar hashes de demandas, contas, apoios e dossiês
 * - Verificar a existência de registros
 * - Consultar informações de registros existentes
 *
 * IMPORTANTE: Nenhum dado pessoal é armazenado on-chain.
 * Apenas hashes SHA-256 são registrados para prova de existência.
 */
contract CivicRegistry {

    // Estrutura de um registro
    struct Record {
        bool exists;
        string tipo;          // demanda, conta, apoio, dossie
        string metadata;      // JSON com informações adicionais (não sensíveis)
        uint256 timestamp;    // Momento do registro
        address registrar;    // Endereço que registrou
    }

    // Mapeamento de hash -> registro
    mapping(bytes32 => Record) private records;

    // Contador de registros por tipo
    mapping(string => uint256) public recordCountByType;

    // Total de registros
    uint256 public totalRecords;

    // Endereço do administrador (pode ser alterado para multisig no futuro)
    address public admin;

    // Lista de registradores autorizados
    mapping(address => bool) public authorizedRegistrars;

    // Eventos
    event RecordRegistered(
        bytes32 indexed dataHash,
        address indexed registrar,
        string tipo,
        uint256 timestamp
    );

    event RegistrarAdded(address indexed registrar);
    event RegistrarRemoved(address indexed registrar);
    event AdminTransferred(address indexed oldAdmin, address indexed newAdmin);

    // Modificadores
    modifier onlyAdmin() {
        require(msg.sender == admin, "Apenas admin pode executar");
        _;
    }

    modifier onlyAuthorized() {
        require(
            authorizedRegistrars[msg.sender] || msg.sender == admin,
            "Nao autorizado a registrar"
        );
        _;
    }

    /**
     * @dev Construtor - define o deployer como admin e registrador autorizado
     */
    constructor() {
        admin = msg.sender;
        authorizedRegistrars[msg.sender] = true;
    }

    /**
     * @dev Registra um novo hash na blockchain
     * @param _dataHash Hash SHA-256 dos dados (convertido para bytes32)
     * @param _tipo Tipo de registro (demanda, conta, apoio, dossie)
     * @param _metadata JSON string com metadados não sensíveis
     * @return recordId Número sequencial do registro
     */
    function registerRecord(
        bytes32 _dataHash,
        string calldata _tipo,
        string calldata _metadata
    ) external onlyAuthorized returns (uint256 recordId) {
        require(_dataHash != bytes32(0), "Hash invalido");
        require(!records[_dataHash].exists, "Hash ja registrado");
        require(bytes(_tipo).length > 0, "Tipo obrigatorio");

        records[_dataHash] = Record({
            exists: true,
            tipo: _tipo,
            metadata: _metadata,
            timestamp: block.timestamp,
            registrar: msg.sender
        });

        totalRecords++;
        recordCountByType[_tipo]++;
        recordId = totalRecords;

        emit RecordRegistered(_dataHash, msg.sender, _tipo, block.timestamp);

        return recordId;
    }

    /**
     * @dev Verifica se um hash está registrado
     * @param _dataHash Hash a verificar
     * @return bool True se existe
     */
    function verifyRecord(bytes32 _dataHash) external view returns (bool) {
        return records[_dataHash].exists;
    }

    /**
     * @dev Consulta informações de um registro
     * @param _dataHash Hash do registro
     * @return exists Se o registro existe
     * @return tipo Tipo do registro
     * @return timestamp Momento do registro
     * @return registrar Endereço que registrou
     */
    function getRecord(bytes32 _dataHash) external view returns (
        bool exists,
        string memory tipo,
        uint256 timestamp,
        address registrar
    ) {
        Record storage record = records[_dataHash];
        return (
            record.exists,
            record.tipo,
            record.timestamp,
            record.registrar
        );
    }

    /**
     * @dev Consulta registro completo incluindo metadata
     * @param _dataHash Hash do registro
     */
    function getRecordFull(bytes32 _dataHash) external view returns (
        bool exists,
        string memory tipo,
        string memory metadata,
        uint256 timestamp,
        address registrar
    ) {
        Record storage record = records[_dataHash];
        return (
            record.exists,
            record.tipo,
            record.metadata,
            record.timestamp,
            record.registrar
        );
    }

    // === Funções Administrativas ===

    /**
     * @dev Adiciona um novo registrador autorizado
     * @param _registrar Endereço a autorizar
     */
    function addRegistrar(address _registrar) external onlyAdmin {
        require(_registrar != address(0), "Endereco invalido");
        require(!authorizedRegistrars[_registrar], "Ja autorizado");

        authorizedRegistrars[_registrar] = true;
        emit RegistrarAdded(_registrar);
    }

    /**
     * @dev Remove um registrador autorizado
     * @param _registrar Endereço a remover
     */
    function removeRegistrar(address _registrar) external onlyAdmin {
        require(authorizedRegistrars[_registrar], "Nao autorizado");
        require(_registrar != admin, "Nao pode remover admin");

        authorizedRegistrars[_registrar] = false;
        emit RegistrarRemoved(_registrar);
    }

    /**
     * @dev Transfere administração do contrato
     * @param _newAdmin Novo endereço admin
     */
    function transferAdmin(address _newAdmin) external onlyAdmin {
        require(_newAdmin != address(0), "Endereco invalido");

        address oldAdmin = admin;
        admin = _newAdmin;
        authorizedRegistrars[_newAdmin] = true;

        emit AdminTransferred(oldAdmin, _newAdmin);
    }

    /**
     * @dev Verifica se um endereço é registrador autorizado
     * @param _address Endereço a verificar
     */
    function isAuthorized(address _address) external view returns (bool) {
        return authorizedRegistrars[_address] || _address == admin;
    }
}
