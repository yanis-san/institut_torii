from django.contrib import admin
from .models import AppointmentCategory, TimeSlot, Appointment


class TimeSlotInline(admin.TabularInline):
    model = TimeSlot
    extra = 1


@admin.register(AppointmentCategory)
class AppointmentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_minutes', 'is_active', 'order')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [TimeSlotInline]


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('category', 'date', 'start_time', 'end_time', 'max_bookings', 'is_active')
    list_filter = ('category', 'date', 'is_active')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'timeslot', 'status', 'appointment_code', 'created_at')
    list_filter = ('status', 'timeslot__category')
    search_fields = ('first_name', 'last_name', 'email', 'appointment_code')
    readonly_fields = ('appointment_code', 'created_at', 'updated_at')
