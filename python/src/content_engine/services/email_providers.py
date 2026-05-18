"""Email provider adapter layer.

Abstracts campaign creation, sending, and list management across
Brevo, Mailchimp, and Resend behind a single interface.

Usage:
    provider = await get_email_provider(brand_id)
    campaign = await provider.create_campaign(list_id, subject, html, sender)
    await provider.send_campaign(campaign)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import resend

from ..config import settings
from ..db import get_db

log = logging.getLogger(__name__)


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class SenderInfo:
    name: str
    email: str


@dataclass
class CampaignRef:
    """Provider-agnostic campaign reference."""
    provider: str
    campaign_id: str
    extra: dict = field(default_factory=dict)


@dataclass
class SendResult:
    campaign_ref: CampaignRef
    provider_send_id: str
    recipients_count: int


@dataclass
class CampaignReport:
    """Standardized campaign metrics across providers."""
    campaign_ref: CampaignRef
    sent: int = 0
    delivered: int = 0
    opens: int = 0
    unique_opens: int = 0
    clicks: int = 0
    unique_clicks: int = 0
    unsubscribes: int = 0
    bounces: int = 0

    @property
    def open_rate(self) -> float:
        return round(self.unique_opens / self.delivered, 4) if self.delivered else 0.0

    @property
    def click_rate(self) -> float:
        return round(self.unique_clicks / self.delivered, 4) if self.delivered else 0.0

    @property
    def click_to_open(self) -> float:
        return round(self.unique_clicks / self.unique_opens, 4) if self.unique_opens else 0.0


@dataclass
class ContactList:
    list_id: str
    name: str
    total_subscribers: int = 0


@dataclass
class ProviderConfig:
    provider: str
    api_key: str
    sender_name: str
    sender_email: str
    list_id: str
    webhook_secret: str
    ab_split_pct: int
    ab_wait_hours: int


# ── Abstract base ─────────────────────────────────────────────────────────────

class EmailProvider(ABC):
    """Abstract email provider interface."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @property
    def sender(self) -> SenderInfo:
        return SenderInfo(
            name=self.config.sender_name,
            email=self.config.sender_email,
        )

    @abstractmethod
    async def create_campaign(
        self,
        list_id: str,
        subject: str,
        html: str,
        sender: SenderInfo | None = None,
    ) -> CampaignRef:
        """Create a regular email campaign (draft, not yet sent)."""

    @abstractmethod
    async def create_ab_campaign(
        self,
        list_id: str,
        subjects: list[str],
        html: str,
        split_pct: int | None = None,
        winner_criteria: str = "open",
        wait_hours: int | None = None,
        sender: SenderInfo | None = None,
    ) -> CampaignRef:
        """Create an A/B split campaign with multiple subject lines."""

    @abstractmethod
    async def send_campaign(self, campaign_ref: CampaignRef) -> SendResult:
        """Send (launch) a previously created campaign."""

    @abstractmethod
    async def get_report(self, campaign_ref: CampaignRef) -> CampaignReport:
        """Fetch standardized campaign analytics."""

    @abstractmethod
    async def get_lists(self) -> list[ContactList]:
        """List all subscriber lists/audiences on the provider."""

    @abstractmethod
    async def validate(self) -> bool:
        """Verify the API key is valid. Raises on failure."""


# ── Brevo ─────────────────────────────────────────────────────────────────────

