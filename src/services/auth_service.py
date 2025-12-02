from datetime import datetime, timedelta
from typing import Optional
import bcrypt
import random
import re
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from src.core.config import settings
from src.models.user import User
from src.models.verification_code import VerificationCode

class AuthService:
    """Service for handling authentication operations"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    @staticmethod
    def create_jwt_token(user_id: str, email: str) -> str:
        """Create a JWT token for a user"""
        # Parse JWT_EXPIRES_IN (e.g., "7d" -> 7 days)
        expires_in = settings.JWT_EXPIRES_IN
        if expires_in.endswith('d'):
            days = int(expires_in[:-1])
            expiration = datetime.utcnow() + timedelta(days=days)
        elif expires_in.endswith('h'):
            hours = int(expires_in[:-1])
            expiration = datetime.utcnow() + timedelta(hours=hours)
        else:
            # Default to 7 days
            expiration = datetime.utcnow() + timedelta(days=7)
        
        payload = {
            'user_id': str(user_id),
            'email': email,
            'exp': expiration,
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return token
    
    @staticmethod
    def verify_jwt_token(token: str) -> Optional[dict]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def generate_verification_code() -> str:
        """Generate a 6-digit verification code"""
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def create_verification_code(email: str, db: Session) -> str:
        """Create and store a verification code for an email"""
        # Delete old codes for this email
        db.query(VerificationCode).filter(
            VerificationCode.email == email
        ).delete()
        
        # Generate new code
        code = AuthService.generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Store in database
        verification = VerificationCode(
            email=email,
            code=code,
            expires_at=expires_at
        )
        db.add(verification)
        db.commit()
        
        return code
    
    @staticmethod
    def verify_code(email: str, code: str, db: Session) -> bool:
        """Verify a code for an email"""
        verification = db.query(VerificationCode).filter(
            VerificationCode.email == email,
            VerificationCode.code == code,
            VerificationCode.expires_at > datetime.utcnow()
        ).first()
        
        if verification:
            # Delete the code after successful verification
            db.delete(verification)
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_cpf(cpf: str) -> bool:
        """Validate CPF (simplified - only checks format and length)"""
        # Remove any non-digit characters
        cpf = re.sub(r'\D', '', cpf)
        
        # Check if it has 11 digits
        if len(cpf) != 11:
            return False
        
        # Check if all digits are the same (invalid CPF)
        if cpf == cpf[0] * 11:
            return False
        
        # Basic validation passed
        return True
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate Brazilian phone format (11 digits)"""
        # Remove any non-digit characters
        phone = re.sub(r'\D', '', phone)
        
        # Check if it has 11 digits (DDD + 9 digits)
        return len(phone) == 11
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 6:
            return False, "Senha deve ter no mínimo 6 caracteres"
        
        return True, ""
