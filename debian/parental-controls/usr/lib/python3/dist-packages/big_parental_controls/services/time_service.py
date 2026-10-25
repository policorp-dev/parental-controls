"""Service for managing time-based restrictions for supervised users."""

import json
import logging
import subprocess

from big_parental_controls.core.constants import GROUP_HELPER

log = logging.getLogger(__name__)

DAY_CODES = {
    "monday": "Mo",
    "tuesday": "Tu",
    "wednesday": "We",
    "thursday": "Th",
    "friday": "Fr",
    "saturday": "Sa",
    "sunday": "Su",
}


def _load_limits() -> dict:
    """Load time limits config. Returns {username: {daily_minutes, schedule}}."""
    try:
        result = subprocess.run(
            ["pkexec", GROUP_HELPER, "time-limit-get-all"],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout or "{}")
            if isinstance(data, dict):
                return data
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}
    return {}


def _load_user_limits(username: str) -> dict:
    """Load only one user's time limits config via helper."""
    try:
        result = subprocess.run(
            ["pkexec", GROUP_HELPER, "time-limit-get-user", username],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout or "{}")
            if isinstance(data, dict):
                return data
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}
    return {}


def _save_limits(data: dict) -> None:
    """Save time limits config via group-helper."""
    subprocess.run(
        ["pkexec", GROUP_HELPER, "time-limit-save", json.dumps(data, indent=2)],
        check=True,
        timeout=30,
    )


def set_schedule(
    username: str,
    ranges: list[dict],
    days: list[str] | None = None,
) -> bool:
    """Set login schedule for a user via pam_time."""
    if not ranges:
        return remove_schedule(username)

    day_str = "|".join(DAY_CODES.get(d.lower(), d) for d in days) if days else "Al"

    parts = []
    for r in ranges:
        sh = r["start_hour"]
        sm = r.get("start_min", 0)
        eh = r["end_hour"]
        em = r.get("end_min", 0)
        parts.append(f"{day_str}{sh:02d}{sm:02d}-{eh:02d}{em:02d}")

    timespec = "|".join(parts)

    try:
        subprocess.run(
            ["pkexec", GROUP_HELPER, "time-schedule-set", username, timespec],
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError:
        log.error("Failed to set schedule for %s", username)
        return False

    limits = _load_limits()
    user_cfg = limits.setdefault(username, {})
    user_cfg["schedule"] = {
        "ranges": [
            {
                "start_hour": r["start_hour"],
                "start_min": r.get("start_min", 0),
                "end_hour": r["end_hour"],
                "end_min": r.get("end_min", 0),
            }
            for r in ranges
        ],
        "days": days,
    }
    _save_limits(limits)
    _enable_timer()
    return True


def remove_schedule(username: str) -> bool:
    """Remove login schedule for a user."""
    try:
        subprocess.run(
            ["pkexec", GROUP_HELPER, "time-schedule-remove", username],
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError:
        log.warning("Failed to remove schedule for %s", username)

    limits = _load_limits()
    if username in limits:
        limits[username].pop("schedule", None)
        if not limits[username]:
            del limits[username]
        _save_limits(limits)

    limits = _load_limits()
    if not _has_any_restriction(limits):
        _disable_timer()
    return True


def set_daily_limit(username: str, minutes: int) -> bool:
    """Set daily usage duration limit for a user."""
    limits = _load_limits()
    user_cfg = limits.setdefault(username, {})
    user_cfg["daily_minutes"] = minutes
    _save_limits(limits)
    _enable_timer()
    return True


def remove_daily_limit(username: str) -> bool:
    """Remove daily usage duration limit for a user."""
    limits = _load_limits()
    if username in limits:
        limits[username].pop("daily_minutes", None)
        if not limits[username]:
            del limits[username]
        _save_limits(limits)

    limits = _load_limits()
    if not _has_any_restriction(limits):
        _disable_timer()
    return True


def remove_all(username: str) -> bool:
    """Remove all time restrictions for a user."""
    remove_schedule(username)
    remove_daily_limit(username)
    return True


def get_schedule(username: str) -> dict | None:
    """Get the schedule config for a user, or None."""
    schedule = _load_user_limits(username).get("schedule")
    if schedule is None:
        return None

    # Migrate legacy single-range format
    if "ranges" not in schedule and "start_hour" in schedule:
        schedule = {
            "ranges": [
                {
                    "start_hour": schedule["start_hour"],
                    "start_min": schedule.get("start_min", 0),
                    "end_hour": schedule["end_hour"],
                    "end_min": schedule.get("end_min", 0),
                }
            ],
            "days": schedule.get("days"),
        }

    return schedule


def get_daily_limit(username: str) -> int:
    """Get daily limit in minutes for a user (0 = unlimited)."""
    value = _load_user_limits(username).get("daily_minutes", 0)
    return int(value) if isinstance(value, int) else 0


def _has_any_restriction(limits: dict) -> bool:
    """True if any user has a daily limit or a schedule restriction."""
    return any(
        cfg.get("daily_minutes", 0) > 0 or bool(cfg.get("schedule"))
        for cfg in limits.values()
    )


def _enable_timer() -> None:
    """Enable the systemd timer for time checking."""
    try:
        subprocess.run(
            ["pkexec", GROUP_HELPER, "time-timer-enable"],
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError:
        log.error("Failed to enable time check timer")


def _disable_timer() -> None:
    """Disable the systemd timer for time checking."""
    try:
        subprocess.run(
            ["pkexec", GROUP_HELPER, "time-timer-disable"],
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError:
        log.warning("Failed to disable time check timer")