class BrevoProvider(EmailProvider):
    """Email provider adapter for Brevo (ex-Sendinblue)."""

    def _client(self):  # type: ignore[return]
        try:
            import brevo_python  # type: ignore
            configuration = brevo_python.Configuration()
            configuration.api_key["api-key"] = self.config.api_key
            return brevo_python.ApiClient(configuration)
        except ImportError as e:
            raise RuntimeError("brevo-python SDK not installed") from e

    async def validate(self) -> bool:
        import brevo_python  # type: ignore
        client = self._client()
        api = brevo_python.AccountApi(client)
        try:
            api.get_account()
            return True
        except Exception as exc:
            raise RuntimeError(f"Brevo API key invalid: {exc}") from exc

    async def get_lists(self) -> list[ContactList]:
        import brevo_python  # type: ignore
        client = self._client()
        api = brevo_python.ContactsApi(client)
        result = api.get_lists(limit=50, offset=0)
        lists = []
        for lst in (result.lists or []):
            lists.append(ContactList(
                list_id=str(lst.id),
                name=lst.name or "",
                total_subscribers=getattr(lst, "total_subscribers", 0) or 0,
            ))
        return lists

    async def create_campaign(
        self,
        list_id: str,
        subject: str,
        html: str,
        sender: SenderInfo | None = None,
    ) -> CampaignRef:
        import brevo_python  # type: ignore
        s = sender or self.sender
        client = self._client()
        api = brevo_python.EmailCampaignsApi(client)

        body = brevo_python.CreateEmailCampaign(
            name=f"Newsletter — {subject[:60]}",
            subject=subject,
            sender=brevo_python.CreateEmailCampaignSender(name=s.name, email=s.email),
            html_content=html,
            recipients=brevo_python.CreateEmailCampaignRecipients(list_ids=[int(list_id)]),
        )
        result = api.create_email_campaign(body)
        return CampaignRef(provider="brevo", campaign_id=str(result.id))

    async def create_ab_campaign(
        self,
        list_id: str,
        subjects: list[str],
        html: str,
        split_pct: int | None = None,
        winner_criteria: str = "open",
        wait_hours: int | None = None,
        sender: SenderInfo | None = None,
    ) -> CampaignRef:
        import brevo_python  # type: ignore
        s = sender or self.sender
        split = split_pct or self.config.ab_split_pct
        hours = wait_hours or self.config.ab_wait_hours

        # Brevo maps winner_criteria differently
        brevo_criteria_map = {"open": "open", "click": "click", "ctor": "ctor"}
        brevo_criteria = brevo_criteria_map.get(winner_criteria, "open")

        client = self._client()
        api = brevo_python.EmailCampaignsApi(client)

        body = brevo_python.CreateEmailCampaign(
            name=f"Newsletter A/B — {subjects[0][:50]}",
            subject_a=subjects[0],
            subject_b=subjects[1] if len(subjects) > 1 else subjects[0],
            sender=brevo_python.CreateEmailCampaignSender(name=s.name, email=s.email),
            html_content=html,
            recipients=brevo_python.CreateEmailCampaignRecipients(list_ids=[int(list_id)]),
            ab_testing=True,
            split_rule=split,
            winner_criteria=brevo_criteria,
            winner_delay=hours,
        )
        result = api.create_email_campaign(body)
        return CampaignRef(
            provider="brevo",
            campaign_id=str(result.id),
            extra={"ab": True, "subjects": subjects},
        )

    async def send_campaign(self, campaign_ref: CampaignRef) -> SendResult:
        import brevo_python  # type: ignore
        client = self._client()
        api = brevo_python.EmailCampaignsApi(client)
        api.send_email_campaign_now(int(campaign_ref.campaign_id))
        return SendResult(
            campaign_ref=campaign_ref,
            provider_send_id=campaign_ref.campaign_id,
            recipients_count=0,  # Brevo doesn't return count on send
        )

    async def get_report(self, campaign_ref: CampaignRef) -> CampaignReport:
        import brevo_python  # type: ignore
        client = self._client()
        api = brevo_python.EmailCampaignsApi(client)
        result = api.get_email_campaign(int(campaign_ref.campaign_id))
        stats = getattr(result, "statistics", None) or {}
        overall = getattr(stats, "overall_stats", None) or {}

        def _int(obj: Any, key: str) -> int:
            return int(getattr(obj, key, 0) or 0)

        return CampaignReport(
            campaign_ref=campaign_ref,
            sent=_int(overall, "sent"),
            delivered=_int(overall, "delivered"),
            opens=_int(overall, "opens"),
            unique_opens=_int(overall, "unique_opens"),
            clicks=_int(overall, "clicks"),
            unique_clicks=_int(overall, "unique_clicks"),
            unsubscribes=_int(overall, "unsubscriptions"),
            bounces=_int(overall, "hard_bounces") + _int(overall, "soft_bounces"),
        )


# ── Resend (fallback) ─────────────────────────────────────────────────────────

