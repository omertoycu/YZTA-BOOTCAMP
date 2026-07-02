from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.graph import build_matching_graph
from app.agents.scoring import calculate_lead_score
from app.api.deps import get_current_user
from app.middleware.tenant import get_tenant_db
from app.models.lead import Lead
from app.models.lead_score import LeadScore
from app.schemas.lead import LeadCreate, LeadResponse, MatchResult
from app.schemas.lead_score import LeadScoreResponse

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadResponse, status_code=201)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    lead = Lead(office_id=current_user["office_id"], **payload.model_dump())
    db.add(lead)
    db.commit()
    return lead


@router.post("/{lead_id}/match", response_model=list[MatchResult])
def match_lead(lead_id: str, db: Session = Depends(get_tenant_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    graph = build_matching_graph(db)
    result = graph.invoke(
        {
            "office_id": str(lead.office_id),
            "lead_id": str(lead.id),
            "budget_min": float(lead.budget_min) if lead.budget_min else None,
            "budget_max": float(lead.budget_max) if lead.budget_max else None,
            "room_count": lead.room_count,
            "district": lead.district,
        }
    )
    return result["candidate_listings"]


@router.post("/{lead_id}/score", response_model=LeadScoreResponse, status_code=201)
def score_lead(
    lead_id: str,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    score, breakdown = calculate_lead_score(lead)
    lead_score = LeadScore(
        office_id=current_user["office_id"],
        lead_id=lead.id,
        score=score,
        score_breakdown=breakdown,
    )
    db.add(lead_score)
    db.commit()
    return lead_score
