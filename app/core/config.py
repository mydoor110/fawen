from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache
import yaml
from pathlib import Path

class SystemSettings(BaseSettings):
    name: str
    version: str
    environment: str

class NumberPoliciesSettings(BaseSettings):
    allow_edit_during_approval: bool
    require_reason: bool
    log_all_changes: bool

class NumberPoolSettings(BaseSettings):
    auto_allocate: bool
    recycle_first: bool

class NumberFormatSettings(BaseSettings):
    prefix: str
    year_length: int
    number_length: int
    separator: str

class NumberSettings(BaseSettings):
    policies: NumberPoliciesSettings
    pool: NumberPoolSettings
    format: NumberFormatSettings

class ProofreadingSettings(BaseSettings):
    mode: str
    timeout_days: int
    can_skip: bool
    require_comment: bool

class TimeoutRemindersSettings(BaseSettings):
    enabled: bool = True
    remind_before_days: List[int] = Field(default_factory=lambda: [7, 3, 1])

class ApprovalSettings(BaseSettings):
    allow_skip_proofreading: bool
    timeout_days: int
    notify_on_assign: bool
    allow_reassign: bool
    timeout_strategy: str = "notify_only"  # auto_approve | auto_reject | escalate | notify_only
    timeout_reminders: TimeoutRemindersSettings = Field(default_factory=TimeoutRemindersSettings)

class DocumentSettings(BaseSettings):
    max_size_mb: int
    allowed_formats: List[str]
    storage_path: str
    destroy_path: str

class AuditSettings(BaseSettings):
    log_all_actions: bool
    retain_days: int
    include_ip: bool

class JwtSettings(BaseSettings):
    secret_key: str = Field(default="your-secret-key-change-in-production")
    algorithm: str = "HS256"
    expire_hours: int = 24

class PasswordSettings(BaseSettings):
    min_length: int = 6
    require_special_char: bool = False

class CorsSettings(BaseSettings):
    allowed_origins: List[str] = Field(default_factory=list)

class SecuritySettings(BaseSettings):
    jwt: JwtSettings
    password: PasswordSettings
    cors: CorsSettings

class DatabaseSettings(BaseSettings):
    url: str = Field(default="postgresql://fawen:fawen@localhost:5432/fawen")
    echo: bool = False

class ServerSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 5000

class Settings(BaseSettings):
    system: SystemSettings
    number: NumberSettings
    proofreading: ProofreadingSettings
    approval: ApprovalSettings
    document: DocumentSettings
    audit: AuditSettings
    security: SecuritySettings
    database: DatabaseSettings
    server: ServerSettings

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    config_path = Path("config.yaml")
    with open(config_path, encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    return Settings(**config_data)

settings = get_settings()
