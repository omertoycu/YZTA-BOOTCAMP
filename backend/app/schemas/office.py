import uuid
from datetime import datetime

from pydantic import BaseModel


class OfficeResponse(BaseModel):
    id: uuid.UUID
    name: str
    subscription_plan: str
    notification_phone: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OfficeUpdate(BaseModel):
    notification_phone: str | None = None
