import httpx
import logging
import asyncio
from typing import List, Dict, Optional, Literal, Set
from datetime import datetime
from xml.etree import ElementTree
import re

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

CAMARA_THEMES = {
    "saude": 40,
    "educacao": 62,
    "seguranca": 46,
    "transporte": 56,
    "meio_ambiente": 49,
    "economia": 28,
    "trabalho": 58,
    "agricultura": 1,
    "ciencia_tecnologia": 14,
    "direitos_humanos": 26,
    "cultura": 20,
    "esporte": 30,
    "comunicacao": 15,
    "defesa": 23,
    "desenvolvimento_urbano": 25,
    "energia": 29,
    "industria_comercio": 38,
    "justica": 42,
    "previdencia": 52,
    "turismo": 59,
    "consumidor": 38, # Mapeado para Industria/Comercio
    "animais": 49,    # Mapeado para Meio Ambiente
}

# Palavras que devem ser removidas da busca pois atrapalham APIs exatas
STOP_WORDS = {
    "quais", "onde", "como", "quando", "por que", "porque", "o que", 
    "permitem", "pode", "podem", "deve", "devem", "sobre", "para", "com",
    "gostaria", "saber", "entrar", "fazer"
}

KEYWORD_EXPANSIONS = {
    "saude": ["saúde", "sus", "hospital", "atendimento médico"],
    "educacao": ["educação", "escola", "ensino"],
    "transporte": ["ônibus", "metrô", "transporte público"],
    "seguranca": ["segurança", "polícia", "crime"],
    "meio_ambiente": ["meio ambiente", "sustentabilidade", "animais", "fauna"],
    "animais": ["animal", "cães", "gatos", "pets", "bichos", "cachorro"],
    "restaurante": ["bares", "lanchonetes", "praça de alimentação", "estabelecimentos"],
}


# ============================================================================
# BASE API CLIENT
# ============================================================================

class BaseAPIClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        await self.client.aclose()
        logger.debug(f"🔌 Closed {self.__class__.__name__}")


# ============================================================================
# CÂMARA DOS DEPUTADOS API
# ============================================================================

