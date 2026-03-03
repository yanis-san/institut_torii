"""
Modèle d'inscription en ligne avec validation de paiement CCP.

Workflow:
1. L'étudiant remplit le formulaire (sans compte) et upload un reçu CCP.
2. Il passe en statut 'pending'.
3. L'admin valide le paiement depuis l'interface d'admin Django.
4. Un code unique est généré et affiché à l'étudiant.
5. Ce code permet de consulter une page de suivi en temps réel
   (nombre d'inscrits confirmés dans le groupe).
"""
import uuid
import re

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import RegexValidator

from courses.models import Cohort


def generate_enrollment_code():
    """Génère un code d'inscription court et unique (8 caractères hex majuscules)."""
    return uuid.uuid4().hex[:8].upper()


LATIN_ONLY = RegexValidator(
    regex=r'^[a-zA-ZÀ-ÿœŒæÆçÇ\s\-\']+$',
    message=_('Seuls les caractères latins, espaces, tirets et apostrophes sont autorisés.'),
)


class Enrollment(models.Model):
    """
    Inscription d'un étudiant à une cohorte.
    Pas de compte utilisateur requis — accès via code unique.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente de validation')
        CONFIRMED = 'confirmed', _('Confirmé')
        REJECTED = 'rejected', _('Rejeté')
        REFUNDED = 'refunded', _('Remboursé')

    # --- Identité ---
    first_name = models.CharField(
        _('prénom'), max_length=100, validators=[LATIN_ONLY],
    )
    last_name = models.CharField(
        _('nom'), max_length=100, validators=[LATIN_ONLY],
    )
    email = models.EmailField(_('email'))
    phone = models.CharField(_('téléphone'), max_length=30, blank=True)

    # --- Inscription ---
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name=_('cohorte'),
    )

    # --- Paiement ---
    payment_receipt = models.FileField(
        _('reçu de paiement CCP'),
        upload_to='receipts/%Y/%m/',
        help_text=_('Photo ou scan du reçu CCP (JPG, PNG, PDF)'),
    )

    # --- Statut ---
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # --- Code unique d'accès ---
    enrollment_code = models.CharField(
        _("code d'inscription"),
        max_length=8,
        unique=True,
        default=generate_enrollment_code,
        editable=False,
        help_text=_("Code unique envoyé à l'étudiant après confirmation."),
    )

    # --- Validation admin ---
    confirmed_at = models.DateTimeField(
        _('date de confirmation'),
        null=True,
        blank=True,
    )
    confirmed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_enrollments',
        verbose_name=_('confirmé par'),
    )
    rejection_reason = models.TextField(
        _('motif de rejet'),
        blank=True,
    )

    # --- Notes admin ---
    admin_notes = models.TextField(_('notes internes'), blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        verbose_name = _('inscription')
        verbose_name_plural = _('inscriptions')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} — {self.cohort} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        # Standardize names
        if self.last_name:
            self.last_name = self.last_name.strip().upper()
        if self.first_name:
            self.first_name = self.first_name.strip().title()

        # Standardize phone
        if self.phone:
            phone = re.sub(r'[\s\-\.\(\)]+', '', self.phone.strip())
            phone = re.sub(r'^(\+\d{2,3})0+', r'\1', phone)
            self.phone = phone

        # Compress payment receipt → WebP (no resize, preserve full resolution)
        # Skip compression for PDFs
        if self.payment_receipt and hasattr(self.payment_receipt, 'file'):
            if not self.payment_receipt.name.lower().endswith('.pdf'):
                self._compress_receipt()

        super().save(*args, **kwargs)

    def _compress_receipt(self):
        """Convert receipt to WebP without resizing — keeps full resolution."""
        from io import BytesIO
        from PIL import Image as PILImage
        from django.core.files.base import ContentFile

        try:
            img = PILImage.open(self.payment_receipt)
        except Exception:
            return

        if img.mode in ('RGBA', 'P', 'LA'):
            bg = PILImage.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        buf = BytesIO()
        img.save(buf, format='WEBP', quality=85)
        buf.seek(0)

        name = self.payment_receipt.name.rsplit('.', 1)[0] + '.webp'
        self.payment_receipt.save(name, ContentFile(buf.read()), save=False)

    def confirm(self, user=None):
        """Valide l'inscription (appelé par l'admin)."""
        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()
        self.confirmed_by = user
        self.save(update_fields=['status', 'confirmed_at', 'confirmed_by', 'updated_at'])

    def reject(self, reason='', user=None):
        """Rejette l'inscription."""
        self.status = self.Status.REJECTED
        self.rejection_reason = reason
        self.save(update_fields=['status', 'rejection_reason', 'updated_at'])
