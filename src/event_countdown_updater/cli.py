from __future__ import annotations

import argparse
import os
import sys
import time

from .config import load_config
from .countdown import build_plan, format_duration, parse_now
from .roblox_open_cloud import RobloxOpenCloudClient, RobloxOpenCloudError


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except Exception as error:
        print(f"Config error: {error}", file=sys.stderr)
        return 2

    if args.command == "watch":
        if args.now:
            print("--now cannot be used with watch because watch uses real time.", file=sys.stderr)
            return 2
        if args.interval < 1:
            print("--interval must be at least 1 second.", file=sys.stderr)
            return 2
        return watch_plan(config, live=args.live, interval=args.interval)

    try:
        now = parse_now(args.now, config) if args.now else None
        plan = build_plan(config, now)
    except Exception as error:
        print(f"Config error: {error}", file=sys.stderr)
        return 2

    if args.command == "status":
        print_plan(plan)
        return 0 if plan.should_update else 3

    if args.command == "apply":
        return apply_plan(config, plan, live=args.live)

    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update Roblox event countdown title and icon.")
    parser.add_argument("--config", default="config.toml", help="Path to TOML config.")
    parser.add_argument("--now", help="Override current time, format: YYYY-MM-DD HH:MM[:SS].")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Print the selected countdown stage.")

    apply_parser = subparsers.add_parser("apply", help="Apply the selected stage.")
    apply_parser.add_argument(
        "--live",
        action="store_true",
        help="Actually call Roblox. Without this flag the command is a dry-run.",
    )

    watch_parser = subparsers.add_parser("watch", help="Keep checking and apply when the stage changes.")
    watch_parser.add_argument(
        "--live",
        action="store_true",
        help="Actually call Roblox. Without this flag changed stages are printed as dry-runs.",
    )
    watch_parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Seconds between checks. Default: 60.",
    )

    return parser


def print_plan(plan) -> None:
    print(f"remaining: {format_duration(plan.remaining_seconds)}")
    if not plan.should_update:
        print(f"stage: skipped ({plan.reason})")
        return
    print(f"stage: {plan.stage.label}")
    print(f"title: {plan.title}")
    print(f"icon: {plan.stage.icon}")


def apply_plan(config, plan, live: bool) -> int:
    print_plan(plan)
    if not plan.should_update:
        return 3

    missing_icon = config.update_icon and not plan.stage.icon.exists()
    if missing_icon:
        print(f"Icon file does not exist: {plan.stage.icon}", file=sys.stderr)
        return 2

    if not live:
        print("dry-run: no Roblox calls were made. Add --live to update the experience.")
        return 0

    api_key = os.environ.get("ROBLOX_API_KEY", "").strip()
    if not api_key:
        print("ROBLOX_API_KEY is not set.", file=sys.stderr)
        return 2

    client = RobloxOpenCloudClient(api_key)
    try:
        if config.update_experience_title:
            client.update_universe(config.universe_id, plan.title)
            print("updated: experience title")

        if config.update_place_title:
            if not config.place_id:
                print("update_place_title is true, but place_id is empty.", file=sys.stderr)
                return 2
            client.update_place(config.universe_id, config.place_id, plan.title)
            print("updated: place title")

        if config.update_icon:
            client.update_game_icon(
                config.universe_id,
                config.language_code,
                plan.stage.icon,
                config.icon_upload_field,
            )
            print("updated: game icon")
    except RobloxOpenCloudError as error:
        print(str(error), file=sys.stderr)
        return 1

    return 0


def watch_plan(config, live: bool, interval: int) -> int:
    last_signature: tuple[str, str] | None = None
    mode = "live" if live else "dry-run"
    print(f"watch: started in {mode} mode; checking every {interval}s. Press Ctrl+C to stop.")

    try:
        while True:
            plan = build_plan(config)
            signature = plan_signature(plan)
            if signature is None:
                print_plan(plan)
                last_signature = None
            elif signature != last_signature:
                result = apply_plan(config, plan, live=live)
                if result == 0:
                    last_signature = signature
                else:
                    print(f"watch: apply failed with exit code {result}; retrying on next check.", file=sys.stderr)
            else:
                print(f"watch: unchanged stage {plan.stage.label}; remaining {format_duration(plan.remaining_seconds)}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
        print("watch: stopped.")
        return 0


def plan_signature(plan) -> tuple[str, str] | None:
    if not plan.should_update:
        return None
    return (plan.stage.label, plan.title)


if __name__ == "__main__":
    raise SystemExit(main())
