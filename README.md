# Event Countdown Updater

Small CLI tool for changing a Roblox experience title and game icon as an event approaches.

It:

- reads the event time in `Europe/Moscow` by default;
- picks the first configured stage whose threshold is still ahead;
- supports dry-run previews;
- updates Roblox through Open Cloud with an API key from `ROBLOX_API_KEY`.

## Setup

1. Copy `config.example.toml` to `config.toml`.
2. Fill in `universe_id`, `place_id` if you also want to update the start place, and icon paths.
3. Install the CLI locally:

```powershell
python -m pip install -e .
```

4. Put your API key in the environment:

```powershell
$env:ROBLOX_API_KEY = "YOUR_OPEN_CLOUD_API_KEY"
```

The API key needs access to the target experience. For title updates, enable `universe:write`. If you also update a place title, enable `universe.place:write`. For the icon endpoint, enable Open Cloud access for game internationalization/localization if Roblox shows that scope in your key permissions.

## Commands

On Windows you can use the helper script:

```powershell
.\run.bat
```

It runs from the project folder, uses `config.toml` by default, asks for status/dry-run/live mode, optional `--now`, and prompts for `ROBLOX_API_KEY` only when live mode is selected. To use another config:

```powershell
.\run.bat path\to\config.toml
```

Preview current stage:

```powershell
event-countdown-updater --config config.toml status
```

Dry-run an update:

```powershell
event-countdown-updater --config config.toml apply
```

Actually call Roblox:

```powershell
event-countdown-updater --config config.toml apply --live
```

Use a custom time for testing:

```powershell
event-countdown-updater --config config.toml --now "2026-05-20 17:30" status
```

## Notes

The tool updates the experience title through:

- `PATCH https://apis.roblox.com/cloud/v2/universes/{universe_id}`

The icon endpoint is:

- `POST https://apis.roblox.com/legacy-game-internationalization/v1/game-icon/games/{gameId}/language-codes/{languageCode}`

The icon upload is sent as multipart form data. If Roblox expects a different multipart field name for your account or endpoint version, change `icon_upload_field` in `config.toml`.
