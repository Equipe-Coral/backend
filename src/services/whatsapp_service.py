import httpx
import logging
from typing import Optional
from src.core.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    """Service for sending WhatsApp messages via whatsapp-bot service"""
    
    # URL of the whatsapp-bot service
    WHATSAPP_BOT_URL = settings.WHATSAPP_BOT_URL
    
    @staticmethod
    async def send_message(phone: str, message: str) -> dict:
        """
        Send a generic message via WhatsApp
        
        Args:
            phone: Phone number (can be with or without @c.us suffix)
            message: Message text to send
            
        Returns:
            dict with 'success' key and optional 'error' message
        """
        # Clean phone number (remove @c.us if present)
        clean_phone = phone.replace('@c.us', '')
        
        # Development mode: skip WhatsApp and just log
        if settings.SKIP_WHATSAPP_IN_DEV:
            logger.info(f"📤 DEV MODE: Would send message to {clean_phone}")
            logger.info(f"Message: {message[:100]}...")
            return {"success": True, "dev_mode": True}
        
        try:
            # Format phone with country code if needed
            if not clean_phone.startswith('55'):
                formatted_phone = f"55{clean_phone}"
            else:
                formatted_phone = clean_phone
            
            # Send request to whatsapp-bot service
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{WhatsAppService.WHATSAPP_BOT_URL}/send-message",
                    json={
                        "phone": formatted_phone,
                        "message": message
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"Message sent successfully to {clean_phone}")
                    return {"success": True}
                else:
                    error_msg = f"Failed to send message: {response.status_code}"
                    logger.error(f"{error_msg} - {response.text}")
                    return {"success": False, "error": error_msg}
                    
        except Exception as e:
            error_msg = f"Error sending WhatsApp message: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    @staticmethod
    async def send_verification_code(phone: str, code: str) -> dict:
        """
        Send verification code via WhatsApp
        
        Args:
            phone: Phone number (11 digits - DDD + number)
            code: 6-digit verification code
            
        Returns:
            dict with 'success' key and optional 'error' message
        """
        # Development mode: skip WhatsApp and just log
        if settings.SKIP_WHATSAPP_IN_DEV:
            logger.warning(f"⚠️  DEV MODE: Skipping WhatsApp. Code for {phone}: {code}")
            print(f"\n{'='*60}")
            print(f"🔐 CÓDIGO DE VERIFICAÇÃO (DEV MODE)")
            print(f"{'='*60}")
            print(f"Telefone: {phone}")
            print(f"Código: {code}")
            print(f"{'='*60}\n")
            return {"success": True, "dev_mode": True}
        
        try:
            message = (
                f"🌊 *Coral - Código de Verificação*\n\n"
                f"Seu código de verificação é: *{code}*\n\n"
                f"Este código expira em 10 minutos.\n\n"
                f"Se você não solicitou este código, ignore esta mensagem."
            )
            
            # Format phone with country code: 55 (Brazil) + phone
            formatted_phone = f"55{phone}"
            
            # Send request to whatsapp-bot service
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{WhatsAppService.WHATSAPP_BOT_URL}/send-message",
                    json={
                        "phone": formatted_phone,
                        "message": message
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"Verification code sent successfully to {phone}")
                    return {"success": True}
                else:
                    error_msg = f"Failed to send message: {response.status_code}"
                    logger.error(f"{error_msg} - {response.text}")
                    return {"success": False, "error": error_msg}
                    
        except httpx.TimeoutException:
            error_msg = "Timeout ao enviar mensagem via WhatsApp"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Erro ao enviar mensagem via WhatsApp: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}
    
    @staticmethod
    async def check_whatsapp_connection() -> bool:
        """
        Check if WhatsApp bot service is connected and ready
        
        Returns:
            bool indicating if service is available
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{WhatsAppService.WHATSAPP_BOT_URL}/status"
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"WhatsApp bot service not available: {e}")
            return False