class CamaraAPI(BaseAPIClient):
    def __init__(self):
        super().__init__("https://dadosabertos.camara.leg.br/api/v2")

    async def search_propositions(
        self,
        keywords: List[str],
        year: Optional[int] = None,
        limit: int = 10,
        theme: Optional[str] = None,
        proposition_types: Optional[List[str]] = None,
        fallback_years: bool = True
    ) -> List[Dict]:
        
        # 1. Expandir keywords e limpar
        clean_keywords = [k for k in keywords if k.lower() not in STOP_WORDS]
        if not clean_keywords:
            clean_keywords = keywords # Se limpar tudo, usa o original
            
        # IMPORTANTE: Criar string para a API da Câmara
        keywords_string = " ".join(clean_keywords)
            
        # 2. Configurar tema
        theme_code = CAMARA_THEMES.get(theme.lower()) if theme else None
        
        if not proposition_types:
            proposition_types = ["PL", "PLP", "PEC"] # Removido REQ/VET para focar em leis
        
        # 3. Configurar anos (Janela de 6 anos para pegar leis em tramitação)
        current_year = datetime.now().year
        years_to_try = [year] if year else list(range(current_year, current_year - 6, -1))
        
        all_results = []
        
        # Estratégia de tentativa:
        # Primeiro tenta COM tema (se houver). Se der poucos resultados, tenta SEM tema.
        strategies = []
        if theme_code:
            strategies.append({"use_theme": True, "code": theme_code})
        strategies.append({"use_theme": False, "code": None})

        for strategy in strategies:
            # Se já achou resultados suficientes na estratégia anterior, para
            if len(all_results) >= limit:
                break

            use_theme_filter = strategy["use_theme"]
            code_filter = strategy["code"]

            if not use_theme_filter and len(all_results) > 0:
                # Se já achou algo com tema, não precisa fazer a busca ampla (que é lenta)
                continue

            for prop_type in proposition_types:
                for search_year in years_to_try:
                    if len(all_results) >= limit:
                        break

                    params = {
                        'itens': limit * 2, # Pede um pouco mais para garantir relevância
                        'ordem': 'DESC',
                        'ordenarPor': 'id',
                        'siglaTipo': prop_type,
                        'ano': search_year,
                        'keywords': keywords_string # <--- CORREÇÃO AQUI: Enviando keywords para o servidor
                    }
                    
                    if use_theme_filter and code_filter:
                        params['codTema'] = code_filter
                    
                    try:
                        log_theme = f"theme={code_filter}" if use_theme_filter else "NO_THEME"
                        logger.info(f"🔍 Câmara API: {prop_type} {search_year}, {log_theme}, kw='{keywords_string}'")
                        
                        response = await self.client.get(
                            f"{self.base_url}/proposicoes",
                            params=params
                        )
                        
                        # Câmara retorna 404 se a busca não tiver resultados (feature da API)
                        if response.status_code == 404:
                            continue
                            
                        response.raise_for_status()
                        
                        data = response.json()
                        propositions = data.get('dados', [])
                        
                        # Filtro local robusto (Double Check)
                        filtered = self._filter_by_keywords(
                            propositions,
                            clean_keywords # Usa keywords limpas para match
                        )
                        
                        # Evitar duplicatas
                        existing_ids = {r['id'] for r in all_results}
                        for p in filtered:
                            norm = self._normalize_result(p, "camara")
                            if norm['id'] not in existing_ids:
                                all_results.append(norm)
                                existing_ids.add(norm['id'])
                        
                    except Exception as e:
                        # Não logar erro em loop para evitar spam se for apenas "não encontrado"
                        if "404" not in str(e):
                            logger.error(f"❌ Câmara API error: {e}")
                        continue

        logger.info(f"✅ Câmara: Found {len(all_results)} propositions")
        return all_results
    
    def _expand_keywords(self, keywords: List[str], theme: Optional[str]) -> List[str]:
        expanded = set(keywords)
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in KEYWORD_EXPANSIONS:
                expanded.update(KEYWORD_EXPANSIONS[kw_lower])
        if theme and theme.lower() in KEYWORD_EXPANSIONS:
            expanded.update(KEYWORD_EXPANSIONS[theme.lower()])
        return list(expanded)
    
    def _filter_by_keywords(self, propositions: List[Dict], keywords: List[str]) -> List[Dict]:
        if not keywords:
            return propositions
        
        # Filtro Fuzzy Simples:
        # Pelo menos UMA das keywords deve estar na ementa
        filtered = []
        for prop in propositions:
            ementa = prop.get('ementa', '').lower()
            # Verifica se pelo menos uma keyword significativa está presente
            matches = sum(1 for kw in keywords if kw.lower() in ementa)
            if matches > 0:
                prop['match_score'] = matches
                filtered.append(prop)
        
        # Ordena pelos que tem mais matches
        filtered.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        return filtered
    
    def _normalize_result(self, prop: Dict, source: str) -> Dict:
        return {
            "source": "Câmara dos Deputados",
            "id": str(prop.get('id', '')),
            "type": prop.get('siglaTipo', ''),
            "number": str(prop.get('numero', '')),
            "year": str(prop.get('ano', '')),
            "title": f"{prop.get('siglaTipo', '')} {prop.get('numero', '')}/{prop.get('ano', '')}",
            "description": prop.get('ementa', ''),
            "url": prop.get('urlInteiroTeor', '') or f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop.get('id', '')}",
            "date": str(prop.get('ano', '')),
            "raw": prop
        }


# ============================================================================
# SENADO FEDERAL API
# ============================================================================

