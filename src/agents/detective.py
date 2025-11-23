from src.services.camara_api import MultiSourceLegislativeAPI
from src.models.legislative_item import LegislativeItem
from src.models.pl_interaction import PLInteraction
from sqlalchemy.orm import Session
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# THEME MAPPING (expanded)
# ============================================================================

THEME_MAPPING = {
    # Saúde
    "saude": "saude",
    "hospital": "saude",
    "medico": "saude",
    "sus": "saude",
    "ubs": "saude",
    "posto de saude": "saude",
    
    # Transporte
    "transporte": "transporte",
    "onibus": "transporte",
    "metro": "transporte",
    "mobilidade": "transporte",
    "transito": "transporte",
    
    # Educação
    "educacao": "educacao",
    "escola": "educacao",
    "professor": "educacao",
    "aluno": "educacao",
    "universidade": "educacao",
    
    # Segurança
    "seguranca": "seguranca",
    "policia": "seguranca",
    "crime": "seguranca",
    "violencia": "seguranca",
    
    # Meio Ambiente
    "meio ambiente": "meio_ambiente",
    "lixo": "meio_ambiente",
    "poluicao": "meio_ambiente",
    "reciclagem": "meio_ambiente",
    
    # Consumidor/Comércio
    "consumidor": "industria_comercio",
    "comercio": "industria_comercio",
    "loja": "industria_comercio",
    "restaurante": "industria_comercio",
    "bar": "industria_comercio",
    "estabelecimento": "industria_comercio",
    
    # Direitos dos Animais
    "cachorro": "meio_ambiente",
    "animal": "meio_ambiente",
    "pet": "meio_ambiente",
    "gato": "meio_ambiente",
    "cao": "meio_ambiente",
    
    # Zeladoria
    "buraco": "desenvolvimento_urbano",
    "calcada": "desenvolvimento_urbano",
    "iluminacao": "desenvolvimento_urbano",
    "pavimentacao": "desenvolvimento_urbano",
    
    # Trabalho
    "trabalho": "trabalho",
    "emprego": "trabalho",
    "trabalhador": "trabalho",
    "desemprego": "trabalho",
    
    # Habitação
    "moradia": "desenvolvimento_urbano",
    "habitacao": "desenvolvimento_urbano",
    "casa": "desenvolvimento_urbano",
    
    # Cultura
    "cultura": "cultura",
    "arte": "cultura",
    "museu": "cultura",
    
    # Esporte
    "esporte": "esporte",
    "futebol": "esporte",
    "atletismo": "esporte",
}


# ============================================================================
# DETECTIVE AGENT
# ============================================================================

