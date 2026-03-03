from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
import re

from courses.models import Cohort
from .models import Enrollment


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
    ('+81', '🇯🇵 Japon (+81)'),
    ('+86', '🇨🇳 Chine (+86)'),
    ('+82', '🇰🇷 Corée du Sud (+82)'),
]

LATIN_ONLY = RegexValidator(
    regex=r'^[a-zA-ZÀ-ÿœŒæÆçÇ\s\-\']+$',
    message=_('Seuls les caractères latins, espaces, tirets et apostrophes sont autorisés.'),
)

INPUT_CLASS = (
    'w-full px-4 py-3 rounded-xl border border-gray-200 '
    'focus:ring-2 focus:ring-red-400 focus:border-red-400 '
    'transition-all duration-200'
)


class EnrollmentForm(forms.ModelForm):
    """Formulaire d'inscription en ligne avec upload reçu CCP."""

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

    class Meta:
        model = Enrollment
        fields = [
            'last_name', 'first_name', 'email', 'phone',
            'payment_receipt',
        ]
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
            'payment_receipt': forms.ClearableFileInput(attrs={
                'class': 'hidden',
                'accept': 'image/jpeg,image/png,image/webp,application/pdf',
            }),
        }

    def __init__(self, *args, cohort=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cohort = cohort

        # Add Latin-only validator to name fields
        self.fields['first_name'].validators.append(LATIN_ONLY)
        self.fields['last_name'].validators.append(LATIN_ONLY)

    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '').strip()
        if not value:
            raise forms.ValidationError(_('Le prénom est obligatoire.'))
        if not re.match(r'^[a-zA-ZÀ-ÿœŒæÆçÇ\s\-\']+$', value):
            raise forms.ValidationError(_('Seuls les caractères latins sont autorisés.'))
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get('last_name', '').strip()
        if not value:
            raise forms.ValidationError(_('Le nom est obligatoire.'))
        if not re.match(r'^[a-zA-ZÀ-ÿœŒæÆçÇ\s\-\']+$', value):
            raise forms.ValidationError(_('Seuls les caractères latins sont autorisés.'))
        return value

    def clean_email(self):
        value = self.cleaned_data.get('email', '').strip().lower()
        if not value:
            raise forms.ValidationError(_("L'email est obligatoire."))
        if not re.match(r'^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$', value):
            raise forms.ValidationError(_("Format d'email invalide."))
        return value

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            return ''
        digits = re.sub(r'\D', '', phone)
        if digits and len(digits) < 6:
            raise forms.ValidationError(_('Le numéro de téléphone est trop court.'))
        if len(digits) > 15:
            raise forms.ValidationError(_('Le numéro de téléphone est trop long.'))
        return phone

    def clean_payment_receipt(self):
        from PIL import Image as PILImage
        f = self.cleaned_data.get('payment_receipt')
        if not f:
            raise forms.ValidationError(_('Le reçu de paiement est obligatoire.'))
        # Max 10 MB (PDFs can be larger)
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_('Le fichier est trop volumineux (max 10 Mo).'))
        # Validate file extension
        allowed_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.pdf')
        if not f.name.lower().endswith(allowed_extensions):
            raise forms.ValidationError(
                _('Format non autorisé. Formats acceptés : JPG, PNG, PDF.')
            )
        # Validate content: PDF or image
        if f.name.lower().endswith('.pdf'):
            # Check PDF magic bytes
            header = f.read(5)
            f.seek(0)
            if header != b'%PDF-':
                raise forms.ValidationError(
                    _('Le fichier PDF est invalide ou corrompu.')
                )
        else:
            # Validate actual image content with Pillow
            try:
                img = PILImage.open(f)
                img.verify()
                f.seek(0)  # Reset file pointer after verify
            except Exception:
                raise forms.ValidationError(
                    _('Le fichier uploadé n\'est pas une image valide.')
                )
        return f

    def clean(self):
        cleaned = super().clean()
        # Merge country_code + phone
        country_code = self.data.get('country_code', '+213')
        phone = cleaned.get('phone', '')
        if phone:
            digits = re.sub(r'\D', '', phone)
            digits = digits.lstrip('0')
            cleaned['phone'] = f'{country_code}{digits}'

        # Check cohort accepts registrations
        if self.cohort and not self.cohort.is_registration_open:
            raise forms.ValidationError(
                _("Les inscriptions pour cette cohorte ne sont pas ouvertes.")
            )

        # Check for duplicate enrollment (same email + same cohort + active status)
        email = cleaned.get('email', '')
        if email and self.cohort:
            from .models import Enrollment
            if Enrollment.objects.filter(
                email=email,
                cohort=self.cohort,
                status__in=['pending', 'confirmed'],
            ).exists():
                raise forms.ValidationError(
                    _("Vous êtes déjà inscrit(e) à cette formation avec cette adresse email.")
                )

        # Check capacity
        if self.cohort and self.cohort.max_capacity:
            confirmed_count = self.cohort.enrollments.filter(
                status__in=['pending', 'confirmed'],
            ).count()
            if confirmed_count >= self.cohort.max_capacity:
                raise forms.ValidationError(
                    _("Cette cohorte est complète. Plus de places disponibles.")
                )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cohort:
            instance.cohort = self.cohort
        if commit:
            instance.save()
        return instance


class EnrollmentCodeForm(forms.Form):
    """Formulaire pour consulter le statut via code d'inscription."""

    code = forms.CharField(
        max_length=8,
        min_length=8,
        label=_("Code d'inscription"),
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS + ' text-center tracking-widest font-mono text-lg uppercase',
            'placeholder': 'XXXXXXXX',
            'maxlength': '8',
            'autocomplete': 'off',
        }),
    )

    def clean_code(self):
        code = self.cleaned_data['code'].strip().upper()
        if not re.match(r'^[A-F0-9]{8}$', code):
            raise forms.ValidationError(_('Le code doit contenir 8 caractères hexadécimaux.'))
        return code
