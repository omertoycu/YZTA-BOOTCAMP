from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.calendar_invite import build_appointment_ics
from app.agents.follow_up import disable_auto_follow_up, enable_auto_follow_up
from app.agents.graph import build_matching_graph
from app.agents.lead_voice_note import VoiceNoteError, transcribe_and_extract_note
from app.agents.match_ranking import rerank_candidates_with_ai
from app.agents.reply_draft import ReplyDraftError, draft_reply
from app.agents.scoring import calculate_lead_score
from app.agents.voice_listing import MAX_AUDIO_BYTES
from app.agents.whatsapp_extract import (
    MAX_EXTRACTIONS_PER_24H,
    WhatsAppExtractError,
    compute_new_extraction_counters,
    extract_lead_fields,
    should_run_extraction,
)
from app.agents.whatsapp_send import WhatsAppSendError, send_whatsapp_text
from app.api.deps import get_current_user
from app.middleware.tenant import get_tenant_db
from app.models.lead import Lead
from app.models.lead_note import LeadNote
from app.models.lead_score import LeadScore
from app.models.office import Office
from app.models.user import User
from app.models.whatsapp_message import WhatsAppMessage
from app.schemas.lead import (
    AppointmentCreate,
    AppointmentResponse,
    AutoFollowUpRequest,
    DealUpdate,
    FollowUpRequest,
    FollowUpResponse,
    LeadCreate,
    LeadFieldExtractionDraft,
    LeadNoteCreate,
    LeadNoteResponse,
    LeadReminderUpdate,
    LeadResponse,
    LeadStatusUpdate,
    LeadUpdate,
    LeadVoiceNoteDraftResponse,
    MatchResult,
    SendMatchesResponse,
    SuggestReplyResponse,
    WhatsAppMessageResponse,
)
from app.schemas.lead_score import LeadScoreResponse

router = APIRouter(prefix="/leads", tags=["leads"])

def _build_default_follow_up(lead: Lead, office: Office) -> str:
    """Tek tık takip mesajının varsayılan metni — eskiden herkes için aynı tek
    cümleydi; artık adayın adı ve bilinen kriterleriyle kişiselleştiriliyor
    (deterministik, Gemini maliyeti yok — AI'lı kişisel yanıt isteyen danışman
    zaten "AI ile Yanıt Öner" akışını kullanıyor)."""
    greeting = f"Merhaba {lead.contact_name}," if lead.contact_name else "Merhaba,"
    criteria_parts = []
    if lead.room_count:
        criteria_parts.append(lead.room_count)
    if lead.listing_type_preference:
        criteria_parts.append("satılık" if lead.listing_type_preference == "sale" else "kiralık")
    if lead.budget_max:
        criteria_parts.append(f"{float(lead.budget_max):,.0f} TL'ye kadar".replace(",", "."))
    criteria = f" ({', '.join(criteria_parts)})" if criteria_parts else ""
    district = lead.district or "aradığınız bölgede"
    if lead.district:
        district = f"{lead.district} bölgesinde"
    return (
        f"{greeting} ben {office.name} danışmanınız. {district} aradığınız kriterlere{criteria} "
        "uygun portföyleri sizin için takip ediyorum — yeni seçenekleri birlikte değerlendirmek "
        "için size uygun bir zamanda görüşebilir miyiz?"
    )

# Satış hunisi aşamaları — won/lost terminal, gerisi ileri-geri serbest
# (danışman yanlış tıklamayı düzeltebilmeli, katı bir state machine değil).
LEAD_STATUSES = ("new", "contacted", "viewing", "negotiation", "won", "lost")


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


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: str, db: Session = Depends(get_tenant_db)):
    """Adayı kalıcı olarak siler. Bağlı notlar/skorlar/WhatsApp geçmişi
    (lead_notes, lead_scores, whatsapp_inbound_events, whatsapp_messages)
    migration 0019'daki ON DELETE CASCADE ile otomatik silinir — burada
    ayrıca elle temizlemeye gerek yok. Geri alınamaz, frontend onay ister."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
    db.delete(lead)
    db.commit()


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: str, payload: LeadUpdate, db: Session = Depends(get_tenant_db)):
    """Danışmanın AI'ın yanlış/eksik çıkardığı bölge/bütçe/oda/yarıçap
    alanlarını elle düzeltmesi (bkz. PATCH /offices/me ile aynı exclude_unset
    deseni) — hem manuel düzeltme hem de POST /{id}/reanalyze-messages'ın
    döndürdüğü taslağı onaylamanın TEK yazma yolu."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(lead, field, value)
    if updates:
        lead.fields_extracted_by_ai = False
    db.commit()
    return lead


