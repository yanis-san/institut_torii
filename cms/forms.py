from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from .models import HomePage, SiteSettings
from courses.models import Category, Language, CourseFormat, Cohort, CohortSchedule
from registration.models import Enrollment


# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────

class CMSLoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Identifiant"),
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded-xl px-4 py-3 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none',
            'placeholder': 'Identifiant',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        label=_("Mot de passe"),
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded-xl px-4 py-3 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none',
            'placeholder': '••••••••',
        }),
    )


# ──────────────────────────────────────────────
# Content forms
# ──────────────────────────────────────────────

_INPUT = 'w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded-xl px-4 py-3 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none'
_TEXTAREA = _INPUT + ' min-h-[120px]'
_SELECT = _INPUT + ' cursor-pointer'
_FILE = 'w-full text-zinc-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-red-600 file:text-white hover:file:bg-red-700 file:cursor-pointer'
_CHECKBOX = 'w-5 h-5 rounded border-zinc-600 bg-zinc-800 text-red-500 focus:ring-red-500 cursor-pointer'


class HomePageForm(forms.ModelForm):
    class Meta:
        model = HomePage
        exclude = []
        widgets = {
            'hero_title': forms.TextInput(attrs={'class': _INPUT}),
            'hero_subtitle': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'hero_image': forms.ClearableFileInput(attrs={'class': _FILE}),
            'hero_cta_text': forms.TextInput(attrs={'class': _INPUT}),
            'hero_cta_url': forms.TextInput(attrs={'class': _INPUT}),
            'about_title': forms.TextInput(attrs={'class': _INPUT}),
            'about_text': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 5}),
            'about_image': forms.ClearableFileInput(attrs={'class': _FILE}),
            'stat_students': forms.TextInput(attrs={'class': _INPUT}),
            'stat_students_label': forms.TextInput(attrs={'class': _INPUT}),
            'stat_teachers': forms.TextInput(attrs={'class': _INPUT}),
            'stat_teachers_label': forms.TextInput(attrs={'class': _INPUT}),
            'stat_languages': forms.TextInput(attrs={'class': _INPUT}),
            'stat_languages_label': forms.TextInput(attrs={'class': _INPUT}),
            'stat_years': forms.TextInput(attrs={'class': _INPUT}),
            'stat_years_label': forms.TextInput(attrs={'class': _INPUT}),
            'testimonial_1_text': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'testimonial_1_author': forms.TextInput(attrs={'class': _INPUT}),
            'testimonial_1_role': forms.TextInput(attrs={'class': _INPUT}),
            'testimonial_2_text': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'testimonial_2_author': forms.TextInput(attrs={'class': _INPUT}),
            'testimonial_2_role': forms.TextInput(attrs={'class': _INPUT}),
            'testimonial_3_text': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'testimonial_3_author': forms.TextInput(attrs={'class': _INPUT}),
            'testimonial_3_role': forms.TextInput(attrs={'class': _INPUT}),
            'cta_title': forms.TextInput(attrs={'class': _INPUT}),
            'cta_text': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
        }


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        exclude = []
        widgets = {
            'phone': forms.TextInput(attrs={'class': _INPUT}),
            'email': forms.EmailInput(attrs={'class': _INPUT}),
            'address': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'google_maps_url': forms.URLInput(attrs={'class': _INPUT}),
            'facebook_url': forms.URLInput(attrs={'class': _INPUT}),
            'instagram_url': forms.URLInput(attrs={'class': _INPUT}),
            'tiktok_url': forms.URLInput(attrs={'class': _INPUT}),
            'youtube_url': forms.URLInput(attrs={'class': _INPUT}),
            'whatsapp_number': forms.TextInput(attrs={'class': _INPUT}),
            'site_name': forms.TextInput(attrs={'class': _INPUT}),
            'meta_description': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'og_image': forms.ClearableFileInput(attrs={'class': _FILE}),
            'opening_hours': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
        }


