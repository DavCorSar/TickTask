"""
Telegram bot integration.

This module is the bot's transport + dispatch layer:

* **Transport** — thin wrappers over the Bot API (``send_message``,
  ``edit_message_text``, ``answer_callback_query``, ``get_updates``,
  webhook/commands setup). All HTTP goes through ``_request`` so it can be
  stubbed in tests.
* **Dispatch** — ``process_update`` routes incoming updates: account linking
  (``/start <token>``), read commands (``/tasks``, ``/events``), and
  button-driven write actions (clock in/out, create task/subtask). Business
  rules live in :mod:`ticktask.services`; this layer only formats messages and
  builds inline keyboards. Multi-step flows keep short-lived per-chat state in
  the Django cache.

The bot is a single app-wide credential (``TELEGRAM_BOT_TOKEN``); who to message
is stored per user as a ``chat_id`` (see ``UserTelegramSettings``).
"""

import json
import logging
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from ticktask import services

logger = logging.getLogger(__name__)

_API_URL = "https://api.telegram.org/bot{token}/{method}"
LINK_TOKEN_TTL_MINUTES = 15
# How long a multi-step flow (e.g. "create task" awaiting a name) stays active.
STATE_TTL_SECONDS = 300
# How many rows the list commands / pickers show at most.
LIST_LIMIT = 10

# Commands advertised in Telegram's "/" menu.
BOT_COMMANDS = [
    ("clockin", "Start tracking time on a subtask"),
    ("clockout", "Stop the current time entry"),
    ("tasks", "Show your recent activity"),
    ("events", "Show your upcoming events"),
    ("newtask", "Create a new task"),
    ("newsubtask", "Create a new subtask"),
    ("cancel", "Cancel the current action"),
    ("help", "Show available commands"),
]


def is_configured() -> bool:
    """Whether a bot token is available."""
    return bool(settings.TELEGRAM_BOT_TOKEN)


# --------------------------------------------------------------------------- #
# Transport
# --------------------------------------------------------------------------- #


def _request(method: str, payload: dict) -> dict:
    """POSTs ``payload`` to a Bot API ``method`` and returns the parsed JSON."""
    url = _API_URL.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)
    data = json.dumps(payload).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        return json.loads(response.read().decode())


def send_message(chat_id, text: str, reply_markup: dict | None = None) -> None:
    """Sends a text message to a chat. Raises if the bot isn't configured."""
    if not is_configured():
        raise RuntimeError("Telegram bot is not configured (TELEGRAM_BOT_TOKEN).")
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    _request("sendMessage", payload)


def edit_message_text(
    chat_id, message_id, text: str, reply_markup: dict | None = None
) -> None:
    """Edits an existing message (used to advance inline-keyboard flows in place)."""
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    _request("editMessageText", payload)


def answer_callback_query(callback_query_id, text: str | None = None) -> None:
    """Acknowledges a button tap so Telegram stops the loading spinner."""
    payload = {"callback_query_id": callback_query_id}
    if text is not None:
        payload["text"] = text
    _request("answerCallbackQuery", payload)


def get_updates(offset=None, timeout: int = 25) -> list:
    """Long-polls the Bot API for new updates."""
    payload = {"timeout": timeout}
    if offset is not None:
        payload["offset"] = offset
    return _request("getUpdates", payload).get("result", [])


def set_webhook(url: str) -> dict:
    """Registers ``url`` as the bot's webhook."""
    return _request("setWebhook", {"url": url})


def delete_webhook() -> dict:
    """Removes any configured webhook."""
    return _request("deleteWebhook", {})


def set_my_commands() -> dict:
    """Registers the command menu shown in Telegram's ``/`` picker."""
    commands = [{"command": c, "description": d} for c, d in BOT_COMMANDS]
    return _request("setMyCommands", {"commands": commands})


def deep_link(token: str) -> str:
    """Builds the ``t.me`` deep link that starts the bot with a link token."""
    return f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}"


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #


def process_update(update: dict) -> None:
    """
    Routes an incoming bot update to the right handler: button taps
    (``callback_query``), the ``/start`` linking flow, slash commands, or the
    text reply that continues a multi-step flow.
    """
    if "callback_query" in update:
        _handle_callback(update["callback_query"])
        return

    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if not chat_id:
        return

    # Linking works before the chat is associated to any account.
    if text.startswith("/start"):
        _handle_start(chat_id, text)
        return

    user = _user_for_chat(chat_id)
    if user is None:
        _safe_send(chat_id, _NOT_LINKED)
        return

    if text.startswith("/"):
        _clear_state(chat_id)  # a fresh command cancels any pending flow
        _handle_command(user, chat_id, text)
        return

    # Plain text: it may be the answer to a "send me a name" prompt.
    state = _get_state(chat_id)
    if state:
        _handle_state_input(user, chat_id, state, text)
    else:
        _send_help(chat_id)


