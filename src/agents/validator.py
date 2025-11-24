import re
from typing import Dict, List

class DemandValidatorAgent:
    """Valida o conteúdo final de uma demanda para garantir que informações essenciais estejam presentes.
    Regras atuais:
    - Temas que exigem localização específica (ex: iluminação, buraco, zeladoria) devem conter referência a via/ponto (Rua, Avenida, Praça, Escola, etc.).
    - Detecta placeholders como [Nome da Rua] e marca como faltante.
    """

    LOCATION_THEMES = {"iluminacao", "buraco", "zeladoria", "transporte"}
    STREET_PATTERNS = [r"\bRua\b", r"\bAv\.?\b", r"\bAvenida\b", r"\bTravessa\b", r"\bEstrada\b", r"\bPraça\b", r"\bRodovia\b", r"\bEscola\b", r"\bHospital\b"]

    def evaluate(self, title: Dict, description: str, theme: str, collected_data: Dict, full_text: str) -> Dict:
        missing: List[str] = []

        normalized_theme = (theme or "").lower()
        needs_location = normalized_theme in self.LOCATION_THEMES

        # Placeholder detection
        if "[Nome da Rua]" in title or "[Nome da Rua]" in description:
            missing.append("location_entity")
        else:
            if needs_location:
                # Check street/ponto tokens in title/description/full_text
                haystack = " ".join([title or "", description or "", full_text or ""]).lower()
                found_token = any(re.search(pat, haystack, flags=re.IGNORECASE) for pat in self.STREET_PATTERNS)
                if not found_token:
                    # If collected_data location seems generic (only neighborhood) we still mark missing
                    loc_val = (collected_data.get("location") or "").lower()
                    # Heurística: se não tem número ou palavra de via
                    if not any(re.search(pat, loc_val, flags=re.IGNORECASE) for pat in self.STREET_PATTERNS):
                        missing.append("location_entity")

        return {"missing_fields": missing}
