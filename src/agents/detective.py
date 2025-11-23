from src.services.camara_api import CamaraAPI
from src.models.legislative_item import LegislativeItem
from src.models.pl_interaction import PLInteraction
from sqlalchemy.orm import Session
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DetectiveAgent:
    """
    Investigates legislative items (PLs, PECs) related to user demands

    Responsibilities:
    - Search for related PLs using Câmara API
    - Cache PLs in database to reduce API calls
    - Expand keywords by theme for better search results
    - Track user interactions with PLs
    """

    def __init__(self):
        self.camara_api = CamaraAPI()

    async def find_related_pls(
        self,
        theme: str,
        keywords: List[str],
        db: Session
    ) -> List[Dict]:
        """
        Find PLs related to a theme/demand

        Flow:
        1. Expand keywords based on theme
        2. Search Câmara API
        3. Save/update PLs in database (cache)
        4. Return formatted results

        Args:
            theme: Theme of the demand (saude, transporte, etc)
            keywords: Keywords from user message
            db: Database session

        Returns:
            List of related PLs with formatted data

        Example:
            >>> detective = DetectiveAgent()
            >>> pls = await detective.find_related_pls('saude', ['hospital'], db)
            >>> print(pls[0]['title'])
            'PL 1234/2024'
        """

        # 1. Expand keywords by theme
        expanded_keywords = self._expand_keywords(theme, keywords)
        logger.info(f"🔍 Searching PLs for theme '{theme}' with keywords: {expanded_keywords}")

        # 2. Search Câmara API
        propositions = await self.camara_api.search_propositions(
            keywords=expanded_keywords,
            limit=5
        )

        # 2.1. If no results with keywords, try without keyword filtering
        if not propositions and expanded_keywords:
            logger.info("🔄 No results with keywords, trying broader search...")
            propositions = await self.camara_api.search_propositions(
                keywords=[],  # No keyword filtering
                limit=5
            )

        if not propositions:
            logger.info("📭 No PLs found in Câmara API")
            return []

        # 3. Process and save to database
        pls = []
        for prop in propositions:
            pl = await self._upsert_legislative_item(prop, db)
            if pl:
                pls.append({
                    'id': str(pl.id),
                    'external_id': pl.external_id,
                    'type': pl.type,
                    'number': pl.number,
                    'year': pl.year,
                    'title': pl.title,
                    'summary': pl.summary,
                    'ementa': pl.ementa,
                    'status': pl.status
                })

        logger.info(f"✅ Processed {len(pls)} PLs")
        return pls

    def _expand_keywords(self, theme: str, keywords: List[str]) -> List[str]:
        """
        Expand keywords based on theme

        Adds related terms to improve search results in Câmara API

        Args:
            theme: Theme identifier
            keywords: Original keywords from user

        Returns:
            Expanded list of keywords (max 5 to avoid too broad searches)

        Example:
            >>> detective._expand_keywords('saude', ['hospital'])
            ['hospital', 'saúde', 'SUS', 'médico']
        """

        theme_expansions = {
            'saude': ['saúde', 'SUS', 'hospital', 'médico', 'atendimento', 'medicamento'],
            'transporte': ['transporte', 'mobilidade', 'ônibus', 'metrô', 'trânsito', 'viário'],
            'educacao': ['educação', 'escola', 'ensino', 'professor', 'aluno', 'estudante'],
            'seguranca': ['segurança', 'polícia', 'violência', 'crime', 'policial'],
            'meio_ambiente': ['meio ambiente', 'ambiental', 'poluição', 'sustentabilidade', 'ecologia'],
            'zeladoria': ['urbano', 'cidade', 'municipal', 'infraestrutura', 'zeladoria', 'público'],
            'habitacao': ['habitação', 'moradia', 'casa', 'imóvel', 'residencial'],
            'assistencia_social': ['assistência social', 'social', 'vulnerabilidade', 'família'],
            'cultura': ['cultura', 'cultural', 'arte', 'artista', 'patrimônio'],
            'esporte': ['esporte', 'esportivo', 'atleta', 'lazer', 'recreação'],
            'animais': ['animal', 'animais', 'pet', 'cão', 'cachorro', 'gato', 'proteção animal'],
            'consumidor': ['consumidor', 'consumo', 'direito do consumidor', 'estabelecimento', 'comércio'],
            'outros': []  # For 'outros', use only the original keywords from user
        }

        # Start with original keywords
        expanded = list(keywords)

        # Add theme-specific expansions
        if theme in theme_expansions:
            expanded.extend(theme_expansions[theme])

        # Remove duplicates and limit to 5 keywords
        # (too many keywords can make search too broad)
        expanded = list(set(expanded))[:5]

        return expanded

    async def _upsert_legislative_item(
        self,
        proposition_data: Dict,
        db: Session
    ) -> Optional[LegislativeItem]:
        """
        Insert or update legislative item in database

        Uses external_id as unique key (upsert pattern)
        This creates a cache layer to avoid repeated API calls

        Args:
            proposition_data: Data from Câmara API
            db: Database session

        Returns:
            LegislativeItem object or None if error
        """
        try:
            external_id = str(proposition_data['id'])

            # Check if already exists
            existing = db.query(LegislativeItem).filter(
                LegislativeItem.external_id == external_id
            ).first()

            # Extract data from API response
            siglaTipo = proposition_data.get('siglaTipo', 'PL')
            numero = proposition_data.get('numero', '')
            ano = proposition_data.get('ano', datetime.now().year)
            ementa = proposition_data.get('ementa', '')

            if existing:
                # Update existing record
                existing.title = f"{siglaTipo} {numero}/{ano}"
                existing.ementa = ementa
                existing.summary = ementa[:500] if ementa else None
                existing.full_data = proposition_data
                existing.updated_at = datetime.now()

                db.commit()
                db.refresh(existing)

                logger.debug(f"🔄 Updated PL: {existing.title}")
                return existing
            else:
                # Create new record
                pl = LegislativeItem(
                    external_id=external_id,
                    source='camara',
                    type=siglaTipo,
                    number=str(numero),
                    year=int(ano),
                    title=f"{siglaTipo} {numero}/{ano}",
                    ementa=ementa,
                    summary=ementa[:500] if ementa else None,
                    status='Em tramitação',
                    full_data=proposition_data,
                    keywords=[]  # Will be populated in future updates
                )

                db.add(pl)
                db.commit()
                db.refresh(pl)

                logger.debug(f"➕ Created PL: {pl.title}")
                return pl

        except Exception as e:
            logger.error(f"❌ Error upserting legislative item: {e}")
            db.rollback()
            return None

    async def register_pl_view(
        self,
        user_id: str,
        pl_id: str,
        db: Session
    ):
        """
        Register that user viewed a PL

        Used for analytics and future recommendation systems

        Args:
            user_id: UUID of the user
            pl_id: UUID of the legislative item
            db: Database session
        """
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
            logger.error(f"❌ Error registering PL view: {e}")
            db.rollback()

    async def close(self):
        """Close API client connections"""
        await self.camara_api.close()
