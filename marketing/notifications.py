"""
Transactional email notifications — Institut Torii.

Sends automatic emails on key events:
- Contact form submitted → acknowledgment to prospect
- Enrollment submitted → acknowledgment with payment instructions
- Enrollment confirmed → confirmation with enrollment code
- Enrollment rejected → notification with reason
- Enrollment refunded → refund notification

Each send is logged in NotificationLog for full CMS visibility.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context

from .models import NotificationLog
from .services import get_from_email, strip_html

logger = logging.getLogger(__name__)

SITE_NAME = 'Institut Torii'
SITE_URL = 'https://institut-torii.com'
LOGO_URL = f'{SITE_URL}/static/img/logo/logo_horizontal.png'

# ──────────────────────────────────────────────
# Email wrapper (header + footer around body)
# ──────────────────────────────────────────────

def _build_email_wrapper():
    """Build the email wrapper HTML with logo header and branded footer."""
    return (
        '<!DOCTYPE html>'
        '<html lang="fr">'
        '<head><meta charset="UTF-8"></head>'
        '<body style="margin:0;padding:0;background:#f4f4f5;'
        "font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">"
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;">'
        '<tr><td align="center" style="padding:32px 16px;">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">'
        # Logo header
        '<tr><td align="center" style="padding:28px 24px 16px;border-bottom:1px solid #f0f0f0;">'
        f'<a href="{SITE_URL}" style="text-decoration:none;">'
        f'<img src="{LOGO_URL}" alt="Institut Torii" width="180" style="display:block;max-width:180px;height:auto;">'
        '</a></td></tr>'
        # Body placeholder
        '<tr><td style="padding:0;">BODY_CONTENT_PLACEHOLDER</td></tr>'
        # Footer
        '<tr><td style="padding:0;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="background:#18181b;border-radius:0 0 12px 12px;">'
        # Footer logo
        '<tr><td align="center" style="padding:28px 24px 16px;">'
        f'<img src="{LOGO_URL}" alt="Institut Torii" width="120" '
        'style="display:block;max-width:120px;height:auto;opacity:0.9;">'
        '</td></tr>'
        # Footer text
        '<tr><td align="center" style="padding:0 24px;">'
        '<p style="margin:0 0 4px;font-size:15px;font-weight:600;color:#ffffff;">'
        "L\u2019\u00e9quipe Institut Torii</p>"
        '<p style="margin:0;font-size:13px;color:#a1a1aa;">'
        'Centre de formation en langues asiatiques</p>'
        '</td></tr>'
        # Phone
        '<tr><td align="center" style="padding:16px 24px 0;">'
        '<span style="font-size:13px;color:#a1a1aa;">&#9742; 0557 74 59 20</span>'
        '</td></tr>'
        # Address
        '<tr><td align="center" style="padding:8px 24px 0;">'
        '<span style="font-size:13px;color:#a1a1aa;">&#128205; Alger, El Achour</span>'
        '</td></tr>'
        # Website link
        '<tr><td align="center" style="padding:12px 24px 8px;">'
        f'<a href="{SITE_URL}" style="font-size:13px;color:#ef4444;text-decoration:none;">'
        'institut-torii.com</a>'
        '</td></tr>'
        # Copyright
        '<tr><td align="center" style="padding:0 24px 24px;">'
        '<p style="margin:0;font-size:11px;color:#52525b;">'
        '\u00a9 2026 Institut Torii. Tous droits r\u00e9serv\u00e9s.</p>'
        '</td></tr>'
        '</table></td></tr>'
        '</table>'
        '</td></tr></table>'
        '</body></html>'
    )


EMAIL_WRAPPER = _build_email_wrapper()


def wrap_email_html(body_html):
    """Wrap body content in the branded email template with header + footer."""
    return EMAIL_WRAPPER.replace('BODY_CONTENT_PLACEHOLDER', body_html)

DEFAULT_TEMPLATES = {
    'contact_received': {
        'subject': 'Nous avons bien reçu votre message — {{ site_name }}',
        'body_html': """
<div style="font-family: sans-serif; padding: 24px;">
    <h2 style="color: #333;">Bonjour {{ first_name }},</h2>
    <p>Nous avons bien reçu votre demande de renseignement et nous vous en remercions.</p>
    <p>Notre équipe reviendra vers vous dans les <strong>48 heures ouvrables</strong>.</p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 14px; color: #666;">
        Si vous avez des questions urgentes, n'hésitez pas à nous répondre directement à cet email.
    </p>
</div>""",
    },

    'enrollment_received': {
        'subject': 'Inscription reçue — {{ cohort_name }} — {{ site_name }}',
        'body_html': """
<div style="font-family: sans-serif; padding: 24px;">
    <h2 style="color: #333;">Bonjour {{ first_name }},</h2>
    <p>Nous avons bien reçu votre inscription à <strong>{{ cohort_name }}</strong>.</p>
    <p>Votre code de suivi est : <strong style="font-size: 18px; color: #dc2626;">{{ enrollment_code }}</strong></p>
    <p>Conservez bien ce code, il vous permettra de suivre l'état de votre inscription à tout moment.</p>
    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <p style="margin: 0 0 8px 0; font-weight: 600;">📋 Prochaine étape :</p>
        <p style="margin: 0;">Notre équipe va vérifier votre reçu de paiement. Vous recevrez un email de confirmation dès que votre inscription sera validée.</p>
    </div>
