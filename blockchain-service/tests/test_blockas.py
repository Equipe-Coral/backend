"""
Testes para o endpoint /blockas do Blockchain Service.
"""

import pytest
from fastapi.testclient import TestClient

# Importações para mock
import sys
from unittest.mock import MagicMock, patch

# Mock do database antes de importar o app
sys.modules['src.models.database'] = MagicMock()

from src.services.hasher import HasherService
from src.models.schemas import (
    TipoRegistro,
    DemandaPayload,
    ContaPayload,
    ApoioPayload,
    DossiePayload,
)


class TestHasherService:
    """Testes para o serviço de hashing."""

    def setup_method(self):
        self.hasher = HasherService(salt="test_salt")

    def test_hash_phone(self):
        """Testa hashing de telefone."""
        phone = "+5511999999999"
        hash1 = self.hasher.hash_phone(phone)
        hash2 = self.hasher.hash_phone(phone)

        # Mesmo telefone deve gerar mesmo hash
        assert hash1 == hash2
        # Hash deve ter 64 caracteres (SHA-256 hex)
        assert len(hash1) == 64
        # Hash não deve conter o telefone original
        assert phone not in hash1

    def test_hash_phone_different_phones(self):
        """Telefones diferentes devem gerar hashes diferentes."""
        hash1 = self.hasher.hash_phone("+5511999999999")
        hash2 = self.hasher.hash_phone("+5511888888888")

        assert hash1 != hash2

    def test_hash_dict(self):
        """Testa hashing de dicionário."""
        data = {"key": "value", "number": 123}
        hash1 = self.hasher.hash_dict(data)

        # Hash deve ter 64 caracteres
        assert len(hash1) == 64

        # Ordem das chaves não deve afetar o hash
        data2 = {"number": 123, "key": "value"}
        hash2 = self.hasher.hash_dict(data2)
        assert hash1 == hash2

    def test_prepare_demanda(self):
        """Testa preparação de dados de demanda."""
        payload = DemandaPayload(
            demand_id="123",
            title="Test Demand",
            creator_phone="+5511999999999",
            theme="zeladoria",
            scope_level=1
        )

        prepared = self.hasher.prepare_demanda(payload)

        assert prepared["type"] == "demanda"
        assert prepared["demand_id"] == "123"
        assert prepared["title"] == "Test Demand"
        assert "creator_hash" in prepared
        assert "+5511999999999" not in str(prepared)  # Telefone não deve aparecer
        assert "timestamp" in prepared

    def test_prepare_conta(self):
        """Testa preparação de dados de conta."""
        payload = ContaPayload(
            phone="+5511999999999",
            user_id="user-123"
        )

        prepared = self.hasher.prepare_conta(payload)

        assert prepared["type"] == "conta"
        assert "civic_id" in prepared
        assert prepared["user_id"] == "user-123"
        assert "+5511999999999" not in str(prepared)

    def test_prepare_apoio(self):
        """Testa preparação de dados de apoio."""
        payload = ApoioPayload(
            demand_id="demand-123",
            supporter_phone="+5511999999999"
        )

        prepared = self.hasher.prepare_apoio(payload)

        assert prepared["type"] == "apoio"
        assert prepared["demand_id"] == "demand-123"
        assert "supporter_hash" in prepared
        assert "+5511999999999" not in str(prepared)

    def test_prepare_dossie(self):
        """Testa preparação de dados de dossiê."""
        payload = DossiePayload(
            demand_id="demand-123",
            file_hash="abc123def456",
            file_name="documento.pdf",
            file_type="application/pdf"
        )

        prepared = self.hasher.prepare_dossie(payload)

        assert prepared["type"] == "dossie"
        assert prepared["demand_id"] == "demand-123"
        assert prepared["file_hash"] == "abc123def456"
        assert prepared["file_name"] == "documento.pdf"

    def test_prepare_and_hash(self):
        """Testa preparação e hashing completo."""
        payload = DemandaPayload(
            demand_id="123",
            title="Test",
            creator_phone="+5511999999999"
        )

        prepared, data_hash = self.hasher.prepare_and_hash(
            TipoRegistro.DEMANDA,
            payload
        )

        assert isinstance(prepared, dict)
        assert len(data_hash) == 64


class TestSchemas:
    """Testes para os schemas Pydantic."""

    def test_demanda_payload_required_fields(self):
        """Testa campos obrigatórios de DemandaPayload."""
        payload = DemandaPayload(
            demand_id="123",
            title="Test",
            creator_phone="+5511999999999"
        )

        assert payload.demand_id == "123"
        assert payload.title == "Test"
        assert payload.creator_phone == "+5511999999999"
        assert payload.description is None
        assert payload.theme is None

    def test_conta_payload(self):
        """Testa ContaPayload."""
        payload = ContaPayload(phone="+5511999999999")

        assert payload.phone == "+5511999999999"
        assert payload.user_id is None

    def test_tipo_registro_enum(self):
        """Testa enum TipoRegistro."""
        assert TipoRegistro.DEMANDA.value == "demanda"
        assert TipoRegistro.CONTA.value == "conta"
        assert TipoRegistro.APOIO.value == "apoio"
        assert TipoRegistro.DOSSIE.value == "dossie"


class TestPrivacyCompliance:
    """Testes para garantir compliance de privacidade."""

    def setup_method(self):
        self.hasher = HasherService(salt="privacy_test")

    def test_phone_never_in_prepared_data(self):
        """Garante que telefone nunca aparece nos dados preparados."""
        phones = [
            "+5511999999999",
            "11999999999",
            "+55 11 99999-9999"
        ]

        for phone in phones:
            # Demanda
            payload = DemandaPayload(
                demand_id="123",
                title="Test",
                creator_phone=phone
            )
            prepared = self.hasher.prepare_demanda(payload)
            assert phone not in str(prepared)

            # Conta
            payload = ContaPayload(phone=phone)
            prepared = self.hasher.prepare_conta(payload)
            assert phone not in str(prepared)

            # Apoio
            payload = ApoioPayload(demand_id="123", supporter_phone=phone)
            prepared = self.hasher.prepare_apoio(payload)
            assert phone not in str(prepared)

    def test_hash_is_deterministic(self):
        """Garante que o mesmo input sempre gera o mesmo hash."""
        payload = DemandaPayload(
            demand_id="123",
            title="Test",
            creator_phone="+5511999999999",
            theme="saude",
            scope_level=2
        )

        _, hash1 = self.hasher.prepare_and_hash(TipoRegistro.DEMANDA, payload)
        _, hash2 = self.hasher.prepare_and_hash(TipoRegistro.DEMANDA, payload)

        assert hash1 == hash2

    def test_different_data_different_hash(self):
        """Garante que dados diferentes geram hashes diferentes."""
        payload1 = DemandaPayload(
            demand_id="123",
            title="Test 1",
            creator_phone="+5511999999999"
        )
        payload2 = DemandaPayload(
            demand_id="123",
            title="Test 2",
            creator_phone="+5511999999999"
        )

        _, hash1 = self.hasher.prepare_and_hash(TipoRegistro.DEMANDA, payload1)
        _, hash2 = self.hasher.prepare_and_hash(TipoRegistro.DEMANDA, payload2)

        assert hash1 != hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
