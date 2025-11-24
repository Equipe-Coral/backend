"""
Serviço de hashing para geração de hashes SHA-256.
Responsável por criar hashes dos dados antes de enviar para blockchain.
"""

import hashlib
import json
from typing import Any, Dict

from src.config import settings
from src.models.schemas import (
    TipoRegistro,
    DemandaPayload,
    ContaPayload,
    ApoioPayload,
    DossiePayload,
)


class HasherService:
    """
    Serviço para geração de hashes SHA-256.
    Garante que dados sensíveis (como telefone) sejam hasheados antes de ir para blockchain.
    """

    def __init__(self, salt: str = None):
        self.salt = salt or settings.CIVIC_ID_SALT

    def _sha256(self, data: str) -> str:
        """Gera hash SHA-256 de uma string."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def hash_phone(self, phone: str) -> str:
        """
        Gera hash do telefone com salt.
        Compatível com o civic_id do backend principal.
        """
        return self._sha256(f"{phone}{self.salt}")

    def hash_dict(self, data: Dict[str, Any]) -> str:
        """
        Gera hash de um dicionário.
        Serializa para JSON com ordenação de chaves para consistência.
        """
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return self._sha256(json_str)

    def prepare_demanda(self, payload: DemandaPayload) -> Dict[str, Any]:
        """
        Prepara dados de demanda para blockchain.
        Hasheia o telefone do criador para privacidade.
        """
        return {
            "type": TipoRegistro.DEMANDA.value,
            "demand_id": payload.demand_id,
            "title": payload.title,
            "creator_hash": self.hash_phone(payload.creator_phone),
            "theme": payload.theme,
            "scope_level": payload.scope_level,
            "timestamp": self._get_timestamp(),
        }

    def prepare_conta(self, payload: ContaPayload) -> Dict[str, Any]:
        """
        Prepara dados de conta/ID Cívico para blockchain.
        Hasheia o telefone para criar o ID cívico.
        """
        return {
            "type": TipoRegistro.CONTA.value,
            "civic_id": self.hash_phone(payload.phone),
            "user_id": payload.user_id,
            "timestamp": self._get_timestamp(),
        }

    def prepare_apoio(self, payload: ApoioPayload) -> Dict[str, Any]:
        """
        Prepara dados de apoio para blockchain.
        Hasheia o telefone do apoiador.
        """
        return {
            "type": TipoRegistro.APOIO.value,
            "demand_id": payload.demand_id,
            "supporter_hash": self.hash_phone(payload.supporter_phone),
            "timestamp": self._get_timestamp(),
        }

    def prepare_dossie(self, payload: DossiePayload) -> Dict[str, Any]:
        """
        Prepara dados de dossiê para blockchain.
        O file_hash já vem pronto do chamador.
        """
        return {
            "type": TipoRegistro.DOSSIE.value,
            "demand_id": payload.demand_id,
            "file_hash": payload.file_hash,
            "file_name": payload.file_name,
            "file_type": payload.file_type,
            "timestamp": self._get_timestamp(),
        }

    def prepare_and_hash(
        self, tipo: TipoRegistro, payload: Any
    ) -> tuple[Dict[str, Any], str]:
        """
        Prepara os dados e gera o hash final.
        Retorna: (dados_preparados, hash_dos_dados)
        """
        if tipo == TipoRegistro.DEMANDA:
            prepared = self.prepare_demanda(payload)
        elif tipo == TipoRegistro.CONTA:
            prepared = self.prepare_conta(payload)
        elif tipo == TipoRegistro.APOIO:
            prepared = self.prepare_apoio(payload)
        elif tipo == TipoRegistro.DOSSIE:
            prepared = self.prepare_dossie(payload)
        else:
            raise ValueError(f"Tipo de registro não suportado: {tipo}")

        data_hash = self.hash_dict(prepared)
        return prepared, data_hash

    def _get_timestamp(self) -> int:
        """Retorna timestamp Unix atual."""
        import time
        return int(time.time())
