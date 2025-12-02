"""
Serviço de busca de leis vigentes usando Google Gemini
Utiliza prompt engineering avançado para identificar leis que já garantem direitos
"""

import logging
from typing import Optional, Dict, List
import google.generativeai as genai
from src.core.config import settings

logger = logging.getLogger(__name__)


class LawSearchService:
    """Busca e explica leis vigentes usando Gemini"""
    
    # Base de conhecimento local para fallback (casos mais comuns)
    COMMON_LAWS = {
        'cinema_lanche': {
            'keywords': ['cinema', 'lanche', 'comida', 'entrada', 'pipoca', 'refrigerante'],
            'law': {
                'name': 'Código de Defesa do Consumidor (Lei 8.078/1990)',
                'article': 'Art. 39, inciso IX',
                'scope': 'federal',
                'simple_explanation': 'A lei proíbe que estabelecimentos comerciais OBRIGUEM você a comprar produtos deles como condição para usar o serviço. O cinema não pode te forçar a comprar a pipoca deles para assistir o filme. Você tem o direito de levar seu próprio lanche.',
                'how_to_use': 'Você pode exigir sua entrada mesmo com lanche próprio. Se negarem, peça o nome do responsável e registre uma reclamação no Procon. Tire foto/vídeo se possível.',
                'where_to_complain': 'Procon (www.procon.sp.gov.br ou app Procon SP), Reclame Aqui, ou Juizado Especial Cível (causas até 20 salários mínimos não precisam de advogado)'
            }
        },
        'taxa_servico': {
            'keywords': ['gorjeta', 'taxa', 'serviço', '10%', 'obrigatória', 'restaurante'],
            'law': {
                'name': 'Código de Defesa do Consumidor (Lei 8.078/1990)',
                'article': 'Art. 39, inciso I',
                'scope': 'federal',
                'simple_explanation': 'A gorjeta (ou taxa de serviço) de 10% NÃO é obrigatória no Brasil. O estabelecimento pode sugerir, mas você tem o direito de recusar ou pagar menos. Ninguém pode te forçar a pagar.',
                'how_to_use': 'Peça para retirar a taxa da conta. Se o garçom insistir, chame o gerente. Você pode pagar apenas o valor da comida. Se houver cobrança forçada, denuncie ao Procon.',
                'where_to_complain': 'Procon, Reclame Aqui, ou diretamente no Ministério Público (MP)'
            }
        },
        'falta_medico_ubs': {
            'keywords': ['médico', 'ubs', 'posto', 'saúde', 'sus', 'atendimento'],
            'law': {
                'name': 'Constituição Federal (1988)',
                'article': 'Art. 196',
                'scope': 'federal',
                'simple_explanation': 'A Constituição garante que a SAÚDE é um direito de todos e dever do Estado. Isso significa que o governo (municipal, estadual ou federal) é OBRIGADO a oferecer atendimento médico gratuito para você.',
                'how_to_use': 'Registre uma reclamação formal na ouvidoria da Secretaria Municipal de Saúde. Se não resolver, procure a Defensoria Pública (gratuita) para entrar com ação contra o município exigindo o atendimento.',
                'where_to_complain': 'Ouvidoria do SUS (136 ou disque136.saude.gov.br), Ministério Público, Defensoria Pública (atendimento gratuito), Conselho Municipal de Saúde'
            }
        }
    }
    
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        # Usar gemini-2.0-flash-lite (mais rápido e leve)
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
    
    async def search_existing_laws(
        self,
        user_problem: str,
        theme: str,
        location: Optional[Dict] = None
    ) -> Dict:
        """
        Busca leis vigentes que já garantem o direito mencionado
        
        Args:
            user_problem: Descrição do problema do usuário
            theme: Tema classificado (consumidor, saúde, educação, etc.)
            location: Localização (para leis municipais/estaduais)
        
        Returns:
            dict: {
                'found': bool,
                'laws': [
                    {
                        'name': str,
                        'article': str,
                        'scope': str (federal/estadual/municipal),
                        'simple_explanation': str,
                        'how_to_use': str,
                        'where_to_complain': str
                    }
                ]
            }
        """
        try:
            # TENTATIVA 1: Buscar com Gemini
            prompt = self._build_search_prompt(user_problem, theme, location)
            response = await self._call_gemini(prompt)
            result = self._parse_gemini_response(response)
            
            logger.info(f"✅ Law search complete (Gemini): {len(result['laws'])} laws found")
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Gemini search failed: {e}. Trying local fallback...")
            
            # TENTATIVA 2: Fallback para base local
            result = self._search_local_knowledge(user_problem)
            
            if result['found']:
                logger.info(f"✅ Law search complete (Local): {len(result['laws'])} laws found")
            else:
                logger.info(f"❌ No laws found in local knowledge base")
            
            return result
    
    def _search_local_knowledge(self, user_problem: str) -> Dict:
        """
        Busca na base de conhecimento local (fallback quando Gemini falha)
        
        Usa matching simples de keywords
        """
        user_text_lower = user_problem.lower()
        
        # Buscar em cada caso comum
        for case_id, case_data in self.COMMON_LAWS.items():
            keywords = case_data['keywords']
            
            # Contar quantas keywords aparecem no texto
            matches = sum(1 for kw in keywords if kw in user_text_lower)
            
            # Se pelo menos 2 keywords, considera match
            if matches >= 2:
                logger.info(f"✅ Matched local case: {case_id} ({matches} keywords)")
                return {
                    'found': True,
                    'laws': [case_data['law']]
                }
        
        # Nenhum match
        return {'found': False, 'laws': []}
    
    def _build_search_prompt(
        self,
        user_problem: str,
        theme: str,
        location: Optional[Dict]
    ) -> str:
        """
        Constrói prompt usando técnicas avançadas:
        - Chain of Thought (CoT)
        - Few-Shot Learning
        - Role Prompting
        - Structured Output
        """
        
        city = location.get('city', 'não especificada') if location else 'não especificada'
        state = location.get('state', 'não especificado') if location else 'não especificado'
        
        prompt = f"""Você é um assistente jurídico especializado em **direitos do consumidor e legislação brasileira**.

**CONTEXTO:**
Um cidadão relatou o seguinte problema:
"{user_problem}"

Tema identificado: {theme}
Localização: {city}, {state}

**SUA MISSÃO:**
Identificar se **JÁ EXISTE UMA LEI VIGENTE** no Brasil que garanta o direito mencionado ou proíba a prática relatada.

**INSTRUÇÕES (Chain of Thought):**

1. **ANÁLISE DO PROBLEMA:**
   - Qual é o direito sendo violado?
   - Qual prática abusiva está ocorrendo?
   - Qual bem jurídico está em questão? (consumidor, saúde, educação, etc.)

2. **BUSCA EM SUA BASE DE CONHECIMENTO:**
   Verifique nestas fontes (em ordem de prioridade):
   
   a) **Constituição Federal (1988)**
      - Direitos fundamentais (Art. 5º, 6º, etc.)
      - Defesa do consumidor (Art. 5º, XXXII)
   
   b) **Código de Defesa do Consumidor (Lei 8.078/1990)**
      - Direitos básicos do consumidor
      - Práticas abusivas (Art. 39)
      - Cláusulas abusivas (Art. 51)
   
   c) **Códigos específicos:**
      - Código Civil (Lei 10.406/2002)
      - Estatuto da Criança e Adolescente (Lei 8.069/1990)
      - Estatuto do Idoso (Lei 10.741/2003)
      - Lei de Acessibilidade (Lei 13.146/2015)
   
   d) **Leis estaduais e municipais:**
      - Considere a localização: {city}, {state}
      - Leis de defesa do consumidor estaduais
      - Códigos de posturas municipais

3. **CRITÉRIO DE RELEVÂNCIA:**
   - A lei **GARANTE EXPLICITAMENTE** o direito mencionado? OU
   - A lei **PROÍBE EXPLICITAMENTE** a prática relatada?
   
   **NÃO INVENTE:** Se não tiver certeza, responda "NAO_ENCONTRADO".

4. **FORMATO DE RESPOSTA (JSON ESTRUTURADO):**

Se encontrar lei(is) relevante(s):
```json
{{
  "found": true,
  "laws": [
    {{
      "name": "Nome completo da lei (ex: Código de Defesa do Consumidor)",
      "article": "Artigo específico (ex: Art. 39, inciso IX)",
      "scope": "federal|estadual|municipal",
      "simple_explanation": "Explicação em linguagem SIMPLES do que a lei diz (máximo 100 palavras, como se explicasse para uma criança de 12 anos)",
      "how_to_use": "Como o cidadão pode USAR essa lei na prática? (máximo 80 palavras)",
      "where_to_complain": "Onde denunciar/reclamar? (Procon, Ministério Público, ouvidoria, etc.)"
    }}
  ]
}}
```

Se NÃO encontrar nenhuma lei relevante:
```json
{{
  "found": false,
  "laws": []
}}
```

**EXEMPLOS (Few-Shot Learning):**

**Exemplo 1:**
Problema: "O cinema não deixou eu entrar com meu lanche, mas eles vendem comida lá dentro"
Resposta:
```json
{{
  "found": true,
  "laws": [
    {{
      "name": "Código de Defesa do Consumidor (Lei 8.078/1990)",
      "article": "Art. 39, inciso IX",
      "scope": "federal",
      "simple_explanation": "A lei proíbe que estabelecimentos comerciais OBRIGUEM você a comprar produtos deles como condição para usar o serviço. O cinema não pode te forçar a comprar a pipoca deles para assistir o filme. Você tem o direito de levar seu próprio lanche.",
      "how_to_use": "Você pode exigir sua entrada mesmo com lanche próprio. Se negarem, peça o nome do responsável e registre uma reclamação no Procon. Tire foto/vídeo se possível.",
      "where_to_complain": "Procon (www.procon.sp.gov.br ou app Procon SP), Reclame Aqui, ou Juizado Especial Cível (causas até 20 salários mínimos não precisam de advogado)"
    }}
  ]
}}
```

**Exemplo 2:**
Problema: "O restaurante cobrou taxa de serviço obrigatória de 10%"
Resposta:
```json
{{
  "found": true,
  "laws": [
    {{
      "name": "Código de Defesa do Consumidor (Lei 8.078/1990)",
      "article": "Art. 39, inciso I",
      "scope": "federal",
      "simple_explanation": "A gorjeta (ou taxa de serviço) de 10% NÃO é obrigatória no Brasil. O estabelecimento pode sugerir, mas você tem o direito de recusar ou pagar menos. Ninguém pode te forçar a pagar.",
      "how_to_use": "Peça para retirar a taxa da conta. Se o garçom insistir, chame o gerente. Você pode pagar apenas o valor da comida. Se houver cobrança forçada, denuncie ao Procon.",
      "where_to_complain": "Procon, Reclame Aqui, ou diretamente no Ministério Público (MP)"
    }}
  ]
}}
```

**Exemplo 3:**
Problema: "Falta médico na UBS do meu bairro há 3 meses"
Resposta:
```json
{{
  "found": true,
  "laws": [
    {{
      "name": "Constituição Federal (1988)",
      "article": "Art. 196",
      "scope": "federal",
      "simple_explanation": "A Constituição garante que a SAÚDE é um direito de todos e dever do Estado. Isso significa que o governo (municipal, estadual ou federal) é OBRIGADO a oferecer atendimento médico gratuito para você.",
      "how_to_use": "Registre uma reclamação formal na ouvidoria da Secretaria Municipal de Saúde. Se não resolver, procure a Defensoria Pública (gratuita) para entrar com ação contra o município exigindo o atendimento.",
      "where_to_complain": "Ouvidoria do SUS (136 ou disque136.saude.gov.br), Ministério Público, Defensoria Pública (atendimento gratuito), Conselho Municipal de Saúde"
    }}
  ]
}}
```

**AGORA, ANALISE O PROBLEMA DO CIDADÃO E RESPONDA:**

IMPORTANTE: 
- Responda APENAS com o JSON válido
- NÃO adicione texto antes ou depois do JSON
- Se não encontrar lei relevante, retorne {{"found": false, "laws": []}}
- Seja PRECISO e PRÁTICO nas explicações
"""
        
        return prompt
    
    async def _call_gemini(self, prompt: str) -> str:
        """Chama Gemini com configurações otimizadas e retry"""
        import time
        from google.api_core.exceptions import ResourceExhausted
        
        max_retries = 2
        retry_delay = 2  # segundos
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,  # Baixa para respostas mais determinísticas
                        top_p=0.8,
                        top_k=40,
                        max_output_tokens=2048,
                    ),
                )
                
                return response.text
                
            except ResourceExhausted as e:
                logger.warning(f"Quota exceeded on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Max retries reached. Quota exceeded: {e}")
                    raise
            except Exception as e:
                logger.error(f"Error calling Gemini: {e}")
                raise
    
    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse da resposta JSON do Gemini"""
        try:
            import json
            import re
            
            # Remover markdown code blocks se existirem
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                # Extrair JSON de dentro do code block
                match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)
                else:
                    # Tentar remover apenas os backticks
                    cleaned = cleaned.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            result = json.loads(cleaned)
            
            # Validação
            if not isinstance(result, dict):
                raise ValueError("Response is not a dict")
            
            if 'found' not in result:
                raise ValueError("Missing 'found' field")
            
            if result['found'] and 'laws' not in result:
                raise ValueError("Missing 'laws' field when found=true")
            
            # Garantir estrutura padrão
            if not result['found']:
                result['laws'] = []
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return {'found': False, 'laws': []}
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return {'found': False, 'laws': []}


# Instância global
law_search_service = LawSearchService()
