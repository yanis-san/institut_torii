from django.shortcuts import render
from courses.models import Cohort


def home(request):
    """Page d'accueil avec les cohortes mises en avant (best sellers)."""
    featured_cohorts = (
        Cohort.objects
        .filter(is_active=True, is_featured=True)
        .select_related('category', 'language', 'format')
        .prefetch_related('schedules')[:6]
    )
    return render(request, 'home/index.html', {
        'featured_cohorts': featured_cohorts,
    })


def about(request):
    """Page à propos."""
    return render(request, 'home/about.html')
