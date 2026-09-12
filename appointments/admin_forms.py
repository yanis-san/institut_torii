from django import forms
from django.utils.translation import gettext_lazy as _
from .models import AppointmentCategory

class GenerateTimeSlotsForm(forms.Form):
    # Map weekdays (0=Monday to 6=Sunday for Python's datetime.weekday())
    DAYS_OF_WEEK = (
        (0, _('Lundi')),
        (1, _('Mardi')),
        (2, _('Mercredi')),
        (3, _('Jeudi')),
        (4, _('Vendredi')),
        (5, _('Samedi')),
        (6, _('Dimanche')),
    )

    category = forms.ModelChoiceField(
        queryset=AppointmentCategory.objects.filter(is_active=True),
        label=_("Catégorie"),
        empty_label=None
    )
    start_date = forms.DateField(
        label=_("Date de début"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'vDateField'})
    )
    end_date = forms.DateField(
        label=_("Date de fin"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'vDateField'})
    )
    days_of_week = forms.MultipleChoiceField(
        choices=DAYS_OF_WEEK,
        label=_("Jours de la semaine"),
        widget=forms.CheckboxSelectMultiple
    )
    start_time = forms.TimeField(
        label=_("Heure de début (ex: 09:00)"),
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'vTimeField'})
    )
    end_time = forms.TimeField(
        label=_("Heure de fin (ex: 16:00)"),
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'vTimeField'})
    )
    interval_minutes = forms.IntegerField(
        label=_("Intervalle (minutes)"),
        initial=30,
        min_value=5
    )
    break_start_time = forms.TimeField(
        label=_("Début de la pause (optionnel)"),
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'vTimeField'})
    )
    break_end_time = forms.TimeField(
        label=_("Fin de la pause (optionnel)"),
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'vTimeField'})
    )
    max_bookings = forms.IntegerField(
        label=_("Places par créneau"),
        initial=1,
        min_value=1
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        break_start = cleaned_data.get('break_start_time')
        break_end = cleaned_data.get('break_end_time')

        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', _("La date de fin doit être après la date de début."))

        if start_time and end_time and start_time >= end_time:
            self.add_error('end_time', _("L'heure de fin doit être après l'heure de début."))

        if break_start or break_end:
            if not (break_start and break_end):
                self.add_error('break_start_time', _("Veuillez renseigner les deux heures pour la pause."))
            elif break_start >= break_end:
                self.add_error('break_end_time', _("La fin de la pause doit être après son début."))
            elif break_start <= start_time or break_end >= end_time:
                self.add_error('break_start_time', _("La pause doit être comprise dans la plage horaire."))

        return cleaned_data
