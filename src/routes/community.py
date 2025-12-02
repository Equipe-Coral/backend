from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.core.database import get_db
from src.models.demand import Demand
from src.models.demand_supporter import DemandSupporter
from src.models.user import User
from typing import List, Dict

router = APIRouter(prefix="/api/community", tags=["Community"])

@router.get("/stats")
async def get_community_stats(db: Session = Depends(get_db)):
    demands_count = db.query(Demand).filter(Demand.status == 'active').count()
    contributions_count = db.query(DemandSupporter).count()
    # Engaged users: simple count of users for now
    engaged_count = db.query(User).count()
    
    return {
        "demands": demands_count,
        "contributions": contributions_count,
        "engaged": engaged_count
    }

@router.get("/categories")
async def get_category_stats(db: Session = Depends(get_db)):
    # Group demands by theme and count
    stats = db.query(Demand.theme, func.count(Demand.id)).group_by(Demand.theme).all()
    
    result = []
    for theme, count in stats:
        result.append({
            "id": theme,
            "count": count
        })
        
    return result
