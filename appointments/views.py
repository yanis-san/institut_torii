from datetime import date, datetime

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from marketing.notifications import send_notification

from .forms import AppointmentForm
from .models import Appointment, AppointmentCategory, TimeSlot


# ──────────────────────────────────────────────
# Public views
# ──────────────────────────────────────────────

def book(request):
    """Page principale de prise de rendez-vous : choix catégorie → date → créneau → formulaire."""
    categories = AppointmentCategory.objects.filter(is_active=True)
    return render(request, 'appointments/book.html', {
        'categories': categories,
    })


def available_dates(request, slug):
    """HTMX: retourne les dates disponibles pour une catégorie."""
    category = get_object_or_404(AppointmentCategory, slug=slug, is_active=True)
    today = date.today()
    now = datetime.now().time()

    qs = TimeSlot.objects.filter(
        category=category, is_active=True, date__gte=today,
    )
    # Exclure les créneaux d'aujourd'hui dont l'heure est déjà passée
    future_slots = [
        s for s in qs
        if s.date > today or s.start_time > now
    ]
    dates_list = sorted({s.date for s in future_slots})
    return render(request, 'appointments/_dates.html', {
        'category': category,
        'dates': dates_list,
    })


def available_slots(request, slug):
    """HTMX: retourne les créneaux pour une catégorie + date."""
    category = get_object_or_404(AppointmentCategory, slug=slug, is_active=True)
    date_str = request.GET.get('date', '')
    try:
        selected_date = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return render(request, 'appointments/_slots.html', {'slots': []})

    slots = TimeSlot.objects.filter(
        category=category, date=selected_date, is_active=True,
    ).order_by('start_time')

    # Si c'est aujourd'hui, exclure les créneaux dont l'heure est passée
    if selected_date == date.today():
        now = datetime.now().time()
        slots = slots.filter(start_time__gt=now)

    return render(request, 'appointments/_slots.html', {
        'category': category,
        'slots': slots,
        'selected_date': selected_date,
    })


def booking_form(request, pk):
    """HTMX: retourne le formulaire de réservation pour un créneau."""
    slot = get_object_or_404(TimeSlot, pk=pk, is_active=True)
    if not slot.is_available:
        return render(request, 'appointments/_slot_full.html', {'slot': slot})
    form = AppointmentForm()
    return render(request, 'appointments/_form.html', {
        'form': form,
        'slot': slot,
    })


@require_POST
def confirm_booking(request, pk):
    """POST: confirme la réservation."""
    slot = get_object_or_404(TimeSlot, pk=pk, is_active=True)

    if not slot.is_available:
        return render(request, 'appointments/_slot_full.html', {'slot': slot})

    form = AppointmentForm(request.POST)
    if form.is_valid():
        appointment = form.save(commit=False)
        appointment.timeslot = slot
        appointment.save()

        # Envoyer l'email de confirmation
        notify_appointment_booked(appointment)

        return render(request, 'appointments/_success.html', {
            'appointment': appointment,
        })

    return render(request, 'appointments/_form.html', {
        'form': form,
        'slot': slot,
    })


def success(request, code):
    """Page de succès après réservation (lien direct)."""
    appointment = get_object_or_404(Appointment, appointment_code=code)
    return render(request, 'appointments/success.html', {
        'appointment': appointment,
    })


# ──────────────────────────────────────────────
# Email notification
# ──────────────────────────────────────────────


def notify_appointment_booked(appointment):
    """Envoie un email de confirmation après prise de rendez-vous."""
    slot = appointment.timeslot
    return send_notification(
        event_type='appointment_booked',
        recipient_email=appointment.email,
        context={
            'first_name': appointment.first_name,
            'last_name': appointment.last_name,
            'email': appointment.email,
            'category_name': slot.category.name,
            'date': slot.date.strftime('%d/%m/%Y'),
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M'),
            'appointment_code': appointment.appointment_code,
        },
        recipient_name=f'{appointment.first_name} {appointment.last_name}',
        related_model='appointment',
        related_id=appointment.pk,
        from_type='contact',
    )