class DetectiveAgent:
    """
    Investigates legislative items (PLs, PECs, Laws) related to user demands
    
    ENHANCED VERSION WITH MULTI-SOURCE API:
    - Câmara dos Deputados (Federal bills)
    - Senado Federal (Senate bills)  
    - LexML (Unified search - all spheres)
    - Querido Diário (Municipal official gazettes)
    
    KEY IMPROVEMENTS:
    1. Intelligent keyword extraction and expansion
    2. Automatic theme detection
    3. Smart scope-based routing
    4. ADJUSTED relevance scoring (less strict)
    5. Multiple search strategies with fallback
    """

    def __init__(self):
        self.api = MultiSourceLegislativeAPI()

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
        Find legislation related to a theme/demand using intelligent multi-source search
        
        ENHANCED SEARCH STRATEGY:
        1. Extract and expand keywords intelligently
        2. Detect theme automatically from keywords + explicit theme
        3. Search multiple sources based on scope
        4. Score and rank results by relevance (LESS STRICT)
        5. Return top 3-5 most relevant items
        
        Args:
            theme: Explicit theme (may be generic like "consumidor")
            keywords: Keywords extracted from user message
            db: Database session
            scope_level: Demand scope (1=hiper-local, 2=regional, 3=macro)
            location: Location details {city, state, ibge_code}
            user_message: Original user message for context
        
        Returns:
            List of top 3-5 most relevant legislation items
        """
        
        logger.info(f"🔍 Starting intelligent search: theme='{theme}', keywords={keywords}, scope={scope_level}")
        
        # Step 1: Enhance keywords with context
        enhanced_keywords = self._enhance_keywords(keywords, theme, user_message)
        logger.info(f"🔎 Enhanced keywords: {enhanced_keywords}")
        
        # Step 2: Detect specific theme
        detected_theme = self._detect_theme(enhanced_keywords, theme)
        logger.info(f"🎯 Detected theme: {detected_theme}")
        
        # Step 3: Try multiple search strategies
        all_results = []
        
        # Strategy 1: Multi-source with detected theme
        try:
            results = await self.api.search_relevant_legislation(
                keywords=enhanced_keywords,
                scope=scope_level,
                location=location,
                theme=detected_theme,
                limit=15  # Get more results for filtering
            )
            all_results.extend(results)
            logger.info(f"✅ Strategy 1 (theme-based): Found {len(results)} items")
        except Exception as e:
            logger.error(f"❌ Strategy 1 failed: {e}")
        
        # Strategy 2: If no results, try broader search without theme
        if len(all_results) < 3:
            try:
                logger.info("🔄 Trying broader search without theme restriction...")
                results = await self.api.search_relevant_legislation(
                    keywords=enhanced_keywords,
                    scope=scope_level,
                    location=location,
                    theme=None,  # No theme restriction
                    limit=15
                )
                all_results.extend(results)
                logger.info(f"✅ Strategy 2 (broader): Found {len(results)} items")
            except Exception as e:
                logger.error(f"❌ Strategy 2 failed: {e}")
        
        # Strategy 3: If still no results, try with only most important keywords
        if len(all_results) < 3:
            try:
                logger.info("🔄 Trying with core keywords only...")
                core_keywords = enhanced_keywords[:2]  # Use only top 2 keywords
                results = await self.api.search_relevant_legislation(
                    keywords=core_keywords,
                    scope=3,  # Always search federal for fallback
                    location=location,
                    theme=None,  # No theme restriction
                    limit=20
                )
                all_results.extend(results)
                logger.info(f"✅ Strategy 3 (core keywords): Found {len(results)} items")
            except Exception as e:
                logger.error(f"❌ Strategy 3 failed: {e}")
        
        if not all_results:
            logger.info("📭 No legislation found from any strategy")
            return []
        
        logger.info(f"📊 Total results before processing: {len(all_results)}")
        
        # Step 4: Advanced relevance scoring
        scored_results = self._score_relevance(
            all_results,
            enhanced_keywords,
            user_message
        )
        
        # Log top scores for debugging
        for i, r in enumerate(scored_results[:5]):
            logger.info(f"  #{i+1}: Score={r.get('_relevance_score', 0)} - {r.get('title', 'N/A')[:60]}")
        
        # Step 5: Filter low-quality results (LESS STRICT)
        filtered_results = self._filter_by_quality(
            scored_results,
            enhanced_keywords,
            min_score=0  # 👈 CHANGED: Accept any score (was 2)
        )
        
        logger.info(f"🎯 After filtering: {len(filtered_results)} relevant items")
        
        # If still no results, return top scored without filtering
        if not filtered_results and scored_results:
            logger.warning("⚠️ No results passed quality filter, returning top scored items anyway")
            filtered_results = scored_results[:5]
        
        # Step 6: Process and save to database
        legislation = []
        
        for item in filtered_results[:5]:  # Top 5
            saved_item = await self._upsert_legislative_item(item, db)
            
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
                    'source': self._format_source_name(saved_item.source),
                    'relevance_score': item.get('_relevance_score', 0)
                })
        
        logger.info(f"✅ Returning {len(legislation)} legislative items")
        return legislation[:3]  # Return top 3 most relevant

    def _enhance_keywords(
        self,
        keywords: List[str],
        theme: str,
        user_message: Optional[str] = None
    ) -> List[str]:
        """
        Enhance keywords with context and variations
        
        LESS AGGRESSIVE: Keep original keywords + add some context
        """
        enhanced = list(keywords)  # Start with original keywords
        
        # Don't add generic terms that pollute results
        noise_words = {'o', 'a', 'de', 'da', 'do', 'em', 'na', 'no', 'para', 'por', 
                      'com', 'um', 'uma', 'os', 'as', 'que', 'é', 'sobre', 'ter',
                      'existe', 'lei', 'pl', 'projeto', 'PL'}  # 👈 Added 'PL'
        
        # Remove noise from original keywords
        enhanced = [k for k in enhanced if k.lower() not in noise_words]
        
        # Extract from user message if available (but don't over-extract)
        if user_message:
            words = user_message.lower().split()
            meaningful_words = [w for w in words if w not in noise_words and len(w) > 4]
            enhanced.extend(meaningful_words[:2])  # 👈 CHANGED: Only top 2 (was 5)
        
        # Remove duplicates but preserve order
        seen = set()
        result = []
        for k in enhanced:
            if k.lower() not in seen:
                seen.add(k.lower())
                result.append(k)
        
        logger.debug(f"Enhanced keywords: {keywords} -> {result}")
        return result

    def _detect_theme(
        self,
        keywords: List[str],
        explicit_theme: Optional[str] = None
    ) -> Optional[str]:
        """
        Detect specific theme from keywords
        
        Priority: explicit_theme > keyword mapping > None
        """
        # If explicit theme is specific enough, use it
        specific_themes = ['saude', 'transporte', 'educacao', 'seguranca', 
                          'meio_ambiente', 'trabalho', 'cultura', 'esporte',
                          'industria_comercio', 'desenvolvimento_urbano']
        
        if explicit_theme and explicit_theme in specific_themes:
            logger.debug(f"Using explicit theme: {explicit_theme}")
            return explicit_theme
        
        # Detect from keywords (exact match first)
        for keyword in keywords:
            kw_lower = keyword.lower()
            if kw_lower in THEME_MAPPING:
                detected = THEME_MAPPING[kw_lower]
                logger.debug(f"Theme detected (exact): '{keyword}' -> '{detected}'")
                return detected
        
        # Fallback to explicit theme if provided
        if explicit_theme:
            logger.debug(f"Using fallback explicit theme: {explicit_theme}")
            return explicit_theme
        
        logger.debug("No specific theme detected")
        return None

    def _score_relevance(
        self,
        results: List[Dict],
        keywords: List[str],
        user_message: Optional[str] = None
    ) -> List[Dict]:
        """
        Score each result by relevance to user query
        
        ADJUSTED: More lenient scoring
        """
        keywords_lower = [k.lower() for k in keywords]
        
        for result in results:
            score = 0
            
            title = result.get('title', '').lower()
            description = result.get('description', '').lower()
            
            # Factor 1: Keyword matches in title (weight: 3) 👈 REDUCED from 5
            for kw in keywords_lower:
                if kw in title:
                    score += 3
            
            # Factor 2: Keyword matches in description (weight: 1) 👈 REDUCED from 2
            for kw in keywords_lower:
                score += description.count(kw) * 1
            
            # Factor 3: Multiple keyword matches (weight: 2) 👈 REDUCED from 3
            matching_keywords = sum(1 for kw in keywords_lower if kw in title or kw in description)
            score += matching_keywords * 2
            
            # Factor 4: Recency bonus
            if result.get('year'):
                try:
                    year = int(result['year'])
                    current_year = datetime.now().year
                    if year >= current_year:
                        score += 2  # 👈 REDUCED from 3
                    elif year >= current_year - 1:
                        score += 1  # 👈 REDUCED from 2
                except:
                    pass
            
            # Factor 5: Source quality bonus
            source = result.get('source', '')
            if source in ['camara', 'senado']:
                score += 1  # 👈 REDUCED from 2
            
            # Factor 6: Has any content bonus
            if description:
                score += 1
            
            # Store score in result
            result['_relevance_score'] = score
        
        # Sort by score
        return sorted(results, key=lambda x: x.get('_relevance_score', 0), reverse=True)

    def _filter_by_quality(
        self,
        results: List[Dict],
        keywords: List[str],
        min_score: int = 0  # 👈 CHANGED: Was 2
    ) -> List[Dict]:
        """
        Filter out low-quality/irrelevant results
        
        LESS STRICT: Only remove obvious bad results
        """
        keywords_lower = [k.lower() for k in keywords]
        filtered = []
        
        for result in results:
            # Check minimum score
            if result.get('_relevance_score', 0) < min_score:
                logger.debug(f"❌ Filtered (score {result.get('_relevance_score', 0)}): {result.get('title', 'N/A')[:50]}")
                continue
            
            # Must have title
            if not result.get('title'):
                logger.debug(f"❌ Filtered (no title)")
                continue
            
            # Must have description (but can be short)
            description = result.get('description', '')
            if not description or len(description) < 10:  # 👈 CHANGED: Was 20
                logger.debug(f"❌ Filtered (no description): {result.get('title', 'N/A')[:50]}")
                continue
            
            # Passed all filters
            logger.debug(f"✅ Passed (score {result.get('_relevance_score', 0)}): {result.get('title', 'N/A')[:50]}")
            filtered.append(result)
        
        return filtered

    def _format_source_name(self, source: str) -> str:
        """Format source name for display"""
        source_names = {
            'camara': 'Câmara dos Deputados',
            'senado': 'Senado Federal',
            'lexml': 'LexML (Multi-esfera)',
            'querido_diario': 'Diário Oficial Municipal'
        }
        return source_names.get(source, source.title())

    async def _upsert_legislative_item(
        self,
        item_data: Dict,
        db: Session
    ) -> Optional[LegislativeItem]:
        """
        Insert or update legislative item in database
        
        Creates cache layer to avoid repeated API calls
        """
        try:
            source = item_data.get('source', 'unknown')
            external_id = item_data.get('id', '')
            
            # Create unique external ID with source prefix
            if not external_id.startswith(source):
                external_id = f"{source}_{external_id}"
            
            item_type = item_data.get('type', '')
            number = item_data.get('number', '')
            year = item_data.get('year', '')
            title = item_data.get('title', '')
            description = item_data.get('description', '')
            
            # Check if exists
            existing = db.query(LegislativeItem).filter(
                LegislativeItem.external_id == external_id
            ).first()
            
            if existing:
                # Update
                existing.title = title
                existing.ementa = description
                existing.summary = description[:500] if description else None
                existing.full_data = item_data
                existing.updated_at = datetime.now()
                
                db.commit()
                db.refresh(existing)
                
                logger.debug(f"🔄 Updated: {existing.title}")
                return existing
            else:
                # Create
                item = LegislativeItem(
                    external_id=external_id,
                    source=source,
                    type=item_type,
                    number=str(number),
                    year=int(year) if year and str(year).isdigit() else datetime.now().year,
                    title=title,
                    ementa=description,
                    summary=description[:500] if description else None,
                    status=item_data.get('status', 'Desconhecido'),
                    full_data=item_data,
                    keywords=[]
                )
                
                db.add(item)
                db.commit()
                db.refresh(item)
                
                logger.debug(f"➕ Created: {item.title} (source: {source})")
                return item
        
        except Exception as e:
            logger.error(f"❌ Error upserting item: {e}", exc_info=True)
            db.rollback()
            return None

    async def register_pl_view(
        self,
        user_id: str,
        pl_id: str,
        db: Session
    ):
        """Register that user viewed a legislative item"""
        try:
            interaction = PLInteraction(
                user_id=user_id,
                pl_id=pl_id,
                interaction_type='view'
            )
            
            db.add(interaction)
            db.commit()
            
            logger.info(f"👁️ Registered PL view: user={user_id}, pl={pl_id}")
        
        except Exception as e:
            logger.error(f"❌ Error registering view: {e}")
            db.rollback()

    async def close(self):
        """Close all API client connections"""
        await self.api.close_all()
        logger.debug("🔌 Closed all legislative API clients")