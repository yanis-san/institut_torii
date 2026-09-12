from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """Admin pour les inscriptions avec validation de paiement."""

    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            from marketing.notifications import (
                notify_enrollment_confirmed,
                notify_teacher_enrollment_update,
                notify_enrollment_rejected,
                notify_enrollment_refunded
            )
            if obj.status == 'confirmed':
                obj.confirm(user=request.user)
                notify_enrollment_confirmed(obj, user=request.user)
                notify_teacher_enrollment_update(obj)
            elif obj.status == 'rejected':
                obj.reject(reason=obj.rejection_reason, user=request.user)
                notify_enrollment_rejected(obj, user=request.user)
            elif obj.status == 'refunded':
                notify_enrollment_refunded(obj, user=request.user)
        super().save_model(request, obj, form, change)

    list_display = (
        'full_name', 'email', 'cohort', 'status_badge',
        'enrollment_code', 'created_at',
    )
    list_filter = ('status', 'cohort', 'cohort__language', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'enrollment_code')
    readonly_fields = (
        'enrollment_code', 'created_at', 'updated_at',
        'confirmed_at', 'confirmed_by', 'receipt_preview',
    )
    list_per_page = 30
#    date_hierarchy = 'created_at'

    actions = ['validate_payment', 'reject_enrollment', 'mark_refunded']

    fieldsets = (
        (_('Identité'), {
            'fields': ('first_name', 'last_name', 'email', 'phone'),
        }),
        (_('Inscription'), {
            'fields': ('cohort', 'status', 'enrollment_code'),
        }),
        (_('Paiement'), {
            'fields': ('receipt_preview', 'payment_receipt'),
        }),
        (_('Validation'), {
            'fields': ('confirmed_at', 'confirmed_by', 'rejection_reason'),
        }),
        (_('Notes'), {
            'fields': ('admin_notes',),
            'classes': ('collapse',),
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.display(description=_('Nom complet'))
    def full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'

    @admin.display(description=_('Statut'))
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',    # amber
            'confirmed': '#10b981',  # green
            'rejected': '#ef4444',   # red
            'refunded': '#6b7280',   # gray
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description=_('Aperçu reçu'))
    def receipt_preview(self, obj):
        if obj.payment_receipt:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-height:200px;border-radius:8px;'
                'border:1px solid #e5e7eb;" /></a>',
                obj.payment_receipt.url, obj.payment_receipt.url,
            )
        return _('Aucun reçu')

    @admin.action(description='✅ Valider le paiement')
    def validate_payment(self, request, queryset):
        """Valide les paiements des inscriptions sélectionnées."""
        from marketing.notifications import notify_enrollment_confirmed, notify_teacher_enrollment_update
        count = 0
        for enrollment in queryset.filter(status='pending'):
            enrollment.confirm(user=request.user)
            notify_enrollment_confirmed(enrollment, user=request.user)
            notify_teacher_enrollment_update(enrollment)
            count += 1
        self.message_user(request, f'{count} inscription(s) validée(s) et notifiée(s).')

    @admin.action(description='❌ Rejeter l\'inscription')
    def reject_enrollment(self, request, queryset):
        """Rejette les inscriptions sélectionnées."""
        from marketing.notifications import notify_enrollment_rejected
        count = 0
        for enrollment in queryset.exclude(status='confirmed'):
            enrollment.status = 'rejected'
            enrollment.save(update_fields=['status'])
            notify_enrollment_rejected(enrollment, user=request.user)
            count += 1
        self.message_user(request, f'{count} inscription(s) rejetée(s) et notifiée(s).')

    @admin.action(description='💰 Marquer comme remboursé')
    def mark_refunded(self, request, queryset):
        """Marque les inscriptions comme remboursées."""
        from marketing.notifications import notify_enrollment_refunded
        count = 0
        for enrollment in queryset.filter(status__in=['confirmed', 'rejected']):
            enrollment.status = 'refunded'
            enrollment.save(update_fields=['status'])
            notify_enrollment_refunded(enrollment, user=request.user)
            count += 1
        self.message_user(request, f'{count} inscription(s) marquée(s) remboursée(s) et notifiée(s).')