class ResendProvider(EmailProvider):
    """Resend adapter — transactional send only, no campaigns or list management."""

    async def validate(self) -> bool:
        if not self.config.api_key:
            raise RuntimeError("Resend API key not configured")
        return True

    async def get_lists(self) -> list[ContactList]:
        return []  # Resend has no list management

    async def create_campaign(
        self,
        list_id: str,
        subject: str,
        html: str,
        sender: SenderInfo | None = None,
    ) -> CampaignRef:
        # Resend has no campaign concept — store params for send step
        s = sender or self.sender
        return CampaignRef(
            provider="resend",
            campaign_id="pending",
            extra={"subject": subject, "html": html, "sender": s, "list_id": list_id},
        )

    async def create_ab_campaign(
        self,
        list_id: str,
        subjects: list[str],
        html: str,
        split_pct: int | None = None,
        winner_criteria: str = "open",
        wait_hours: int | None = None,
        sender: SenderInfo | None = None,
    ) -> CampaignRef:
        # Resend doesn't support A/B — use first subject
        log.warning("ResendProvider does not support A/B testing; using first subject")
        return await self.create_campaign(list_id, subjects[0], html, sender)

    async def send_campaign(self, campaign_ref: CampaignRef) -> SendResult:
        extra = campaign_ref.extra
        sender: SenderInfo = extra.get("sender") or self.sender

        resend.api_key = self.config.api_key or settings.resend_api_key
        result = resend.Emails.send({
            "from": f"{sender.name} <{sender.email}>",
            "to": [extra.get("list_id", "")],  # list_id is recipient for Resend
            "subject": extra.get("subject", "Newsletter"),
            "html": extra.get("html", ""),
        })
        send_id = result.get("id") if isinstance(result, dict) else str(result)
        return SendResult(
            campaign_ref=CampaignRef(provider="resend", campaign_id=send_id),
            provider_send_id=send_id,
            recipients_count=1,
        )

    async def get_report(self, campaign_ref: CampaignRef) -> CampaignReport:
        # Resend doesn't expose detailed analytics via API
        return CampaignReport(campaign_ref=campaign_ref)


# ── Mailchimp ─────────────────────────────────────────────────────────────────

