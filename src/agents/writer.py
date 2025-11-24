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
        if is_new_user:
            return (
                "Olá! Sou o Coral, seu assistente cívico. 🌊\n\n"
                "Estou aqui para ajudar você a resolver problemas do seu bairro e entender melhor as leis.\n\n"
                "Para começarmos, *qual é o seu bairro e cidade?*"
            )
        return (
            "Olá de novo! 👋\n\n"
            "Como posso ajudar você hoje? Você pode me contar um problema do seu bairro ou tirar dúvidas sobre leis."
        )

    async def ask_location_retry(self) -> str:
        return (
            "Não consegui entender qual é o seu bairro e cidade. 🤔\n\n"
            "Poderia escrever novamente? Exemplo: *Centro, São Paulo*."
        )

    async def confirm_location(self, location: Dict = None, is_correct: bool = True) -> str:
        if not is_correct:
            return "Desculpe, não entendi. Por favor, responda apenas com *Sim* ou *Não*."
        
        neighborhood = location.get('neighborhood', '')
        city = location.get('city', '')
        state = location.get('state', '')
        
        return (
            f"Entendi que você está em: *{neighborhood}, {city} - {state}*.\n\n"
            "Está correto? (Responda *Sim* ou *Não*)"
        )

    async def onboarding_complete(self) -> str:
        return (
            "Ótimo! Cadastro concluído. ✅\n\n"
            "Agora me conte: *o que está acontecendo no seu bairro?* "
            "Você pode relatar um problema (buraco, iluminação, etc.) ou sugerir uma melhoria."
        )

    # =========================================================================
    # MÉTODOS DE DEMANDA E AÇÕES
    # =========================================================================
    async def confirm_demand_content(self, title, description, theme, scope_level, urgency) -> str:
        return (
            f"Entendi. Vamos confirmar se peguei tudo certo:\n\n"
            f"📌 *Título:* {title}\n"
            f"📝 *Descrição:* {description}\n"
            f"🏷️ *Tema:* {theme}\n"
            f"🚨 *Urgência:* {urgency}\n\n"
            f"Essas informações estão corretas? Responda com *Sim* ou *Não*."
        )

    async def present_action_options(self, has_similar_demands: bool) -> str:
        options = (
            "Como você gostaria de prosseguir?\n\n"
            "1️⃣ *Criar uma Demanda*: Para relatar um problema e buscar solução.\n"
        )
        if has_similar_demands:
             options += "2️⃣ *Apoiar Demanda Existente*: Vi que já existem problemas parecidos.\n"
        else:
             options += "2️⃣ *Ideia Legislativa*: Transformar isso em uma sugestão de lei.\n"
             
        options += "3️⃣ *Apenas Conversar*: Tirar dúvidas ou falar mais sobre o assunto."
        return options

    async def ask_problem_rephrase(self) -> str:
        return "Tudo bem, entendi errado. 😅\n\nPoderia me explicar o problema novamente, com mais detalhes?"

    async def unclear_confirmation_request(self) -> str:
        return "Desculpe, não entendi. Por favor responda com *Sim* ou *Não*."

    async def show_similar_demands(self, demands: List[Dict]) -> str:
        msg = "Encontrei algumas demandas parecidas com a sua. Veja se alguma delas é o que você quer relatar:\n\n"
        for i, d in enumerate(demands, 1):
            msg += f"*{i}.* {d.get('title')} ({d.get('supporters_count', 0)} apoios)\n"
        
        msg += "\nDigite o *número* da demanda para apoiar, ou digite *nova* para criar uma nova demanda."
        return msg

    async def legislative_idea_ready(self, draft: Dict) -> str:
        return (
            "Aqui está uma sugestão de texto para sua Ideia Legislativa:\n\n"
            f"📜 *{draft.get('title', 'Ideia Legislativa')}*\n\n"
            f"{draft.get('description', '')}\n\n"
            "Você pode copiar esse texto e postar no portal e-Cidadania!"
        )

    async def converse_only_message(self) -> str:
        return "Entendi! Estou aqui para conversar e tirar dúvidas. Sobre o que quer falar?"

    async def unclear_decision_request(self) -> str:
        return "Não entendi. Digite o número da opção desejada."

    async def demand_created(self, title, theme, scope_level, urgency, share_link, related_pls) -> str:
        msg = (
            f"🎉 Demanda *{title}* criada com sucesso!\n\n"
            f"Compartilhe este link para conseguir mais apoios: {share_link}\n"
        )
        if related_pls:
            msg += "\nTambém encontrei alguns Projetos de Lei relacionados:\n"
            for pl in related_pls:
                msg += f"- {pl.get('title', 'PL')}\n"
        return msg

    # =========================================================================
    # MÉTODOS DE DÚVIDAS (QUESTION HANDLER)
    # =========================================================================
    async def explain_pls_and_actions(self, theme: str, pls: List[Dict]) -> str:
        msg = f"Sobre o tema *{theme}*, encontrei os seguintes projetos:\n\n"
        for pl in pls:
            msg += f"📜 *{pl.get('title', 'Projeto')}*\n{pl.get('summary', '')[:100]}...\n\n"
        
        msg += (
            "O que você deseja fazer?\n"
            "1️⃣ Criar uma nova demanda sobre isso\n"
            "2️⃣ Apoiar uma demanda existente"
        )
        return msg

    # =========================================================================
    # MÉTODOS FALTANTES (QUE CAUSAVAM ERRO)
    # =========================================================================
    async def ask_confirmation_for_action(self, theme: str, reformulated_demand: str) -> str:
        return (
            f"Entendi que você quer falar sobre *{theme}*.\n\n"
            f"Resumo: {reformulated_demand}\n\n"
            "Podemos prosseguir com isso? (Sim/Não)"
        )

    async def demand_not_found(self) -> str:
        return "Desculpe, não consegui carregar os detalhes dessa demanda agora. Tente novamente."

    async def show_similar_demands_for_support(self, demands: List[Dict]) -> str:
        return await self.show_similar_demands(demands) # Reutiliza lógica

    async def unclear_action_choice(self, has_similar: bool) -> str:
        return "Opção inválida. Por favor, digite o *número* da opção desejada."

    async def ask_for_new_demand_description(self) -> str:
        return "Entendido! Vamos criar uma nova. Por favor, descreva o problema ou ideia com detalhes."

    async def unclear_support_choice(self, num_options: int) -> str:
        return f"Opção inválida. Digite um número de 1 a {num_options}, ou 'nova'."

    async def demand_already_supported(self, title: str = None, current_count: int = None) -> str:
        return (
            f"Você já apoia a demanda *{title}*! 🙌\n"
            f"Atualmente ela tem {current_count} apoios."
        )

    async def demand_supported_success(self, title: str, new_count: int) -> str:
        return (
            f"Sucesso! Você apoiou a demanda *{title}*. 🚀\n"
            f"Agora ela conta com {new_count} apoios!"
        )

    async def generic_error_response(self) -> str:
        return "Ops! Tive um erro interno ao processar seu pedido. Tente novamente em alguns instantes."

    async def empty_message_response(self, is_audio: bool) -> str:
        msg = "áudio vazio" if is_audio else "mensagem vazia"
        return f"Parece que recebi uma {msg}. Poderia enviar novamente?"

    async def ask_for_help_options(self) -> str:
        return (
            "Não entendi muito bem. 😕\n\n"
            "Você pode:\n"
            "1. Relatar um problema\n"
            "2. Tirar uma dúvida sobre leis"
        )

    # =========================================================================
    # MÉTODOS DE ENTREVISTA (DEMAND BUILDER)
    # =========================================================================
    
    async def ask_for_more_details(self) -> str:
        return (
            "Preciso de um pouco mais de detalhes para entender bem o problema. 🕵️\n\n"
            "O que exatamente aconteceu? Há quanto tempo isso ocorre?"
        )

    async def ask_for_specific_location(self, theme: str) -> str:
        return (
            f"Para resolvermos questões sobre *{theme}*, preciso saber o local exato. 📍\n\n"
            "Qual é o nome da rua, número ou ponto de referência (ex: nome da escola ou posto de saúde)?"
        )

    async def ask_for_missing_specific_location(self, theme: str) -> str:
        return (
            f"Ainda falta o local exato para essa demanda de *{theme}*. 🔍\n\n"
            "Por favor informe: nome da Rua/Avenida/Travessa + número ou ponto de referência (ex: 'Rua das Flores 120', 'Praça Central', 'Em frente à Escola X')."
        )

    async def ask_for_urgency(self) -> str:
        return (
            "Qual é a urgência desse problema? 🚨\n\n"
            "Isso oferece risco imediato à segurança ou saúde, ou é uma solicitação de melhoria?"
        )
    
    async def confirm_final_demand(self, title: str, desc: str, urgency: str, scope_level: int, location: Dict = None) -> str:
        neighborhood = location.get('neighborhood') if location else None
        city = location.get('city') if location else None
        state = location.get('state') if location else None

        scope_map = {
            1: 'Local (bairro / ponto específico)',
            2: 'Municipal / Urbano',
            3: 'Amplo (regional / estadual / geral)'
        }
        scope_label = scope_map.get(scope_level, 'Indefinido')

        location_str = ''
        if neighborhood or city or state:
            location_str = f"📍 *Local*: {neighborhood or ''}{', ' if neighborhood and city else ''}{city or ''}{' - ' if city and state else ''}{state or ''}\n"

        return (
            "Pronto! Aqui está o resumo da sua demanda:\n\n"
            f"📌 *Título:* {title}\n"
            f"📝 *Descrição:* {desc}\n"
            f"🔎 *Escopo:* {scope_label}\n"
            f"🚨 *Urgência (estimada):* {urgency}\n"
            f"{location_str}"
            "Posso registrar assim? (Responda *Sim* ou *Não*)"
        )