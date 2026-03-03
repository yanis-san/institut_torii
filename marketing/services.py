"""
Email marketing services — rendering, segment building, sending.

Core logic for the email marketing system:
- Template rendering with Django template engine
- Recipient list building from database segments
- Batch email sending with rate limiting
- Open/click tracking support
"""
import logging
import time
from html.parser import HTMLParser
from io import StringIO

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.utils import timezone

from .models import (
    EmailCampaign,
    CampaignRecipient,
    EmailSubscription,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Email addresses configuration
# ──────────────────────────────────────────────

EMAIL_ADDRESSES = {
    'contact': 'contact@institut-torii.com',
    'inscription': 'inscription@institut-torii.com',
    'notification': 'notification@institut-torii.com',
}

SITE_NAME = 'Institut Torii'

# Batch settings
BATCH_SIZE = 50
BATCH_DELAY = 2  # seconds between batches


def get_from_email(from_type):
    """Resolve from_email_type to actual email address."""
    address = getattr(settings, 'EMAIL_ADDRESSES', EMAIL_ADDRESSES).get(
        from_type, EMAIL_ADDRESSES['contact'],
    )
    return f'{SITE_NAME} <{address}>'


# ──────────────────────────────────────────────
# HTML → text stripping
# ──────────────────────────────────────────────

class _HTMLStripper(HTMLParser):
    """Simple HTML tag stripper for plain-text fallback."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, data):
        self.text.write(data)

    def get_data(self):
        return self.text.getvalue()


def strip_html(html):
    """Convert HTML to plain text."""
    stripper = _HTMLStripper()
    stripper.feed(html)
    text = stripper.get_data()
    # Collapse multiple newlines
    lines = [line.strip() for line in text.splitlines()]
    return '\n'.join(line for line in lines if line)


# ──────────────────────────────────────────────
# Template rendering
# ──────────────────────────────────────────────

def render_email_content(template_body, context_dict):
    """Render a Django template string with the given context."""
    tpl = Template(template_body)
    ctx = Context(context_dict)
    return tpl.render(ctx)


def build_email_context(recipient, campaign, unsubscribe_url=''):
    """Build the template context dict for a specific recipient."""
    return {
        'first_name': recipient.first_name or '',
        'last_name': recipient.last_name or '',
        'email': recipient.email,
        'site_name': SITE_NAME,
        'campaign_name': campaign.name,
        'unsubscribe_url': unsubscribe_url,
    }


# ──────────────────────────────────────────────
# Segment building
# ──────────────────────────────────────────────

def build_recipient_list(campaign):
    """
    Build a deduplicated list of recipient dicts from the campaign's segment.

    Returns list of dicts:
        [{'email': ..., 'first_name': ..., 'last_name': ...,
          'source_type': ..., 'source_id': ...}, ...]
    """
    # Lazy imports to avoid circular dependencies
    from contact.models import Prospect
    from registration.models import Enrollment

    seen_emails = set()
    recipients = []

    def _add(email, first_name, last_name, source_type, source_id):
        key = email.lower()
        if key in seen_emails:
            return
        seen_emails.add(key)
        recipients.append({
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'source_type': source_type,
            'source_id': source_id,
        })

    segment = campaign.segment_type
    filters = campaign.segment_filter or {}

    if segment == EmailCampaign.SegmentType.ALL_PROSPECTS:
        for p in Prospect.objects.all():
            _add(p.email, p.first_name, p.last_name, 'prospect', p.pk)

    elif segment == EmailCampaign.SegmentType.ALL_ENROLLED:
        for e in Enrollment.objects.all():
            _add(e.email, e.first_name, e.last_name, 'enrollment', e.pk)

    elif segment == EmailCampaign.SegmentType.ALL_CONFIRMED:
        for e in Enrollment.objects.filter(status='confirmed'):
            _add(e.email, e.first_name, e.last_name, 'enrollment', e.pk)

    elif segment == EmailCampaign.SegmentType.PROSPECTS_BY_LANGUAGE:
        lang_id = filters.get('language_id')
        qs = Prospect.objects.all()
        if lang_id:
            qs = qs.filter(interested_language_id=lang_id)
        for p in qs:
            _add(p.email, p.first_name, p.last_name, 'prospect', p.pk)

    elif segment == EmailCampaign.SegmentType.PROSPECTS_BY_RATING:
        rating = filters.get('rating')
        qs = Prospect.objects.all()
        if rating:
            qs = qs.filter(rating=rating)
        else:
            qs = qs.none()  # No rating filter = no results (must be explicit)
        for p in qs:
            _add(p.email, p.first_name, p.last_name, 'prospect', p.pk)

    elif segment == EmailCampaign.SegmentType.ENROLLED_BY_COHORT:
        cohort_id = filters.get('cohort_id')
        qs = Enrollment.objects.all()
        if cohort_id:
            qs = qs.filter(cohort_id=cohort_id)
        for e in qs:
            _add(e.email, e.first_name, e.last_name, 'enrollment', e.pk)

    elif segment == EmailCampaign.SegmentType.ENROLLED_BY_LANGUAGE:
        lang_id = filters.get('language_id')
        qs = Enrollment.objects.select_related('cohort__language')
        if lang_id:
            qs = qs.filter(cohort__language_id=lang_id)
        for e in qs:
            _add(e.email, e.first_name, e.last_name, 'enrollment', e.pk)

    elif segment == EmailCampaign.SegmentType.CUSTOM:
        # Custom emails are added manually as CampaignRecipient records
        pass

    # Filter out unsubscribed emails
    if recipients:
        unsubscribed = set(
            EmailSubscription.objects.filter(
                is_subscribed=False,
                email__in=[r['email'].lower() for r in recipients],
            ).values_list('email', flat=True)
        )
        recipients = [
            r for r in recipients
            if r['email'].lower() not in unsubscribed
        ]

    return recipients


def populate_campaign_recipients(campaign):
    """
    Build the recipient list and create CampaignRecipient records.
    Returns the count of recipients created.
    """
    recipient_data = build_recipient_list(campaign)

    # Remove existing pending recipients (in case of re-population)
    campaign.recipients.filter(status=CampaignRecipient.Status.PENDING).delete()

    created = []
    for r in recipient_data:
        # Skip if already exists (e.g., previously sent)
        if campaign.recipients.filter(email=r['email']).exists():
            continue
        created.append(CampaignRecipient(
            campaign=campaign,
            email=r['email'],
            first_name=r['first_name'],
            last_name=r['last_name'],
            source_type=r['source_type'],
            source_id=r['source_id'],
        ))

    if created:
        CampaignRecipient.objects.bulk_create(created)

    campaign.total_recipients = campaign.recipients.count()
    campaign.save(update_fields=['total_recipients', 'updated_at'])

    return len(created)


# ──────────────────────────────────────────────
# Email sending
# ──────────────────────────────────────────────

def send_single_email(recipient, campaign, base_url=''):
    """
    Send a single email to one recipient.
    Returns True on success, False on failure.
    """
    # Get or create subscription for unsubscribe link
    sub = EmailSubscription.get_or_create_subscription(recipient.email)
    unsubscribe_url = f'{base_url}/email/unsubscribe/{sub.unsubscribe_token}/'

    # Build context and render
    context = build_email_context(recipient, campaign, unsubscribe_url)
    subject = render_email_content(campaign.effective_subject, context)
    html_body = render_email_content(campaign.template.body_html, context)

    # Plain text fallback
    if campaign.template.body_text:
        text_body = render_email_content(campaign.template.body_text, context)
    else:
        text_body = strip_html(html_body)

    # Sender
    from_email = get_from_email(campaign.from_email_type)
    reply_to_list = []
    if campaign.reply_to:
        reply_to_list = [campaign.reply_to]

    # Build and send
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[recipient.email],
        reply_to=reply_to_list or None,
        headers={
            'List-Unsubscribe': f'<{unsubscribe_url}>',
            'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
        },
    )
    msg.attach_alternative(html_body, 'text/html')

    try:
        msg.send(fail_silently=False)
        recipient.status = CampaignRecipient.Status.SENT
        recipient.sent_at = timezone.now()
        recipient.error_message = ''
        recipient.save(update_fields=['status', 'sent_at', 'error_message'])
        return True
    except Exception as exc:
        logger.error('Email send failed to %s: %s', recipient.email, exc)
        recipient.status = CampaignRecipient.Status.FAILED
        recipient.error_message = str(exc)[:500]
        recipient.save(update_fields=['status', 'error_message'])
        return False


def send_campaign(campaign, base_url=''):
    """
    Send all pending emails for a campaign in batches.
    Updates campaign counters and status.
    """
    if campaign.status not in (
        EmailCampaign.Status.DRAFT,
        EmailCampaign.Status.SCHEDULED,
        EmailCampaign.Status.SENDING,
    ):
        logger.warning('Campaign %s not in sendable state: %s', campaign.pk, campaign.status)
        return

    # Mark campaign as sending
    campaign.status = EmailCampaign.Status.SENDING
    campaign.started_at = campaign.started_at or timezone.now()
    campaign.save(update_fields=['status', 'started_at', 'updated_at'])

    pending = campaign.recipients.filter(
        status=CampaignRecipient.Status.PENDING,
    ).order_by('pk')

    total_pending = pending.count()
    sent = 0
    failed = 0

    batch_size = getattr(settings, 'EMAIL_BATCH_SIZE', BATCH_SIZE)
    batch_delay = getattr(settings, 'EMAIL_BATCH_DELAY', BATCH_DELAY)

    for i in range(0, total_pending, batch_size):
        batch = list(pending[i:i + batch_size])
        for recipient in batch:
            success = send_single_email(recipient, campaign, base_url)
            if success:
                sent += 1
            else:
                failed += 1

        # Update counters after each batch
        campaign.sent_count = campaign.recipients.filter(
            status=CampaignRecipient.Status.SENT,
        ).count()
        campaign.failed_count = campaign.recipients.filter(
            status=CampaignRecipient.Status.FAILED,
        ).count()
        campaign.save(update_fields=['sent_count', 'failed_count', 'updated_at'])

        # Rate limiting between batches
        if i + batch_size < total_pending and batch_delay > 0:
            time.sleep(batch_delay)

    # Mark as completed
    campaign.status = EmailCampaign.Status.SENT
    campaign.completed_at = timezone.now()
    campaign.sent_count = campaign.recipients.filter(
        status=CampaignRecipient.Status.SENT,
    ).count()
    campaign.failed_count = campaign.recipients.filter(
        status=CampaignRecipient.Status.FAILED,
    ).count()
    campaign.save(update_fields=[
        'status', 'completed_at', 'sent_count', 'failed_count', 'updated_at',
    ])

    logger.info(
        'Campaign "%s" completed: %d sent, %d failed out of %d.',
        campaign.name, sent, failed, total_pending,
    )
    return sent, failed
