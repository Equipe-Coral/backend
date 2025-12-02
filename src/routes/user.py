from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from src.core.database import get_db
from src.models.user import User
from src.models.demand import Demand
from src.models.demand_supporter import DemandSupporter
from src.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["User"])

# Pydantic Models
class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    cpf: str
    uf: str
    city: str
    address: str
    number: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    interests: Optional[List[str]] = None
    stats: Optional[Dict[str, int]] = None
    activities: Optional[List[Dict[str, Any]]] = None
    demandsStatus: Optional[Dict[str, Dict[str, int]]] = None

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, min_length=11, max_length=11)
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    number: Optional[str] = Field(None, min_length=1, max_length=20)
    uf: Optional[str] = Field(None, min_length=2, max_length=2)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=300)
    avatar_url: Optional[str] = Field(None, max_length=512)
    interests: Optional[List[str]] = None

class UpdateProfileResponse(BaseModel):
    message: str
    user: UserProfileResponse


# Dependency to get current user from JWT token
async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and verify JWT token from Authorization header
    """
    # Check if header starts with "Bearer "
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )
    
    # Extract token
    token = authorization.replace("Bearer ", "")
    
    # Verify token
    payload = AuthService.verify_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )
    
    # Get user from database
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado"
        )
    
    return user


# Optional authentication dependency
async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Extract and verify JWT token from Authorization header (optional)
    Returns None if no token is provided or token is invalid
    """
    if not authorization:
        return None
    
    # Check if header starts with "Bearer "
    if not authorization.startswith("Bearer "):
        return None
    
    # Extract token
    token = authorization.replace("Bearer ", "")
    
    # Verify token
    try:
        payload = AuthService.verify_jwt_token(token)
        if not payload:
            return None
    except:
        return None
    
    # Get user from database
    user_id = payload.get("user_id")
    if not user_id:
        return None
        
    user = db.query(User).filter(User.id == user_id).first()
    return user
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )
    
    return user


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile with stats and activities
    """
    # Calculate stats
    created_count = db.query(func.count(Demand.id)).filter(Demand.creator_id == current_user.id).scalar() or 0
    supported_count = db.query(func.count(DemandSupporter.demand_id)).filter(DemandSupporter.user_id == current_user.id).scalar() or 0
    active_count = db.query(func.count(Demand.id)).filter(
        Demand.creator_id == current_user.id,
        Demand.status == 'active'
    ).scalar() or 0
    completed_count = db.query(func.count(Demand.id)).filter(
        Demand.creator_id == current_user.id,
        Demand.status == 'completed'
    ).scalar() or 0
    
    stats = {
        "created": created_count,
        "supported": supported_count,
        "active": active_count,
        "completed": completed_count
    }
    
    # Get recent activities (last 5 demands created/supported)
    activities = []
    recent_demands = db.query(Demand).filter(Demand.creator_id == current_user.id).order_by(Demand.created_at.desc()).limit(5).all()
    for demand in recent_demands:
        days_ago = (func.now() - demand.created_at).days if hasattr(demand.created_at, 'days') else 0
        activities.append({
            "id": str(demand.id),
            "type": "created",
            "text": f'Você criou a demanda "{demand.title}"',
            "time": f"há {days_ago} dias" if days_ago > 0 else "hoje"
        })
    
    # Demands status breakdown
    demands_status = {
        "analysis": {"current": active_count, "total": created_count},
        "waiting": {"current": 0, "total": 0},
        "completed": {"current": completed_count, "total": completed_count}
    }
    
    return UserProfileResponse(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        phone=current_user.phone,
        cpf=current_user.cpf,
        uf=current_user.uf,
        city=current_user.city,
        address=current_user.address,
        number=current_user.number,
        bio=current_user.bio,
        avatar_url=current_user.avatar_url,
        interests=current_user.interests or [],
        stats=stats,
        activities=activities,
        demandsStatus=demands_status
    )


@router.put("/profile", response_model=UpdateProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile
    """
    # Update only provided fields
    if request.name is not None:
        current_user.name = request.name
    
    if request.phone is not None:
        # Validate phone
        if not AuthService.validate_phone(request.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telefone inválido. Use 11 dígitos (DDD + número)"
            )
        
        # Check if phone is already used by another user
        existing_phone = db.query(User).filter(
            User.phone == request.phone,
            User.id != current_user.id
        ).first()
        
        if existing_phone and existing_phone.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telefone já cadastrado por outro usuário"
            )
        
        current_user.phone = request.phone
    
    if request.address is not None:
        current_user.address = request.address
    
    if request.number is not None:
        current_user.number = request.number

    if request.uf is not None:
        # Validate UF (2 letters)
        uf_val = (request.uf or '').strip().upper()
        if len(uf_val) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="UF inválido. Use 2 letras (ex: SP)"
            )
        current_user.uf = uf_val

    if request.city is not None:
        current_user.city = request.city
    
    if request.bio is not None:
        # Validate bio length
        if len(request.bio) > 300:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Biografia deve ter no máximo 300 caracteres"
            )
        current_user.bio = request.bio
    
    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url
    
    if request.interests is not None:
        current_user.interests = request.interests
    
    # Save changes
    db.commit()
    db.refresh(current_user)
    
    return UpdateProfileResponse(
        message="Perfil atualizado com sucesso",
        user=UserProfileResponse(
            id=str(current_user.id),
            name=current_user.name,
            email=current_user.email,
            phone=current_user.phone,
            cpf=current_user.cpf,
            uf=current_user.uf,
            city=current_user.city,
            address=current_user.address,
            number=current_user.number,
            bio=current_user.bio,
            avatar_url=current_user.avatar_url,
            interests=current_user.interests or []
        )
    )
