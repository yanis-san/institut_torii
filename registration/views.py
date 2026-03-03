from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit

from courses.models import Cohort
from marketing.notifications import notify_enrollment_received
from .forms import EnrollmentForm, EnrollmentCodeForm
from .models import Enrollment


def cohort_list(request):
    """Liste des cohortes ouvertes aux inscriptions."""
    cohorts = Cohort.objects.filter(
        is_active=True,
        registration_open_date__isnull=False,
        registration_close_date__isnull=False,
    ).select_related('category', 'language', 'format').order_by('start_date')

    return render(request, 'registration/cohort_list.html', {
        'cohorts': cohorts,
    })


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def enroll(request, slug):
    """Formulaire d'inscription à une cohorte spécifique."""
    cohort = get_object_or_404(
        Cohort.objects.select_related('category', 'language', 'format'),
        slug=slug,
        is_active=True,
    )

    if not cohort.is_registration_open:
        not_yet_open = (
            cohort.registration_open_date
            and cohort.registration_open_date > timezone.now()
        )
        return render(request, 'registration/enroll_closed.html', {
            'cohort': cohort,
            'not_yet_open': not_yet_open,
        })

    # Check capacity
    current_count = cohort.enrollments.filter(
        status__in=['pending', 'confirmed'],
    ).count()
    is_full = cohort.max_capacity and current_count >= cohort.max_capacity

    if request.method == 'POST':
        form = EnrollmentForm(request.POST, request.FILES, cohort=cohort)
        if form.is_valid():
            enrollment = form.save()
            # Send acknowledgment email with code
            notify_enrollment_received(enrollment)
            return redirect('registration:success', code=enrollment.enrollment_code)
    else:
        form = EnrollmentForm(cohort=cohort)

    return render(request, 'registration/enroll.html', {
        'form': form,
        'cohort': cohort,
        'is_full': is_full,
        'current_count': current_count,
    })


def enrollment_success(request, code):
    """Page de confirmation après inscription — affiche le code unique."""
    enrollment = get_object_or_404(Enrollment, enrollment_code=code)
    return render(request, 'registration/success.html', {
        'enrollment': enrollment,
    })


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def check_status(request):
    """Page pour consulter le statut d'inscription via code."""
    enrollment = None
    cohort_stats = None

    if request.method == 'POST':
        form = EnrollmentCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                enrollment = Enrollment.objects.select_related(
                    'cohort', 'cohort__language', 'cohort__format',
                ).get(enrollment_code=code)

                # Stats du groupe
                confirmed = enrollment.cohort.enrollments.filter(
                    status='confirmed',
                ).count()
                pending = enrollment.cohort.enrollments.filter(
                    status='pending',
                ).count()

                cohort_stats = {
                    'confirmed': confirmed,
                    'pending': pending,
                    'total': confirmed + pending,
                    'max_capacity': enrollment.cohort.max_capacity,
                    'min_students': enrollment.cohort.min_students,
                    'is_open': enrollment.cohort.is_registration_open,
                }
            except Enrollment.DoesNotExist:
                form.add_error('code', _('Code introuvable. Vérifiez et réessayez.'))
    else:
        form = EnrollmentCodeForm()

    return render(request, 'registration/check_status.html', {
        'form': form,
        'enrollment': enrollment,
        'cohort_stats': cohort_stats,
    })


def cohort_status_api(request, slug):
    """API JSON pour mise à jour en temps réel (htmx polling)."""
    cohort = get_object_or_404(Cohort, slug=slug, is_active=True)

    if not cohort.is_registration_open:
        return JsonResponse(
            {'error': 'Registration closed'},
            status=403,
        )

    confirmed = cohort.enrollments.filter(status='confirmed').count()
    pending = cohort.enrollments.filter(status='pending').count()

    return JsonResponse({
        'confirmed': confirmed,
        'pending': pending,
        'total': confirmed + pending,
        'max_capacity': cohort.max_capacity,
        'min_students': cohort.min_students,
        'is_open': True,
    })