@router.get("/{lead_id}/messages", response_model=list[WhatsAppMessageResponse])
def list_lead_messages(lead_id: str, db: Session = Depends(get_tenant_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
    return (
        db.execute(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.lead_id == lead.id)
            .order_by(WhatsAppMessage.created_at.asc())
        )
        .scalars()
        .all()
    )


def _lead_to_match_state(lead: Lead) -> dict:
    return {
        "office_id": str(lead.office_id),
        "lead_id": str(lead.id),
        "budget_min": float(lead.budget_min) if lead.budget_min else None,
        "budget_max": float(lead.budget_max) if lead.budget_max else None,
        "room_count": lead.room_count,
        "district": lead.district,
        "radius_km": float(lead.radius_km) if lead.radius_km else None,
        "listing_type_preference": lead.listing_type_preference,
        "property_type_preference": lead.property_type_preference,
    }


def _last_inbound_message_text(db: Session, lead_id) -> str | None:
    return db.execute(
        select(WhatsAppMessage.body)
        .where(WhatsAppMessage.lead_id == lead_id, WhatsAppMessage.direction == "in")
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _match_criteria(lead: Lead) -> dict:
    """rerank_candidates_with_ai'ın prompt'una geçirilen okunabilir kriter özeti."""
    return {
        "bölge": lead.district,
        "bütçe_min": float(lead.budget_min) if lead.budget_min else None,
        "bütçe_max": float(lead.budget_max) if lead.budget_max else None,
        "oda_sayısı": lead.room_count,
        "işlem_tipi": lead.listing_type_preference,
        "emlak_tipi": lead.property_type_preference,
    }


@router.post("/{lead_id}/match", response_model=list[MatchResult])
def match_lead(lead_id: str, db: Session = Depends(get_tenant_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    graph = build_matching_graph(db)
    result = graph.invoke(_lead_to_match_state(lead))
    return rerank_candidates_with_ai(
        original_message=_last_inbound_message_text(db, lead.id),
        criteria=_match_criteria(lead),
        candidates=result["candidate_listings"],
    )


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
    payload: FollowUpRequest = FollowUpRequest(),
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Lead'e manuel tetiklenen bir WhatsApp takip mesajı gönderir. Otomatik
    (zamanlanmış) takip zinciri ayrı bir altyapı (cron/scheduler) gerektirir —
    bu, danışmanın panelden bir tıkla tetiklediği MVP versiyonu.

    payload'un varsayılanı var: frontend'in "Takip Mesajı Gönder" butonu hiç
    body göndermiyor (sadece override mesajı yazılacaksa body atılır) — varsayılan
    olmadan FastAPI, body tamamen eksik olduğunda 422 "Field required" döner ve bu
    hiç WhatsApp bağlantısı kontrolüne bile ulaşmadan buton her zaman patlar."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    office = db.get(Office, current_user["office_id"])
    if not office or not office.whatsapp_phone_number_id:
        raise HTTPException(status_code=503, detail="Bu ofis için WhatsApp gönderimi henüz bağlı değil")

    message = payload.message or _build_default_follow_up(lead, office)

    try:
        send_whatsapp_text(office.whatsapp_phone_number_id, lead.contact_phone, message)
    except WhatsAppSendError as exc:
        if str(exc) == "__not_configured__":
            raise HTTPException(status_code=503, detail="WhatsApp gönderimi şu an aktif değil") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    lead.last_contacted_at = datetime.now(timezone.utc)
    db.add(
        WhatsAppMessage(
            office_id=lead.office_id, lead_id=lead.id, direction="out", message_type="text", body=message
        )
    )
    db.commit()
    return FollowUpResponse(sent=True, message=message)


@router.patch("/{lead_id}/status", response_model=LeadResponse)
def update_lead_status(
    lead_id: str,
    payload: LeadStatusUpdate,
    db: Session = Depends(get_tenant_db),
):
    """Lead'i satış hunisinde bir aşamaya taşır. Kazanıldı/kaybedildi'ye
    taşınan lead'in otomatik takip zinciri de kapatılır — kapanmış bir
    konuşmaya takip mesajı gitmemeli."""
    if payload.status not in LEAD_STATUSES:
        raise HTTPException(status_code=400, detail=f"Geçersiz durum. Geçerli değerler: {', '.join(LEAD_STATUSES)}")

    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    lead.status = payload.status
    if payload.status in ("won", "lost"):
        disable_auto_follow_up(lead)
    db.commit()
    return lead


@router.post("/{lead_id}/notes", response_model=LeadNoteResponse, status_code=201)
def create_lead_note(
    lead_id: str,
    payload: LeadNoteCreate,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Not boş olamaz")

    note = LeadNote(
        office_id=current_user["office_id"],
        lead_id=lead.id,
        author_id=current_user["user_id"],
        body=body,
    )
    db.add(note)
    # Yazar, commit'ten ÖNCE okunmalı: commit SET LOCAL tenant context'ini
    # sıfırlar ve sonraki SELECT'i RLS boş döndürür (bkz. CLAUDE.md madde 2/7).
    author = db.get(User, current_user["user_id"])
    author_email = author.email if author else None
    db.commit()
    response = LeadNoteResponse.model_validate(note)
    response.author_email = author_email
    return response


@router.get("/{lead_id}/notes", response_model=list[LeadNoteResponse])
def list_lead_notes(lead_id: str, db: Session = Depends(get_tenant_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    notes = (
        db.execute(select(LeadNote).where(LeadNote.lead_id == lead.id).order_by(LeadNote.created_at.desc()))
        .scalars()
        .all()
    )
    # Yazar e-postaları tek sorguda toplanır (not başına ayrı SELECT atılmaz).
    author_ids = {note.author_id for note in notes}
    authors = {
        user.id: user.email
        for user in db.execute(select(User).where(User.id.in_(author_ids))).scalars().all()
    } if author_ids else {}

    responses = []
    for note in notes:
        response = LeadNoteResponse.model_validate(note)
        response.author_email = authors.get(note.author_id)
        responses.append(response)
    return responses


@router.post("/{lead_id}/voice-note", response_model=LeadVoiceNoteDraftResponse)
def create_lead_voice_note(
    lead_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Danışmanın saha dönüşü bir aday hakkında kaydettiği sesli notu Gemini ile
    görüşme notu özeti + önerilen pipeline durumu + hatırlatma taslağına çevirir.
    Hiçbir şey otomatik yazılmaz — frontend, danışman taslağı gözden geçirip
    onayladıktan sonra mevcut POST /leads/{id}/notes, PATCH /leads/{id}/status
    ve PATCH /leads/{id}/reminder uç noktalarını çağırarak kalıcı hale getirir."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    audio_bytes = file.file.read(MAX_AUDIO_BYTES + 1)
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Ses kaydı çok büyük (maksimum 20MB)")
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Boş ses kaydı")

    content_type = (file.content_type or "audio/webm").split(";")[0].strip()

    try:
        draft = transcribe_and_extract_note(audio_bytes, content_type)
    except VoiceNoteError as exc:
        if str(exc) == "__not_configured__":
            raise HTTPException(status_code=503, detail="Sesli not işleme şu an aktif değil") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return LeadVoiceNoteDraftResponse(**draft)


@router.patch("/{lead_id}/reminder", response_model=LeadResponse)
def update_lead_reminder(
    lead_id: str,
    payload: LeadReminderUpdate,
    db: Session = Depends(get_tenant_db),
):
    """Danışmanın kendine bıraktığı kişisel hatırlatmayı (tarih + not) set eder
    ya da temizler (reminder_at=null gönderilerek). Otomatik WhatsApp takip
    zincirinden (auto_follow_up_enabled/next_follow_up_at) tamamen bağımsızdır —
    adaya hiçbir otomatik mesaj gitmez, sadece danışman panelinde görünür."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    lead.reminder_at = payload.reminder_at
    lead.reminder_note = payload.reminder_note
    db.commit()
    return lead


@router.patch("/{lead_id}/deal", response_model=LeadResponse)
def update_lead_deal(
    lead_id: str,
    payload: DealUpdate,
    db: Session = Depends(get_tenant_db),
):
    """Komisyon takibi: satış/kira bedeli + danışmanın kazandığı komisyonu
    kaydeder. Bilinçli olarak `PATCH /{lead_id}/status` (won/lost geçişi) ile
    birleştirilmedi — danışman sözleşme detaylarını genelde durum
    değişiminden günler sonra netleştirir, ayrı ayrı güncellenebilmeli."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    lead.deal_amount = payload.deal_amount
    lead.commission_amount = payload.commission_amount
    lead.deal_closed_at = payload.deal_closed_at
    db.commit()
    return lead


@router.post("/{lead_id}/send-matches", response_model=SendMatchesResponse)
def send_matches_via_whatsapp(
    lead_id: str,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Matching Agent'ın bulduğu portföyleri (en iyi 3) tek WhatsApp mesajı
    olarak adaya gönderir — danışmanın eşleşmeleri elle yazıp kopyalaması yerine
    tek tık. Eşleşme yoksa mesaj göndermez, 404 döner."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    office = db.get(Office, current_user["office_id"])
    if not office or not office.whatsapp_phone_number_id:
        raise HTTPException(status_code=503, detail="Bu ofis için WhatsApp gönderimi henüz bağlı değil")

    graph = build_matching_graph(db)
    result = graph.invoke(_lead_to_match_state(lead))
    ranked = rerank_candidates_with_ai(
        original_message=_last_inbound_message_text(db, lead.id),
        criteria=_match_criteria(lead),
        candidates=result["candidate_listings"],
    )
    matches = ranked[:3]
    if not matches:
        raise HTTPException(status_code=404, detail="Bu adayın kriterlerine uyan portföy bulunamadı")

    lines = [f"Merhaba! {office.name} olarak kriterlerinize uyan portföylerimiz:"]
    for i, match in enumerate(matches, start=1):
        lines.append(f"{i}) {match['title']} — {match['price']:,.0f} TL".replace(",", "."))
    lines.append("Detaylar ve yer gösterimi için bu numaradan bize ulaşabilirsiniz.")
    message = "\n".join(lines)

    try:
        send_whatsapp_text(office.whatsapp_phone_number_id, lead.contact_phone, message)
    except WhatsAppSendError as exc:
        if str(exc) == "__not_configured__":
            raise HTTPException(status_code=503, detail="WhatsApp gönderimi şu an aktif değil") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    lead.last_contacted_at = datetime.now(timezone.utc)
    db.add(
        WhatsAppMessage(
            office_id=lead.office_id, lead_id=lead.id, direction="out", message_type="text", body=message
        )
    )
    db.commit()
    return SendMatchesResponse(sent=True, match_count=len(matches), message=message)


@router.post("/{lead_id}/reanalyze-messages", response_model=LeadFieldExtractionDraft)
def reanalyze_lead_messages(lead_id: str, db: Session = Depends(get_tenant_db)):
    """Danışmanın "Yeniden Analiz Et" tetiklemesi: lead'in gelen WhatsApp METİN
    mesajlarını birleştirip Gemini'ye tekrar gönderir. Otomatik webhook
    akışından (fill-only, doğrudan yazar) kasıtlı olarak farklı: SADECE TASLAK
    döner, hiçbir şey otomatik yazılmaz — danışman taslağı (gerekirse
    düzenleyip) PATCH /{lead_id} ile onaylar. "Zaten tüm alanlar dolu"
    atlamasını bypass eder ama 24 saatlik hız sınırını ASLA bypass etmez."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    inbound_texts = (
        db.execute(
            select(WhatsAppMessage.body)
            .where(
                WhatsAppMessage.lead_id == lead.id,
                WhatsAppMessage.direction == "in",
                WhatsAppMessage.message_type == "text",
            )
            .order_by(WhatsAppMessage.created_at.asc())
        )
        .scalars()
        .all()
    )
    combined_text = "\n".join(t for t in inbound_texts if t)
    if not combined_text.strip():
        raise HTTPException(status_code=422, detail="Bu aday için analiz edilecek WhatsApp metin mesajı yok")

    if not should_run_extraction(
        message_type="text",
        message_body=combined_text,
        district=lead.district,
        budget_max=lead.budget_max,
        room_count=lead.room_count,
        extraction_count=lead.llm_extraction_count,
        last_extraction_at=lead.last_llm_extraction_at,
        force=True,
    ):
        raise HTTPException(
            status_code=429,
            detail=f"Bu aday için son 24 saatte izin verilen analiz sayısına ({MAX_EXTRACTIONS_PER_24H}) ulaşıldı",
        )

    now = datetime.now(timezone.utc)
    try:
        extracted = extract_lead_fields(combined_text)
    except WhatsAppExtractError as exc:
        if str(exc) == "__not_configured__":
            raise HTTPException(status_code=503, detail="AI ile alan çıkarımı şu an aktif değil") from exc
        lead.llm_extraction_count, lead.last_llm_extraction_at = compute_new_extraction_counters(
            lead.llm_extraction_count, lead.last_llm_extraction_at, now
        )
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    lead.llm_extraction_count, lead.last_llm_extraction_at = compute_new_extraction_counters(
        lead.llm_extraction_count, lead.last_llm_extraction_at, now
    )
    db.commit()
    return LeadFieldExtractionDraft(**extracted)


@router.post("/{lead_id}/suggest-reply", response_model=SuggestReplyResponse)
def suggest_reply(lead_id: str, db: Session = Depends(get_tenant_db)):
    """Matching Agent'ın bulduğu GERÇEK portföyleri (send-matches ile aynı, en
    iyi 3) Gemini'ye vererek kısa bir WhatsApp yanıt taslağı ürettirir —
    RAG'ın retrieval adımı Matching Agent, generation adımı Gemini. OTOMATİK
    GÖNDERMEZ: döndürülen taslak, danışmanın gözden geçirip mevcut
    POST /{lead_id}/follow-up'a (message override ile) gönderdiği metindir."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    last_inbound = _last_inbound_message_text(db, lead.id)

    graph = build_matching_graph(db)
    result = graph.invoke(_lead_to_match_state(lead))
    candidates = rerank_candidates_with_ai(
        original_message=last_inbound,
        criteria=_match_criteria(lead),
        candidates=result["candidate_listings"],
    )[:3]

    try:
        draft = draft_reply(
            last_message=last_inbound,
            district=lead.district,
            room_count=lead.room_count,
            budget_max=float(lead.budget_max) if lead.budget_max else None,
            candidate_listings=candidates,
        )
    except ReplyDraftError as exc:
        if str(exc) == "__not_configured__":
            raise HTTPException(status_code=503, detail="Yanıt taslağı özelliği şu an aktif değil") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SuggestReplyResponse(draft=draft, match_count=len(candidates))


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


@router.post("/{lead_id}/appointment", response_model=AppointmentResponse)
def create_appointment(
    lead_id: str,
    payload: AppointmentCreate,
    db: Session = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Yer gösterme randevusu planlar (.ics ile indirilebilir, bkz.
    GET /{lead_id}/appointment.ics) ve isteğe bağlı bir WhatsApp onay mesajı
    gönderir. Randevu her koşulda kaydedilir — WhatsApp onayı başarısız olsa
    bile (örn. henüz bağlı değil), danışman zaten sözlü onaylamış olabilir;
    başarısızlık response'ta ayrıca bildirilir, sert hataya düşülmez."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    lead.appointment_at = payload.appointment_at
    lead.appointment_location = payload.location
    lead.appointment_reminder_sent = False

    whatsapp_confirmation_sent = False
    whatsapp_confirmation_error = None
    if payload.send_whatsapp_confirmation:
        office = db.get(Office, current_user["office_id"])
        if not office or not office.whatsapp_phone_number_id:
            whatsapp_confirmation_error = "Bu ofis için WhatsApp gönderimi henüz bağlı değil"
        else:
            local_time = payload.appointment_at.strftime("%d.%m.%Y %H:%M")
            message = (
                f"Randevunuz onaylandı: {local_time} — {payload.location}. Görüşmek üzere!"
            )
            try:
                send_whatsapp_text(office.whatsapp_phone_number_id, lead.contact_phone, message)
                whatsapp_confirmation_sent = True
                db.add(
                    WhatsAppMessage(
                        office_id=lead.office_id, lead_id=lead.id, direction="out",
                        message_type="text", body=message,
                    )
                )
            except WhatsAppSendError as exc:
                whatsapp_confirmation_error = str(exc) if str(exc) != "__not_configured__" else (
                    "WhatsApp gönderimi şu an aktif değil"
                )

    db.commit()
    return AppointmentResponse(
        lead=lead,
        whatsapp_confirmation_sent=whatsapp_confirmation_sent,
        whatsapp_confirmation_error=whatsapp_confirmation_error,
    )


@router.delete("/{lead_id}/appointment", response_model=LeadResponse)
def cancel_appointment(lead_id: str, db: Session = Depends(get_tenant_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    lead.appointment_at = None
    lead.appointment_location = None
    lead.appointment_reminder_sent = False
    db.commit()
    return lead


@router.get("/{lead_id}/appointment.ics")
def get_appointment_ics(lead_id: str, db: Session = Depends(get_tenant_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
    if not lead.appointment_at:
        raise HTTPException(status_code=404, detail="Bu aday için planlanmış bir randevu yok")

    ics_bytes = build_appointment_ics(
        summary=f"Yer Gösterimi — {lead.contact_phone}",
        location=lead.appointment_location or "",
        start=lead.appointment_at,
        uid=f"appointment-{lead.id}@portfoyai.app",
    )
    return Response(
        content=ics_bytes,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="randevu.ics"'},
    )