</div>""",
    },

    'enrollment_confirmed': {
        'subject': '✅ Inscription confirmée — {{ cohort_name }} — {{ site_name }}',
        'body_html': """
<div style="font-family: sans-serif; padding: 24px;">
    <h2 style="color: #16a34a;">Félicitations {{ first_name }} ! 🎉</h2>
    <p>Votre inscription à <strong>{{ cohort_name }}</strong> est officiellement <strong style="color: #16a34a;">confirmée</strong>.</p>
    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <p style="margin: 0 0 8px 0; font-weight: 600;">📌 Vos informations :</p>
        <ul style="margin: 0; padding-left: 20px;">
            <li>Formation : <strong>{{ cohort_name }}</strong></li>
            <li>Code de suivi : <strong>{{ enrollment_code }}</strong></li>
            {% if start_date %}<li>Début : <strong>{{ start_date }}</strong></li>{% endif %}
        </ul>
    </div>
    <p>Nous vous contacterons prochainement avec les détails pratiques (horaires, lieu, etc.).</p>
</div>""",
    },

    'enrollment_rejected': {
        'subject': 'Inscription non validée — {{ cohort_name }} — {{ site_name }}',
        'body_html': """
<div style="font-family: sans-serif; padding: 24px;">
    <h2 style="color: #333;">Bonjour {{ first_name }},</h2>
    <p>Nous avons examiné votre inscription à <strong>{{ cohort_name }}</strong> et malheureusement, celle-ci n'a pas pu être validée.</p>
    {% if rejection_reason %}
    <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <p style="margin: 0 0 8px 0; font-weight: 600;">📋 Motif :</p>
        <p style="margin: 0;">{{ rejection_reason }}</p>
    </div>
    {% endif %}
    <p>Si vous pensez qu'il s'agit d'une erreur, n'hésitez pas à nous répondre à cet email ou à nous contacter.</p>
</div>""",
    },

    'enrollment_refunded': {
        'subject': 'Remboursement — {{ cohort_name }} — {{ site_name }}',
        'body_html': """
<div style="font-family: sans-serif; padding: 24px;">
    <h2 style="color: #333;">Bonjour {{ first_name }},</h2>
    <p>Nous vous informons que votre inscription à <strong>{{ cohort_name }}</strong> a été remboursée.</p>
    <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <p style="margin: 0 0 8px 0; font-weight: 600;">💰 Remboursement :</p>
        <p style="margin: 0;">Le remboursement sera effectué selon le même mode de paiement utilisé lors de votre inscription. Le délai peut varier selon votre banque.</p>
    </div>
    <p>Pour toute question, n'hésitez pas à nous répondre à cet email.</p>
</div>""",
    },

    'appointment_booked': {
        'subject': 'Confirmation de rendez-vous — {{ category_name }} — {{ site_name }}',
        'body_html': """
<div style="font-family: sans-serif; padding: 24px;">
    <h2 style="color: #333;">Bonjour {{ first_name }},</h2>
    <p>Votre rendez-vous a bien été enregistré. Voici le récapitulatif :</p>
    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <p style="margin: 0 0 8px 0; font-weight: 600;">📅 Détails du rendez-vous</p>
        <p style="margin: 0;">Catégorie : <strong>{{ category_name }}</strong></p>
        <p style="margin: 0;">Date : <strong>{{ date }}</strong></p>
        <p style="margin: 0;">Horaire : <strong>{{ start_time }} – {{ end_time }}</strong></p>
        <p style="margin: 0;">Code : <strong>{{ appointment_code }}</strong></p>
    </div>
    <p>Veuillez vous présenter à l'accueil de l'Institut Torii à l'heure convenue avec votre code de rendez-vous.</p>
    <p>Pour toute question ou annulation, n'hésitez pas à nous contacter.</p>
