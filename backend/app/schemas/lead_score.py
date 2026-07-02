import uuid
from datetime import datetime

from pydantic import BaseModel


class LeadScoreResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    score: int
    score_breakdown: dict
    computed_at: datetime

    model_config = {"from_attributes": True}