_NOT_LINKED = (
    "This chat isn't connected to a TickTask account yet. Open TickTask "
    "settings and use the connect link to get started."
)


# --------------------------------------------------------------------------- #
# Linking (/start)
# --------------------------------------------------------------------------- #


def _handle_start(chat_id, text: str) -> None:
    """Handles ``/start``: link with a token, else greet/help."""
    parts = text.split(maxsplit=1)
    token = parts[1].strip() if len(parts) > 1 else ""
    if token:
        _link_account(chat_id, token)
        return
    if _user_for_chat(chat_id) is not None:
        _send_help(chat_id)
        return
    _safe_send(
        chat_id, "Open the link from TickTask settings to connect your account."
    )


def _link_account(chat_id, token: str) -> None:
    """Links ``chat_id`` to the account holding an unexpired ``token``."""
    from ticktask.models import UserTelegramSettings  # pylint: disable=import-outside-toplevel

    cutoff = timezone.now() - timedelta(minutes=LINK_TOKEN_TTL_MINUTES)
    row = UserTelegramSettings.objects.filter(  # pylint: disable=no-member
        link_token=token, link_token_created_at__gte=cutoff
    ).first()
    if row is None:
        _safe_send(
            chat_id,
            "That link is invalid or has expired. Generate a new one in TickTask settings.",
        )
        return

    row.chat_id = str(chat_id)
    row.connected_at = timezone.now()
    row.link_token = None
    row.link_token_created_at = None
    row.save(
        update_fields=["chat_id", "connected_at", "link_token", "link_token_created_at"]
    )
    _safe_send(
        chat_id,
        "✅ Connected to TickTask. Send /help to see what I can do.",
    )


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def _handle_command(user, chat_id, text: str) -> None:
    """Dispatches a ``/command`` (bot mention and arguments stripped)."""
    word = text.split()[0].lstrip("/").lower()
    cmd = word.split("@")[0]  # tolerate /clockin@TickTaskBot in groups
    handler = {
        "help": lambda u, c: _send_help(c),
        "tasks": _cmd_recent,
        "recent": _cmd_recent,
        "events": _cmd_events,
        "upcoming": _cmd_events,
        "clockin": _cmd_clockin,
        "clockout": _cmd_clockout,
        "newtask": _cmd_newtask,
        "newsubtask": _cmd_newsubtask,
        "cancel": _cmd_cancel,
    }.get(cmd)
    if handler is None:
        _send_help(chat_id)
        return
    handler(user, chat_id)


def _send_help(chat_id) -> None:
    """Lists the available commands."""
    lines = ["Here's what I can do:"]
    lines += [f"/{c} — {d}" for c, d in BOT_COMMANDS]
    _safe_send(chat_id, "\n".join(lines))


def _cmd_recent(user, chat_id) -> None:
    """``/tasks`` — recent activity and the current open entry, if any."""
    entries = services.recent_time_entries(user, limit=LIST_LIMIT)
    if not entries:
        _safe_send(chat_id, "No time tracked yet. Use /clockin to get started.")
        return
    lines = ["🕒 Recent activity:"]
    for entry in entries:
        label = _entry_label(entry)
        if entry.clock_out is None:
            lines.append(f"🟢 {label} — in progress")
        else:
            duration = _format_duration(entry.clock_out - entry.clock_in)
            lines.append(f"• {label} — {duration}")
    _safe_send(chat_id, "\n".join(lines))


def _cmd_events(user, chat_id) -> None:
    """``/events`` — upcoming calendar events for the next few days."""
    events = services.upcoming_events(user, days=7, limit=LIST_LIMIT)
    if not events:
        _safe_send(chat_id, "No upcoming events in the next 7 days.")
        return
    lines = ["📅 Upcoming events:"]
    for event in events:
        lines.append(f"• {event.title} — {_format_event_when(event)}")
    _safe_send(chat_id, "\n".join(lines))


def _cmd_clockin(user, chat_id) -> None:
    """``/clockin`` — offer to close the open entry, else show the task picker."""
    open_entry = services.get_open_entry(user)
    if open_entry is not None:
        send_message(
            chat_id,
            f"You're already clocked in on {_entry_label(open_entry)}. "
            "Clock out first?",
            reply_markup=_inline([[("⏹ Clock out", f"co:{open_entry.id}")]]),
        )
        return
    _show_task_picker(chat_id, user)


def _cmd_clockout(user, chat_id) -> None:
    """``/clockout`` — close the current open entry, if there is one."""
    open_entry = services.get_open_entry(user)
    if open_entry is None:
        _safe_send(chat_id, "You're not clocked in right now.")
        return
    _do_clock_out(chat_id, user, open_entry.id)


