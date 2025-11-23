import httpx
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class CamaraAPI:
    """
    Client for Câmara dos Deputados Open Data API

    API Documentation: https://dadosabertos.camara.leg.br/swagger/api.html

    Features:
    - Search propositions (PLs, PECs, etc) by keywords
    - Get detailed information about specific propositions
    - Get tramitation status
    - Automatic timeout and error handling
    """

    BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_propositions(
        self,
        keywords: List[str],
        year: Optional[int] = None,
        limit: int = 10,
        theme_code: Optional[int] = None,
        fallback_years: bool = True
    ) -> List[Dict]:
        """
        Search propositions (PLs, PECs, etc) by keywords and filters

        Note: The keywords parameter in Camara API is very strict and often returns
        no results. We use a combination of year + type + theme filtering instead,
        then filter results by keywords in the ementa text client-side.

        Args:
            keywords: List of keywords to search for (used for client-side filtering)
            year: Specific year to search (None = current year)
            limit: Maximum number of results to return
            theme_code: Theme code from Camara API (40=saude, etc)
            fallback_years: If True and no results, try previous years

        Returns:
            List of propositions found

        Example:
            >>> api = CamaraAPI()
            >>> results = await api.search_propositions(['saúde', 'SUS'], limit=5)
            >>> print(results[0]['siglaTipo'], results[0]['numero'], results[0]['ano'])
            PL 1234 2024
        """

        # Determine years to search
        current_year = datetime.now().year
        years_to_try = [year] if year else [current_year, current_year - 1, current_year - 2]

        all_propositions_found = []

        for search_year in years_to_try:
            params = {
                'itens': limit * 3,  # Get more results for client-side filtering
                'ordem': 'DESC',
                'ordenarPor': 'id',  # Most recent first
                'siglaTipo': 'PL',  # Focus on main legislation type
                'ano': search_year
            }

            # Add theme if provided
            if theme_code:
                params['codTema'] = theme_code

            try:
                url = f"{self.BASE_URL}/proposicoes"
                logger.info(f"🔍 Searching Câmara API with filters: year={search_year}, theme={theme_code}")

                response = await self.client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                all_propositions = data.get('dados', [])

                # Client-side filtering by keywords in ementa
                if keywords and all_propositions:
                    keywords_lower = [k.lower() for k in keywords]

                    for prop in all_propositions:
                        ementa = prop.get('ementa', '').lower()
                        # Check if any keyword appears in ementa
                        if any(kw in ementa for kw in keywords_lower):
                            all_propositions_found.append(prop)
                            if len(all_propositions_found) >= limit:
                                break
                else:
                    all_propositions_found.extend(all_propositions[:limit])

                # If we have enough results, stop searching
                if len(all_propositions_found) >= limit:
                    break

                # If no fallback, only search first year
                if not fallback_years:
                    break

            except httpx.TimeoutException:
                logger.error(f"⏱️ Timeout searching Câmara API for year {search_year}")
                continue
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ HTTP error searching Câmara API for year {search_year}: {e.response.status_code}")
                continue
            except Exception as e:
                logger.error(f"❌ Error searching Câmara API for year {search_year}: {e}")
                continue

        propositions = all_propositions_found[:limit]
        logger.info(f"✅ Found {len(propositions)} propositions across {len(years_to_try)} year(s)")
        return propositions

    async def get_proposition_details(self, proposition_id: int) -> Optional[Dict]:
        """
        Get complete details of a specific proposition

        Args:
            proposition_id: ID of the proposition in Câmara system

        Returns:
            Complete proposition details or None if error

        Example:
            >>> details = await api.get_proposition_details(2236371)
            >>> print(details['ementa'])
        """
        try:
            url = f"{self.BASE_URL}/proposicoes/{proposition_id}"

            logger.debug(f"📋 Fetching details for proposition {proposition_id}")
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()
            details = data.get('dados', {})

            logger.info(f"✅ Got details for proposition {proposition_id}")
            return details

        except Exception as e:
            logger.error(f"❌ Error getting proposition details: {e}")
            return None

    async def get_proposition_status(self, proposition_id: int) -> Optional[str]:
        """
        Get current tramitation status of a proposition

        Args:
            proposition_id: ID of the proposition in Câmara system

        Returns:
            Description of current status or None if error

        Example:
            >>> status = await api.get_proposition_status(2236371)
            >>> print(status)
            'Aguardando análise da Comissão de Constituição e Justiça'
        """
        try:
            url = f"{self.BASE_URL}/proposicoes/{proposition_id}/tramitacoes"

            # Get only the most recent tramitation
            response = await self.client.get(url, params={'itens': 1, 'ordem': 'DESC'})
            response.raise_for_status()

            data = response.json()
            tramitacoes = data.get('dados', [])

            if tramitacoes:
                latest = tramitacoes[0]
                return latest.get('descricaoTramitacao', 'Em tramitação')

            return 'Status desconhecido'

        except Exception as e:
            logger.error(f"❌ Error getting proposition status: {e}")
            return None

    async def close(self):
        """Close HTTP connections"""
        await self.client.aclose()
        logger.debug("🔌 Closed Câmara API client")
