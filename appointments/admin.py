from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import timedelta, datetime
from .models import AppointmentCategory, TimeSlot, Appointment
from .admin_forms import GenerateTimeSlotsForm


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
    change_list_template = 'admin/appointments/timeslot/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('generate/', self.admin_site.admin_view(self.generate_slots_view), name='appointments_timeslot_generate'),
        ]
        return custom_urls + urls

    def generate_slots_view(self, request):
        if request.method == 'POST':
            form = GenerateTimeSlotsForm(request.POST)
            if form.is_valid():
                category = form.cleaned_data['category']
                start_date = form.cleaned_data['start_date']
                end_date = form.cleaned_data['end_date']
                days_of_week = [int(d) for d in form.cleaned_data['days_of_week']]
                start_time = form.cleaned_data['start_time']
                end_time = form.cleaned_data['end_time']
                interval_minutes = form.cleaned_data['interval_minutes']
                break_start = form.cleaned_data['break_start_time']
                break_end = form.cleaned_data['break_end_time']
                max_bookings = form.cleaned_data['max_bookings']

                created_count = 0
                current_date = start_date
                
                while current_date <= end_date:
                    if current_date.weekday() in days_of_week:
                        current_datetime = datetime.combine(current_date, start_time)
                        end_datetime = datetime.combine(current_date, end_time)
                        
                        while current_datetime + timedelta(minutes=interval_minutes) <= end_datetime:
                            slot_start = current_datetime.time()
                            slot_end = (current_datetime + timedelta(minutes=interval_minutes)).time()
                            
                            is_in_break = False
                            if break_start and break_end:
                                if not (slot_end <= break_start or slot_start >= break_end):
                                    is_in_break = True
                            
                            if not is_in_break:
                                exists = TimeSlot.objects.filter(
                                    category=category,
                                    date=current_date,
                                    start_time=slot_start
                                ).exists()
                                
                                if not exists:
                                    TimeSlot.objects.create(
                                        category=category,
                                        date=current_date,
                                        start_time=slot_start,
                                        end_time=slot_end,
                                        max_bookings=max_bookings,
                                        is_active=True
                                    )
                                    created_count += 1
                                    
                            current_datetime += timedelta(minutes=interval_minutes)
                            
                    current_date += timedelta(days=1)
                
                messages.success(request, f"{created_count} créneau(x) ont été générés avec succès.")
                return redirect('admin:appointments_timeslot_changelist')
        else:
            form = GenerateTimeSlotsForm()
            
        context = dict(
            self.admin_site.each_context(request),
            title="Générer des créneaux horaires",
            form=form,
            opts=self.model._meta,
        )
        return render(request, 'admin/appointments/timeslot/generate.html', context)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'timeslot', 'status', 'appointment_code', 'created_at')
    list_filter = ('status', 'timeslot__category')
    search_fields = ('first_name', 'last_name', 'email', 'appointment_code')
    readonly_fields = ('appointment_code', 'created_at', 'updated_at')