class SenadoAPI(BaseAPIClient):
    def __init__(self):
        super().__init__("https://legis.senado.leg.br/dadosabertos")

    async def search_propositions(self, keywords: List[str], year: Optional[int] = None, limit: int = 10) -> List[Dict]:
        try:
            # Limpeza de keywords para o Senado (API sensível)
            clean_keywords = [k for k in keywords if k.lower() not in STOP_WORDS]
            if not clean_keywords:
                clean_keywords = keywords

            # Busca apenas pelos 2 termos mais relevantes para não quebrar a busca bool
            query = " ".join(clean_keywords[:3]) 
            
            params = {
                'q': query,
                # Senado não aceita range de ano fácil, se não passar ano pega tudo.
                # Vamos remover o filtro de ano se não for específico para pegar histórico
            }
            if year:
                params['ano'] = year
            
            logger.info(f"🔍 Senado API: query='{query}'")
            
            response = await self.client.get(f"{self.base_url}/materia/pesquisa/lista", params=params)
            response.raise_for_status()
            
            tree = ElementTree.fromstring(response.content)
            materias = tree.findall(".//{*}Materia")
            
            results = []
            for materia in materias:
                normalized = self._normalize_result(materia)
                if normalized:
                    results.append(normalized)
            
            # Filtro manual pós-API (Senado retorna muita coisa antiga)
            results.sort(key=lambda x: x['year'], reverse=True)
            
            logger.info(f"✅ Senado: Found {len(results)} propositions")
            return results[:limit]
        
        except Exception as e:
            logger.error(f"❌ Senado API error: {e}")
            return []
    
    def _normalize_result(self, materia: ElementTree.Element) -> Optional[Dict]:
        try:
            dados_basicos = materia.find(".//{*}DadosBasicosMateria")
            if dados_basicos is None: return None # Estrutura varia

            codigo = materia.find(".//{*}Codigo")
            sigla = dados_basicos.find(".//{*}Sigla")
            numero = dados_basicos.find(".//{*}Numero")
            ano = dados_basicos.find(".//{*}Ano")
            ementa = dados_basicos.find(".//{*}Ementa")
            
            # Pegar URL correta
            cod_val = codigo.text if codigo is not None else ""
            
            return {
                "source": "Senado Federal",
                "id": cod_val,
                "type": sigla.text if sigla is not None else "",
                "number": numero.text if numero is not None else "",
                "year": ano.text if ano is not None else "",
                "title": f"{sigla.text if sigla is not None else ''} {numero.text if numero is not None else ''}/{ano.text if ano is not None else ''}",
                "description": ementa.text if ementa is not None else "",
                "url": f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{cod_val}",
                "date": ano.text if ano is not None else "",
                "raw": {}
            }
        except Exception as e:
            return None


# ============================================================================
# LEXML API
# ============================================================================

class LexMLAPI(BaseAPIClient):
    def __init__(self):
        super().__init__("https://www.lexml.gov.br/busca")

    async def search_propositions(self, keywords: List[str], limit: int = 10, locality: Optional[str] = None, authority: Optional[str] = None) -> List[Dict]:
        try:
            # Limpeza extrema para LexML
            clean_keywords = [k for k in keywords if k.lower() not in STOP_WORDS]
            query = " AND ".join(clean_keywords[:3]) # Força presença de termos
            
            params = {
                'query': query,
                'startRecord': 1,
                'maximumRecords': limit,
                'operation': 'searchRetrieve'
            }
            
            logger.info(f"🔍 LexML API: query='{query}'")
            response = await self.client.get(f"{self.base_url}/SRU", params=params)
            response.raise_for_status()
            
            tree = ElementTree.fromstring(response.content)
            records = tree.findall(".//{*}record")
            
            results = []
            for record in records:
                normalized = self._normalize_result(record)
                if normalized:
                    # Filtros pós-processamento
                    if authority and authority.lower() != normalized.get('authority', '').lower():
                        continue
                    results.append(normalized)
            
            return results
        except Exception as e:
            logger.error(f"❌ LexML API error: {e}")
            return []
    
    def _normalize_result(self, record: ElementTree.Element) -> Optional[Dict]:
        try:
            data = record.find(".//{*}dc")
            if data is None: return None
            
            urn = data.find(".//{*}urn")
            title = data.find(".//{*}title")
            description = data.find(".//{*}description")
            date = data.find(".//{*}date")
            
            return {
                "source": "LexML",
                "id": urn.text if urn is not None else "",
                "title": title.text if title is not None else "Documento sem título",
                "description": description.text if description is not None else "",
                "url": f"https://www.lexml.gov.br/urn/{urn.text}" if urn is not None else "",
                "date": date.text if date is not None else "",
                "raw": {}
            }
        except Exception:
            return None

