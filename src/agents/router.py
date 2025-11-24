from src.core.gemini import gemini_client
import logging
import json
import re

logger = logging.getLogger(__name__)

class RouterAgent:
    def __init__(self):
        self.client = gemini_client

    async def classify_and_extract(self, text: str) -> dict:
        """
        Classifica mensagem do usuário
        Retorna classificação com fallback heurístico se API falhar
        """
        
        # FALLBACK HEURÍSTICO (antes de chamar API)
        heuristic_result = self._heuristic_classification(text)
        
        prompt = f"""Você é um assistente de classificação cívica no Brasil.

Analise a mensagem do cidadão e retorne APENAS um JSON válido (sem markdown, sem explicações):

{{
  "classification": "ONBOARDING" | "DEMANDA" | "DUVIDA" | "OUTRO",
  "theme": "saude" | "transporte" | "educacao" | "seguranca" | "meio_ambiente" | "zeladoria" | "animais" | "consumidor" | "outros",
  "location_mentioned": true | false,
  "location_text": "texto extraído" ou null,
  "urgency": "critica" | "alta" | "media" | "baixa",
  "keywords": ["palavra1", "palavra2"],
  "confidence": 0.0 a 1.0
}}

**REGRAS DE CLASSIFICAÇÃO:**

ONBOARDING (saudações, mensagens vagas sem problema concreto):
- "oi", "olá", "bom dia", "opa"
- Perguntas genéricas: "o que você faz?", "pode me ajudar?"

DEMANDA (problema concreto OU intenção explícita de criar registro):
- Intenção direta: "criar uma demanda", "nova demanda", "quero reclamar", "registrar ocorrência", "abrir chamado"
- Reclamações sobre serviços públicos: "buraco na rua", "lixo acumulado", "falta médico"
- Problemas de infraestrutura: "iluminação", "asfalto", "calçada"
- Transporte: "ônibus atrasado", "linha cancelada"
- Sugestões de melhoria: "quero uma ciclovia", "falta creche"

DUVIDA (pergunta sobre legislação, processo, direitos):
- "o que é o PL...", "como funciona...", "existe lei sobre..."
- "quem é meu vereador", "como faço para..."

OUTRO (tudo que não se encaixa):
- Elogios, agradecimentos
- Assuntos não cívicos
- Spam, propaganda

**TEMAS:**
- saude: UBS, hospital, médico, remédio, consulta, dengue
- transporte: ônibus, metrô, trem, ciclovia, rua, trânsito, multa
- educacao: escola, creche, professor, merenda, aula
- seguranca: polícia, violência, roubo, guarda, assalto
- meio_ambiente: lixo, poluição, árvore, parque, reciclagem, enchente
- zeladoria: buraco, iluminação, calçada, limpeza, manutenção, obra
- animais: cachorro, gato, pet, animal de estimação, proteção animal, maus-tratos
- consumidor: restaurante, loja, comércio, estabelecimento, direito do consumidor
- outros: se não se encaixa acima

**URGÊNCIA:**
- critica: risco de vida, violação grave de direitos
- alta: problema persistente, afeta muitas pessoas
- media: problema localizado, sem risco imediato
- baixa: sugestão, dúvida, informação

Mensagem do cidadão: "{text}"

Responda APENAS com o JSON, sem texto adicional.
"""
        
        try:
            response_text = await self.client.generate_content(prompt)
            result = self.client.parse_json(response_text)
            
            if not self._is_valid_result(result):
                logger.warning(f"Invalid classification from Gemini: {result}")
                return heuristic_result
                
            logger.info(f"Classification: {result}")
            return result
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Resource exhausted" in error_msg:
                logger.warning(f"⚠️ Gemini rate limit hit. Using heuristic classification.")
                return heuristic_result
            
            logger.error(f"Error in RouterAgent: {e}")
            return heuristic_result

    def _heuristic_classification(self, text: str) -> dict:
        """
        Classificação baseada em regras heurísticas simples
        Usado como fallback quando API falha
        """
        text_lower = text.lower().strip()
        
        # 1. DEMANDA EXPLÍCITA (Novo)
        explicit_demand_triggers = [
            'criar demanda', 'criar uma demanda', 'nova demanda', 
            'fazer reclamação', 'fazer reclamacao', 'quero reclamar',
            'registrar problema', 'abrir chamado', 'denunciar'
        ]
        if any(trigger in text_lower for trigger in explicit_demand_triggers):
            return {
                "classification": "DEMANDA",
                "theme": "outros", # Tema será definido na entrevista
                "location_mentioned": False,
                "location_text": None,
                "urgency": "media",
                "keywords": ["nova demanda"],
                "confidence": 0.95
            }

        # Palavras-chave por categoria
        onboarding_words = ['oi', 'olá', 'ola', 'bom dia', 'boa tarde', 'boa noite', 
                           'opa', 'e aí', 'e ai', 'oie', 'olar']
        
        demanda_keywords = {
            'zeladoria': ['buraco', 'iluminação', 'iluminacao', 'poste', 'calçada', 'calcada', 
                         'asfalto', 'pavimentação', 'pavimentacao', 'mato', 'entulho'],
            'transporte': ['ônibus', 'onibus', 'linha', 'metrô', 'metro', 'trem', 'ciclovia', 
                          'trânsito', 'transito', 'rua', 'avenida', 'semáforo', 'sinal'],
            'saude': ['ubs', 'hospital', 'médico', 'medico', 'consulta', 'remédio', 'remedio', 
                     'saúde', 'saude', 'posto de saude', 'atendimento'],
            'educacao': ['escola', 'creche', 'professor', 'merenda', 'educação', 'educacao'],
            'seguranca': ['polícia', 'policia', 'violência', 'violencia', 'roubo', 'assalto', 
                         'segurança', 'seguranca', 'guarda'],
            'meio_ambiente': ['lixo', 'poluição', 'poluicao', 'árvore', 'arvore', 'parque', 
                             'reciclagem', 'coleta']
        }
        
        duvida_words = ['o que é', 'o que e', 'como funciona', 'existe lei', 'pl ',
                       'projeto de lei', 'quem é', 'quem e', 'vereador', 'deputado',
                       'como faço', 'como faco', 'posso', 'tenho direito', 'o que eu faço',
                       'pode', 'proibiram', 'lei sobre']
        
        # 2. ONBOARDING (saudações simples)
        if any(word in text_lower for word in onboarding_words) and len(text_lower) < 30:
            return {
                "classification": "ONBOARDING",
                "theme": "outros",
                "location_mentioned": False,
                "location_text": None,
                "urgency": "baixa",
                "keywords": [],
                "confidence": 0.8
            }
        
        # 3. DÚVIDA (perguntas)
        if any(word in text_lower for word in duvida_words):
            return {
                "classification": "DUVIDA",
                "theme": "outros",
                "location_mentioned": False,
                "location_text": None,
                "urgency": "baixa",
                "keywords": [word for word in duvida_words if word in text_lower],
                "confidence": 0.7
            }
        
        # 4. DEMANDA (problema concreto)
        for theme, keywords in demanda_keywords.items():
            matched_keywords = [kw for kw in keywords if kw in text_lower]
            if matched_keywords:
                # Detectar localização básica
                location_patterns = [
                    r'(rua|avenida|av\.?|travessa)\s+[\w\s]+',
                    r'(bairro|região|região)\s+[\w\s]+',
                    r'(perto|próximo|proximo)\s+(da|do|de)\s+[\w\s]+'
                ]
                location_text = None
                location_mentioned = False
                
                for pattern in location_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        location_text = match.group(0)
                        location_mentioned = True
                        break
                
                urgency = "media"
                if any(w in text_lower for w in ['urgente', 'grave', 'perigo', 'risco']):
                    urgency = "alta"
                if any(w in text_lower for w in ['morte', 'ferido', 'acidente']):
                    urgency = "critica"
                
                return {
                    "classification": "DEMANDA",
                    "theme": theme,
                    "location_mentioned": location_mentioned,
                    "location_text": location_text,
                    "urgency": urgency,
                    "keywords": matched_keywords,
                    "confidence": 0.75
                }
        
        # 5. OUTRO (fallback)
        return {
            "classification": "OUTRO",
            "theme": "outros",
            "location_mentioned": False,
            "location_text": None,
            "urgency": "baixa",
            "keywords": [],
            "confidence": 0.5
        }

    def _is_valid_result(self, result: dict) -> bool:
        required_keys = ['classification', 'theme', 'location_mentioned', 
                        'urgency', 'keywords', 'confidence']
        
        if not all(key in result for key in required_keys):
            return False
        
        valid_classifications = ['ONBOARDING', 'DEMANDA', 'DUVIDA', 'OUTRO']
        if result['classification'] not in valid_classifications:
            return False
        
        return True