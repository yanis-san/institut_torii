from django.shortcuts import render, get_object_or_404
from .models import Category, Language, Cohort


def language_detail(request, slug):
    """Page d'une langue : Japonais, Chinois, Coréen."""
    db_slugs = {
        'japanese': ['japanese', 'japonais'],
        'chinese': ['chinese', 'chinois'],
        'korean': ['korean', 'coreen'],
    }
    
    lookup_slugs = db_slugs.get(slug, [slug])
    language = Language.objects.filter(slug__in=lookup_slugs).first()
    
    cohorts = (
        Cohort.objects
        .filter(is_active=True, language=language)
        .select_related('category', 'format')
        .prefetch_related('schedules')
    ) if language else Cohort.objects.none()
    return render(request, f'courses/language_{slug}.html', {
        'language': language,
        'cohorts': cohorts,
    })


def workshop_list(request, workshop_type):
    """Page ateliers artistiques ou culinaires."""
    cohorts = (
        Cohort.objects
        .filter(is_active=True, category__type=workshop_type)
        .select_related('category', 'language', 'format')
        .prefetch_related('schedules')
    )

    template_map = {
        Category.Type.ARTISTIC_WORKSHOP: 'courses/workshops_artistic.html',
        Category.Type.CULINARY_WORKSHOP: 'courses/workshops_culinary.html',
    }
    template = template_map.get(workshop_type, 'courses/workshops_artistic.html')

    return render(request, template, {
        'cohorts': cohorts,
        'workshop_type': workshop_type,
    })


def cohorts_by_category(request):
    """
    API htmx — retourne les cohortes filtrées par catégorie et/ou langue.
    Utilisé par le formulaire de contact pour le chargement dynamique.
    """
    from django.http import JsonResponse

    category_id = request.GET.get('category')
    language_id = request.GET.get('language')

    qs = Cohort.objects.filter(is_active=True)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if language_id:
        qs = qs.filter(language_id=language_id)

    data = [
        {'id': c.id, 'name': str(c), 'price': str(c.price)}
        for c in qs.select_related('category', 'language', 'format')
    ]
    return JsonResponse(data, safe=False)
