"""
Serviço de busca em fontes legislativas (Câmara, Senado, LexML)
Integra com APIs oficiais para encontrar PLs, leis e programas governamentais
"""

import logging
from typing import Optional, List, Dict
import aiohttp
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class LegislativeSearchService:
    """Busca PLs, Leis e Programas Governamentais em APIs oficiais"""
    
    def __init__(self):
        self.camara_api = "https://dadosabertos.camara.leg.br/api/v2"
        self.senado_api = "https://legis.senado.leg.br/dadosabertos"
        # Timeout para requisições
        self.timeout = aiohttp.ClientTimeout(total=10)
    
    async def search_related_propositions(
        self,
        theme: str,
        keywords: List[str],
        max_results: int = 5
    ) -> Dict[str, any]:
        """
        Busca projetos de lei relacionados ao tema
        
        Args:
            theme: Tema principal (saúde, transporte, educação, etc.)
            keywords: Palavras-chave extraídas do relato
            max_results: Número máximo de resultados
        
        Returns:
            dict: {
                'found': bool,
                'pls': [lista de PLs],
                'total_count': int
            }
        """
        try:
            # Construir query de busca
            search_terms = self._build_search_query(theme, keywords)
            
            # Buscar na Câmara
            camara_pls = await self._search_camara(search_terms, max_results)
            
            # Buscar no Senado (futuro)
            # senado_pls = await self._search_senado(search_terms, max_results)
            
            # Combinar resultados
            all_pls = camara_pls  # + senado_pls
            
            # Ordenar por relevância (data + status)
            all_pls = self._rank_propositions(all_pls)[:max_results]
            
            logger.info(f"✅ Found {len(all_pls)} related PLs for theme: {theme}")
            
            return {
                'found': len(all_pls) > 0,
                'pls': all_pls,
                'total_count': len(all_pls)
            }
            
        except Exception as e:
            logger.error(f"❌ Error searching propositions: {e}")
            return {
                'found': False,
                'pls': [],
                'total_count': 0
            }
    
    async def _search_camara(self, search_terms: str, max_results: int) -> List[Dict]:
        """
        Busca na API da Câmara dos Deputados
        
        Docs: https://dadosabertos.camara.leg.br/swagger/api.html
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Endpoint de proposições
                url = f"{self.camara_api}/proposicoes"
                
                params = {
                    'keywords': search_terms,
                    'ordem': 'DESC',
                    'ordenarPor': 'id',
                    'itens': max_results,
                    'pagina': 1
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        proposicoes = data.get('dados', [])
                        
                        # Formatar resultados
                        formatted = []
                        for prop in proposicoes:
                            formatted.append({
                                'id': prop.get('id'),
                                'type': prop.get('siglaTipo'),
                                'number': prop.get('numero'),
                                'year': prop.get('ano'),
                                'ementa': prop.get('ementa'),
                                'url': prop.get('uri'),
                                'source': 'camara',
                                'full_name': f"{prop.get('siglaTipo')} {prop.get('numero')}/{prop.get('ano')}"
                            })
                        
                        return formatted
                    else:
                        logger.warning(f"Câmara API returned {response.status}")
                        return []
                        
        except asyncio.TimeoutError:
            logger.warning("Câmara API timeout")
            return []
        except Exception as e:
            logger.error(f"Error in Câmara search: {e}")
            return []
    
    async def get_proposition_details(self, pl_id: str, source: str = 'camara') -> Optional[Dict]:
        """
        Busca detalhes completos de um PL específico
        
        Args:
            pl_id: ID do PL na API
            source: 'camara' ou 'senado'
        
        Returns:
            dict: Detalhes completos do PL
        """
        if source == 'camara':
            return await self._get_camara_details(pl_id)
        else:
            return None
    
    async def _get_camara_details(self, pl_id: str) -> Optional[Dict]:
        """Busca detalhes de um PL específico na Câmara"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.camara_api}/proposicoes/{pl_id}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        prop = data.get('dados', {})
                        
                        # Buscar autor(es)
                        autores = await self._get_camara_authors(pl_id, session)
                        
                        # Buscar tramitação
                        tramitacao = await self._get_camara_status(pl_id, session)
                        
                        return {
                            'id': prop.get('id'),
                            'full_name': f"{prop.get('siglaTipo')} {prop.get('numero')}/{prop.get('ano')}",
                            'ementa': prop.get('ementa'),
                            'justificativa': prop.get('justificativa'),
                            'autores': autores,
                            'status': tramitacao.get('status'),
                            'last_update': tramitacao.get('last_update'),
                            'url': prop.get('urlInteiroTeor'),
                            'keywords': prop.get('keywords', [])
                        }
                    else:
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting PL details: {e}")
            return None
    
    async def _get_camara_authors(self, pl_id: str, session: aiohttp.ClientSession) -> List[str]:
        """Busca autores de um PL"""
        try:
            url = f"{self.camara_api}/proposicoes/{pl_id}/autores"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    autores = data.get('dados', [])
                    return [autor.get('nome') for autor in autores]
                else:
                    return []
        except:
            return []
    
    async def _get_camara_status(self, pl_id: str, session: aiohttp.ClientSession) -> Dict:
        """Busca status de tramitação de um PL"""
        try:
            url = f"{self.camara_api}/proposicoes/{pl_id}/tramitacoes"
            params = {'ordem': 'DESC', 'ordenarPor': 'dataHora', 'itens': 1}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    tramitacoes = data.get('dados', [])
                    
                    if tramitacoes:
                        last_tram = tramitacoes[0]
                        return {
                            'status': last_tram.get('descricaoTramitacao'),
                            'last_update': last_tram.get('dataHora')
                        }
                    else:
                        return {'status': 'Em tramitação', 'last_update': None}
                else:
                    return {'status': 'Desconhecido', 'last_update': None}
        except:
            return {'status': 'Desconhecido', 'last_update': None}
    
    async def search_government_programs(
        self,
        theme: str,
        location: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Busca programas governamentais relacionados
        
        TODO: Integrar com Portal da Transparência, Querido Diário, etc.
        Por enquanto retorna estrutura vazia
        
        Args:
            theme: Tema da busca
            location: Localização para filtros regionais
        
        Returns:
            dict: {
                'found': bool,
                'programs': [lista de programas],
                'total_count': int
            }
        """
        # Placeholder - implementação futura
        logger.info(f"Searching government programs for theme: {theme}")
        
        return {
            'found': False,
            'programs': [],
            'total_count': 0
        }
    
    def _build_search_query(self, theme: str, keywords: List[str]) -> str:
        """
        Constrói query de busca otimizada
        
        Combina tema + keywords mais relevantes
        """
        # Mapear tema para termos legislativos comuns
        theme_map = {
            'saude': 'saúde atendimento sus hospital',
            'transporte': 'transporte ônibus mobilidade urbana',
            'educacao': 'educação escola ensino',
            'seguranca': 'segurança polícia crime',
            'meio_ambiente': 'meio ambiente sustentabilidade',
            'habitacao': 'habitação moradia',
            'cultura': 'cultura arte',
            'assistencia_social': 'assistência social vulnerabilidade'
        }
        
        theme_terms = theme_map.get(theme.lower(), theme)
        
        # Combinar com keywords (pegar top 3)
        top_keywords = ' '.join(keywords[:3]) if keywords else ''
        
        query = f"{theme_terms} {top_keywords}".strip()
        
        return query
    
    def _rank_propositions(self, propositions: List[Dict]) -> List[Dict]:
        """
        Ordena proposições por relevância
        
        Critérios:
        - PLs mais recentes
        - PLs em tramitação ativa
        """
        # Por enquanto, mantém ordem da API (já vem ordenado por ID DESC)
        return propositions


# Instância global
legislative_service = LegislativeSearchService()
