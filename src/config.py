"""Application settings loaded from environment variables and ``.env``."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration. Every value has a safe default except secrets.

    Attributes:
        raw_data_path: Path to the raw dataset file downloaded by the author.
        data_dir: Root folder for processed data (git-ignored).
        reports_dir: Root folder for generated reports (git-ignored).
        logs_dir: Root folder for structured run logs (git-ignored).
        pseudonymization_key: HMAC key for internal ids. Never logged.
        mlflow_tracking_uri: MLflow tracking backend.
        pushgateway_url: Prometheus Pushgateway address.
        log_level: Root logging level.
        random_seed: Global seed for reproducibility.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="CDM_",
        extra="ignore",
    )

    raw_data_path: Path = PROJECT_ROOT / "data" / "raw" / "loans.csv"
    data_dir: Path = PROJECT_ROOT / "data"
    reports_dir: Path = PROJECT_ROOT / "reports"
    logs_dir: Path = PROJECT_ROOT / "logs"
    pseudonymization_key: SecretStr = Field(default=SecretStr(""))
    mlflow_tracking_uri: str = f"sqlite:///{(PROJECT_ROOT / 'mlruns' / 'mlflow.db').as_posix()}"
    pushgateway_url: str = "127.0.0.1:9091"
    log_level: str = "INFO"
    random_seed: int = 42

    @field_validator("raw_data_path", "data_dir", "reports_dir", "logs_dir")
    @classmethod
    def _anchor_to_project_root(cls, value: Path) -> Path:
        """Relative paths are resolved against the project root, not the cwd."""
        return value if value.is_absolute() else PROJECT_ROOT / value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
