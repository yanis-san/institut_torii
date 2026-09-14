from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
import re

from courses.models import Category, Language, Cohort
from .models import Prospect

from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3


CONTACT_PREFERENCE_CHOICES = [
    ('email', _('Email')),
    ('phone', _('Téléphone')),
    ('whatsapp', _('WhatsApp')),
    ('sms', _('SMS')),
]

COUNTRY_CODES = [
    ('+213', '🇩🇿 Algérie (+213)'),
    ('+33', '🇫🇷 France (+33)'),
    ('+212', '🇲🇦 Maroc (+212)'),
    ('+216', '🇹🇳 Tunisie (+216)'),
    ('+1', '🇺🇸 USA/Canada (+1)'),
    ('+44', '🇬🇧 UK (+44)'),
    ('+49', '🇩🇪 Allemagne (+49)'),
    ('+34', '🇪🇸 Espagne (+34)'),
    ('+39', '🇮🇹 Italie (+39)'),
    ('+90', '🇹🇷 Turquie (+90)'),
    ('+966', '🇸🇦 Arabie Saoudite (+966)'),
    ('+971', '🇦🇪 EAU (+971)'),
    ('+81', '🇯🇵 Japon (+81)'),
    ('+86', '🇨🇳 Chine (+86)'),
    ('+82', '🇰🇷 Corée du Sud (+82)'),
]

LATIN_ONLY = RegexValidator(
    regex=r'^[a-zA-ZÀ-ÿœŒæÆçÇ\s\-\']+$',
    message=_('Seuls les caractères latins, espaces, tirets et apostrophes sont autorisés.'),
)


class ProspectForm(forms.ModelForm):
    """
    Formulaire de contact prospect — collecte un maximum de données.
    Champs dynamiques : la langue et la cohorte dépendent de la catégorie choisie.
    """

    contact_preferences = forms.MultipleChoiceField(
        choices=CONTACT_PREFERENCE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Comment préférez-vous être contacté ?'),
    )

    country_code = forms.ChoiceField(
        choices=COUNTRY_CODES,
        initial='+213',
        required=False,
        label=_('Indicatif'),
        widget=forms.Select(attrs={
            'class': 'px-3 py-3 rounded-l-xl border border-r-0 border-gray-200 '
                     'bg-gray-50 text-sm text-gray-700 '
                     'focus:ring-2 focus:ring-red-400 focus:border-red-400 '
                     'transition-all duration-200',
        }),
    )

    captcha = ReCaptchaField(widget=ReCaptchaV3(action='contact'))

    class Meta:
        model = Prospect
        fields = [
            'last_name', 'first_name', 'email', 'phone',
            'birth_date',
            'interested_category', 'interested_language',
            'interested_cohort', 'other_interests',
            'message', 'contact_preferences',
        ]
        INPUT_CLASS = (
            'w-full px-4 py-3 rounded-xl border border-gray-200 '
            'focus:ring-2 focus:ring-red-400 focus:border-red-400 '
            'transition-all duration-200'
        )
        SELECT_CLASS = INPUT_CLASS
        widgets = {
            'last_name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': _('Votre nom de famille'),
                'x-model': 'lastName',
                '@input': 'validateLastName()',
                'autocomplete': 'family-name',
            }),
            'first_name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': _('Votre prénom'),
                'x-model': 'firstName',
                '@input': 'validateFirstName()',
                'autocomplete': 'given-name',
            }),
            'email': forms.EmailInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': _('votre@email.com'),
                'x-model': 'email',
                '@input': 'validateEmail()',
                'autocomplete': 'email',
            }),
            'phone': forms.TextInput(attrs={
                'class': INPUT_CLASS + ' rounded-l-none',
                'placeholder': _('6XX XX XX XX'),
                'x-model': 'phone',
                '@input': 'validatePhone()',
                'autocomplete': 'tel-national',
            }),
            'birth_date': forms.DateInput(attrs={
                'type': 'date',
                'class': INPUT_CLASS,
            }),
            'interested_category': forms.Select(attrs={
                'class': SELECT_CLASS,
            }),
            'interested_language': forms.Select(attrs={
                'class': SELECT_CLASS,
            }),
            'interested_cohort': forms.Select(attrs={
                'class': SELECT_CLASS,
            }),
            'other_interests': forms.CheckboxSelectMultiple,
            'message': forms.Textarea(attrs={
                'rows': 4,
                'class': INPUT_CLASS,
                'placeholder': _('Votre message (optionnel)'),
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Latin-only validator to name fields
        self.fields['first_name'].validators.append(LATIN_ONLY)
        self.fields['last_name'].validators.append(LATIN_ONLY)

        # Only active cohorts in dropdowns
        self.fields['interested_cohort'].queryset = Cohort.objects.filter(
            is_active=True,
        ).select_related('category', 'language', 'format')
        self.fields['other_interests'].queryset = Cohort.objects.filter(
            is_active=True,
        ).select_related('category', 'language', 'format')

        # Blank labels
        self.fields['interested_category'].empty_label = _("-- Choisissez un type d'activité --")
        self.fields['interested_language'].empty_label = _('-- Choisissez une langue --')
        self.fields['interested_cohort'].empty_label = _('-- Choisissez une formation --')


    # ------------------------------------------------------------------
    # Server-side validation
    # ------------------------------------------------------------------

    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '').strip()
        if not value:
            raise forms.ValidationError(_('Le prénom est obligatoire.'))
        if not re.match(r'^[a-zA-ZÀ-ÿœŒæÆçÇ\s\-\']+$', value):
            raise forms.ValidationError(
                _('Seuls les caractères latins sont autorisés.')
            )
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get('last_name', '').strip()
        if not value:
            raise forms.ValidationError(_('Le nom est obligatoire.'))
        if not re.match(r'^[a-zA-ZÀ-ÿœŒæÆçÇ\s\-\']+$', value):
            raise forms.ValidationError(
                _('Seuls les caractères latins sont autorisés.')
            )
        return value

    def clean_email(self):
        value = self.cleaned_data.get('email', '').strip().lower()
        if not value:
            raise forms.ValidationError(_("L'email est obligatoire."))
        if not re.match(r'^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$', value):
            raise forms.ValidationError(_("Format d'email invalide."))
        return value

    def clean_phone(self):
        """Combine country_code + phone into a single international number."""
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            return ''
        # Remove any non-digit chars
        digits = re.sub(r'\D', '', phone)
        if not digits:
            return ''
        if len(digits) < 6:
            raise forms.ValidationError(
                _('Le numéro de téléphone est trop court.')
            )
        if len(digits) > 15:
            raise forms.ValidationError(
                _('Le numéro de téléphone est trop long.')
            )
        return phone

    def clean(self):
        cleaned = super().clean()
        # Merge country_code + phone
        country_code = self.data.get('country_code', '+213')
        phone = cleaned.get('phone', '')
        if phone:
            digits = re.sub(r'\D', '', phone)
            # Remove leading 0 for proper prefix
            digits = digits.lstrip('0')
            cleaned['phone'] = f'{country_code}{digits}'
        return cleaned
