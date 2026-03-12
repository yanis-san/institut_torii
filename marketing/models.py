"""
Email Marketing Models — Institut Torii.

EmailTemplate: Reusable email templates with Django template variable support.
EmailCampaign: A specific email campaign targeting a segment of contacts.
CampaignRecipient: Tracks individual email delivery for each recipient.
EmailSubscription: Manages per-email unsubscribe preferences.
"""
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


# ──────────────────────────────────────────────
# EmailTemplate
# ──────────────────────────────────────────────

class EmailTemplate(models.Model):
    """Reusable email template with Django template syntax variables."""

    class Category(models.TextChoices):
        WELCOME = 'welcome', _('Bienvenue')
        NEWSLETTER = 'newsletter', _('Newsletter')
        NOTIFICATION = 'notification', _('Notification')
        PROMOTIONAL = 'promotional', _('Promotionnel')
        TRANSACTIONAL = 'transactional', _('Transactionnel')

    name = models.CharField(_('nom interne'), max_length=200)
    category = models.CharField(
        _('catégorie'), max_length=20,
        choices=Category.choices, default=Category.NEWSLETTER,
    )
    subject = models.CharField(
        _('objet par défaut'), max_length=200,
        help_text=_('Supporte les variables : {{ first_name }}, {{ last_name }}'),
    )
    body_html = models.TextField(
        _('contenu HTML'),
        help_text=_(
            'Corps du mail. Variables disponibles : '
            '{{ first_name }}, {{ last_name }}, {{ email }}, '
            '{{ unsubscribe_url }}, {{ site_name }}'
        ),
    )
    body_text = models.TextField(
        _('contenu texte brut'), blank=True,
        help_text=_('Version texte brut (auto-généré depuis le HTML si vide).'),
    )

    is_active = models.BooleanField(_('actif'), default=True)
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        verbose_name = _('template email')
        verbose_name_plural = _('templates email')
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.name} ({self.get_category_display()})'


# ──────────────────────────────────────────────
# EmailCampaign
# ──────────────────────────────────────────────

class EmailCampaign(models.Model):
    """Email campaign targeting a segment of prospects/enrolled students."""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        SCHEDULED = 'scheduled', _('Programmée')
        SENDING = 'sending', _("En cours d'envoi")
        SENT = 'sent', _('Envoyée')
        CANCELLED = 'cancelled', _('Annulée')

    class FromEmail(models.TextChoices):
        CONTACT = 'contact', _('contact@ — Marketing & prospects')
        INSCRIPTION = 'inscription', _('inscription@ — Transactionnel')
        NOTIFICATION = 'notification', _('notification@ — Alertes système')

    class SegmentType(models.TextChoices):
        ALL_PROSPECTS = 'all_prospects', _('Tous les prospects')
        ALL_ENROLLED = 'all_enrolled', _('Tous les inscrits')
        ALL_CONFIRMED = 'all_confirmed', _('Inscrits confirmés uniquement')
        PROSPECTS_BY_LANGUAGE = 'prospects_lang', _('Prospects par langue')
        PROSPECTS_BY_RATING = 'prospects_rating', _('Prospects par note qualité')
        ENROLLED_BY_COHORT = 'enrolled_cohort', _('Inscrits par cohorte')
        ENROLLED_BY_LANGUAGE = 'enrolled_lang', _('Inscrits par langue')
        CUSTOM = 'custom', _('Liste personnalisée')

    # --- Identification ---
    name = models.CharField(_('nom de la campagne'), max_length=200)
    template = models.ForeignKey(
        EmailTemplate, on_delete=models.PROTECT,
        related_name='campaigns', verbose_name=_('template'),
    )
    subject = models.CharField(
        _('objet'), max_length=200, blank=True,
        help_text=_("Laissez vide pour utiliser l'objet du template."),
    )

    # --- Sender ---
    from_email_type = models.CharField(
        _('adresse expéditeur'), max_length=20,
        choices=FromEmail.choices, default=FromEmail.CONTACT,
    )
    reply_to = models.EmailField(
        _('répondre à'), blank=True,
        help_text=_("Laissez vide pour utiliser l'adresse expéditeur."),
    )

    # --- Targeting ---
    segment_type = models.CharField(
        _('segment'), max_length=20,
        choices=SegmentType.choices, default=SegmentType.ALL_PROSPECTS,
    )
    segment_filter = models.JSONField(
        _('filtre du segment'), default=dict, blank=True,
        help_text=_(
            'Filtres additionnels : {"language_id": 1} ou {"cohort_id": 2}'
        ),
    )

    # --- Status & scheduling ---
    status = models.CharField(
        _('statut'), max_length=20,
        choices=Status.choices, default=Status.DRAFT,
    )
    scheduled_at = models.DateTimeField(
        _('programmée pour'), null=True, blank=True,
    )
    started_at = models.DateTimeField(
        _("début d'envoi"), null=True, blank=True,
    )
    completed_at = models.DateTimeField(
        _("fin d'envoi"), null=True, blank=True,
    )

    # --- Counters (updated during send) ---
    total_recipients = models.PositiveIntegerField(
        _('total destinataires'), default=0,
    )
    sent_count = models.PositiveIntegerField(_('envoyés'), default=0)
    failed_count = models.PositiveIntegerField(_('échoués'), default=0)
    opened_count = models.PositiveIntegerField(_('ouverts'), default=0)
    clicked_count = models.PositiveIntegerField(_('cliqués'), default=0)

    # --- Timestamps ---
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        verbose_name = _('campagne email')
        verbose_name_plural = _('campagnes email')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} [{self.get_status_display()}]'

    @property
    def effective_subject(self):
        """Campaign subject if set, otherwise template's default subject."""
        return self.subject or self.template.subject

    @property
    def open_rate(self):
        if self.sent_count == 0:
            return 0
        return round(self.opened_count / self.sent_count * 100, 1)

    @property
    def click_rate(self):
        if self.sent_count == 0:
            return 0
        return round(self.clicked_count / self.sent_count * 100, 1)

    @property
    def delivery_rate(self):
        if self.total_recipients == 0:
            return 0
        return round(self.sent_count / self.total_recipients * 100, 1)


