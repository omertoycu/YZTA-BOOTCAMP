from pydantic import BaseModel


class PlanInfo(BaseModel):
    id: str
    name: str
    monthly_price: float
    features: list[str]
    is_current: bool


class CheckoutRequest(BaseModel):
    plan: str


class CheckoutResponse(BaseModel):
    payment_page_url: str
