from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.follow_up import disable_auto_follow_up, enable_auto_follow_up
from app.agents.graph import build_matching_graph
from app.agents.scoring import calculate_lead_score
from app.agents.whatsapp_send import WhatsAppSendError, send_whatsapp_text
from app.api.deps import get_current_user
from app.middleware.tenant import get_tenant_db
from app.models.lead import Lead
from app.models.lead_score import LeadScore
from app.models.office import Office
from app.schemas.lead import (
    AutoFollowUpRequest,
    FollowUpRequest,
    FollowUpResponse,
    LeadCreate,
    LeadResponse,
    MatchResult,
)
from app.schemas.lead_score import LeadScoreResponse

router = APIRouter(prefix="/leads", tags=["leads"])

DEFAULT_FOLLOW_UP_TEMPLATE = (
    "Merhaba, PortföyAI danışmanınız buradan yazıyor. {district} bölgesinde aradığınız "
    "kriterlere uygun yeni portföylerimiz oldu, size uygun bir zamanda görüşebilir miyiz?"
)


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


@router.get("", response_model=list[LeadResponse])
def list_leads(db: Session = Depends(get_tenant_db)):
    # RLS, current_user'ın office_id'si dışındaki satırları zaten filtreler.
    query = select(Lead).order_by(Lead.created_at.desc())
    return db.execute(query).scalars().all()


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_tenant_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
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
            "radius_km": float(lead.radius_km) if lead.radius_km else None,
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


@router.post("/{lead_id}/follow-up", response_model=FollowUpResponse)
def send_follow_up(
    lead_id: str,
    payload: FollowUpRequest,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Lead'e manuel tetiklenen bir WhatsApp takip mesajı gönderir. Otomatik
    (zamanlanmış) takip zinciri ayrı bir altyapı (cron/scheduler) gerektirir —
    bu, danışmanın panelden bir tıkla tetiklediği MVP versiyonu."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    office = db.get(Office, current_user["office_id"])
    if not office or not office.whatsapp_phone_number_id:
        raise HTTPException(status_code=503, detail="Bu ofis için WhatsApp gönderimi henüz bağlı değil")

    message = payload.message or DEFAULT_FOLLOW_UP_TEMPLATE.format(district=lead.district or "bölgenizde")

    try:
        send_whatsapp_text(office.whatsapp_phone_number_id, lead.contact_phone, message)
    except WhatsAppSendError as exc:
        if str(exc) == "__not_configured__":
            raise HTTPException(status_code=503, detail="WhatsApp gönderimi şu an aktif değil") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    lead.last_contacted_at = datetime.now(timezone.utc)
    db.commit()
    return FollowUpResponse(sent=True, message=message)


@router.patch("/{lead_id}/auto-follow-up", response_model=LeadResponse)
def toggle_auto_follow_up(
    lead_id: str,
    payload: AutoFollowUpRequest,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Otomatik takip zincirini açar/kapatır. Açıldığında zincir baştan başlar
    (ilk mesaj 1 gün sonra); aday yanıt verirse Intake Agent zinciri kendiliğinden
    durdurur. Gerçek gönderimi cron tetikler (bkz. POST /internal/run-follow-ups)."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    if payload.enabled:
        office = db.get(Office, current_user["office_id"])
        if not office or not office.whatsapp_phone_number_id:
            raise HTTPException(status_code=503, detail="Bu ofis için WhatsApp gönderimi henüz bağlı değil")
        enable_auto_follow_up(lead)
    else:
        disable_auto_follow_up(lead)

    db.commit()
    return lead
