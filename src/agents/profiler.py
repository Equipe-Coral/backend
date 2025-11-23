import hashlib
import logging
import google.generativeai as genai
from typing import Optional, Dict
from sqlalchemy.orm import Session
from src.models.user import User
from src.core.config import settings
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import json

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)

class ProfilerAgent:
    """Gerencia o fluxo de onboarding do usuário"""

    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
        self.geolocator = Nominatim(user_agent="coral-bot", timeout=10)

    async def check_user_exists(self, phone: str, db: Session) -> Optional[User]:
        """Verifica se usuário já existe no banco de dados"""
        try:
            user = db.query(User).filter(User.phone == phone).first()
            if user:
                logger.info(f"✅ User FOUND: {phone} | ID: {user.id} | Status: {user.status}")
            else:
                logger.info(f"🆕 NEW user: {phone}")
            return user
        except Exception as e:
            logger.error(f"❌ Error checking user existence: {e}")
            return None

    async def needs_location(self, user: User) -> bool:
        """Verifica se precisa coletar localização do usuário"""
        if not user:
            return True
        return not user.location_primary or user.status == 'onboarding_incomplete'

    async def extract_location_from_text(self, text: str) -> Dict:
        """
        Usa Gemini para extrair localização do texto do usuário.
        
        Retorna:
            {
                "has_location": bool,
                "neighborhood": str | None,
                "city": str | None,
                "state": str | None,
                "full_address": str | None,
                "confidence": float (0.0 to 1.0)
            }
        """
        prompt = f"""Extraia informações de localização do texto do usuário brasileiro.

Retorne APENAS um JSON válido no seguinte formato (sem markdown, sem texto adicional):
{{
  "has_location": true ou false,
  "neighborhood": "nome do bairro" ou null,
  "city": "nome da cidade" ou null,
  "state": "sigla do estado (SP, RJ, MG, etc)" ou null,
  "full_address": "endereço completo se fornecido" ou null,
  "confidence": 0.0 a 1.0
}}

Regras:
- Se o texto não menciona localização clara, has_location = false e confidence baixo
- Extraia bairro se mencionado, cidade e estado do Brasil
- Se só mencionar cidade, deixe neighborhood como null
- Confidence alto (0.8-1.0) se tiver cidade+estado ou bairro+cidade
- Confidence médio (0.5-0.7) se tiver só cidade
- Confidence baixo (<0.5) se for vago ou sem localização

Texto do usuário: "{text}"

JSON:"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            logger.info(f"Location extraction raw response: {response_text}")
            
            location_data = json.loads(response_text)
            
            # Validate structure
            if not isinstance(location_data, dict):
                raise ValueError("Response is not a dictionary")
            
            # Ensure all required fields exist
            location_data.setdefault("has_location", False)
            location_data.setdefault("neighborhood", None)
            location_data.setdefault("city", None)
            location_data.setdefault("state", None)
            location_data.setdefault("full_address", None)
            location_data.setdefault("confidence", 0.0)
            
            logger.info(f"Extracted location data: {location_data}")
            return location_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in location extraction: {e}. Response: {response_text}")
            return {
                "has_location": False,
                "neighborhood": None,
                "city": None,
                "state": None,
                "full_address": None,
                "confidence": 0.0
            }
        except Exception as e:
            logger.error(f"Error extracting location from text: {e}")
            return {
                "has_location": False,
                "neighborhood": None,
                "city": None,
                "state": None,
                "full_address": None,
                "confidence": 0.0
            }

    async def geocode_location(self, location_text: str) -> Dict:
        """
        Geocodifica localização usando Nominatim (OpenStreetMap).
        
        Retorna:
            {
                "coordinates": [lat, lng],
                "formatted_address": str
            }
        """
        try:
            # Add "Brasil" to improve geocoding for Brazilian addresses
            search_query = f"{location_text}, Brasil"
            logger.info(f"Geocoding: {search_query}")
            
            location = self.geolocator.geocode(search_query, language='pt')
            
            if location:
                result = {
                    "coordinates": [location.latitude, location.longitude],
                    "formatted_address": location.address
                }
                logger.info(f"Geocoded successfully: {result}")
                return result
            else:
                logger.warning(f"Could not geocode: {search_query}")
                return {
                    "coordinates": None,
                    "formatted_address": None
                }
                
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Geocoding service error: {e}")
            return {
                "coordinates": None,
                "formatted_address": None
            }
        except Exception as e:
            logger.error(f"Error geocoding location: {e}")
            return {
                "coordinates": None,
                "formatted_address": None
            }

    def generate_civic_id_hash(self, phone: str) -> str:
        """
        Gera hash SHA-256 para ID Cívico do usuário.
        
        Args:
            phone: Número de telefone do usuário
            
        Returns:
            Hash SHA-256 do telefone com salt
        """
        salt = "coral_civic_id"
        civic_id = hashlib.sha256(f"{phone}{salt}".encode()).hexdigest()
        logger.info(f"Generated Civic ID for {phone}: {civic_id[:16]}...")
        return civic_id

    async def create_user(self, phone: str, location_data: Dict, db: Session) -> User:
        """
        Cria novo usuário no banco de dados com ID Cívico.
        
        Args:
            phone: Número de telefone
            location_data: Dados de localização (JSONB)
            db: Sessão do banco de dados
            
        Returns:
            User object criado
        """
        try:
            # Generate Civic ID (for future use)
            civic_id = self.generate_civic_id_hash(phone)
            
            user = User(
                phone=phone,
                location_primary=location_data,
                status='active'
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"User created successfully: {user.id}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.rollback()
            raise