</div>""",
    },
}


# ──────────────────────────────────────────────
# Core send function
# ──────────────────────────────────────────────

def _render(template_str, context_dict):
    """
    Render a notification template string with context using safe rendering.
    
    Context values are HTML-escaped to prevent SSTI/XSS from admin-entered
    values like rejection_reason (e.g. {{ settings.SECRET_KEY }} won't work).
    """
    from django.utils.html import escape
    safe_context = {}
    for key, value in context_dict.items():
        if isinstance(value, str):
            safe_context[key] = escape(value)
        else:
            safe_context[key] = value
    tpl = Template(template_str)
    return tpl.render(Context(safe_context))


def send_notification(
    event_type,
    recipient_email,
    context,
    *,
    recipient_name='',
    related_model='',
    related_id=None,
    sent_by=None,
    from_type='inscription',
):
    """
    Send a transactional email and log it.

    Args:
        event_type: One of NotificationLog.EventType values
        recipient_email: Destination email
        context: Dict of template variables
        recipient_name: Display name for logging
        related_model: 'prospect' or 'enrollment'
        related_id: PK of related object
        sent_by: User who triggered the action (None = automatic)
        from_type: 'contact', 'inscription', or 'notification'

    Returns:
        NotificationLog instance
    """
    # Try DB template first (editable from CMS), fallback to code defaults
    from .models import NotificationTemplate
    template_data = NotificationTemplate.get_template(event_type)
    if not template_data:
        template_data = DEFAULT_TEMPLATES.get(event_type, {})
    if not template_data:
        logger.error('No template for event type: %s', event_type)
        return None

    # Ensure common context
    context.setdefault('site_name', SITE_NAME)
    context.setdefault('site_url', SITE_URL)

    # Render
    subject = _render(template_data['subject'], context)
    html_body = _render(template_data['body_html'], context)
    full_html = wrap_email_html(html_body)
    text_body = strip_html(html_body)

    # Build email
    from_email = get_from_email(from_type)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[recipient_email],
    )
    msg.attach_alternative(full_html, 'text/html')

    # Send
    status = NotificationLog.Status.SENT
    error = ''

    try:
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.error('Notification email failed to %s: %s', recipient_email, exc)
        status = NotificationLog.Status.FAILED
        error = str(exc)[:500]

    # Log
    log = NotificationLog.objects.create(
        event_type=event_type,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        body_html=full_html,
        related_model=related_model,
        related_id=related_id,
        status=status,
        error_message=error,
        sent_by=sent_by,
    )

    return log


# ──────────────────────────────────────────────
# High-level notification functions
# ──────────────────────────────────────────────

def notify_contact_received(prospect):
    """
    Envoie un accusé de réception au prospect après soumission du formulaire.
    Appelé depuis contact/views.py.
    """
    return send_notification(
        event_type='contact_received',
        recipient_email=prospect.email,
        context={
            'first_name': prospect.first_name,
            'last_name': prospect.last_name,
            'email': prospect.email,
        },
        recipient_name=f'{prospect.first_name} {prospect.last_name}',
        related_model='prospect',
        related_id=prospect.pk,
        from_type='contact',
    )


def notify_enrollment_received(enrollment):
    """
    Envoie un accusé de réception après inscription en ligne.
    Appelé depuis registration/views.py.
    """
    cohort = enrollment.cohort
    return send_notification(
        event_type='enrollment_received',
        recipient_email=enrollment.email,
        context={
            'first_name': enrollment.first_name,
            'last_name': enrollment.last_name,
            'email': enrollment.email,
            'cohort_name': cohort.name,
            'enrollment_code': enrollment.enrollment_code,
        },
        recipient_name=f'{enrollment.first_name} {enrollment.last_name}',
        related_model='enrollment',
        related_id=enrollment.pk,
        from_type='inscription',
    )


def notify_enrollment_confirmed(enrollment, user=None):
    """
    Envoie un email de confirmation après validation admin.
    Appelé depuis cms/views.py enrollment_confirm.
    """
    cohort = enrollment.cohort
    start_date = ''
    if cohort.start_date:
        start_date = cohort.start_date.strftime('%d/%m/%Y')

    return send_notification(
        event_type='enrollment_confirmed',
        recipient_email=enrollment.email,
        context={
            'first_name': enrollment.first_name,
            'last_name': enrollment.last_name,
            'email': enrollment.email,
            'cohort_name': cohort.name,
            'enrollment_code': enrollment.enrollment_code,
            'start_date': start_date,
        },
        recipient_name=f'{enrollment.first_name} {enrollment.last_name}',
        related_model='enrollment',
        related_id=enrollment.pk,
        sent_by=user,
        from_type='inscription',
    )


def notify_enrollment_rejected(enrollment, user=None):
    """
    Envoie un email après rejet de l'inscription.
    Appelé depuis cms/views.py enrollment_reject.
    """
    cohort = enrollment.cohort
    return send_notification(
        event_type='enrollment_rejected',
        recipient_email=enrollment.email,
        context={
            'first_name': enrollment.first_name,
            'last_name': enrollment.last_name,
            'email': enrollment.email,
            'cohort_name': cohort.name,
            'rejection_reason': enrollment.rejection_reason,
        },
        recipient_name=f'{enrollment.first_name} {enrollment.last_name}',
        related_model='enrollment',
        related_id=enrollment.pk,
        sent_by=user,
        from_type='inscription',
    )


def notify_enrollment_refunded(enrollment, user=None):
    """
    Envoie un email après remboursement.
    Appelé depuis cms/views.py enrollment_refund.
    """
    cohort = enrollment.cohort
    return send_notification(
        event_type='enrollment_refunded',
        recipient_email=enrollment.email,
        context={
            'first_name': enrollment.first_name,
            'last_name': enrollment.last_name,
            'email': enrollment.email,
            'cohort_name': cohort.name,
        },
        recipient_name=f'{enrollment.first_name} {enrollment.last_name}',
        related_model='enrollment',
        related_id=enrollment.pk,
        sent_by=user,
        from_type='inscription',
    )
