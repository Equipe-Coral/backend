import logging
from src.core.gemini import gemini_client
from typing import List, Union

logger = logging.getLogger(__name__)

class ScribeAgent:
    """
    Agente Escriba (The Scribe):
    Responsável por traduzir relatos informais ("Cidadês") para linguagem 
    técnica e legislativa ("Juridiquês") de forma concisa e estruturada.
    """
    
    def __init__(self):
        self.client = gemini_client

    async def draft_legislative_idea(self, informal_texts: Union[str, List[str]]) -> dict:
        """
        Gera um rascunho de Ideia Legislativa (padrão e-Cidadania).
        Aceita um texto único ou uma lista de relatos.
        """
        # Se for lista, combina os textos
        if isinstance(informal_texts, list):
            combined_text = "\n---\n".join(informal_texts)
        else:
            combined_text = informal_texts

        prompt = f"""
        Você é um Assistente Legislativo Sênior especializado em redação parlamentar.
        
        TAREFA:
        Transforme o(s) relato(s) informal(is) abaixo em uma PROPOSTA LEGISLATIVA formal e concisa (Ideia Legislativa).
        
        DIRETRIZES:
        1. Use linguagem técnica, impessoal e culta (padrão norma culta).
        2. Seja CONCISO e direto.
        3. Identifique o problema central e proponha uma solução normativa.
        4. Evite emoções ou opiniões pessoais; foque nos fatos e na necessidade jurídica.
        5. Use verbos no infinitivo ou imperativo jurídico ("Institui", "Determina", "Altera").

        RELATO(S) INFORMAL(IS):
        "{combined_text}"

        RETORNE APENAS UM JSON (sem markdown):
        {{
            "title": "Título curto e oficial (ex: Altera a Lei X para...)",
            "problem": "Resumo técnico do problema (máx 2 frases)",
            "proposal": "Texto da proposta normativa (o que deve ser feito na lei)",
            "justification": "Argumento formal curto defendendo a proposta"
        }}
        """

        try:
            logger.info("✍️ Scribe drafting legislative idea...")
            response_text = await self.client.generate_content(prompt)
            return self.client.parse_json(response_text)
        except Exception as e:
            logger.error(f"❌ Error in ScribeAgent (legislative idea): {e}")
            return self._get_fallback_draft()

    async def draft_formal_demand(self, informal_text: str, scope_level: int) -> dict:
        """
        Gera uma descrição formal para demandas comunitárias ou ofícios (Nível 1 ou 2).
        Focado em zeladoria e serviços públicos.
        """
        
        scope_context = "Local/Bairro" if scope_level == 1 else "Municipal/Regional"

        prompt = f"""
        Você é um oficial administrativo redigindo uma solicitação formal.
        Escopo da demanda: {scope_context}

        TAREFA:
        Reescreva a reclamação abaixo como uma SOLICITAÇÃO FORMAL para um órgão público.

        DIRETRIZES:
        1. Remova gírias, palavrões e exclamações.
        2. Transforme em um texto objetivo e descritivo.
        3. Mantenha os detalhes técnicos (local, horário, números) se houver.
        4. O tom deve ser de requerimento administrativo.

        RECLAMAÇÃO ORIGINAL:
        "{informal_text}"

        RETORNE APENAS UM JSON (sem markdown):
        {{
            "formal_title": "Assunto técnico (ex: Requerimento de manutenção em via pública)",
            "formal_description": "Texto do corpo da solicitação, polido e pronto para envio."
        }}
        """

        try:
            logger.info("✍️ Scribe drafting formal demand...")
            response_text = await self.client.generate_content(prompt)
            return self.client.parse_json(response_text)
        except Exception as e:
            logger.error(f"❌ Error in ScribeAgent (formal demand): {e}")
            return {
                "formal_title": "Solicitação Administrativa",
                "formal_description": informal_text
            }

    async def draft_comment_for_pl(self, user_opinion: str, pl_title: str) -> dict:
        """
        Gera uma sugestão de comentário formal para o usuário postar em portais oficiais.
        """
        prompt = f"""
        O cidadão quer comentar sobre o Projeto de Lei: "{pl_title}".
        Opinião bruta do cidadão: "{user_opinion}"

        TAREFA:
        Reescreva essa opinião como um comentário construtivo e respeitoso, adequado para ser publicado no portal da Câmara/Senado.
        Mantenha o posicionamento (A favor/Contra), mas melhore a argumentação.

        RETORNE APENAS UM JSON:
        {{
            "position": "Favorável" ou "Contrário",
            "suggested_text": "Texto formal sugerido (máx 3 linhas)"
        }}
        """
        
        try:
            response_text = await self.client.generate_content(prompt)
            return self.client.parse_json(response_text)
        except Exception:
            return {"position": "Neutro", "suggested_text": user_opinion}

    def _get_fallback_draft(self):
        return {
            "title": "Proposta Legislativa",
            "problem": "Não foi possível processar o resumo técnico.",
            "proposal": "Recomenda-se revisão manual do relato.",
            "justification": "Erro na geração automática."
        }