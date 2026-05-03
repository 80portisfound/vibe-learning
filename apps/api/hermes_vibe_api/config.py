from pathlib import Path

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    hermes_home: Path | None = None
    app_data_dir: Path = Field(default_factory=lambda: Path.home() / ".hermes-vibe")
