"""Harness runtime configuration. Loads from env + .env file."""
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class HarnessConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="HARNESS_", extra="ignore")

    # Repo paths (4 parents up: harness/ → src/ → harness pkg dir → packages/ → repo root)
    repo_root: Path = Path(__file__).resolve().parents[4]

    # LLM provider selection
    llm_provider: Literal["anthropic", "openai"] = "anthropic"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 4096
    anthropic_timeout_seconds: int = 60
    anthropic_max_retries: int = 3

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_timeout_seconds: int = 60
    openai_max_retries: int = 3
    openai_base_url: str = ""  # empty = use OpenAI SDK default https://api.openai.com/v1

    # Token budgets per Tier (per HARNESS_DESIGN §9)
    tier1_token_budget: int = 8_000
    tier2_token_budget: int = 20_000
    tier3_token_budget: int = 50_000

    # Storage
    sqlite_path: Path = Path("data/harness.db")
    log_path: Path = Path("data/harness.log")

    # Server
    host: str = "127.0.0.1"
    port: int = 8001

    # Feature flags
    pii_redaction_enabled: bool = True
    metrics_emission_enabled: bool = True

    # Skill knowledge layer — O*NET + JSearch
    # O*NET: free registration at https://services.onetcenter.org/developer/
    onet_username: str = ""
    onet_password: str = ""
    # JSearch: free tier at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    jsearch_api_key: str = ""

    # Wave 3 — Discovery
    discovery_enabled: bool = True
    discovery_interval_hours: int = 6
    discovery_adapters: str = "jobspy,seek,adzuna,gradcracker,workingnomads,hiringcafe,golangjobs,ukvisajobs,tencent_doc"
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    # Wave 3 — Submit caps + intervals
    daily_cap: int = 50
    linkedin_subcap: int = 15
    submit_interval_linkedin: int = 90
    submit_interval_boss: int = 60
    submit_interval_workday: int = 120
    submit_interval_email: int = 30
    default_submit_method_linkedin: str = "userscript"
    default_submit_method_boss: str = "userscript"
    default_submit_method_workday: str = "selenium"
    default_submit_method_email: str = "email"
    default_submit_method_generic: str = "manual"

    # Wave 3 — SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""


config = HarnessConfig()
