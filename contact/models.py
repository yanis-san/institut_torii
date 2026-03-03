from django.db import models
from django.utils.translation import gettext_lazy as _
import re

from courses.models import Category, Language, Cohort


class Prospect(models.Model):
    """
    Prospect capturé via le formulaire de contact.
    On veut un maximum de données exploitables.
    """

    class Level(models.TextChoices):
        BEGINNER = 'beginner', _('Débutant')
        FALSE_BEGINNER = 'false_beginner', _('Faux-débutant')
        INTERMEDIATE = 'intermediate', _('Intermédiaire')
        ADVANCED = 'advanced', _('Avancé')
        EXPERT = 'expert', _('Expert')

    class Source(models.TextChoices):
        WEBSITE = 'website', _('Site web')
        PHONE = 'phone', _('Téléphone')
        RECOMMENDATION = 'recommendation', _('Recommendation')
        SOCIAL_MEDIA = 'social_media', _('Réseaux sociaux')
        EVENT = 'event', _('Événement')
        OTHER = 'other', _('Autre')

    class Rating(models.TextChoices):
        HOT = 'hot', _('Sérieux')
        WARM = 'warm', _('Intéressé')
        COLD = 'cold', _('Froid')
        UNQUALIFIED = 'unqualified', _('Non qualifié')

    # Color mapping for template rendering
    RATING_COLORS = {
        'hot': 'emerald',
        'warm': 'amber',
        'cold': 'blue',
        'unqualified': 'red',
    }

    # --- Identité ---
    first_name = models.CharField(_('prénom'), max_length=100)
    last_name = models.CharField(_('nom'), max_length=100)
    email = models.EmailField(_('email'))
    phone = models.CharField(_('téléphone'), max_length=30, blank=True)

    # --- Profil ---
    birth_date = models.DateField(_('date de naissance'), null=True, blank=True)
    level = models.CharField(
        _('niveau estimé'),
        max_length=20,
        choices=Level.choices,
        blank=True,
    )

    # --- Intérêts ---
    interested_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prospects',
        verbose_name=_("catégorie d'intérêt"),
    )
    interested_language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prospects',
        verbose_name=_("langue d'intérêt"),
    )
    interested_cohort = models.ForeignKey(
        Cohort,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prospects',
        verbose_name=_('cohorte spécifique'),
    )
    other_interests = models.ManyToManyField(
        Cohort,
        blank=True,
        related_name='interested_prospects',
        verbose_name=_("autres cohortes d'intérêt"),
    )

    # --- Message & préférences ---
    message = models.TextField(_('message'), blank=True)
    contact_preferences = models.JSONField(
        _('préférences de contact'),
        default=list,
        blank=True,
        help_text=_('Liste : email, phone, whatsapp, sms'),
    )

    # --- Méta ---
    source = models.CharField(
        _('source'),
        max_length=20,
        choices=Source.choices,
        default=Source.WEBSITE,
    )
    rating = models.CharField(
        _('note qualité'),
        max_length=20,
        choices=Rating.choices,
        blank=True,
        default='',
        help_text=_('Évaluation qualitative du prospect pour le ciblage marketing.'),
    )
    notes = models.TextField(_('notes internes'), blank=True)
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    converted = models.BooleanField(_('converti'), default=False)
    converted_date = models.DateTimeField(_('date conversion'), null=True, blank=True)

    class Meta:
        verbose_name = _('prospect')
        verbose_name_plural = _('prospects')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.email})'

    @property
    def rating_color(self):
        """Return Tailwind color name for the rating badge."""
        return self.RATING_COLORS.get(self.rating, 'zinc')

    def save(self, *args, **kwargs):
        # Standardize names: NOM → MAJUSCULE, Prénom → Title Case
        if self.last_name:
            self.last_name = self.last_name.strip().upper()
        if self.first_name:
            self.first_name = self.first_name.strip().title()

        # Standardize phone: remove spaces/dashes, remove leading 0 after prefix
        if self.phone:
            phone = re.sub(r'[\s\-\.\(\)]+', '', self.phone.strip())
            # If starts with + and has leading 0 after country code
            # e.g. +2130666... → +213666...
            phone = re.sub(r'^(\+\d{2,3})0+', r'\1', phone)
            self.phone = phone

        super().save(*args, **kwargs)
