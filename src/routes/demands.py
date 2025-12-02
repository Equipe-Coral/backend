from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel, Field
from typing import Optional, List
from src.core.database import get_db
from src.models.demand import Demand
from src.models.demand_supporter import DemandSupporter
from src.models.user import User
from src.routes.user import get_current_user, get_current_user_optional
from src.core.gemini import gemini_client
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demands", tags=["Demands"])

# Pydantic Models
class DemandItem(BaseModel):
    id: str
    title: str
    description: str
    location: str
    supports: int
    status: str
    category: str

class CreateDemandRequest(BaseModel):
    title: str
    description: str
    location: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = "Em Análise"

class FormalizeRequest(BaseModel):
    title: str
    description: str
    location: Optional[str] = None
    category: Optional[str] = None

class FormalizeResponse(BaseModel):
    title: str
    description: str
    location: str
    category: str

class DemandListResponse(BaseModel):
    items: List[DemandItem]
    page: int
    pageSize: int
    total: int

class TimelineItem(BaseModel):
    status: str
    date: str
    description: Optional[str] = None
    active: bool = False
    current: bool = False

class CommunityReport(BaseModel):
    summary: str
    impact: str
    organs: str
    protocol: str
    response_status: str

class RelatedBill(BaseModel):
    id: str
    title: str
    summary: str
    relation: str
    status: str

class DemandDetailResponse(BaseModel):
    id: str
    hash: Optional[str] = None
    title: str
    location: str
    status: str
    supports: int
    summary: str
    timeline: List[TimelineItem]
    communityReport: Optional[CommunityReport] = None
    relatedBills: List[RelatedBill] = []
    supportedByUser: bool

class SupportResponse(BaseModel):
    message: str
    supports: int
    supportedByUser: bool


@router.post("/formalize-ai", response_model=FormalizeResponse)
async def formalize_demand_ai(
    request: FormalizeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Use AI to formalize a demand draft
    """
    prompt = f"""
    Você é um assistente que ajuda cidadãos a formalizar demandas comunitárias para órgãos públicos.
    Reescreva a seguinte demanda de forma clara, formal e objetiva, mantendo o significado original:

    Título: {request.title}
    Descrição: {request.description}
    Localização: {request.location or '(não informada)'}
    Categoria: {request.category or '(não informada)'}

    Retorne APENAS um JSON válido no formato:
    {{
      "title": "título formalizado",
      "description": "descrição formalizada em linguagem formal e clara",
      "location": "localização formatada",
      "category": "categoria sugerida (Segurança, Infraestrutura, Meio Ambiente, Saúde ou Economia)"
    }}
    """
    
    try:
        content = await gemini_client.generate_content(prompt)
        parsed = gemini_client.parse_json(content)
        
        return FormalizeResponse(
            title=parsed.get("title", request.title),
            description=parsed.get("description", request.description),
            location=parsed.get("location", request.location or ""),
            category=parsed.get("category", request.category or "")
        )
    except Exception as e:
        logger.error(f"Error in formalize-ai: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar com IA"
        )


@router.post("", response_model=DemandItem, status_code=status.HTTP_201_CREATED)
async def create_demand(
    request: CreateDemandRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new demand
    """
    # Map fields
    location_json = {"address": request.location} if request.location else {}
    
    new_demand = Demand(
        creator_id=current_user.id,
        title=request.title,
        description=request.description,
        location=location_json,
        theme=request.category or "Outros",
        status="active", # Default status
        scope_level=1, # Default
        urgency="medium" # Default
    )
    
    db.add(new_demand)
    db.commit()
    db.refresh(new_demand)
    
    return DemandItem(
        id=str(new_demand.id),
        title=new_demand.title,
        description=new_demand.description,
        location=request.location or "",
        supports=0,
        status=new_demand.status,
        category=new_demand.theme
    )


@router.post("/{demand_id}/formalize", response_model=DemandDetailResponse)
async def formalize_demand(
    demand_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Formalize an existing demand
    """
    demand = db.query(Demand).filter(Demand.id == demand_id).first()
    
    if not demand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demanda não encontrada"
        )
    
    # Update status to indicate formalization
    demand.status = "formalized"
    
    db.commit()
    db.refresh(demand)
    
    # Return detailed response
    # We can reuse the logic from get_demand_detail, but we need to call it or duplicate logic.
    # Calling the function directly is tricky because of Depends.
    # So we duplicate the logic for now or extract it.
    
    # Format location
    location_str = "Localização não especificada"
    if demand.location:
        parts = []
        if demand.location.get('address'):
            parts.append(demand.location['address'])
        if demand.location.get('city'):
            parts.append(demand.location['city'])
        if demand.location.get('state'):
            parts.append(demand.location['state'])
        if parts:
            location_str = ", ".join(parts)
            
    # Build timeline (simplified)
    timeline = [
        TimelineItem(
            status="Relato criado",
            date=demand.created_at.strftime("%Y-%m-%d"),
            active=True
        ),
        TimelineItem(
            status="Publicado como demanda comunitária",
            date=demand.updated_at.strftime("%Y-%m-%d"),
            active=True,
            current=True
        )
    ]
    
    summary = f"Esta demanda foi formalizada e publicada. {demand.description[:200]}..."
    
    return DemandDetailResponse(
        id=str(demand.id),
        hash=f"0x{str(demand.id)[:8]}",
        title=demand.title,
        location=location_str,
        status=demand.status,
        supports=demand.supporters_count or 0,
        summary=summary,
        timeline=timeline,
        communityReport=None,
        relatedBills=[],
        supportedByUser=False # Creator supports it? Maybe.
    )


@router.get("", response_model=DemandListResponse)
async def list_demands(
    q: Optional[str] = Query(None, description="Search term"),
    city: Optional[str] = Query(None, description="City filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    status_filter: Optional[str] = Query(None, alias="status", description="Status filter"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    List demands with optional filters and pagination
    """
    # Build query
    query = db.query(Demand)
    
    # Apply filters
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Demand.title.ilike(search_term),
                Demand.description.ilike(search_term)
            )
        )
    
    if city:
        # Filter by city in location JSON
        query = query.filter(Demand.location['city'].astext.ilike(f"%{city}%"))
    
    if category:
        query = query.filter(Demand.theme.ilike(f"%{category}%"))
    
    if status_filter:
        query = query.filter(Demand.status.ilike(f"%{status_filter}%"))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * pageSize
    demands = query.order_by(Demand.created_at.desc()).offset(offset).limit(pageSize).all()
    
    # Format response
    items = []
    for demand in demands:
        # Format location
        location_str = "Localização não especificada"
        if demand.location:
            parts = []
            if demand.location.get('address'):
                parts.append(demand.location['address'])
            if demand.location.get('city'):
                parts.append(demand.location['city'])
            if demand.location.get('state'):
                parts.append(demand.location['state'])
            if parts:
                location_str = ", ".join(parts)
        
        items.append(DemandItem(
            id=str(demand.id),
            title=demand.title,
            description=demand.description[:150] + "..." if len(demand.description) > 150 else demand.description,
            location=location_str,
            supports=demand.supporters_count or 0,
            status=demand.status.replace('_', ' ').title(),
            category=demand.theme
        ))
    
    return DemandListResponse(
        items=items,
        page=page,
        pageSize=pageSize,
        total=total
    )


