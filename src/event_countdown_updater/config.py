from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta, timezone, tzinfo
from pathlib import Path
import re
import tomllib
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_DURATION_RE = re.compile(r"^\s*(?P<value>\d+)\s*(?P<unit>s|m|h|d)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Stage:
    label: str
    max_remaining_seconds: int
    icon: Path


@dataclass(frozen=True)
class Config:
    event_time: str
    timezone: str
    universe_id: str
    place_id: str | None
    language_code: str
    base_title: str
    title_template: str
    update_experience_title: bool
    update_place_title: bool
    update_icon: bool
    when_too_early: str
    icon_upload_field: str
    stages: tuple[Stage, ...]
    root: Path
    reset_after_seconds: int = 3600
    reset_icon: Path | None = None
    reset_title: str | None = None

    @property
    def tzinfo(self) -> tzinfo:
        return resolve_timezone(self.timezone)


def load_config(path: str | Path) -> Config:
    config_path = Path(path).resolve()
    with config_path.open("rb") as file:
        raw = tomllib.load(file)

    root = config_path.parent
    stages = tuple(
        sorted(
            (
                Stage(
                    label=str(item["label"]),
                    max_remaining_seconds=parse_duration(str(item["max_remaining"])),
                    icon=(root / str(item["icon"])).resolve(),
                )
                for item in raw.get("stages", [])
            ),
            key=lambda stage: stage.max_remaining_seconds,
        )
    )

    if not stages:
        raise ValueError("Config must define at least one [[stages]] entry.")

    when_too_early = str(raw.get("when_too_early", "skip")).lower()
    if when_too_early not in {"skip", "first"}:
        raise ValueError('when_too_early must be either "skip" or "first".')

    place_id = str(raw.get("place_id", "")).strip() or None

    reset_after_raw = str(raw.get("reset_after", "1h")).strip()
    reset_after_seconds = parse_duration(reset_after_raw) if reset_after_raw else 3600
    reset_icon_raw = str(raw.get("reset_icon", "assets/default.png")).strip()
    reset_icon = (root / reset_icon_raw).resolve() if reset_icon_raw else None
    reset_title_raw = str(raw.get("reset_title", "")).strip()
    reset_title = reset_title_raw if reset_title_raw else None

    return Config(
        event_time=str(raw["event_time"]),
        timezone=str(raw.get("timezone", "Europe/Moscow")),
        universe_id=str(raw["universe_id"]).strip(),
        place_id=place_id,
        language_code=str(raw.get("language_code", "en")).strip(),
        base_title=str(raw.get("base_title", "")).strip(),
        title_template=str(raw.get("title_template", "[{label}] {base_title}")),
        update_experience_title=bool(raw.get("update_experience_title", True)),
        update_place_title=bool(raw.get("update_place_title", False)),
        update_icon=bool(raw.get("update_icon", True)),
        when_too_early=when_too_early,
        icon_upload_field=str(raw.get("icon_upload_field", "file")).strip() or "file",
        stages=stages,
        root=root,
        reset_after_seconds=reset_after_seconds,
        reset_icon=reset_icon,
        reset_title=reset_title,
    )


def parse_duration(value: str) -> int:
    match = _DURATION_RE.match(value)
    if not match:
        raise ValueError(f"Invalid duration {value!r}; use examples like 15m, 1h, 12h, 0s.")

    amount = int(match.group("value"))
    unit = match.group("unit").lower()
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return amount * multipliers[unit]


def resolve_timezone(name: str) -> tzinfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name == "Europe/Moscow":
            return timezone(timedelta(hours=3), "Europe/Moscow")
        raise