# ──────────────────────────────────────────────
# Course management forms
# ──────────────────────────────────────────────

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'type', 'description', 'icon', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'type': forms.Select(attrs={'class': _SELECT}),
            'description': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': _INPUT, 'placeholder': '🎌'}),
            'order': forms.NumberInput(attrs={'class': _INPUT}),
        }


class LanguageForm(forms.ModelForm):
    class Meta:
        model = Language
        fields = ['name', 'flag_emoji', 'flag_image_url', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'flag_emoji': forms.TextInput(attrs={'class': _INPUT, 'placeholder': '🇯🇵'}),
            'flag_image_url': forms.URLInput(attrs={'class': _INPUT}),
            'order': forms.NumberInput(attrs={'class': _INPUT}),
        }


class CourseFormatForm(forms.ModelForm):
    class Meta:
        model = CourseFormat
        fields = ['name', 'is_online', 'is_individual', 'description', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'is_online': forms.CheckboxInput(attrs={'class': _CHECKBOX}),
            'is_individual': forms.CheckboxInput(attrs={'class': _CHECKBOX}),
            'description': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': _INPUT}),
        }


class CohortForm(forms.ModelForm):
    class Meta:
        model = Cohort
        fields = [
            'category', 'language', 'format',
            'name', 'slug', 'description', 'image',
            'price', 'registration_fee',
            'duration_value', 'duration_unit',
            'hours_per_session', 'sessions_per_week',
            'start_date', 'end_date',
            'max_capacity', 'min_students',
            'registration_open_date', 'registration_close_date',
            'payment_instructions',
            'ramadan_schedule_note',
            'is_active', 'is_featured', 'order',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': _SELECT}),
            'language': forms.Select(attrs={'class': _SELECT}),
            'format': forms.Select(attrs={'class': _SELECT}),
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'slug': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'auto-généré si vide'}),
            'description': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 4}),
            'image': forms.ClearableFileInput(attrs={'class': _FILE}),
            'price': forms.NumberInput(attrs={'class': _INPUT}),
            'registration_fee': forms.NumberInput(attrs={'class': _INPUT}),
            'duration_value': forms.NumberInput(attrs={'class': _INPUT}),
            'duration_unit': forms.Select(attrs={'class': _SELECT}),
            'hours_per_session': forms.NumberInput(attrs={'class': _INPUT, 'step': '0.5'}),
            'sessions_per_week': forms.NumberInput(attrs={'class': _INPUT}),
            'start_date': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}),
            'max_capacity': forms.NumberInput(attrs={'class': _INPUT}),
            'min_students': forms.NumberInput(attrs={'class': _INPUT}),
            'registration_open_date': forms.DateTimeInput(attrs={'class': _INPUT, 'type': 'datetime-local'}),
            'registration_close_date': forms.DateTimeInput(attrs={'class': _INPUT, 'type': 'datetime-local'}),
            'payment_instructions': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 4}),
            'ramadan_schedule_note': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': _CHECKBOX}),
            'is_featured': forms.CheckboxInput(attrs={'class': _CHECKBOX}),
            'order': forms.NumberInput(attrs={'class': _INPUT}),
        }


class CohortScheduleForm(forms.ModelForm):
    class Meta:
        model = CohortSchedule
        fields = ['day', 'start_time', 'end_time']
        widgets = {
            'day': forms.Select(attrs={'class': _SELECT}),
            'start_time': forms.TimeInput(attrs={'class': _INPUT, 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': _INPUT, 'type': 'time'}),
        }


# ──────────────────────────────────────────────
# Enrollment management form (admin edits)
# ──────────────────────────────────────────────

class EnrollmentStatusForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['status', 'rejection_reason', 'admin_notes']
        widgets = {
            'status': forms.Select(attrs={'class': _SELECT}),
            'rejection_reason': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'admin_notes': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
        }