@router.get("/{demand_id}", response_model=DemandDetailResponse)
async def get_demand_detail(
    demand_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get detailed information about a specific demand.
    Authentication is optional - if provided, will include supportedByUser flag.
    """
    # Find demand
    demand = db.query(Demand).filter(Demand.id == demand_id).first()
    
    if not demand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demanda não encontrada"
        )
    
    # Check if current user supports this demand
    supported_by_user = False
    if current_user:
        support = db.query(DemandSupporter).filter(
            DemandSupporter.demand_id == demand.id,
            DemandSupporter.user_id == current_user.id
        ).first()
        supported_by_user = support is not None
    
    # Format location
    location_str = "Localização não especificada"
    if demand.location:
        parts = []
        if demand.location.get('address'):
            parts.append(demand.location['address'])
        if demand.location.get('city'):
            parts.append(demand.location['city'])
        if demand.location.get('state'):
            parts.append(demand.location['state'])
        if parts:
            location_str = ", ".join(parts)
    
    # Build timeline (simplified)
    timeline = [
        TimelineItem(
            status="Relato criado",
            date=demand.created_at.strftime("%Y-%m-%d"),
            active=True
        ),
        TimelineItem(
            status="Publicado como demanda comunitária",
            date=demand.created_at.strftime("%Y-%m-%d"),
            active=True
        )
    ]
    
    # Add report status if enough supports
    if demand.supporters_count >= 10:
        timeline.append(TimelineItem(
            status="Relatório criado",
            description="Atingiu limiar de apoios",
            date=demand.updated_at.strftime("%Y-%m-%d"),
            active=True,
            current=True
        ))
    
    # Generate summary (simplified)
    summary = f"Esta demanda foi criada para abordar questões relacionadas a {demand.theme}. {demand.description[:200]}..."
    
    # Community report (if applicable)
    community_report = None
    if demand.supporters_count >= 10:
        community_report = CommunityReport(
            summary=f"Relatório comunitário sobre: {demand.title}",
            impact=f"Impacto estimado: Alto. Afeta diretamente a comunidade de {demand.location.get('city', 'região não especificada') if demand.location else 'região não especificada'}.",
            organs="Prefeitura Municipal, Secretaria competente",
            protocol=f"PROTO-2025-{str(demand.id)[:5]}",
            response_status="Aguardando resposta"
        )
    
    # Related bills (placeholder - would query legislative_items in real implementation)
    related_bills = []
    
    return DemandDetailResponse(
        id=str(demand.id),
        hash=f"0x{str(demand.id)[:8]}",
        title=demand.title,
        location=location_str,
        status=demand.status,
        supports=demand.supporters_count or 0,
        summary=summary,
        timeline=timeline,
        communityReport=community_report,
        relatedBills=related_bills,
        supportedByUser=supported_by_user
    )


@router.post("/{demand_id}/support", response_model=SupportResponse)
async def support_demand(
    demand_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add support to a demand (authenticated users only)
    """
    # Find demand
    demand = db.query(Demand).filter(Demand.id == demand_id).first()
    
    if not demand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demanda não encontrada"
        )
    
    # Check if already supported
    existing_support = db.query(DemandSupporter).filter(
        DemandSupporter.demand_id == demand.id,
        DemandSupporter.user_id == current_user.id
    ).first()
    
    if existing_support:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você já apoia esta demanda"
        )
    
    # Add support
    support = DemandSupporter(
        demand_id=demand.id,
        user_id=current_user.id
    )
    db.add(support)
    
    # Update counter
    demand.supporters_count = (demand.supporters_count or 0) + 1
    
    db.commit()
    db.refresh(demand)
    
    return SupportResponse(
        message="Apoio registrado",
        supports=demand.supporters_count,
        supportedByUser=True
    )
