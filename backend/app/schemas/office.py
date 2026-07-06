import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field

from app.core.storage import logo_proxy_url


class OfficeResponse(BaseModel):
    id: uuid.UUID
    name: str
    subscription_plan: str
    notification_phone: str | None
    whatsapp_phone_number_id: str | None
    logo_key: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def logo_url(self) -> str | None:
        # DB'de bare S3 key saklanıyor (bucket private); frontend'in <img>'de
        # kullanabileceği gerçek URL backend proxy route'una işaret eder.
        return logo_proxy_url(self.logo_key)


class OfficeUpdate(BaseModel):
    notification_phone: str | None = None
    whatsapp_phone_number_id: str | None = None
