from __future__ import annotations

from functools import lru_cache
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


FundingType = Literal["budget", "paid"]


class ProgramConfig(BaseModel):
    code: str
    name: str
    subject_id: str | None = None
    general_places: int
    paid_places: int


PROGRAMS: tuple[ProgramConfig, ...] = (
    ProgramConfig(
        code="01.03.02",
        name="Прикладная математика и информатика",
        subject_id="1569730463748068670",
        general_places=10,
        paid_places=7,
    ),
    ProgramConfig(
        code="02.03.02",
        name="Фундаментальная информатика и информационные технологии",
        subject_id="1569730463774283070",
        general_places=15,
        paid_places=4,
    ),
    ProgramConfig(
        code="09.03.01",
        name="Информатика и вычислительная техника",
        subject_id="1569730463884383550",
        general_places=59,
        paid_places=20,
    ),
    ProgramConfig(
        code="09.03.02",
        name="Информационные системы и технологии",
        subject_id="1569730463890675006",
        general_places=19,
        paid_places=15,
    ),
    ProgramConfig(
        code="09.03.03",
        name="Прикладная информатика",
        subject_id="1569730463895917886",
        general_places=20,
        paid_places=18,
    ),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    admission_year: int = 2026
    university: str = "РГРТУ"
    default_exam_score: int = 195
    individual_achievements: int = 0
    check_interval_minutes: int = 120
    timezone: str = "Europe/Moscow"
    notifications_enabled: bool = True
    paid_enabled: bool = True
    scheduler_enabled: bool = False

    max_api_base_url: str = "https://platform-api2.max.ru"
    max_bot_token: SecretStr | None = None
    max_webhook_secret: SecretStr | None = None
    pairing_code: SecretStr | None = None
    app_secret_key: SecretStr = Field(default=SecretStr("change-me"))
    owner_max_user_id: str | None = None
    bot_public_base_url: str = "https://bot.example.ru"

    telegram_api_base_url: str = "https://api.telegram.org"
    telegram_bot_token: SecretStr | None = None
    telegram_allowed_chat_id: str | None = None
    telegram_poll_timeout_seconds: int = 30
    telegram_poll_interval_seconds: float = 1.0
    telegram_delete_webhook_on_start: bool = True
    telegram_drop_pending_updates_on_start: bool = False
    telegram_allowed_chat_ids_file: str = "config/telegram_allowed_chat_ids.txt"

    database_url: str = "sqlite:///./data/rgrtu.db"
    rgrtu_base_url: str = "https://postupai.rsreu.ru"
    rgrtu_campaign_id: int = Field(default=20, validation_alias="RGRTU_CAMPAIGN_ID")
    rgrtu_verify_ssl: bool = True
    user_agent: str = "rgrtu-admission-monitor/0.1 (+https://postupai.rsreu.ru)"

    passing_score_change_threshold: int = 3
    position_change_threshold: int = 3

    @property
    def total_default_score(self) -> int:
        return self.default_exam_score + self.individual_achievements

    @property
    def telegram_allowed_chat_ids(self) -> set[str]:
        raw_values: list[str] = []
        if self.telegram_allowed_chat_id:
            raw_values.append(self.telegram_allowed_chat_id)
        config_path = Path(self.telegram_allowed_chat_ids_file)
        if config_path.exists():
            raw_values.append(config_path.read_text(encoding="utf-8"))
        if not raw_values:
            return set()
        ids: set[str] = set()
        for line in "\n".join(raw_values).splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            ids.update(item for item in re.split(r"[\s,;]+", line) if item)
        return ids

    @field_validator(
        "max_bot_token",
        "max_webhook_secret",
        "pairing_code",
        "telegram_bot_token",
        mode="before",
    )
    @classmethod
    def empty_secret_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("owner_max_user_id", "telegram_allowed_chat_id", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_program(code: str) -> ProgramConfig | None:
    return next((program for program in PROGRAMS if program.code == code), None)