# ──────────────────────────────────────────────
# CampaignRecipient
# ──────────────────────────────────────────────

class CampaignRecipient(models.Model):
    """Tracks individual email delivery for each recipient in a campaign."""

    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente')
        SENT = 'sent', _('Envoyé')
        FAILED = 'failed', _('Échoué')
        BOUNCED = 'bounced', _('Rejeté')

    campaign = models.ForeignKey(
        EmailCampaign, on_delete=models.CASCADE,
        related_name='recipients', verbose_name=_('campagne'),
    )
    email = models.EmailField(_('email'))
    first_name = models.CharField(_('prénom'), max_length=100, blank=True)
    last_name = models.CharField(_('nom'), max_length=100, blank=True)

    # --- Source tracking ---
    source_type = models.CharField(
        _('source'), max_length=20, blank=True,
        help_text=_("'prospect' ou 'enrollment'"),
    )
    source_id = models.PositiveIntegerField(
        _('ID source'), null=True, blank=True,
    )

    # --- Delivery status ---
    status = models.CharField(
        _('statut'), max_length=10,
        choices=Status.choices, default=Status.PENDING,
    )
    sent_at = models.DateTimeField(_('envoyé le'), null=True, blank=True)
    opened_at = models.DateTimeField(_('ouvert le'), null=True, blank=True)
    clicked_at = models.DateTimeField(_('cliqué le'), null=True, blank=True)

    # --- Tracking tokens ---
    open_token = models.UUIDField(
        _("token d'ouverture"), default=uuid.uuid4, unique=True,
    )
    click_token = models.UUIDField(
        _('token de clic'), default=uuid.uuid4, unique=True,
    )

    # --- Error info ---
    error_message = models.TextField(_('message erreur'), blank=True)

    class Meta:
        verbose_name = _('destinataire')
        verbose_name_plural = _('destinataires')
        ordering = ['email']
        unique_together = [('campaign', 'email')]

    def __str__(self):
        return f'{self.email} — {self.get_status_display()}'


# ──────────────────────────────────────────────
# EmailSubscription
# ──────────────────────────────────────────────

class EmailSubscription(models.Model):
    """Manages email subscription/unsubscription per email address."""

    email = models.EmailField(_('email'), unique=True, db_index=True)
    is_subscribed = models.BooleanField(_('abonné'), default=True)
    unsubscribe_token = models.UUIDField(
        _('token désinscription'), default=uuid.uuid4, unique=True,
    )
    unsubscribed_at = models.DateTimeField(
        _('désinscrit le'), null=True, blank=True,
    )
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)

    class Meta:
        verbose_name = _('abonnement email')
        verbose_name_plural = _('abonnements email')

    def __str__(self):
        icon = '✅' if self.is_subscribed else '❌'
        return f'{icon} {self.email}'

    @classmethod
    def is_email_subscribed(cls, email):
        """Check if email is subscribed. No record = subscribed by default."""
        try:
            sub = cls.objects.get(email=email.lower())
            return sub.is_subscribed
        except cls.DoesNotExist:
            return True

    @classmethod
    def get_or_create_subscription(cls, email):
        """Get or create subscription record for an email."""
        sub, _ = cls.objects.get_or_create(
            email=email.lower(),
            defaults={'is_subscribed': True},
        )
        return sub


# ──────────────────────────────────────────────
# NotificationTemplate — editable transactional email templates
# ──────────────────────────────────────────────