def _cmd_newtask(user, chat_id) -> None:
    """``/newtask`` — ask for a name, then create the task."""
    _start_new_task(chat_id)


def _cmd_newsubtask(user, chat_id) -> None:
    """``/newsubtask`` — pick the parent task, then ask for a name."""
    tasks = services.list_active_tasks(user)
    if not tasks:
        _safe_send(chat_id, "You have no tasks yet. Create one with /newtask first.")
        return
    rows = [[(t.name, f"ci:news:{t.id}")] for t in tasks]
    send_message(
        chat_id, "Which task is the subtask for?", reply_markup=_inline(rows)
    )


def _cmd_cancel(user, chat_id) -> None:
    """``/cancel`` — drop any pending multi-step flow."""
    if _get_state(chat_id) is not None:
        _clear_state(chat_id)
        _safe_send(chat_id, "Okay, cancelled.")
    else:
        _safe_send(chat_id, "Nothing to cancel.")


# --------------------------------------------------------------------------- #
# Button taps (callback queries)
# --------------------------------------------------------------------------- #


def _handle_callback(callback: dict) -> None:
    """Handles an inline-keyboard tap, then acknowledges it."""
    data = callback.get("data") or ""
    message = callback.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    message_id = message.get("message_id")

    callback_id = callback.get("id")
    if callback_id is not None:
        _safe(lambda: answer_callback_query(callback_id))

    if not chat_id:
        return
    user = _user_for_chat(chat_id)
    if user is None:
        _safe_send(chat_id, _NOT_LINKED)
        return
    _route_callback(user, chat_id, message_id, data)


def _route_callback(user, chat_id, message_id, data: str) -> None:
    """Dispatches a callback by its compact ``data`` token."""
    parts = data.split(":")
    kind = parts[0]

    if kind == "co":  # clock out a specific entry
        _do_clock_out(chat_id, user, int(parts[1]), message_id=message_id)
        return

    if kind == "ci":
        action = parts[1] if len(parts) > 1 else ""
        if action == "tasks":
            _show_task_picker(chat_id, user, message_id=message_id)
        elif action == "t":
            _show_subtask_picker(chat_id, user, int(parts[2]), message_id=message_id)
        elif action == "s":
            _do_clock_in(chat_id, user, int(parts[2]), message_id=message_id)
        elif action == "newt":
            _start_new_task(chat_id)
        elif action == "news":
            _start_new_subtask(chat_id, int(parts[2]))


def _show_task_picker(chat_id, user, message_id=None) -> None:
    """Shows the user's tasks as buttons leading into the clock-in flow."""
    tasks = services.list_active_tasks(user)
    rows = [[(t.name, f"ci:t:{t.id}")] for t in tasks]
    rows.append([("➕ New task", "ci:newt")])
    text = "Pick a task:" if tasks else "You have no tasks yet — create one:"
    _send_or_edit(chat_id, message_id, text, reply_markup=_inline(rows))


def _show_subtask_picker(chat_id, user, task_id, message_id=None) -> None:
    """Shows a task's subtasks as buttons, plus create/back actions."""
    try:
        subtasks = services.list_active_subtasks(user, task_id)
    except services.ServiceError as exc:
        _send_or_edit(chat_id, message_id, f"⚠️ {exc.message}")
        return
    rows = [[(s.name, f"ci:s:{s.id}")] for s in subtasks]
    rows.append([("➕ New subtask", f"ci:news:{task_id}")])
    rows.append([("⬅ Back", "ci:tasks")])
    text = "Pick a subtask to clock in:" if subtasks else "No subtasks yet — add one:"
    _send_or_edit(chat_id, message_id, text, reply_markup=_inline(rows))


def _do_clock_in(chat_id, user, subtask_id, message_id=None) -> None:
    """Clocks in on a subtask, refusing if an entry is already open."""
    open_entry = services.get_open_entry(user)
    if open_entry is not None:
        _send_or_edit(
            chat_id,
            message_id,
            f"⚠️ You're already clocked in on {_entry_label(open_entry)}. "
            "Use /clockout first.",
        )
        return
    try:
        entry = services.clock_in(user, subtask_id)
    except services.ServiceError as exc:
        _send_or_edit(chat_id, message_id, f"⚠️ {exc.message}")
        return
    _send_or_edit(chat_id, message_id, f"✅ Clocked in on {_entry_label(entry)}.")