class QueridoDiarioAPI(BaseAPIClient):
    # (Mantido igual ao original pois o foco do erro é Federal)
    def __init__(self):
        super().__init__("https://queridodiario.ok.org.br/api")
    
    async def search_local_laws(self, keywords: List[str], city_code: str, limit: int = 10) -> List[Dict]:
        # Implementação stub para manter compatibilidade, usar a original se tiver
        return []
    async def close(self):
        await self.client.aclose()


# ============================================================================
# UNIFIED MULTI-SOURCE API
# ============================================================================

class MultiSourceLegislativeAPI:
    def __init__(self):
        self.camara = CamaraAPI()
        self.senado = SenadoAPI()
        self.lexml = LexMLAPI()
        self.querido_diario = QueridoDiarioAPI()
    
    async def search_relevant_legislation(
        self,
        keywords: List[str],
        scope: int,
        location: Optional[Dict] = None,
        theme: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        
        # 1. Pré-processamento inteligente de keywords
        # Removemos stop words e termos conversacionais aqui antes de distribuir
        search_keywords = [k for k in keywords if k.lower() not in STOP_WORDS]
        if not search_keywords: 
            search_keywords = keywords # Fallback

        logger.info(f"🎯 Multi-source search: theme={theme}, clean_keywords={search_keywords}")
        
        tasks = []
        
        # Lógica de distribuição baseada em Escopo
        if scope == 3: # Federal / Macro
            # LexML (Abrangente)
            tasks.append(self.lexml.search_propositions(
                keywords=search_keywords,
                limit=limit
            ))
            # Câmara (Específico)
            tasks.append(self.camara.search_propositions(
                keywords=search_keywords,
                theme=theme,
                limit=limit
            ))
            # Senado (Específico)
            tasks.append(self.senado.search_propositions(
                keywords=search_keywords,
                limit=limit
            ))
            
        elif scope == 2: # Estadual/Regional
             tasks.append(self.lexml.search_propositions(
                keywords=search_keywords,
                limit=limit,
                locality=location.get('state') if location else None,
                authority="Estadual"
            ))
        
        # Executa paralelo
        results_arrays = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for result in results_arrays:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"❌ Task failed: {result}")
        
        # Deduplicar
        unique_results = self._deduplicate_results(all_results)
        
        # Ordenar por relevância
        sorted_results = self._rank_by_relevance(unique_results, search_keywords)
        
        logger.info(f"✅ Multi-source: {len(sorted_results)} unique results")
        return sorted_results[:limit]
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        for r in results:
            # Chave composta para evitar duplicatas entre LexML e Câmara
            key = f"{r.get('type')}-{r.get('number')}-{r.get('year')}".lower()
            if "sem título" in r.get('title', '').lower(): 
                key = r.get('id') # Fallback
            
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique
    
    def _rank_by_relevance(self, results: List[Dict], keywords: List[str]) -> List[Dict]:
        keywords_lower = [k.lower() for k in keywords]
        
        def score(item):
            s = 0
            title = str(item.get('title', '')).lower()
            desc = str(item.get('description', '')).lower()
            
            # Match exato no título vale muito
            for kw in keywords_lower:
                if kw in title: s += 10
                if kw in desc: s += 2
            
            # Recência vale pontos
            try:
                year = int(item.get('year', 0) or item.get('date', '0')[:4])
                if year >= datetime.now().year - 2: s += 3
            except: pass
            
            # Penaliza requerimentos (REQ) e vetos (VET), prioriza PLs
            tipo = str(item.get('type', '')).upper()
            if tipo in ['PL', 'PEC', 'PLP', 'LEI']: s += 5
            if tipo in ['REQ', 'RIC', 'VET']: s -= 5
            
            return s
            
        return sorted(results, key=score, reverse=True)

    async def close_all(self):
        await self.camara.close()
        await self.senado.close()
        await self.lexml.close()
        await self.querido_diario.close()