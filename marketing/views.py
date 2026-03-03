"""
Marketing views — CMS management + public endpoints.

CMS views (login_required): template CRUD, campaign CRUD, subscriber list.
Public views: unsubscribe, email tracking.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import EmailCampaignForm, EmailTemplateForm, NotificationTemplateForm
from .models import (
    CampaignRecipient,
    EmailCampaign,
    EmailSubscription,
    EmailTemplate,
    NotificationLog,
    NotificationTemplate,
)
from .services import (
    build_recipient_list,
    populate_campaign_recipients,
    render_email_content,
    send_campaign,
)

_LOGIN_URL = reverse_lazy('cms:login')


# ──────────────────────────────────────────────
# Email Templates — CRUD
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def template_list(request):
    """List all email templates."""
    qs = EmailTemplate.objects.all()

    search = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')

    if search:
        qs = qs.filter(
            Q(name__icontains=search) | Q(subject__icontains=search)
        )
    if category:
        qs = qs.filter(category=category)

    return render(request, 'marketing/template_list.html', {
        'templates': qs,
        'categories': EmailTemplate.Category.choices,
        'current_category': category,
        'search_query': search,
    })


@login_required(login_url=_LOGIN_URL)
def template_create(request):
    """Create a new email template."""
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template créé avec succès.')
            return redirect('marketing:template_list')
    else:
        form = EmailTemplateForm()

    return render(request, 'marketing/template_form.html', {
        'form': form,
        'editing': False,
    })


@login_required(login_url=_LOGIN_URL)
def template_edit(request, pk):
    """Edit an existing email template."""
    template = get_object_or_404(EmailTemplate, pk=pk)

    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template mis à jour.')
            return redirect('marketing:template_list')
    else:
        form = EmailTemplateForm(instance=template)

    return render(request, 'marketing/template_form.html', {
        'form': form,
        'template_obj': template,
        'editing': True,
    })


@login_required(login_url=_LOGIN_URL)
@require_POST
def template_delete(request, pk):
    """Delete an email template."""
    template = get_object_or_404(EmailTemplate, pk=pk)

    # Check if template is used by campaigns
    if template.campaigns.exists():
        messages.error(
            request,
            'Ce template est utilisé par des campagnes et ne peut pas être supprimé.',
        )
        return redirect('marketing:template_list')

    template.delete()
    messages.success(request, 'Template supprimé.')
    return redirect('marketing:template_list')


@login_required(login_url=_LOGIN_URL)
def template_preview(request, pk):
    """Preview an email template with sample data."""
    template = get_object_or_404(EmailTemplate, pk=pk)

    sample_context = {
        'first_name': 'Yuki',
        'last_name': 'TANAKA',
        'email': 'yuki@example.com',
        'site_name': 'Institut Torii',
        'campaign_name': 'Aperçu du template',
        'unsubscribe_url': '#',
    }

    rendered_subject = render_email_content(template.subject, sample_context)
    rendered_body = render_email_content(template.body_html, sample_context)

    return render(request, 'marketing/template_preview.html', {
        'template_obj': template,
        'rendered_subject': rendered_subject,
        'rendered_body': rendered_body,
    })


# ──────────────────────────────────────────────
# Email Campaigns — CRUD
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def campaign_list(request):
    """List all campaigns."""
    qs = EmailCampaign.objects.select_related('template').all()

    status = request.GET.get('status', '')
    search = request.GET.get('q', '').strip()

    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            Q(name__icontains=search) | Q(subject__icontains=search)
        )

    return render(request, 'marketing/campaign_list.html', {
        'campaigns': qs,
        'statuses': EmailCampaign.Status.choices,
        'current_status': status,
        'search_query': search,
    })


@login_required(login_url=_LOGIN_URL)
def campaign_create(request):
    """Create a new campaign."""
    if request.method == 'POST':
        form = EmailCampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save()
            messages.success(request, f'Campagne « {campaign.name} » créée. Pensez à préparer les destinataires.')
            return redirect('marketing:campaign_detail', pk=campaign.pk)
    else:
        form = EmailCampaignForm()

    return render(request, 'marketing/campaign_form.html', {
        'form': form,
        'editing': False,
    })


@login_required(login_url=_LOGIN_URL)
def campaign_edit(request, pk):
    """Edit a draft campaign."""
    campaign = get_object_or_404(EmailCampaign, pk=pk)

    if campaign.status != EmailCampaign.Status.DRAFT:
        messages.error(request, 'Seules les campagnes en brouillon peuvent être modifiées.')
        return redirect('marketing:campaign_detail', pk=pk)

    if request.method == 'POST':
        form = EmailCampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, 'Campagne mise à jour.')
            return redirect('marketing:campaign_detail', pk=campaign.pk)
    else:
        form = EmailCampaignForm(instance=campaign)

    return render(request, 'marketing/campaign_form.html', {
        'form': form,
        'campaign': campaign,
        'editing': True,
    })


@login_required(login_url=_LOGIN_URL)
def campaign_detail(request, pk):
    """Campaign detail with stats and recipient list."""
    campaign = get_object_or_404(
        EmailCampaign.objects.select_related('template'),
        pk=pk,
    )

    recipients = campaign.recipients.all()
    sent_recipients = recipients.filter(status=CampaignRecipient.Status.SENT)
    failed_recipients = recipients.filter(status=CampaignRecipient.Status.FAILED)
    pending_recipients = recipients.filter(status=CampaignRecipient.Status.PENDING)

    # Estimate count for segment (before populating)
    estimated_count = None
    if campaign.status == EmailCampaign.Status.DRAFT and campaign.total_recipients == 0:
        estimated_count = len(build_recipient_list(campaign))

    return render(request, 'marketing/campaign_detail.html', {
        'campaign': campaign,
        'recipients': recipients[:100],
        'total_recipients': recipients.count(),
        'sent_count': sent_recipients.count(),
        'failed_count': failed_recipients.count(),
        'pending_count': pending_recipients.count(),
        'estimated_count': estimated_count,
    })


@login_required(login_url=_LOGIN_URL)
@require_POST
def campaign_populate(request, pk):
    """Populate campaign recipients from the selected segment."""
    campaign = get_object_or_404(EmailCampaign, pk=pk)

    if campaign.status != EmailCampaign.Status.DRAFT:
        messages.error(request, 'Seules les campagnes en brouillon peuvent être préparées.')
        return redirect('marketing:campaign_detail', pk=pk)

    count = populate_campaign_recipients(campaign)
    messages.success(request, f'{count} destinataires ajoutés à la campagne.')
    return redirect('marketing:campaign_detail', pk=pk)


@login_required(login_url=_LOGIN_URL)
@require_POST
def campaign_send(request, pk):
    """Trigger sending of a campaign."""
    campaign = get_object_or_404(EmailCampaign, pk=pk)

    if campaign.status not in (EmailCampaign.Status.DRAFT, EmailCampaign.Status.SCHEDULED):
        messages.error(request, "Cette campagne n'est pas en état d'être envoyée.")
        return redirect('marketing:campaign_detail', pk=pk)

    if campaign.total_recipients == 0:
        messages.error(request, "Aucun destinataire. Préparez les destinataires d'abord.")
        return redirect('marketing:campaign_detail', pk=pk)

    # Build base URL for tracking/unsubscribe links
    base_url = request.build_absolute_uri('/').rstrip('/')

    sent, failed = send_campaign(campaign, base_url=base_url)
    messages.success(
        request,
        f'Campagne envoyée : {sent} emails envoyés, {failed} échoués.',
    )
    return redirect('marketing:campaign_detail', pk=pk)


@login_required(login_url=_LOGIN_URL)
@require_POST
def campaign_cancel(request, pk):
    """Cancel a campaign."""
    campaign = get_object_or_404(EmailCampaign, pk=pk)

    if campaign.status in (EmailCampaign.Status.SENT, EmailCampaign.Status.CANCELLED):
        messages.error(request, 'Cette campagne ne peut pas être annulée.')
        return redirect('marketing:campaign_detail', pk=pk)

    campaign.status = EmailCampaign.Status.CANCELLED
    campaign.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Campagne annulée.')
    return redirect('marketing:campaign_detail', pk=pk)


@login_required(login_url=_LOGIN_URL)
@require_POST
def campaign_delete(request, pk):
    """Delete a draft campaign."""
    campaign = get_object_or_404(EmailCampaign, pk=pk)

    if campaign.status != EmailCampaign.Status.DRAFT:
        messages.error(request, 'Seules les campagnes en brouillon peuvent être supprimées.')
        return redirect('marketing:campaign_list')

    campaign.delete()
    messages.success(request, 'Campagne supprimée.')
    return redirect('marketing:campaign_list')


@login_required(login_url=_LOGIN_URL)
def campaign_preview(request, pk):
    """Preview a campaign email with sample data."""
    campaign = get_object_or_404(
        EmailCampaign.objects.select_related('template'),
        pk=pk,
    )

    sample_context = {
        'first_name': 'Yuki',
        'last_name': 'TANAKA',
        'email': 'yuki@example.com',
        'site_name': 'Institut Torii',
        'campaign_name': campaign.name,
        'unsubscribe_url': '#',
    }

    rendered_subject = render_email_content(campaign.effective_subject, sample_context)
    rendered_body = render_email_content(campaign.template.body_html, sample_context)

    return render(request, 'marketing/campaign_preview.html', {
        'campaign': campaign,
        'rendered_subject': rendered_subject,
        'rendered_body': rendered_body,
    })


# ──────────────────────────────────────────────
# Subscribers
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def subscriber_list(request):
    """List all email subscriptions."""
    qs = EmailSubscription.objects.all().order_by('-created_at')

    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if search:
        qs = qs.filter(email__icontains=search)
    if status == 'subscribed':
        qs = qs.filter(is_subscribed=True)
    elif status == 'unsubscribed':
        qs = qs.filter(is_subscribed=False)

    total_subscribed = EmailSubscription.objects.filter(is_subscribed=True).count()
    total_unsubscribed = EmailSubscription.objects.filter(is_subscribed=False).count()

    return render(request, 'marketing/subscriber_list.html', {
        'subscribers': qs,
        'total_subscribed': total_subscribed,
        'total_unsubscribed': total_unsubscribed,
        'search_query': search,
        'current_status': status,
    })


# ──────────────────────────────────────────────
# Notification Log — CMS read-only management
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def notification_list(request):
    """List all transactional email notifications."""
    qs = NotificationLog.objects.select_related('sent_by').all()

    search = request.GET.get('q', '').strip()
    event_type = request.GET.get('event', '')
    status = request.GET.get('status', '')

    if search:
        qs = qs.filter(
            Q(recipient_email__icontains=search)
            | Q(recipient_name__icontains=search)
            | Q(subject__icontains=search)
        )
    if event_type:
        qs = qs.filter(event_type=event_type)
    if status:
        qs = qs.filter(status=status)

    # KPIs
    total_sent = NotificationLog.objects.filter(status='sent').count()
    total_failed = NotificationLog.objects.filter(status='failed').count()

    return render(request, 'marketing/notification_list.html', {
        'notifications': qs[:200],
        'total_count': qs.count(),
        'total_sent': total_sent,
        'total_failed': total_failed,
        'event_types': NotificationLog.EventType.choices,
        'current_event': event_type,
        'current_status': status,
        'search_query': search,
    })


@login_required(login_url=_LOGIN_URL)
def notification_detail(request, pk):
    """View details of a specific notification, including rendered content."""
    notification = get_object_or_404(NotificationLog.objects.select_related('sent_by'), pk=pk)
    return render(request, 'marketing/notification_detail.html', {
        'notification': notification,
    })


# ──────────────────────────────────────────────
# NotificationTemplate — editable transactional email templates
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def notification_template_list(request):
    """List all editable notification templates. Auto-creates defaults."""
    NotificationTemplate.ensure_defaults()
    templates = NotificationTemplate.objects.all()
    return render(request, 'marketing/notification_template_list.html', {
        'templates': templates,
    })


@login_required(login_url=_LOGIN_URL)
def notification_template_edit(request, pk):
    """Edit a transactional email notification template."""
    tpl = get_object_or_404(NotificationTemplate, pk=pk)

    if request.method == 'POST':
        form = NotificationTemplateForm(request.POST, instance=tpl)
        if form.is_valid():
            form.save()
            messages.success(request, f'Template « {tpl.get_event_type_display()} » mis à jour.')
            return redirect('marketing:notification_template_list')
    else:
        form = NotificationTemplateForm(instance=tpl)

    # Available variables per event type
    variables = {
        'contact_received': ['first_name', 'last_name', 'email', 'site_name', 'site_url'],
        'enrollment_received': ['first_name', 'last_name', 'email', 'cohort_name', 'enrollment_code', 'site_name', 'site_url'],
        'enrollment_confirmed': ['first_name', 'last_name', 'email', 'cohort_name', 'enrollment_code', 'start_date', 'site_name', 'site_url'],
        'enrollment_rejected': ['first_name', 'last_name', 'email', 'cohort_name', 'rejection_reason', 'site_name', 'site_url'],
        'enrollment_refunded': ['first_name', 'last_name', 'email', 'cohort_name', 'site_name', 'site_url'],
    }

    return render(request, 'marketing/notification_template_edit.html', {
        'form': form,
        'template': tpl,
        'variables': variables.get(tpl.event_type, []),
    })


@login_required(login_url=_LOGIN_URL)
@require_POST
def notification_template_reset(request, pk):
    """Reset a notification template to its code default."""
    from .notifications import DEFAULT_TEMPLATES
    tpl = get_object_or_404(NotificationTemplate, pk=pk)
    default = DEFAULT_TEMPLATES.get(tpl.event_type)
    if default:
        tpl.subject = default['subject']
        tpl.body_html = default['body_html']
        tpl.is_active = True
        tpl.save()
        messages.success(request, f'Template « {tpl.get_event_type_display()} » réinitialisé.')
    return redirect('marketing:notification_template_list')


@login_required(login_url=_LOGIN_URL)
def notification_template_preview(request, pk):
    """Preview a notification template with sample data."""
    from .notifications import _render
    tpl = get_object_or_404(NotificationTemplate, pk=pk)
    sample_context = {
        'first_name': 'Yuki',
        'last_name': 'TANAKA',
        'email': 'yuki@exemple.com',
        'site_name': 'Institut Torii',
        'site_url': 'https://institut-torii.com',
        'cohort_name': 'Japonais N5 — Été 2026',
        'enrollment_code': 'ABC12345',
        'start_date': '15/09/2026',
        'rejection_reason': 'Reçu de paiement non lisible.',
    }
    rendered_subject = _render(tpl.subject, sample_context)
    rendered_body = _render(tpl.body_html, sample_context)
    return render(request, 'marketing/notification_template_preview.html', {
        'template': tpl,
        'rendered_subject': rendered_subject,
        'rendered_body': rendered_body,
    })


# ──────────────────────────────────────────────
# Public endpoints (no auth required)
# ──────────────────────────────────────────────

def unsubscribe(request, token):
    """Public unsubscribe page — tokenized, no login required."""
    sub = get_object_or_404(EmailSubscription, unsubscribe_token=token)

    if request.method == 'POST':
        sub.is_subscribed = False
        sub.unsubscribed_at = timezone.now()
        sub.save(update_fields=['is_subscribed', 'unsubscribed_at'])
        return render(request, 'marketing/unsubscribe_confirm.html', {
            'email': sub.email,
        })

    return render(request, 'marketing/unsubscribe.html', {
        'email': sub.email,
        'token': token,
    })


def track_open(request, token):
    """Tracking pixel — records email open event."""
    try:
        recipient = CampaignRecipient.objects.get(open_token=token)
        if not recipient.opened_at:
            recipient.opened_at = timezone.now()
            recipient.save(update_fields=['opened_at'])

            # Update campaign counter
            campaign = recipient.campaign
            campaign.opened_count = campaign.recipients.filter(
                opened_at__isnull=False,
            ).count()
            campaign.save(update_fields=['opened_count', 'updated_at'])
    except CampaignRecipient.DoesNotExist:
        pass

    # Return 1x1 transparent GIF pixel
    pixel = (
        b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00'
        b'\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00'
        b'\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00'
        b'\x00\x02\x02\x44\x01\x00\x3b'
    )
    return HttpResponse(pixel, content_type='image/gif')


def track_click(request, token):
    """Click tracking — records click and redirects to target URL."""
    from urllib.parse import urlparse
    url = request.GET.get('url', '/')

    # Allow http(s) and relative URLs only — block javascript:, data:, etc.
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        url = '/'

    try:
        recipient = CampaignRecipient.objects.get(click_token=token)
        if not recipient.clicked_at:
            recipient.clicked_at = timezone.now()
            recipient.save(update_fields=['clicked_at'])

            # Update campaign counter
            campaign = recipient.campaign
            campaign.clicked_count = campaign.recipients.filter(
                clicked_at__isnull=False,
            ).count()
            campaign.save(update_fields=['clicked_count', 'updated_at'])
    except CampaignRecipient.DoesNotExist:
        pass

    return redirect(url)