def _do_clock_out(chat_id, user, entry_id, message_id=None) -> None:
    """Clocks out the given entry and reports the tracked duration."""
    try:
        entry = services.clock_out(user, entry_id)
    except services.ServiceError as exc:
        _send_or_edit(chat_id, message_id, f"⚠️ {exc.message}")
        return
    duration = _format_duration(entry.clock_out - entry.clock_in)
    _send_or_edit(
        chat_id,
        message_id,
        f"⏹ Clocked out of {_entry_label(entry)}. Tracked {duration}.",
    )


# --------------------------------------------------------------------------- #
# Multi-step create flows (ForceReply + cached state)
# --------------------------------------------------------------------------- #


def _start_new_task(chat_id) -> None:
    """Prompts for a task name and remembers we're awaiting it."""
    _set_state(chat_id, {"action": "new_task"})
    send_message(
        chat_id,
        "Send a name for the new task (or /cancel):",
        reply_markup={"force_reply": True},
    )


def _start_new_subtask(chat_id, task_id) -> None:
    """Prompts for a subtask name under ``task_id``."""
    _set_state(chat_id, {"action": "new_subtask", "task_id": task_id})
    send_message(
        chat_id,
        "Send a name for the new subtask (or /cancel):",
        reply_markup={"force_reply": True},
    )


def _handle_state_input(user, chat_id, state: dict, text: str) -> None:
    """Consumes the text reply that completes a pending create flow."""
    action = state.get("action")
    if action == "new_task":
        _clear_state(chat_id)
        try:
            task = services.create_task(user, text)
        except services.ServiceError as exc:
            _safe_send(chat_id, f"⚠️ {exc.message}")
            return
        _show_subtask_picker(chat_id, user, task.id)
    elif action == "new_subtask":
        _clear_state(chat_id)
        try:
            subtask = services.create_subtask(user, state["task_id"], text)
        except services.ServiceError as exc:
            _safe_send(chat_id, f"⚠️ {exc.message}")
            return
        send_message(
            chat_id,
            f"✅ Created {_subtask_label(subtask)}.",
            reply_markup=_inline([[("▶️ Clock in", f"ci:s:{subtask.id}")]]),
        )
    else:
        _clear_state(chat_id)


# --------------------------------------------------------------------------- #
# Formatting & small helpers
# --------------------------------------------------------------------------- #


def _inline(rows) -> dict:
    """Builds an inline keyboard from rows of ``(text, callback_data)`` tuples."""
    return {
        "inline_keyboard": [
            [{"text": text, "callback_data": data} for text, data in row]
            for row in rows
        ]
    }


def _send_or_edit(chat_id, message_id, text, reply_markup=None) -> None:
    """Edits the message in place when continuing a button flow, else sends new."""
    if message_id is not None:
        _safe(lambda: edit_message_text(chat_id, message_id, text, reply_markup))
    else:
        _safe_send(chat_id, text, reply_markup)


def _entry_label(entry) -> str:
    """``Task ▸ Subtask`` label for a time entry."""
    return f"{entry.subtask.task.name} ▸ {entry.subtask.name}"


def _subtask_label(subtask) -> str:
    """``Task ▸ Subtask`` label for a subtask."""
    return f"{subtask.task.name} ▸ {subtask.name}"


def _format_duration(delta) -> str:
    """Formats a ``timedelta`` as a compact ``Hh Mm`` string."""
    total_minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _format_event_when(event) -> str:
    """Formats an event's start for display (UTC for now)."""
    if event.all_day:
        return event.start.strftime("%Y-%m-%d (all day)")
    return event.start.strftime("%Y-%m-%d %H:%M UTC")


def _user_for_chat(chat_id):
    """Returns the account linked to ``chat_id``, or None."""
    from ticktask.models import UserTelegramSettings  # pylint: disable=import-outside-toplevel

    row = (
        UserTelegramSettings.objects.filter(chat_id=str(chat_id))  # pylint: disable=no-member
        .select_related("user")
        .first()
    )
    return row.user if row is not None else None


# --- conversation state (per chat, short-lived) ---------------------------- #


def _state_key(chat_id) -> str:
    return f"tg:state:{chat_id}"


def _get_state(chat_id):
    return cache.get(_state_key(chat_id))


def _set_state(chat_id, state: dict) -> None:
    cache.set(_state_key(chat_id), state, STATE_TTL_SECONDS)


def _clear_state(chat_id) -> None:
    cache.delete(_state_key(chat_id))


# --- best-effort sending (never raises inside update handling) ------------- #


def _safe(func) -> None:
    """Runs a Bot API call, swallowing and logging any error."""
    try:
        func()
    except Exception:  # pylint: disable=broad-except
        logger.exception("Telegram Bot API call failed")


def _safe_send(chat_id, text: str, reply_markup: dict | None = None) -> None:
    """Best-effort send that never raises (used inside update handling)."""
    _safe(lambda: send_message(chat_id, text, reply_markup))
