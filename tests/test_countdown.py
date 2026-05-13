from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from event_countdown_updater.config import Config, Stage, parse_duration
from event_countdown_updater.countdown import build_plan


def make_config(when_too_early: str = "skip") -> Config:
    return Config(
        event_time="2026-05-20 18:00",
        timezone="Europe/Moscow",
        universe_id="123",
        place_id=None,
        language_code="en",
        base_title="Cut Grass for Brainrots",
        title_template="[{label}] {base_title}",
        update_experience_title=True,
        update_place_title=False,
        update_icon=True,
        when_too_early=when_too_early,
        icon_upload_field="file",
        stages=(
            Stage("NOW!", 0, Path("now.png")),
            Stage("15 MIN", 900, Path("15m.png")),
            Stage("30 MIN", 1800, Path("30m.png")),
            Stage("1 HOUR", 3600, Path("1h.png")),
            Stage("12 HOURS", 43200, Path("12h.png")),
        ),
        root=Path("."),
    )


class CountdownTests(unittest.TestCase):
    def test_parse_duration(self) -> None:
        self.assertEqual(parse_duration("15m"), 900)
        self.assertEqual(parse_duration("1h"), 3600)
        self.assertEqual(parse_duration("2d"), 172800)

    def test_selects_first_threshold_above_remaining(self) -> None:
        config = make_config()
        now = datetime(2026, 5, 20, 17, 31, tzinfo=config.tzinfo)

        plan = build_plan(config, now)

        self.assertIsNotNone(plan.stage)
        self.assertEqual(plan.stage.label, "30 MIN")
        self.assertEqual(plan.title, "[30 MIN] Cut Grass for Brainrots")

    def test_selects_now_after_event_time(self) -> None:
        config = make_config()
        now = datetime(2026, 5, 20, 18, 1, tzinfo=config.tzinfo)

        plan = build_plan(config, now)

        self.assertIsNotNone(plan.stage)
        self.assertEqual(plan.stage.label, "NOW!")

    def test_skips_when_too_early_by_default(self) -> None:
        config = make_config()
        now = datetime(2026, 5, 19, 1, 0, tzinfo=config.tzinfo)

        plan = build_plan(config, now)

        self.assertIsNone(plan.stage)
        self.assertFalse(plan.should_update)

    def test_can_use_biggest_stage_when_too_early(self) -> None:
        config = make_config(when_too_early="first")
        now = datetime(2026, 5, 19, 1, 0, tzinfo=config.tzinfo)

        plan = build_plan(config, now)

        self.assertIsNotNone(plan.stage)
        self.assertEqual(plan.stage.label, "12 HOURS")


if __name__ == "__main__":
    unittest.main()
