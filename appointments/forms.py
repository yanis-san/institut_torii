from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Appointment


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['first_name', 'last_name', 'email', 'phone', 'notes']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-colors text-gray-800',
                'placeholder': 'Votre prénom',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-colors text-gray-800',
                'placeholder': 'Votre nom',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-colors text-gray-800',
                'placeholder': 'votre@email.com',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-colors text-gray-800',
                'placeholder': '0XXX XX XX XX (optionnel)',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-colors text-gray-800 resize-none',
                'placeholder': 'Informations complémentaires (optionnel)',
                'rows': 3,
            }),
        }
