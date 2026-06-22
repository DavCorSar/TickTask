"""
Registers (or removes) the Telegram webhook. Run once in production after
deploying with a public HTTPS URL and `TELEGRAM_USE_WEBHOOK=True`.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ticktask import telegram


class Command(BaseCommand):
    help = "Registers the Telegram webhook (or removes it with --delete)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            help="Public base URL of the API, e.g. https://example.com",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Remove the webhook instead of setting it.",
        )

    def handle(self, *args, **options):
        if not telegram.is_configured():
            raise CommandError("TELEGRAM_BOT_TOKEN is not set.")

        if options["delete"]:
            telegram.delete_webhook()
            self.stdout.write(self.style.SUCCESS("Webhook deleted."))
            return

        base = options["url"]
        if not base:
            raise CommandError("--url is required to set the webhook.")
        if not settings.TELEGRAM_WEBHOOK_SECRET:
            raise CommandError("TELEGRAM_WEBHOOK_SECRET is not set.")

        webhook_url = (
            f"{base.rstrip('/')}/api/telegram/webhook/"
            f"{settings.TELEGRAM_WEBHOOK_SECRET}/"
        )
        telegram.set_webhook(webhook_url)
        self.stdout.write(self.style.SUCCESS(f"Webhook set to {webhook_url}"))
