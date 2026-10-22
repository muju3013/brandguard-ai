import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    app_title: str = "BrandGuard AI API"
    version: str = "0.3.0"
    environment: str = os.getenv("ENVIRONMENT", "development").lower()
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    firebase_project_id: str = os.getenv("FIREBASE_PROJECT_ID", "")
    firebase_service_account_path: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "")
    use_firestore: bool = os.getenv("USE_FIRESTORE", "false").lower() in ("true", "1")
    
    bootstrap_admin_email: str = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "")
    
    # In production, demo authentication is strictly forbidden
    enable_demo_auth: bool = (
        False if os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod")
        else os.getenv("ENABLE_DEMO_AUTH", "true").lower() in ("true", "1")
    )
    
    # Phase 3: Gemini AI Settings (Server-side only — never exposed to client)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    gemini_timeout_seconds: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "15.0"))
    gemini_max_retries: int = int(os.getenv("GEMINI_MAX_RETRIES", "2"))
    gemini_enabled: bool = os.getenv("GEMINI_ENABLED", "true").lower() in ("true", "1")

    # Rate Limiting
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    rate_limit_check_per_minute: int = int(os.getenv("RATE_LIMIT_CHECK_PER_MINUTE", "30"))

    @property
    def is_production(self) -> bool:
        return self.environment in ("production", "prod")

    @property
    def resolved_service_account_path(self) -> str:
        if not self.firebase_service_account_path:
            return ""
        if os.path.isabs(self.firebase_service_account_path) and os.path.exists(self.firebase_service_account_path):
            return self.firebase_service_account_path
        backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate = os.path.join(backend_root, self.firebase_service_account_path)
        if os.path.exists(candidate):
            return candidate
        cwd_candidate = os.path.abspath(self.firebase_service_account_path)
        if os.path.exists(cwd_candidate):
            return cwd_candidate
        return self.firebase_service_account_path

    @property
    def cors_origins(self) -> list[str]:
        default_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        custom_origins = os.getenv("CORS_ORIGINS", "")
        if custom_origins:
            parsed = [origin.strip() for origin in custom_origins.split(",") if origin.strip()]
            return list(set(default_origins + parsed))
        return default_origins

settings = Settings()

