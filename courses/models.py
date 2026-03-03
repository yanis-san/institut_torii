from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Category(models.Model):
    """Type d'offre : Cours linguistique, Atelier artistique, Atelier culinaire…"""

    class Type(models.TextChoices):
        LANGUAGE_COURSE = 'language', _('Cours linguistique')
        ARTISTIC_WORKSHOP = 'artistic', _('Atelier artistique')
        CULINARY_WORKSHOP = 'culinary', _('Atelier culinaire')

    name = models.CharField(_('nom'), max_length=120)
    slug = models.SlugField(_('slug'), unique=True, blank=True)
    type = models.CharField(
        _('type'),
        max_length=20,
        choices=Type.choices,
    )
    description = models.TextField(_('description'), blank=True)
    icon = models.CharField(
        _('icône'),
        max_length=10,
        blank=True,
        help_text=_('Emoji ou code icône Boxicons'),
    )
    order = models.PositiveSmallIntegerField(_('ordre'), default=0)

    class Meta:
        verbose_name = _('catégorie')
        verbose_name_plural = _('catégories')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or 'category'
        super().save(*args, **kwargs)


class Language(models.Model):
    """Langue enseignée : Japonais, Chinois, Coréen…"""

    name = models.CharField(_('nom'), max_length=60, unique=True)
    slug = models.SlugField(_('slug'), unique=True, blank=True)
    flag_emoji = models.CharField(_('emoji drapeau'), max_length=10, blank=True)
    flag_image_url = models.URLField(_('URL image drapeau'), blank=True)
    order = models.PositiveSmallIntegerField(_('ordre'), default=0)

    class Meta:
        verbose_name = _('langue')
        verbose_name_plural = _('langues')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or 'language'
        super().save(*args, **kwargs)


class CourseFormat(models.Model):
    """Format de cours : En ligne, Présentiel groupe, Individuel…"""

    name = models.CharField(_('nom'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True, blank=True)
    is_online = models.BooleanField(_('en ligne'), default=False)
    is_individual = models.BooleanField(_('individuel'), default=False)
    description = models.TextField(_('description'), blank=True)
    order = models.PositiveSmallIntegerField(_('ordre'), default=0)

    class Meta:
        verbose_name = _('format de cours')
        verbose_name_plural = _('formats de cours')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or 'format'
        super().save(*args, **kwargs)


class Cohort(models.Model):
    """
    Un groupe/session spécifique avec planning, prix et dates.
    Modèle central du catalogue.
    """

    class DurationUnit(models.TextChoices):
        WEEKS = 'weeks', _('Semaines')
        MONTHS = 'months', _('Mois')

    # --- Relations ---
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='cohorts',
        verbose_name=_('catégorie'),
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cohorts',
        verbose_name=_('langue'),
        help_text=_('Uniquement pour les cours linguistiques'),
    )
    format = models.ForeignKey(
        CourseFormat,
        on_delete=models.CASCADE,
        related_name='cohorts',
        verbose_name=_('format'),
    )

    # --- Infos générales ---
    name = models.CharField(_('nom'), max_length=200)
    slug = models.SlugField(_('slug'), unique=True, blank=True)
    description = models.TextField(_('description'), blank=True)
    image = models.ImageField(
        _('image'),
        upload_to='cohorts/',
        blank=True,
    )

    # --- Prix ---
    price = models.DecimalField(
        _('prix (DA)'),
        max_digits=10,
        decimal_places=0,
    )
    registration_fee = models.DecimalField(
        _("frais d'inscription (DA)"),
        max_digits=10,
        decimal_places=0,
        default=1000,
        help_text=_('Frais annuels obligatoires'),
    )

    # --- Durée ---
    duration_value = models.PositiveSmallIntegerField(_('durée'))
    duration_unit = models.CharField(
        _('unité de durée'),
        max_length=10,
        choices=DurationUnit.choices,
        default=DurationUnit.MONTHS,
    )
    hours_per_session = models.DecimalField(
        _('heures par séance'),
        max_digits=4,
        decimal_places=1,
        default=2.0,
    )
    sessions_per_week = models.PositiveSmallIntegerField(
        _('séances par semaine'),
        default=1,
    )

    # --- Dates ---
    start_date = models.DateField(_('date de début'), null=True, blank=True)
    end_date = models.DateField(_('date de fin'), null=True, blank=True)

    # --- Capacité ---
    max_capacity = models.PositiveSmallIntegerField(
        _('capacité max'),
        null=True,
        blank=True,
    )

    # --- Horaires Ramadan (optionnel) ---
    ramadan_schedule_note = models.TextField(
        _('horaires Ramadan'),
        blank=True,
        help_text=_('Note affichée pendant le Ramadan'),
    )

    # --- Publication ---
    is_active = models.BooleanField(_('actif'), default=True)
    is_featured = models.BooleanField(
        _('mis en avant'),
        default=False,
        help_text=_("Affiché sur la page d'accueil"),
    )
    order = models.PositiveSmallIntegerField(_('ordre'), default=0)

    # --- Inscription en ligne ---
    registration_open_date = models.DateTimeField(
        _('ouverture des inscriptions'),
        null=True,
        blank=True,
        help_text=_("Laisser vide si inscriptions non ouvertes en ligne"),
    )
    registration_close_date = models.DateTimeField(
        _('fermeture des inscriptions'),
        null=True,
        blank=True,
    )
    min_students = models.PositiveSmallIntegerField(
        _("nombre minimum d'étudiants"),
        default=0,
        help_text=_("Si le minimum n'est pas atteint, les étudiants seront remboursés."),
    )
    payment_instructions = models.TextField(
        _('instructions de paiement'),
        blank=True,
        help_text=_("Numéro CCP, RIP, détails du virement... affiché sur le formulaire"),
    )

    class Meta:
        verbose_name = _('cohorte')
        verbose_name_plural = _('cohortes')
        ordering = ['order', 'start_date', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or 'cohort'
        super().save(*args, **kwargs)

    @property
    def duration_display(self):
        """Ex: '3 mois' ou '8 semaines'."""
        label = _('mois') if self.duration_unit == self.DurationUnit.MONTHS else _('semaines')
        return f'{self.duration_value} {label}'

    @property
    def is_registration_open(self):
        """True si les inscriptions en ligne sont actuellement ouvertes."""
        if not self.registration_open_date or not self.registration_close_date:
            return False
        now = timezone.now()
        return self.registration_open_date <= now <= self.registration_close_date


class CohortSchedule(models.Model):
    """
    Horaire d'une séance pour un jour donné.
    Permet la flexibilité : Dim 14h-16h, Mar 18h-20h, etc.
    """

    class DayOfWeek(models.IntegerChoices):
        SUNDAY = 0, _('Dimanche')
        MONDAY = 1, _('Lundi')
        TUESDAY = 2, _('Mardi')
        WEDNESDAY = 3, _('Mercredi')
        THURSDAY = 4, _('Jeudi')
        FRIDAY = 5, _('Vendredi')
        SATURDAY = 6, _('Samedi')

    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name=_('cohorte'),
    )
    day = models.IntegerField(_('jour'), choices=DayOfWeek.choices)
    start_time = models.TimeField(_('heure de début'))
    end_time = models.TimeField(_('heure de fin'))

    class Meta:
        verbose_name = _('horaire')
        verbose_name_plural = _('horaires')
        ordering = ['day', 'start_time']
        unique_together = ['cohort', 'day', 'start_time']

    def __str__(self):
        return f'{self.get_day_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}'