class NotificationTemplate(models.Model):
    """
    Editable transactional email templates.
    One per event_type. Falls back to code defaults if not in DB.
    Editable from the CMS so admins can customise wording without code changes.
    """

    class EventType(models.TextChoices):
        CONTACT_RECEIVED = 'contact_received', _('Contact — Accusé de réception')
        ENROLLMENT_RECEIVED = 'enrollment_received', _('Inscription — Accusé de réception')
        ENROLLMENT_CONFIRMED = 'enrollment_confirmed', _('Inscription — Confirmée')
        ENROLLMENT_REJECTED = 'enrollment_rejected', _('Inscription — Rejetée')
        ENROLLMENT_REFUNDED = 'enrollment_refunded', _('Inscription — Remboursée')
        APPOINTMENT_BOOKED = 'appointment_booked', _('Rendez-vous — Confirmation')

    event_type = models.CharField(
        _("type d'événement"), max_length=30,
        choices=EventType.choices, unique=True,
    )
    subject = models.CharField(
        _('objet'), max_length=300,
        help_text=_(
            'Variables disponibles : {{ first_name }}, {{ last_name }}, '
            '{{ email }}, {{ site_name }}, {{ cohort_name }}, '
            '{{ enrollment_code }}, {{ start_date }}, {{ rejection_reason }}'
        ),
    )
    body_html = models.TextField(
        _('contenu HTML'),
        help_text=_(
            'Corps du mail en HTML. Mêmes variables que l\'objet. '
            'Le texte brut est auto-généré depuis le HTML.'
        ),
    )
    is_active = models.BooleanField(
        _('actif'), default=True,
        help_text=_(
            'Si désactivé, le template par défaut du code sera utilisé.'
        ),
    )
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        verbose_name = _('template de notification')
        verbose_name_plural = _('templates de notification')
        ordering = ['event_type']

    def __str__(self):
        return self.get_event_type_display()

    @classmethod
    def get_template(cls, event_type):
        """
        Return (subject, body_html) for the given event_type.
        Returns the DB version if active, else None (caller falls back to default).
        """
        try:
            tpl = cls.objects.get(event_type=event_type, is_active=True)
            return {'subject': tpl.subject, 'body_html': tpl.body_html}
        except cls.DoesNotExist:
            return None

    @classmethod
    def ensure_defaults(cls):
        """
        Create DB entries from DEFAULT_TEMPLATES for any missing event types.
        Called from the CMS list view so entries exist to edit.
        """
        from marketing.notifications import DEFAULT_TEMPLATES
        for event_type, data in DEFAULT_TEMPLATES.items():
            cls.objects.get_or_create(
                event_type=event_type,
                defaults={
                    'subject': data['subject'],
                    'body_html': data['body_html'],
                    'is_active': True,
                },
            )


# ──────────────────────────────────────────────
# NotificationLog — tracks every transactional email sent
# ──────────────────────────────────────────────

class NotificationLog(models.Model):
    """
    Historique de chaque email transactionnel envoyé automatiquement.
    Permet de voir dans le CMS tout ce qui a été envoyé, à qui, quand.
    """

    class EventType(models.TextChoices):
        CONTACT_RECEIVED = 'contact_received', _('Contact — Accusé de réception')
        ENROLLMENT_RECEIVED = 'enrollment_received', _('Inscription — Accusé de réception')
        ENROLLMENT_CONFIRMED = 'enrollment_confirmed', _('Inscription — Confirmée')
        ENROLLMENT_REJECTED = 'enrollment_rejected', _('Inscription — Rejetée')
        ENROLLMENT_REFUNDED = 'enrollment_refunded', _('Inscription — Remboursée')
        APPOINTMENT_BOOKED = 'appointment_booked', _('Rendez-vous — Confirmation')

    class Status(models.TextChoices):
        SENT = 'sent', _('Envoyé')
        FAILED = 'failed', _('Échoué')

    event_type = models.CharField(
        _("type d'événement"), max_length=30, choices=EventType.choices,
    )
    recipient_email = models.EmailField(_('destinataire'))
    recipient_name = models.CharField(_('nom du destinataire'), max_length=200, blank=True)
    subject = models.CharField(_('objet'), max_length=300)
    body_html = models.TextField(_('contenu envoyé'), blank=True)

    # Link to source object
    related_model = models.CharField(
        _('modèle source'), max_length=50, blank=True,
        help_text=_("Ex: 'prospect', 'enrollment'"),
    )
    related_id = models.PositiveIntegerField(
        _('ID source'), null=True, blank=True,
    )

    status = models.CharField(
        _('statut'), max_length=10,
        choices=Status.choices, default=Status.SENT,
    )
    error_message = models.TextField(_('erreur'), blank=True)
    sent_at = models.DateTimeField(_('envoyé le'), auto_now_add=True)
    sent_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('déclenché par'),
        help_text=_("L'admin qui a déclenché l'action (null si automatique)."),
    )

    class Meta:
        verbose_name = _('notification envoyée')
        verbose_name_plural = _('notifications envoyées')
        ordering = ['-sent_at']

    def __str__(self):
        return f'{self.get_event_type_display()} → {self.recipient_email} [{self.get_status_display()}]'
