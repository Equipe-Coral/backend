"""
Handler de Investigação de Demandas
Implementa os 4 cenários da matriz de decisão (seção 2.3 do fluxos.md)

Busca paralela de:
1. PLs/Leis relacionados (APIs Câmara/Senado)
2. Programas governamentais existentes
3. Demandas comunitárias similares (busca vetorial)

Retorna contexto completo para o usuário tomar decisão informada
"""

import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from src.services.legislative_search_service import legislative_service
from src.services.law_search_service import law_search_service
from src.services.similarity_service import SimilarityService
from src.services.embedding_service import EmbeddingService
from src.agents.writer import WriterAgent
import asyncio

logger = logging.getLogger(__name__)


class DemandInvestigationHandler:
    """Handler que investiga demandas e retorna cenário contextualizado"""
    
    def __init__(self):
        self.legislative_service = legislative_service
        self.law_search_service = law_search_service
        self.similarity_service = SimilarityService()
        self.embedding_service = EmbeddingService()
        self.writer = WriterAgent()
    
    async def investigate_and_present_options(
        self,
        user_text: str,
        classification_result: Dict,
        user_location: Optional[Dict],
        db: Session
    ) -> str:
        """
        Executa investigação completa e retorna mensagem contextualizada
        
        Fluxo:
        1. Extrai tema, keywords, scope_level
        2. Busca PLs/Leis (paralelo)
        3. Busca programas governamentais (paralelo)
        4. Busca demandas similares (paralelo)
        5. Identifica cenário (1, 2, 3 ou 4)
        6. Retorna mensagem apropriada
        
        Args:
            user_text: Texto original do usuário
            classification_result: Resultado da classificação do RouterAgent
            user_location: Localização do usuário
            db: Sessão do banco
        
        Returns:
            str: Mensagem formatada para o usuário
        """
        try:
            # 1. EXTRAIR DADOS DA CLASSIFICAÇÃO
            theme = classification_result.get('theme', 'geral')
            keywords = classification_result.get('keywords', [])
            scope_level = classification_result.get('scope_level', 2)
            
            logger.info(f"🔍 Starting investigation: theme={theme}, scope={scope_level}")
            
            # 2. FEEDBACK IMEDIATO ao usuário
            # Nota: Este é um comentário interno. A mensagem real é enviada pelo WhatsApp antes desta função ser chamada
            
            # 3. INVESTIGAÇÃO PARALELA
            # PRIORIDADE 1: Buscar leis vigentes (pode resolver imediatamente)
            existing_laws = await self.law_search_service.search_existing_laws(
                user_problem=user_text,
                theme=theme,
                location=user_location
            )
            
            # Se encontrou lei vigente, retorna IMEDIATAMENTE
            if existing_laws['found']:
                logger.info(f"✅ Found existing law that guarantees this right!")
                return await self._scenario_existing_law(existing_laws, user_text)
            
            # Se NÃO encontrou lei vigente, continua busca (não informa ao usuário)
            # O sistema vai buscar PLs e demandas sem dizer "não existe lei"
            
            # PRIORIDADE 2: Buscar PLs, programas e demandas
            pls_result, programs_result, similar_demands = await asyncio.gather(
                self.legislative_service.search_related_propositions(theme, keywords),
                self.legislative_service.search_government_programs(theme, user_location),
                self._search_similar_demands(user_text, theme, scope_level, user_location, db)
            )
            
            logger.info(
                f"📊 Investigation results: "
                f"PLs={pls_result['total_count']}, "
                f"Programs={programs_result['total_count']}, "
                f"Similar demands={len(similar_demands)}"
            )
            
            # 4. VERIFICAR SE EXISTE PROGRAMA QUE RESOLVE (PRIORIDADE MÁXIMA)
            if programs_result['found']:
                return await self._scenario_program_exists(programs_result)
            
            # 5. IDENTIFICAR CENÁRIO DA MATRIZ DE DECISÃO
            has_pl = pls_result['found']
            has_similar = len(similar_demands) > 0
            
            if not has_pl and not has_similar:
                # CENÁRIO 1: Sem PL + Sem demanda similar
                return await self._scenario_1_no_pl_no_demand(user_text, theme)
            
            elif not has_pl and has_similar:
                # CENÁRIO 2: Sem PL + Com demanda similar
                return await self._scenario_2_no_pl_has_demand(similar_demands[0])
            
            elif has_pl and not has_similar:
                # CENÁRIO 3: Com PL + Sem demanda similar
                return await self._scenario_3_has_pl_no_demand(pls_result['pls'])
            
            else:
                # CENÁRIO 4: Com PL + Com demanda similar
                return await self._scenario_4_has_pl_has_demand(pls_result['pls'], similar_demands[0])
        
        except Exception as e:
            logger.error(f"❌ Error in investigation: {e}", exc_info=True)
            # Fallback para opções genéricas
            return await self._fallback_generic_options()
    
    async def _search_similar_demands(
        self,
        text: str,
        theme: str,
        scope_level: int,
        user_location: Optional[Dict],
        db: Session
    ) -> list:
        """Busca demandas similares usando embedding + pgvector"""
        try:
            # Gerar embedding do texto
            embedding = await self.embedding_service.generate_embedding(text)
            
            # Buscar similares
            similar = await self.similarity_service.find_similar_demands(
                embedding=embedding,
                theme=theme,
                scope_level=scope_level,
                user_location=user_location or {},
                db=db,
                similarity_threshold=0.75,  # Threshold mais flexível
                max_results=3
            )
            
            return similar
        
        except Exception as e:
            logger.error(f"Error searching similar demands: {e}")
            return []
    
    # ========== CENÁRIOS ==========
    
    async def _scenario_existing_law(self, existing_laws: Dict, user_text: str) -> str:
        """
        PRIORIDADE MÁXIMA: Já existe LEI VIGENTE que garante esse direito
        
        Não precisa criar nada - o cidadão só precisa EXERCER o direito!
        """
        laws = existing_laws['laws']
        primary_law = laws[0]  # Lei principal
        
        message = (
            f"🎯 *Ótima notícia! Seu direito JÁ É GARANTIDO POR LEI!*\n\n"
            f"📜 *{primary_law['name']}*\n"
            f"📋 {primary_law['article']}\n\n"
            f"💡 *O que a lei diz:*\n"
            f"{primary_law['simple_explanation']}\n\n"
            f"✅ *Como usar esse direito:*\n"
            f"{primary_law['how_to_use']}\n\n"
            f"📢 *Onde denunciar:*\n"
            f"{primary_law['where_to_complain']}\n\n"
        )
        
        # Se encontrou mais de uma lei, mencionar
        if len(laws) > 1:
            message += f"📚 Outras leis: "
            message += ", ".join([f"{law['name']}" for law in laws[1:]])
            message += "\n\n"
        
        message += (
            f"💪 *O que você quer fazer?*\n\n"
            f"*1* - Criar demanda comunitária\n"
            f"(mobilizar outras pessoas)\n\n"
            f"*2* - Ver orientação completa\n"
            f"(passo a passo detalhado)\n\n"
            f"*3* - Nada por enquanto\n"
            f"(já entendi meus direitos)\n\n"
            f"Digite *1*, *2* ou *3*:"
        )
        
        return message
    
    async def _scenario_program_exists(self, programs_result: Dict) -> str:
        """
        PRIORIDADE MÁXIMA: Existe programa governamental que resolve
        
        SAÍDA #5 do fluxos.md
        """
        program = programs_result['programs'][0]
        
        message = (
            f"🎯 *Espera! Descobri algo importante!*\n\n"
            f"O que você quer já é garantido por um programa do governo:\n\n"
            f"📋 *{program['name']}*\n"
            f"{program['description']}\n\n"
            f"📍 *Como acessar:*\n"
            f"{program['access_info']}\n\n"
            f"🔗 Link oficial: {program['url']}\n\n"
            f"Isso resolve o seu problema?"
        )
        
        return message
    
    async def _scenario_1_no_pl_no_demand(self, user_text: str, theme: str) -> str:
        """
        CENÁRIO 1: Não existe PL + Não existe demanda similar
        
        Usuário pode ser protagonista:
        - Criar demanda comunitária (SAÍDA #1)
        - Criar ideia legislativa (SAÍDA #3)
        - Cancelar
        """
        message = (
            f"🔍 *Investigação completa:*\n\n"
            f"Analisei sua solicitação em múltiplas fontes e não encontrei:\n"
            f"❌ Projetos de lei relacionados ao tema\n"
            f"❌ Outras pessoas que reportaram isso aqui no Coral\n\n"
            f"Mas isso não é problema! Você pode ser o *primeiro* a levantar essa questão. 💪\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"*O que você gostaria de fazer?*\n\n"
            f"1️⃣ *Criar demanda comunitária*\n"
            f"   → Outras pessoas poderão apoiar\n"
            f"   → Quando atingir {self._get_threshold()} apoios, enviaremos denúncia institucional automática\n"
            f"   → Você mobiliza a comunidade\n\n"
            f"2️⃣ *Criar ideia legislativa*\n"
            f"   → Vou te ajudar a transformar isso em proposta de lei\n"
            f"   → Cadastro no e-Cidadania (Senado)\n"
            f"   → 20.000 apoios = vira Sugestão Legislativa oficial\n\n"
            f"3️⃣ *Cancelar*\n\n"
            f"Digite o número da opção:"
        )
        
        return message
    
    async def _scenario_2_no_pl_has_demand(self, similar_demand: Dict) -> str:
        """
        CENÁRIO 2: Não existe PL + Existe demanda similar
        
        Usuário pode:
        - Apoiar demanda existente (SAÍDA #2)
        - Criar ideia legislativa (SAÍDA #3)
        - Cancelar
        """
        # Calcular tempo desde criação
        time_ago = self._format_time_ago(similar_demand['created_at'])
        
        message = (
            f"🔍 *Investigação completa:*\n\n"
            f"Analisei sua solicitação e encontrei:\n"
            f"❌ Nenhum projeto de lei sobre esse tema ainda\n"
            f"✅ *Outras pessoas com o mesmo problema!*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📌 *Demanda existente:*\n\n"
            f"*{similar_demand['title']}*\n"
            f"👥 {similar_demand['supporters_count']} pessoas apoiando\n"
            f"📅 Criado há {time_ago}\n"
            f"🏷️ Tema: {similar_demand['theme']}\n\n"
            f"_{similar_demand['description'][:150]}..._\n\n"
            f"💡 *Por que apoiar?*\n"
            f"• Sua voz se junta com outras {similar_demand['supporters_count']} pessoas\n"
            f"• Quanto mais apoios, mais força para pressionar\n"
            f"• Com {self._get_threshold()} apoios, fazemos denúncia institucional automática\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"*O que você gostaria de fazer?*\n\n"
            f"1️⃣ *Apoiar a demanda existente*\n"
            f"   → Juntar sua voz e fortalecer a causa\n\n"
            f"2️⃣ *Criar ideia legislativa*\n"
            f"   → Se você acha que precisa de uma lei sobre isso\n\n"
            f"3️⃣ *Cancelar*\n\n"
            f"Digite o número da opção:"
        )
        
        return message
    
    async def _scenario_3_has_pl_no_demand(self, pls: list) -> str:
        """
        CENÁRIO 3: Existe PL + Não existe demanda similar
        
        Usuário pode:
        - Apoiar/comentar no PL (SAÍDA #4)
        - Criar demanda comunitária (SAÍDA #1)
        - Criar ideia legislativa (SAÍDA #3) - se PL não resolve bem
        - Cancelar
        """
        # Pegar primeiro PL (mais relevante)
        pl = pls[0]
        
        message = (
            f"🔍 *Investigação completa:*\n\n"
            f"Analisei sua solicitação e encontrei:\n"
            f"✅ *Projeto de lei relacionado ao tema!*\n"
            f"❌ Nenhuma demanda comunitária sobre isso aqui no Coral\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📚 *Projeto de Lei encontrado:*\n\n"
            f"*{pl['full_name']}*\n"
            f"{pl['ementa'][:200]}...\n\n"
            f"🔗 Ver PL completo: (link será gerado)\n\n"
            f"💡 *O que significa?*\n"
            f"• Já existe uma proposta de lei sobre esse tema\n"
            f"• Você pode participar oficialmente comentando\n"
            f"• Seu comentário ajuda parlamentares a entenderem o impacto real\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"*O que você gostaria de fazer?*\n\n"
            f"1️⃣ *Apoiar/comentar neste PL*\n"
            f"   → Vou te ajudar a comentar oficialmente\n"
            f"   → Participação direta no processo legislativo\n\n"
            f"2️⃣ *Criar demanda comunitária*\n"
            f"   → Para monitorar o problema localmente enquanto o PL tramita\n\n"
            f"3️⃣ *Criar outra ideia legislativa*\n"
            f"   → Se você acha que este PL não resolve bem\n\n"
            f"4️⃣ *Cancelar*\n\n"
            f"Digite o número da opção:"
        )
        
        return message
    
    async def _scenario_4_has_pl_has_demand(self, pls: list, similar_demand: Dict) -> str:
        """
        CENÁRIO 4: Existe PL + Existe demanda similar
        
        Usuário pode:
        - Apoiar demanda comunitária (SAÍDA #2)
        - Apoiar/comentar no PL (SAÍDA #4)
        - Criar ideia legislativa (SAÍDA #3) - se PL não resolve
        - Cancelar
        """
        pl = pls[0]
        time_ago = self._format_time_ago(similar_demand['created_at'])
        
        message = (
            f"🔍 *Investigação completa:*\n\n"
            f"Analisei sua solicitação e encontrei *informações importantes!*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📚 *PROJETO DE LEI RELACIONADO:*\n\n"
            f"*{pl['full_name']}*\n"
            f"{pl['ementa'][:150]}...\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📌 *DEMANDA COMUNITÁRIA EXISTENTE:*\n\n"
            f"*{similar_demand['title']}*\n"
            f"👥 {similar_demand['supporters_count']} pessoas apoiando\n"
            f"📅 Criado há {time_ago}\n\n"
            f"💡 *Você tem 2 caminhos:*\n"
            f"• Apoiar a mobilização local (demanda comunitária)\n"
            f"• Participar do processo legislativo (comentar no PL)\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"*O que você gostaria de fazer?*\n\n"
            f"1️⃣ *Apoiar a demanda comunitária*\n"
            f"   → Juntar sua voz com outras {similar_demand['supporters_count']} pessoas\n"
            f"   → Pressão local e mobilização\n\n"
            f"2️⃣ *Apoiar/comentar no PL*\n"
            f"   → Participar oficialmente do processo legislativo\n"
            f"   → Influenciar a lei que está sendo criada\n\n"
            f"3️⃣ *Criar outra ideia legislativa*\n"
            f"   → Se você acha que o PL não resolve bem\n\n"
            f"4️⃣ *Cancelar*\n\n"
            f"Digite o número da opção:"
        )
        
        return message
    
    async def _fallback_generic_options(self) -> str:
        """Opções genéricas em caso de erro na investigação"""
        message = (
            f"Entendi que você quer relatar algo! 👍\n\n"
            f"*Como posso ajudar?*\n\n"
            f"1️⃣ *Criar nova demanda* - Registrar um problema para mobilizar a comunidade\n"
            f"2️⃣ *Ver demandas próximas* - Apoiar demandas existentes na sua região\n"
            f"3️⃣ *Tirar dúvida* - Fazer pergunta sobre leis ou serviços públicos\n\n"
            f"Digite o número da opção:"
        )
        return message
    
    # ========== HELPERS ==========
    
    def _get_threshold(self) -> int:
        """Retorna threshold de apoios para denúncia institucional"""
        # TODO: Tornar configurável
        return 20
    
    def _format_time_ago(self, created_at) -> str:
        """Formata tempo desde criação"""
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            delta = now - created_at.replace(tzinfo=timezone.utc)
            
            days = delta.days
            
            if days == 0:
                return "hoje"
            elif days == 1:
                return "1 dia"
            elif days < 7:
                return f"{days} dias"
            elif days < 30:
                weeks = days // 7
                return f"{weeks} semana{'s' if weeks > 1 else ''}"
            else:
                months = days // 30
                return f"{months} {'mês' if months == 1 else 'meses'}"
        except:
            return "alguns dias"


# Instância global
investigation_handler = DemandInvestigationHandler()
