import uuid
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class AppointmentCategory(models.Model):
    """Catégorie de rendez-vous (ex: Test de niveau, Entretien, Consultation…)."""

    name = models.CharField(_('nom'), max_length=200)
    slug = models.SlugField(_('slug'), unique=True, blank=True)
    description = models.TextField(_('description'), blank=True)
    icon = models.CharField(
        _('icône'), max_length=10, blank=True,
        help_text=_('Emoji ou code icône Boxicons'),
    )
    duration_minutes = models.PositiveSmallIntegerField(
        _('durée (minutes)'), default=30,
        help_text=_('Durée indicative du rendez-vous'),
    )
    is_active = models.BooleanField(_('actif'), default=True)
    order = models.PositiveSmallIntegerField(_('ordre'), default=0)

    class Meta:
        verbose_name = _('catégorie de rendez-vous')
        verbose_name_plural = _('catégories de rendez-vous')
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while AppointmentCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TimeSlot(models.Model):
    """Créneau horaire disponible pour la prise de rendez-vous."""

    category = models.ForeignKey(
        AppointmentCategory,
        on_delete=models.CASCADE,
        related_name='timeslots',
        verbose_name=_('catégorie'),
    )
    date = models.DateField(_('date'))
    start_time = models.TimeField(_('heure de début'))
    end_time = models.TimeField(_('heure de fin'))
    max_bookings = models.PositiveSmallIntegerField(
        _('places disponibles'), default=1,
        help_text=_('Nombre de personnes pouvant réserver ce créneau'),
    )
    is_active = models.BooleanField(_('actif'), default=True)

    class Meta:
        verbose_name = _('créneau horaire')
        verbose_name_plural = _('créneaux horaires')
        ordering = ['date', 'start_time']
        unique_together = [('category', 'date', 'start_time')]

    def __str__(self):
        return f'{self.date.strftime("%d/%m/%Y")} — {self.start_time.strftime("%H:%M")}-{self.end_time.strftime("%H:%M")}'

    @property
    def bookings_count(self):
        return self.appointments.filter(
            status__in=[Appointment.Status.CONFIRMED, Appointment.Status.PENDING],
        ).count()

    @property
    def is_available(self):
        return self.is_active and self.bookings_count < self.max_bookings

    @property
    def remaining_spots(self):
        return max(0, self.max_bookings - self.bookings_count)


def generate_appointment_code():
    return uuid.uuid4().hex[:8].upper()


class Appointment(models.Model):
    """Rendez-vous pris par un visiteur."""

    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente')
        CONFIRMED = 'confirmed', _('Confirmé')
        CANCELLED = 'cancelled', _('Annulé')
        COMPLETED = 'completed', _('Terminé')
        NO_SHOW = 'no_show', _('Absent')

    # --- Créneau ---
    timeslot = models.ForeignKey(
        TimeSlot,
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name=_('créneau'),
    )

    # --- Identité du visiteur ---
    first_name = models.CharField(_('prénom'), max_length=100)
    last_name = models.CharField(_('nom'), max_length=100)
    email = models.EmailField(_('email'))
    phone = models.CharField(_('téléphone'), max_length=30)

    # --- Suivi ---
    appointment_code = models.CharField(
        _('code de rendez-vous'), max_length=8,
        unique=True, default=generate_appointment_code, editable=False,
    )
    status = models.CharField(
        _('statut'), max_length=20,
        choices=Status.choices, default=Status.CONFIRMED,
    )
    notes = models.TextField(_('notes'), blank=True)
    admin_notes = models.TextField(_('notes internes'), blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        verbose_name = _('rendez-vous')
        verbose_name_plural = _('rendez-vous')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} — {self.timeslot}'

    @property
    def category(self):
        return self.timeslot.category
