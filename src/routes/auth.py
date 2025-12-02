from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from src.core.database import get_db
from src.models.user import User
from src.services.auth_service import AuthService
from src.services.whatsapp_service import WhatsAppService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Pydantic Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=11, max_length=11)
    cpf: str = Field(..., min_length=11, max_length=11)
    password: str = Field(..., min_length=6)
    uf: str = Field(..., min_length=2, max_length=2)
    city: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=255)
    number: str = Field(..., min_length=1, max_length=20)

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)

class ResendCodeRequest(BaseModel):
    email: EmailStr

class AuthResponse(BaseModel):
    token: str
    user: dict

class MessageResponse(BaseModel):
    message: str
    email: Optional[str] = None


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas"
        )
    
    # Verify password
    if not AuthService.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas"
        )
    
    # Check if user is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta não verificada. Verifique seu e-mail e código WhatsApp."
        )
    
    # Generate JWT token
    token = AuthService.create_jwt_token(str(user.id), user.email)
    
    return AuthResponse(
        token=token,
        user={
            "id": str(user.id),
            "name": user.name,
            "email": user.email
        }
    )


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user and send verification code via WhatsApp
    """
    # Validate email format
    if not AuthService.validate_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail inválido"
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já cadastrado"
        )
    
    # Validate CPF
    if not AuthService.validate_cpf(request.cpf):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CPF inválido"
        )
    
    # Check if CPF already exists
    existing_cpf = db.query(User).filter(User.cpf == request.cpf).first()
    if existing_cpf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CPF já cadastrado"
        )
    
    # Validate phone
    if not AuthService.validate_phone(request.phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telefone inválido. Use 11 dígitos (DDD + número)"
        )
    
    # Validate password
    is_valid, error_msg = AuthService.validate_password(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Check if phone already exists
    # We need to check both formats (with and without 9) to avoid duplicates
    
    phones_to_check = [request.phone]
    
    if len(request.phone) == 11: # Has 9 digit
        # Check without 9
        phones_to_check.append(f"{request.phone[:2]}{request.phone[3:]}")
    elif len(request.phone) == 10: # No 9 digit
        # Check with 9
        phones_to_check.append(f"{request.phone[:2]}9{request.phone[2:]}")
        
    existing_phone = db.query(User).filter(User.phone.in_(phones_to_check)).first()
    
    if existing_phone:
        # If phone exists and has a password, it means it's already a full account
        if existing_phone.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telefone já cadastrado em uma conta existente"
            )
        # If it exists but no password, it's likely a WhatsApp-only user (or incomplete), so we'll update it
    
    # Hash password
    password_hash = AuthService.hash_password(request.password)
    
    # Prepare location JSON for chatbot compatibility
    location_json = {
        "formatted_address": f"{request.address}, {request.number} - {request.city}/{request.uf}",
        "city": request.city,
        "state": request.uf,
        "address": request.address,
        "number": request.number,
        "neighborhood": None, # Not provided in web form
        "coordinates": None   # Not provided in web form
    }

    # Create or Update user
    if existing_phone:
        # Update existing chatbot user with web registration data
        existing_phone.name = request.name
        existing_phone.email = request.email
        existing_phone.cpf = request.cpf
        existing_phone.password_hash = password_hash
        existing_phone.uf = request.uf
        existing_phone.city = request.city
        existing_phone.address = request.address
        existing_phone.number = request.number
        existing_phone.location_primary = location_json # Sync location for bot
        existing_phone.is_verified = False
        existing_phone.status = 'active' # Mark as active so bot skips onboarding
        user = existing_phone
    else:
        # Create new user
        user = User(
            phone=request.phone,
            name=request.name,
            email=request.email,
            cpf=request.cpf,
            password_hash=password_hash,
            uf=request.uf,
            city=request.city,
            address=request.address,
            number=request.number,
            location_primary=location_json, # Sync location for bot
            is_verified=False,
            status='active'  # Web users start as active
        )
        db.add(user)
    
    db.commit()
    db.refresh(user)
    
    # Generate and send verification code
    code = AuthService.create_verification_code(request.email, db)
    
    # Send code via WhatsApp
    whatsapp_result = await WhatsAppService.send_verification_code(request.phone, code)
    
    # Determine message based on mode
    if whatsapp_result.get("dev_mode"):
        message = f"✅ Usuário registrado! Código de verificação (DEV): {code}"
    elif whatsapp_result.get("success"):
        message = "Código de verificação enviado para o WhatsApp"
    else:
        # Log error but don't fail registration
        logger.error(f"Failed to send WhatsApp verification: {whatsapp_result.get('error')}")
        message = f"⚠️ Usuário registrado, mas falha ao enviar WhatsApp. Código (temporário): {code}"
    
    return MessageResponse(
        message=message,
        email=request.email
    )


@router.post("/verify", response_model=AuthResponse)
async def verify_code(
    request: VerifyCodeRequest,
    db: Session = Depends(get_db)
):
    """
    Verify the code sent via WhatsApp
    """
    # Verify the code
    if not AuthService.verify_code(request.email, request.code, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado"
        )
    
    # Find user and mark as verified
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    user.is_verified = True
    db.commit()
    db.refresh(user)
    
    # Generate JWT token
    token = AuthService.create_jwt_token(str(user.id), user.email)
    
    return AuthResponse(
        token=token,
        user={
            "id": str(user.id),
            "name": user.name,
            "email": user.email
        }
    )


@router.post("/resend-code", response_model=MessageResponse)
async def resend_code(
    request: ResendCodeRequest,
    db: Session = Depends(get_db)
):
    """
    Resend verification code via WhatsApp
    """
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário já verificado"
        )
    
    # Generate and send new code
    code = AuthService.create_verification_code(request.email, db)
    
    # Send code via WhatsApp
    whatsapp_result = await WhatsAppService.send_verification_code(user.phone, code)
    
    # Determine message based on mode
    if whatsapp_result.get("dev_mode"):
        return MessageResponse(
            message=f"✅ Código reenviado (DEV): {code}"
        )
    elif whatsapp_result.get("success"):
        return MessageResponse(
            message="Código reenviado com sucesso"
        )
    else:
        logger.error(f"Failed to resend WhatsApp verification: {whatsapp_result.get('error')}")
        return MessageResponse(
            message=f"⚠️ Falha no WhatsApp. Código (temporário): {code}"
        )
