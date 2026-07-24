from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str = "sqlite:///./dev.db"

    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    redis_url: str = "redis://localhost:6379/0"

    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_storage_bucket: str = "g-erp-documents"

    local_storage_dir: str = "./storage_data"

    # Used to build absolute redirect URLs for a real payment gateway's
    # hosted checkout (Stripe needs an absolute success_url/cancel_url, not a
    # relative path) -- the customer's browser, not our backend, follows
    # these, so this must be the frontend's own public origin.
    frontend_base_url: str = "http://localhost:3000"

    cors_allow_origins: list[str] = ["http://localhost:3000"]
    cors_allow_methods: list[str] = ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["Authorization", "Content-Type", "X-Request-ID"]

    # Symmetric key protecting third-party integration credentials at rest
    # (modules/communication/infrastructure/security/encryption.py). Any
    # string works -- it's stretched into a proper Fernet key via SHA-256,
    # so operators don't need to hand-generate a base64 Fernet key.
    channel_credentials_encryption_key: str = "dev-channel-credentials-key-change-me"

    # AI Sales Assistant real provider (Phase 21). Empty key means the
    # "anthropic" provider name is registered but not usable -- resolved at
    # call time (modules/ai/infrastructure/providers/anthropic_provider.py),
    # not a boot-time guard, since unlike the secrets above this integration
    # is genuinely optional (a company may run on the mock provider only).
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    # Which registered provider name `get_provider(None)` resolves to when a
    # caller doesn't pass one explicitly -- lets ops flip every company from
    # "mock" to "anthropic" (or back, e.g. during a cost incident) via one
    # environment variable, no code change or redeploy of calling code.
    ai_default_provider: str = "mock"
    # Per-company daily spend cap in USD across every real (non-mock)
    # provider call, enforced in modules/ai/application/use_cases/_shared.py
    # before the provider is ever invoked. 0 or below disables the cap.
    ai_daily_budget_usd: float = 20.0

    # Online payment collection (Phase 22). Empty secret key means the
    # "stripe" gateway is registered but not usable -- resolved at call time
    # (modules/finance/infrastructure/providers/stripe_provider.py), the same
    # "genuinely optional integration" pattern anthropic_api_key established.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # Which registered gateway `get_payment_gateway_provider(None)` resolves
    # to when a caller (Customer Portal) doesn't pass one explicitly.
    payment_gateway_default_provider: str = "mock"

    # E-signature integration (Phase 22), shared by Sales (measurement
    # sign-off) and Installation (job completion sign-off) -- lives in core
    # config since the provider library itself lives in core/esignature/
    # (cross-cutting infrastructure, like core/storage, not owned by either
    # module). Dropbox Sign (formerly HelloSign) API v3.
    esignature_api_key: str = ""
    esignature_default_provider: str = "mock"


settings = Settings()
