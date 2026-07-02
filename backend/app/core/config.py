from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://portfoyai_app:portfoyai_app@localhost:5432/portfoyai"
    # Sadece register/login için: e-posta ile ofis bilinmeden kullanıcı arama,
    # RLS'in tek-tenant modeliyle doğası gereği çelişir. Bkz. migration 0003.
    auth_database_url: str = "postgresql+psycopg2://portfoyai_auth:portfoyai_auth@localhost:5432/portfoyai"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    google_maps_api_key: str | None = None
    iyzico_api_key: str | None = None
    iyzico_secret_key: str | None = None
    whatsapp_token: str | None = None
    sentry_dsn: str | None = None

    # Pricing Agent: bölgesel emsal ilan embedding'leri için kalıcı ChromaDB dizini.
    chroma_persist_dir: str = "./chroma_data"


settings = Settings()
