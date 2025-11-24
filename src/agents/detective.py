from src.core.gemini import gemini_client
from src.models.legislative_item import LegislativeItem
from src.models.pl_interaction import PLInteraction
from sqlalchemy.orm import Session
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DetectiveAgent:
    """
    Investiga itens legislativos usando a inteligência do Gemini para encontrar
    e resumir PLs relevantes baseadas no contexto do usuário.
    """

    def __init__(self):
        self.client = gemini_client

    async def find_related_pls(
        self,
        theme: str,
        keywords: List[str],
        db: Session,
        scope_level: int = 3,
        location: Optional[Dict] = None,
        user_message: Optional[str] = None
    ) -> List[Dict]:
        """
        Usa o Gemini para encontrar 3 PLs principais sobre o tema.
        """
        
        # Preparar contexto de localização
        loc_str = ""
        if location:
            city = location.get('city')
            state = location.get('state')
            if city and state:
                loc_str = f"na cidade de {city}-{state}"
            elif state:
                loc_str = f"no estado de {state}"
        
        # Construir o Prompt
        prompt = f"""
        Você é um consultor legislativo especialista. O usuário tem uma demanda sobre: "{theme}".
        Contexto/Mensagem do usuário: "{user_message or 'Não informado'}"
        Palavras-chave: {', '.join(keywords)}
        Localização do usuário: {loc_str or 'Brasil (Nacional)'}
        Escopo: Nível {scope_level} (1=Bairro, 2=Cidade/Estado, 3=Nacional)

        TAREFA:
        Liste as 3 principais leis ou Projetos de Lei (PLs) REAIS e existentes no Brasil que melhor se aplicam a este caso.
        Priorize leis em tramitação ou aprovadas recentemente que resolvam a dor do usuário.
        
        Se o problema for muito local (ex: buraco na rua), cite leis municipais genéricas ou o Código de Posturas típico.
        Se for nacional (ex: imposto), cite PLs federais da Câmara ou Senado.

        Retorne APENAS um JSON estrito (sem markdown) com esta lista:
        [
            {{
                "source": "Câmara dos Deputados" ou "Senado Federal" ou "Câmara Municipal",
                "type": "PL" ou "Lei",
                "number": "número/ano",
                "year": "ano",
                "title": "Título curto e oficial",
                "description": "Resumo de 1 frase explicando como isso ajuda o usuário",
                "status": "Situação atual (ex: Em tramitação, Aprovada)",
                "url": "Link oficial se souber, ou null"
            }}
        ]
        """

        try:
            # 1. Chamar o Gemini (Linha que faltava no seu código)
            logger.info(f"🔍 Asking Gemini for PLs: theme={theme}")
            response_text = await self.client.generate_content(prompt)
            
            # 2. Parsear o JSON
            results = self.client.parse_json(response_text)

            # Garantir que é uma lista
            if isinstance(results, dict):
                # Se retornou um dict, verifica se tem uma chave 'results' ou 'pls'
                if 'results' in results: results = results['results']
                elif 'pls' in results: results = results['pls']
                else: results = [results] # Assume que o dict é o item único

            if not isinstance(results, list):
                logger.warning(f"Gemini output is not a list: {results}")
                return []

            legislation = []
            
            for item in results[:3]:
                # Validação mínima
                if not item.get('title') or not item.get('type'):
                    continue

                # Normalização básica para evitar erros
                item_type = item.get('type', 'Lei')
                item_number = str(item.get('number', ''))
                item_year = str(item.get('year', ''))
                
                # Gerar ID único
                item['id'] = f"{item_type}_{item_number}".replace(" ", "").replace("/", "_")
                
                # Salvar/Atualizar no banco de dados (Cache)
                saved_item = await self._upsert_legislative_item(item, db)
                
                # Gerar URL de busca como fallback se não vier link
                # Correção: URL limpa para evitar erro de formatação
                search_query = f"{item_type} {item_number} {item_year}".strip().replace(" ", "+")
                fallback_url = f"https://www.google.com/search?q={search_query}"
                
                if saved_item:
                    legislation.append({
                        'id': str(saved_item.id),
                        'external_id': saved_item.external_id,
                        'type': saved_item.type,
                        'number': saved_item.number,
                        'year': saved_item.year,
                        'title': saved_item.title,
                        'summary': saved_item.summary,
                        'ementa': saved_item.ementa,
                        'status': saved_item.status,
                        'source': saved_item.source,
                        'url': item.get('url') or fallback_url,
                        'relevance_score': 100
                    })
            
            return legislation

        except Exception as e:
            logger.error(f"❌ Error in DetectiveAgent (Gemini): {e}", exc_info=True)
            return []

    async def _upsert_legislative_item(
        self,
        item_data: Dict,
        db: Session
    ) -> Optional[LegislativeItem]:
        """Salva o item legislativo no banco para histórico"""
        try:
            source = item_data.get('source', 'IA')
            external_id = item_data.get('id', 'unknown')
            
            # Verificar se já existe
            existing = db.query(LegislativeItem).filter(
                LegislativeItem.external_id == external_id
            ).first()
            
            title = item_data.get('title', 'Sem título')
            description = item_data.get('description', '')
            
            if existing:
                existing.title = title
                existing.ementa = description
                existing.summary = description
                existing.updated_at = datetime.now()
                db.commit()
                return existing
            else:
                item = LegislativeItem(
                    external_id=external_id,
                    source=source,
                    type=item_data.get('type', 'PL'),
                    number=str(item_data.get('number', '0')),
                    year=int(item_data.get('year', datetime.now().year)) if str(item_data.get('year')).isdigit() else datetime.now().year,
                    title=title,
                    ementa=description,
                    summary=description,
                    status=item_data.get('status', 'Indefinido'),
                    full_data=item_data,
                    keywords=[]
                )
                db.add(item)
                db.commit()
                db.refresh(item)
                return item
        
        except Exception as e:
            logger.error(f"Error upserting item: {e}")
            db.rollback()
            return None

    async def register_pl_view(self, user_id: str, pl_id: str, db: Session):
        """Registra que o usuário visualizou um item"""
        try:
            interaction = PLInteraction(
                user_id=user_id,
                pl_id=pl_id,
                interaction_type='view'
            )
            db.add(interaction)
            db.commit()
        except Exception as e:
            logger.error(f"Error registering view: {e}")
            db.rollback()

    async def close(self):
        pass