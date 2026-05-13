from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .config import Config, Stage


@dataclass(frozen=True)
class CountdownPlan:
    remaining_seconds: int
    stage: Stage | None
    title: str | None
    reason: str | None = None

    @property
    def should_update(self) -> bool:
        return self.stage is not None and self.title is not None


def build_plan(config: Config, now: datetime | None = None) -> CountdownPlan:
    event_time = parse_event_time(config)
    current_time = now or datetime.now(config.tzinfo)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=config.tzinfo)

    remaining = int((event_time - current_time).total_seconds())
    stage = select_stage(config, remaining)
    if stage is None:
        largest = config.stages[-1].max_remaining_seconds
        return CountdownPlan(
            remaining_seconds=remaining,
            stage=None,
            title=None,
            reason=f"Event is more than {format_duration(largest)} away.",
        )

    return CountdownPlan(
        remaining_seconds=remaining,
        stage=stage,
        title=config.title_template.format(label=stage.label, base_title=config.base_title),
    )


def parse_event_time(config: Config) -> datetime:
    text = config.event_time.strip()
    formats = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")
    for date_format in formats:
        try:
            return datetime.strptime(text, date_format).replace(tzinfo=config.tzinfo)
        except ValueError:
            pass
    raise ValueError("event_time must use YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS.")


def parse_now(text: str, config: Config) -> datetime:
    clone = Config(
        event_time=text,
        timezone=config.timezone,
        universe_id=config.universe_id,
        place_id=config.place_id,
        language_code=config.language_code,
        base_title=config.base_title,
        title_template=config.title_template,
        update_experience_title=config.update_experience_title,
        update_place_title=config.update_place_title,
        update_icon=config.update_icon,
        when_too_early=config.when_too_early,
        icon_upload_field=config.icon_upload_field,
        stages=config.stages,
        root=config.root,
    )
    return parse_event_time(clone)


def select_stage(config: Config, remaining_seconds: int) -> Stage | None:
    if remaining_seconds <= 0:
        return config.stages[0]

    for stage in config.stages:
        if stage.max_remaining_seconds > 0 and remaining_seconds <= stage.max_remaining_seconds:
            return stage

    if config.when_too_early == "first":
        return config.stages[-1]
    return None


def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0s"

    parts: list[str] = []
    remaining = seconds
    for label, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        amount, remaining = divmod(remaining, size)
        if amount:
            parts.append(f"{amount}{label}")
    return " ".join(parts)