class MailchimpProvider(EmailProvider):
    """Email provider adapter for Mailchimp (Marketing API v3)."""

    def _client(self):
        try:
            import mailchimp_marketing as mc  # type: ignore
            client = mc.Client()
            # Mailchimp API key format: <key>-<dc> e.g. abc123-us1
            key = self.config.api_key
            dc = key.rsplit("-", 1)[-1] if "-" in key else "us1"
            client.set_config({"api_key": key, "server": dc})
            return client
        except ImportError as e:
            raise RuntimeError("mailchimp-marketing SDK not installed") from e

    async def validate(self) -> bool:
        client = self._client()
        try:
            client.ping.get()
            return True
        except Exception as exc:
            raise RuntimeError(f"Mailchimp API key invalid: {exc}") from exc

    async def get_lists(self) -> list[ContactList]:
        client = self._client()
        response = client.lists.get_all_lists(count=100)
        lists = []
        for lst in (response.get("lists") or []):
            lists.append(ContactList(
                list_id=lst["id"],
                name=lst.get("name", ""),
                total_subscribers=lst.get("stats", {}).get("member_count", 0),
            ))
        return lists

    async def create_campaign(
        self,
        list_id: str,
        subject: str,
        html: str,
        sender: SenderInfo | None = None,
    ) -> CampaignRef:
        s = sender or self.sender
        client = self._client()

        campaign = client.campaigns.create({
            "type": "regular",
            "recipients": {"list_id": list_id},
            "settings": {
                "subject_line": subject,
                "from_name": s.name,
                "reply_to": s.email,
            },
        })
        campaign_id = campaign["id"]

        client.campaigns.set_content(campaign_id, {"html": html})
        return CampaignRef(provider="mailchimp", campaign_id=campaign_id)

    async def create_ab_campaign(
        self,
        list_id: str,
        subjects: list[str],
        html: str,
        split_pct: int | None = None,
        winner_criteria: str = "open",
        wait_hours: int | None = None,
        sender: SenderInfo | None = None,
    ) -> CampaignRef:
        s = sender or self.sender
        split = split_pct or self.config.ab_split_pct
        hours = wait_hours or self.config.ab_wait_hours
        mc_criteria = {"open": "opens", "click": "clicks", "ctor": "clicks"}.get(winner_criteria, "opens")

        client = self._client()
        campaign = client.campaigns.create({
            "type": "variate",
            "recipients": {"list_id": list_id},
            "variate_settings": {
                "winner_criteria": mc_criteria,
                "wait_time": hours * 60,  # Mailchimp uses minutes
                "test_size": split,
                "subject_lines": subjects[:4],  # Mailchimp supports up to 4
                "from_names": [s.name],
                "reply_to_addresses": [s.email],
            },
            "settings": {
                "subject_line": subjects[0],
                "from_name": s.name,
                "reply_to": s.email,
            },
        })
        campaign_id = campaign["id"]

        client.campaigns.set_content(campaign_id, {"html": html})
        return CampaignRef(
            provider="mailchimp",
            campaign_id=campaign_id,
            extra={"ab": True, "subjects": subjects},
        )

    async def send_campaign(self, campaign_ref: CampaignRef) -> SendResult:
        client = self._client()
        client.campaigns.send(campaign_ref.campaign_id)
        return SendResult(
            campaign_ref=campaign_ref,
            provider_send_id=campaign_ref.campaign_id,
            recipients_count=0,
        )

    async def get_report(self, campaign_ref: CampaignRef) -> CampaignReport:
        client = self._client()
        r = client.reports.get_campaign_report(campaign_ref.campaign_id)
        sends = r.get("emails_sent", 0) or 0
        bounces_hard = (r.get("bounces") or {}).get("hard_bounces", 0)
        bounces_soft = (r.get("bounces") or {}).get("soft_bounces", 0)
        opens_data = r.get("opens") or {}
        clicks_data = r.get("clicks") or {}
        unsubscribes = (r.get("unsubscribed") or 0)

        return CampaignReport(
            campaign_ref=campaign_ref,
            sent=sends,
            delivered=sends - bounces_hard - bounces_soft,
            opens=opens_data.get("opens_total", 0),
            unique_opens=opens_data.get("unique_opens", 0),
            clicks=clicks_data.get("clicks_total", 0),
            unique_clicks=clicks_data.get("unique_clicks", 0),
            unsubscribes=unsubscribes,
            bounces=bounces_hard + bounces_soft,
        )


# ── Factory ───────────────────────────────────────────────────────────────────

async def get_email_provider(brand_id: str) -> EmailProvider:
    """Return the configured EmailProvider for a brand.

    Falls back to ResendProvider using env-var credentials if no
    email_provider_config row exists for the brand.
    """
    db = get_db()
    row = (
        db.table("email_provider_config")
        .select("*")
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
        .data
    )

    if not row:
        # Global fallback — Resend via env var
        fallback_config = ProviderConfig(
            provider="resend",
            api_key=settings.resend_api_key,
            sender_name=settings.newsletter_from_name,
            sender_email=settings.newsletter_from_email,
            list_id="",
            webhook_secret="",
            ab_split_pct=20,
            ab_wait_hours=4,
        )
        return ResendProvider(fallback_config)

    # Resolve sender: row → brands.from_email → env var
    brand_row = (
        db.table("brands")
        .select("from_email, from_name")
        .eq("id", brand_id)
        .maybe_single()
        .execute()
        .data
    ) or {}

    sender_email = (
        row.get("sender_email")
        or brand_row.get("from_email")
        or settings.newsletter_from_email
    )
    sender_name = (
        row.get("sender_name")
        or brand_row.get("from_name")
        or settings.newsletter_from_name
    )

    config = ProviderConfig(
        provider=row["provider"],
        api_key=row["api_key"],
        sender_name=sender_name,
        sender_email=sender_email,
        list_id=row.get("list_id", ""),
        webhook_secret=row.get("webhook_secret", ""),
        ab_split_pct=row.get("ab_split_pct", 20),
        ab_wait_hours=row.get("ab_wait_hours", 4),
    )

    match config.provider:
        case "brevo":
            return BrevoProvider(config)
        case "mailchimp":
            return MailchimpProvider(config)
        case "resend":
            return ResendProvider(config)
        case _:
            log.warning("Unknown provider %s, falling back to Resend", config.provider)
            return ResendProvider(config)
