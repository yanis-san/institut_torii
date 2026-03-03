"""
Marketing forms — CMS management of email templates & campaigns.
"""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import EmailTemplate, EmailCampaign, NotificationTemplate
from contact.models import Prospect
from courses.models import Language, Cohort

# Reuse CMS style constants
_INPUT = (
    'w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded-xl '
    'px-4 py-3 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none'
)
_TEXTAREA = _INPUT + ' min-h-[120px]'
_SELECT = _INPUT + ' cursor-pointer'
_CHECKBOX = (
    'w-5 h-5 rounded border-zinc-600 bg-zinc-800 text-red-500 '
    'focus:ring-red-500 cursor-pointer'
)


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ['name', 'category', 'subject', 'body_html', 'body_text', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'category': forms.Select(attrs={'class': _SELECT}),
            'subject': forms.TextInput(attrs={
                'class': _INPUT,
                'placeholder': 'Ex: Bienvenue {{ first_name }} !',
            }),
            'body_html': forms.Textarea(attrs={
                'class': _TEXTAREA + ' font-mono text-sm min-h-[300px]',
                'rows': 15,
                'placeholder': '<h1>Bonjour {{ first_name }},</h1>\n<p>Votre contenu ici...</p>',
            }),
            'body_text': forms.Textarea(attrs={
                'class': _TEXTAREA + ' font-mono text-sm',
                'rows': 8,
                'placeholder': 'Version texte (auto-générée si vide)',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': _CHECKBOX}),
        }


class EmailCampaignForm(forms.ModelForm):
    # Extra fields for segment filtering
    filter_language = forms.ModelChoiceField(
        queryset=Language.objects.all(),
        required=False,
        label=_('Filtrer par langue'),
        widget=forms.Select(attrs={'class': _SELECT}),
        empty_label=_('— Toutes les langues —'),
    )
    filter_cohort = forms.ModelChoiceField(
        queryset=Cohort.objects.filter(is_active=True),
        required=False,
        label=_('Filtrer par cohorte'),
        widget=forms.Select(attrs={'class': _SELECT}),
        empty_label=_('— Toutes les cohortes —'),
    )
    filter_rating = forms.ChoiceField(
        choices=[('', _('— Toutes les notes —'))] + list(Prospect.Rating.choices),
        required=False,
        label=_('Filtrer par note qualité'),
        widget=forms.Select(attrs={'class': _SELECT}),
    )

    class Meta:
        model = EmailCampaign
        fields = [
            'name', 'template', 'subject',
            'from_email_type', 'reply_to',
            'segment_type',
            'scheduled_at',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': _INPUT,
                'placeholder': 'Ex: Newsletter Mars 2026',
            }),
            'template': forms.Select(attrs={'class': _SELECT}),
            'subject': forms.TextInput(attrs={
                'class': _INPUT,
                'placeholder': "Laissez vide pour utiliser l'objet du template",
            }),
            'from_email_type': forms.Select(attrs={'class': _SELECT}),
            'reply_to': forms.EmailInput(attrs={
                'class': _INPUT,
                'placeholder': "Laissez vide pour utiliser l'adresse expéditeur",
            }),
            'segment_type': forms.Select(attrs={'class': _SELECT}),
            'scheduled_at': forms.DateTimeInput(attrs={
                'class': _INPUT,
                'type': 'datetime-local',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active templates
        self.fields['template'].queryset = EmailTemplate.objects.filter(is_active=True)

        # Pre-populate filter fields from segment_filter JSON
        if self.instance and self.instance.pk:
            sf = self.instance.segment_filter or {}
            if sf.get('language_id'):
                self.fields['filter_language'].initial = sf['language_id']
            if sf.get('cohort_id'):
                self.fields['filter_cohort'].initial = sf['cohort_id']
            if sf.get('rating'):
                self.fields['filter_rating'].initial = sf['rating']

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Build segment_filter from extra fields
        segment_filter = {}
        if self.cleaned_data.get('filter_language'):
            segment_filter['language_id'] = self.cleaned_data['filter_language'].pk
        if self.cleaned_data.get('filter_cohort'):
            segment_filter['cohort_id'] = self.cleaned_data['filter_cohort'].pk
        if self.cleaned_data.get('filter_rating'):
            segment_filter['rating'] = self.cleaned_data['filter_rating']
        instance.segment_filter = segment_filter

        if commit:
            instance.save()
        return instance


class NotificationTemplateForm(forms.ModelForm):
    """Form for editing transactional notification templates from the CMS."""

    class Meta:
        model = NotificationTemplate
        fields = ['subject', 'body_html', 'is_active']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': _INPUT,
                'placeholder': 'Ex: Nous avons reçu votre message — {{ site_name }}',
            }),
            'body_html': forms.Textarea(attrs={
                'class': _TEXTAREA + ' font-mono text-sm min-h-[400px]',
                'rows': 20,
            }),
            'is_active': forms.CheckboxInput(attrs={'class': _CHECKBOX}),
        }
