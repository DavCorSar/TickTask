"""
Long-polls Telegram for bot updates and processes them (account linking).
Use this in development (`TELEGRAM_USE_WEBHOOK=False`); production uses the
webhook endpoint instead.
"""

import logging
import time

from django.core.management.base import BaseCommand, CommandError

from ticktask import telegram

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Long-polls Telegram for bot updates (account linking)."

    def handle(self, *args, **options):
        if not telegram.is_configured():
            raise CommandError("TELEGRAM_BOT_TOKEN is not set.")

        try:
            telegram.set_my_commands()
        except Exception as exc:  # pylint: disable=broad-except
            self.stderr.write(f"Could not register bot commands: {exc}")

        self.stdout.write(self.style.SUCCESS("Polling Telegram… (Ctrl-C to stop)"))
        offset = None
        while True:
            try:
                updates = telegram.get_updates(offset=offset, timeout=25)
            except Exception as exc:  # pylint: disable=broad-except
                self.stderr.write(f"getUpdates failed: {exc}")
                time.sleep(3)
                continue

            for update in updates:
                offset = update["update_id"] + 1
                try:
                    telegram.process_update(update)
                except Exception:  # pylint: disable=broad-except
                    logger.exception("Failed to process Telegram update %s", update)
