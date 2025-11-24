import logging
from typing import Dict, List, Optional, Any
from src.core.gemini import gemini_client

logger = logging.getLogger(__name__)

class WriterAgent:
    """
    Agente Redator (The Voice):
    Responsável por gerar todas as respostas finais para o usuário.
    """

    def __init__(self):
        self.client = gemini_client
        
        # Persona e Diretrizes Globais
        self.system_prompt = """
        Você é o Coral, um assistente cívico brasileiro virtual.
        
        SUA PERSONALIDADE:
        - Amigável, empático, prestativo e otimista.
        - Usa linguagem simples e acessível ("Cidadês").
        - É politicamente neutro.
        - Focado em resolver problemas e organizar a ação coletiva.
        
        REGRAS DE FORMATAÇÃO (WHATSAPP):
        - Use *negrito* para destacar títulos.
        - Use emojis com moderação.
        - Nunca use Markdown de código (```).
        - Seja conciso.
        """

    async def _generate(self, instructions: str, context: Dict[str, Any] = None) -> str:
        context_str = str(context) if context else "Nenhum dado específico."
        prompt = f"{self.system_prompt}\nDADOS: {context_str}\nTAREFA: {instructions}\nGere APENAS a resposta."
        try:
            response = await self.client.generate_content(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"❌ Error in WriterAgent: {e}")
            return self._get_fallback_response(instructions)

    def _get_fallback_response(self, instructions: str) -> str:
        if "erro" in instructions.lower():
            return "Desculpe, tive um erro interno. Tente novamente mais tarde."
        return "Poderia repetir? Não entendi bem."

    # =========================================================================
    # MÉTODOS DO ONBOARDING
    # =========================================================================
    async def welcome_message(self, is_new_user: bool = True) -> str:
        instruction = "Boas-vindas a novo usuário (pedir local) OU usuário recorrente (perguntar como ajudar)."
        return await self._generate(instruction, {"is_new_user": is_new_user})

    async def ask_location_retry(self) -> str:
        return await self._generate("Localização não entendida. Pedir Bairro e Cidade novamente com exemplos.")

    async def confirm_location(self, location: Dict = None, is_correct: bool = True) -> str:
        if not is_correct:
            return await self._generate("Usuário disse algo confuso na confirmação. Pedir Sim ou Não.")
        return await self._generate("Confirmar localização encontrada (Bairro, Cidade).", {"location": location})

    async def onboarding_complete(self) -> str:
        return await self._generate("Cadastro concluído. Perguntar o que está acontecendo no bairro.")

    # =========================================================================
    # MÉTODOS DE DEMANDA E AÇÕES
    # =========================================================================
    async def confirm_demand_content(self, title, description, theme, scope_level, urgency) -> str:
        return await self._generate(
            "Resumir problema para confirmação (Título, Descrição, Tema). Pedir Sim/Não.",
            {"title": title, "desc": description, "theme": theme}
        )

    async def present_action_options(self, has_similar_demands: bool) -> str:
        return await self._generate(
            "Listar opções numeradas: 1. Criar Demanda, 2. Ideia Legislativa (ou Apoiar se houver similar), 3. Conversar.",
            {"has_similar": has_similar}
        )

    async def ask_problem_rephrase(self) -> str:
        return await self._generate("Usuário disse que entendi errado. Pedir para explicar o problema de novo com detalhes.")

    async def unclear_confirmation_request(self) -> str:
        return "Desculpe, não entendi. Por favor responda com *Sim* ou *Não*."

    async def show_similar_demands(self, demands: List[Dict]) -> str:
        return await self._generate(
            "Listar demandas similares encontradas. Pedir para escolher número para apoiar ou 'nova' para criar.",
            {"demands": demands}
        )

    async def legislative_idea_ready(self, draft: Dict) -> str:
        return await self._generate(
            "Apresentar texto da Ideia Legislativa gerada e instruir como postar no e-Cidadania.",
            {"draft": draft}
        )

    async def converse_only_message(self) -> str:
        return "Entendi! Estou aqui para conversar e tirar dúvidas. Sobre o que quer falar?"

    async def unclear_decision_request(self) -> str:
        return "Não entendi. Digite o número da opção desejada."

    async def demand_created(self, title, theme, scope_level, urgency, share_link, related_pls) -> str:
        return await self._generate(
            "Sucesso na criação da demanda. Incentivar compartilhamento. Mostrar PLs relacionados se houver.",
            {"title": title, "link": share_link, "pls": related_pls}
        )

    # =========================================================================
    # MÉTODOS DE DÚVIDAS (QUESTION HANDLER)
    # =========================================================================
    async def explain_pls_and_actions(self, theme: str, pls: List[Dict]) -> str:
        return await self._generate(
            "Explicar PLs encontrados sobre o tema. Listar opções de ação (Criar demanda, Apoiar existente).",
            {"theme": theme, "pls": pls}
        )

    # =========================================================================
    # MÉTODOS FALTANTES (QUE CAUSAVAM ERRO)
    # =========================================================================
    async def ask_confirmation_for_action(self, theme: str, reformulated_demand: str) -> str:
        return await self._generate(
            "Confirmar intenção de ação. Mostrar o tema e o texto reformulado. Pedir Sim/Não.",
            {"theme": theme, "reformulated": reformulated_demand}
        )

    async def demand_not_found(self) -> str:
        return "Desculpe, não consegui carregar os detalhes dessa demanda agora. Tente novamente."

    async def show_similar_demands_for_support(self, demands: List[Dict]) -> str:
        return await self.show_similar_demands(demands) # Reutiliza lógica

    async def unclear_action_choice(self, has_similar: bool) -> str:
        return await self._generate(
            "Usuário escolheu opção inválida. Listar opções válidas novamente (números).",
            {"has_similar": has_similar}
        )

    async def ask_for_new_demand_description(self) -> str:
        return "Entendido! Vamos criar uma nova. Por favor, descreva o problema ou ideia com detalhes."

    async def unclear_support_choice(self, num_options: int) -> str:
        return f"Opção inválida. Digite um número de 1 a {num_options}, ou 'nova'."

    async def demand_already_supported(self, title: str = None, current_count: int = None) -> str:
        return await self._generate(
            "Informar que usuário já apoia essa demanda. Mostrar total de apoios.",
            {"title": title, "count": current_count}
        )

    async def demand_supported_success(self, title: str, new_count: int) -> str:
        return await self._generate(
            "Sucesso ao apoiar demanda! Celebrar e mostrar novo total de apoios.",
            {"title": title, "count": new_count}
        )

    async def generic_error_response(self) -> str:
        return "Ops! Tive um erro interno ao processar seu pedido. Tente novamente em alguns instantes."

    async def empty_message_response(self, is_audio: bool) -> str:
        msg = "áudio vazio" if is_audio else "mensagem vazia"
        return f"Parece que recebi uma {msg}. Poderia enviar novamente?"

    async def ask_for_help_options(self) -> str:
        return await self._generate("Usuário enviou algo que não entendi (fora de contexto). Oferecer menu de ajuda (Demanda, Dúvida).")

    # =========================================================================
    # MÉTODOS DE ENTREVISTA (DEMAND BUILDER)
    # =========================================================================
    
    async def ask_for_more_details(self) -> str:
        return await self._generate(
            "O relato do usuário está muito curto. Peça gentilmente mais detalhes. Pergunte 'O que exatamente aconteceu?' ou 'Há quanto tempo isso ocorre?'"
        )

    async def ask_for_specific_location(self, theme: str) -> str:
        return await self._generate(
            f"Precisamos saber o local exato para o tema {theme}. Pergunte o nome da rua, número, ou o nome do estabelecimento (escola, posto de saúde) afetado."
        )

    async def ask_for_urgency(self) -> str:
        return await self._generate(
            "Precisamos definir a prioridade. Pergunte se isso oferece risco imediato à segurança/saúde ou se é uma solicitação de melhoria."
        )
    
    async def confirm_final_demand(self, title: str, desc: str, urgency: str) -> str:
        return await self._generate(
            "Apresente o resumo final da demanda (Título, Descrição, Urgência). Pergunte se podemos registrar assim.",
            {"title": title, "desc": desc, "urgency": urgency}
        )