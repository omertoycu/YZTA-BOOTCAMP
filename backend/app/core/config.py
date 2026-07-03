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
    # Meta'nın webhook kurulum handshake'inde (GET) döndüğümüz hub.verify_token'la eşleşmeli.
    whatsapp_verify_token: str | None = None
    # X-Hub-Signature-256 doğrulaması için; boşsa (henüz Meta onayı yoksa) imza kontrolü atlanır.
    whatsapp_app_secret: str | None = None
    sentry_dsn: str | None = None

    # İlan fotoğrafları: herhangi bir S3-uyumlu servis (Railway Bucket, Cloudflare R2, vb.).
    # s3_endpoint_url boşsa fotoğraf yükleme endpoint'i 503 döner (henüz kurulmadıysa sert hata değil).
    s3_endpoint_url: str | None = None
    s3_bucket_name: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_public_url_base: str | None = None

    # Pricing Agent: bölgesel emsal ilan embedding'leri için kalıcı ChromaDB dizini.
    chroma_persist_dir: str = "./chroma_data"

    # Next.js ofis paneli farklı origin'den (localhost:3000) istek atar; virgülle ayrılmış liste.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
