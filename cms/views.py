import json
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.forms import inlineformset_factory
from django.http import FileResponse, Http404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)

from .models import HomePage, PageView, SiteSettings
from .forms import (
    CMSLoginForm, HomePageForm, SiteSettingsForm,
    CategoryForm, LanguageForm, CourseFormatForm, CohortForm, CohortScheduleForm,
    EnrollmentStatusForm,
)
from courses.models import Category, Language, CourseFormat, Cohort, CohortSchedule
from contact.models import Prospect
from registration.models import Enrollment
from appointments.models import AppointmentCategory, TimeSlot, Appointment
from appointments.forms import AppointmentForm as PublicAppointmentForm

_LOGIN_URL = reverse_lazy('cms:login')


# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────

@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def cms_login(request):
    if request.user.is_authenticated:
        return redirect('cms:dashboard')
    if request.method == 'POST':
        form = CMSLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('cms:dashboard')
    else:
        form = CMSLoginForm()
    return render(request, 'cms/login.html', {'form': form})


@require_POST
def cms_logout(request):
    logout(request)
    return redirect('cms:login')


# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def dashboard(request):
    now = timezone.now()
    seven_days_ago = now - timezone.timedelta(days=7)
    thirty_days_ago = now - timezone.timedelta(days=30)

    # --- Inscriptions ---
    # "Active" = confirmed + pending (les inscriptions réellement en cours)
    # Rejected et refunded ne comptent pas dans les totaux principaux
    confirmed_enrollments = Enrollment.objects.filter(status='confirmed').count()
    pending_enrollments = Enrollment.objects.filter(status='pending').count()
    total_active_enrollments = confirmed_enrollments + pending_enrollments
    rejected_enrollments = Enrollment.objects.filter(status='rejected').count()
    refunded_enrollments = Enrollment.objects.filter(status='refunded').count()
    recent_enrollments = Enrollment.objects.filter(
        created_at__gte=seven_days_ago,
        status__in=['confirmed', 'pending'],
    ).count()

    # --- Prospects ---
    total_prospects = Prospect.objects.count()
    recent_prospects = Prospect.objects.filter(created_at__gte=seven_days_ago).count()
    unread_prospects = Prospect.objects.filter(notes='').count()

    # --- Cohortes ---
    active_cohorts = Cohort.objects.filter(is_active=True).count()
    open_registrations = Cohort.objects.filter(
        registration_open_date__lte=now,
        registration_close_date__gte=now,
    ).count()

    # --- Revenus ---
    # Uniquement les inscriptions confirmées : prix cohorte + frais d'inscription
    # Les remboursés sont déduits séparément pour le revenu net
    confirmed_revenue = Enrollment.objects.filter(
        status='confirmed',
    ).aggregate(
        total=Sum(F('cohort__price') + F('cohort__registration_fee')),
    )['total'] or 0

    refunded_revenue = Enrollment.objects.filter(
        status='refunded',
    ).aggregate(
        total=Sum(F('cohort__price') + F('cohort__registration_fee')),
    )['total'] or 0

    revenue = confirmed_revenue - refunded_revenue

    monthly_revenue = Enrollment.objects.filter(
        status='confirmed',
        confirmed_at__gte=thirty_days_ago,
    ).aggregate(
        total=Sum(F('cohort__price') + F('cohort__registration_fee')),
    )['total'] or 0

    monthly_refunded = Enrollment.objects.filter(
        status='refunded',
        updated_at__gte=thirty_days_ago,
    ).aggregate(
        total=Sum(F('cohort__price') + F('cohort__registration_fee')),
    )['total'] or 0

    monthly_revenue = monthly_revenue - monthly_refunded

    latest_enrollments = (
        Enrollment.objects
        .select_related('cohort', 'cohort__language')
        .order_by('-created_at')[:5]
    )
    latest_prospects = (
        Prospect.objects
        .select_related('interested_language')
        .order_by('-created_at')[:5]
    )

    enrollment_by_status = (
        Enrollment.objects
        .values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )

    enrollments_by_cohort = (
        Cohort.objects
        .filter(is_active=True)
        .annotate(
            enrollment_count=Count('enrollments'),
            confirmed_count=Count('enrollments', filter=Q(enrollments__status='confirmed')),
            pending_count=Count('enrollments', filter=Q(enrollments__status='pending')),
        )
        .filter(enrollment_count__gt=0)
        .order_by('-enrollment_count')[:10]
    )

    prospects_by_language = (
        Prospect.objects
        .filter(interested_language__isnull=False)
        .values('interested_language__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    return render(request, 'cms/dashboard.html', {
        'total_active_enrollments': total_active_enrollments,
        'pending_enrollments': pending_enrollments,
        'confirmed_enrollments': confirmed_enrollments,
        'rejected_enrollments': rejected_enrollments,
        'refunded_enrollments': refunded_enrollments,
        'recent_enrollments': recent_enrollments,
        'total_prospects': total_prospects,
        'recent_prospects': recent_prospects,
        'unread_prospects': unread_prospects,
        'active_cohorts': active_cohorts,
        'open_registrations': open_registrations,
        'revenue': revenue,
        'monthly_revenue': monthly_revenue,
        'latest_enrollments': latest_enrollments,
        'latest_prospects': latest_prospects,
        'enrollment_by_status': enrollment_by_status,
        'enrollments_by_cohort': enrollments_by_cohort,
        'prospects_by_language': prospects_by_language,
    })


# ──────────────────────────────────────────────
# Prospects (contact messages)
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def prospect_list(request):
    qs = Prospect.objects.select_related(
        'interested_category', 'interested_language', 'interested_cohort',
    ).order_by('-created_at')

    lang = request.GET.get('language')
    status = request.GET.get('status')
    rating = request.GET.get('rating')
    search = request.GET.get('q')

    if lang:
        qs = qs.filter(interested_language_id=lang)
    if status == 'converted':
        qs = qs.filter(converted=True)
    elif status == 'unread':
        qs = qs.filter(notes='')
    elif status == 'new':
        qs = qs.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7))
    if rating:
        qs = qs.filter(rating=rating)
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    languages = Language.objects.all()
    return render(request, 'cms/prospects/list.html', {
        'prospects': qs,
        'languages': languages,
        'current_lang': lang,
        'current_status': status,
        'current_rating': rating or '',
        'rating_choices': Prospect.Rating.choices,
        'search_query': search or '',
    })


@login_required(login_url=_LOGIN_URL)
def prospect_detail(request, pk):
    prospect = get_object_or_404(
        Prospect.objects.select_related(
            'interested_category', 'interested_language', 'interested_cohort',
        ),
        pk=pk,
    )
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        converted = request.POST.get('converted') == 'on'
        rating = request.POST.get('rating', '')
        # Validate rating value
        valid_ratings = {c[0] for c in Prospect.Rating.choices}
        if rating and rating not in valid_ratings:
            rating = ''
        prospect.notes = notes
        prospect.converted = converted
        prospect.rating = rating
        if converted and not prospect.converted_date:
            prospect.converted_date = timezone.now()
        prospect.save(update_fields=['notes', 'converted', 'converted_date', 'rating'])
        messages.success(request, _('Prospect mis à jour.'))
        return redirect('cms:prospect_detail', pk=pk)
    return render(request, 'cms/prospects/detail.html', {
        'prospect': prospect,
        'rating_choices': Prospect.Rating.choices,
    })


@login_required(login_url=_LOGIN_URL)
@require_POST
def prospect_set_rating(request, pk):
    """HTMX endpoint to update prospect rating inline from the list."""
    prospect = get_object_or_404(Prospect, pk=pk)
    rating = request.POST.get('rating', '')
    valid_ratings = {c[0] for c in Prospect.Rating.choices}
    if rating and rating not in valid_ratings:
        rating = prospect.rating  # keep current if invalid
    prospect.rating = rating
    prospect.save(update_fields=['rating'])
    return render(request, 'cms/prospects/_rating_cell.html', {
        'prospect': prospect,
        'rating_choices': Prospect.Rating.choices,
    })


@login_required(login_url=_LOGIN_URL)
@require_POST
def prospect_delete(request, pk):
    prospect = get_object_or_404(Prospect, pk=pk)
    prospect.delete()
    messages.success(request, _('Prospect supprimé.'))
    return redirect('cms:prospect_list')


# ──────────────────────────────────────────────
# Enrollments
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def enrollment_list(request):
    qs = Enrollment.objects.select_related(
        'cohort', 'cohort__language', 'cohort__format',
    ).order_by('-created_at')

    status = request.GET.get('status')
    cohort_id = request.GET.get('cohort')
    search = request.GET.get('q')

    if status:
        qs = qs.filter(status=status)
    if cohort_id:
        qs = qs.filter(cohort_id=cohort_id)
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(enrollment_code__icontains=search)
        )

    cohorts = Cohort.objects.filter(is_active=True)
    return render(request, 'cms/enrollments/list.html', {
        'enrollments': qs,
        'cohorts': cohorts,
        'current_status': status,
        'current_cohort': cohort_id,
        'search_query': search or '',
    })


@login_required(login_url=_LOGIN_URL)
def enrollment_detail(request, pk):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related(
            'cohort', 'cohort__language', 'cohort__format', 'confirmed_by',
        ),
        pk=pk,
    )
    if request.method == 'POST':
        form = EnrollmentStatusForm(request.POST, instance=enrollment)
        if form.is_valid():
            obj = form.save(commit=False)
            if obj.status == 'confirmed' and enrollment.status != 'confirmed':
                obj.confirmed_at = timezone.now()
                obj.confirmed_by = request.user
            obj.save()
            messages.success(request, _('Inscription mise à jour.'))
            return redirect('cms:enrollment_detail', pk=pk)
    else:
        form = EnrollmentStatusForm(instance=enrollment)

    cohort = enrollment.cohort
    stats = {
        'confirmed': cohort.enrollments.filter(status='confirmed').count(),
        'pending': cohort.enrollments.filter(status='pending').count(),
        'rejected': cohort.enrollments.filter(status='rejected').count(),
        'refunded': cohort.enrollments.filter(status='refunded').count(),
    }
    # Build protected receipt URL
    receipt_url = None
    receipt_is_pdf = False
    if enrollment.payment_receipt:
        from django.urls import reverse
        # payment_receipt.name = 'receipts/2026/03/file.jpg' → path = '2026/03/file.jpg'
        receipt_path = enrollment.payment_receipt.name
        if receipt_path.startswith('receipts/'):
            receipt_path = receipt_path[len('receipts/'):]
        receipt_url = reverse('cms:serve_receipt', args=[receipt_path])
        receipt_is_pdf = enrollment.payment_receipt.name.lower().endswith('.pdf')

    return render(request, 'cms/enrollments/detail.html', {
        'enrollment': enrollment,
        'form': form,
        'stats': stats,
        'receipt_url': receipt_url,
        'receipt_is_pdf': receipt_is_pdf,
    })


@login_required(login_url=_LOGIN_URL)
@require_POST
def enrollment_confirm(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    enrollment.confirm(user=request.user)
    # Send confirmation email to student
    from marketing.notifications import notify_enrollment_confirmed
    notify_enrollment_confirmed(enrollment, user=request.user)
    messages.success(request, _('Paiement validé — inscription confirmée. Email de confirmation envoyé.'))
    return redirect('cms:enrollment_detail', pk=pk)


@login_required(login_url=_LOGIN_URL)
@require_POST
def enrollment_reject(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    reason = request.POST.get('reason', '')
    enrollment.reject(reason=reason)
    # Send rejection email to student
    from marketing.notifications import notify_enrollment_rejected
    notify_enrollment_rejected(enrollment, user=request.user)
    messages.success(request, _('Inscription rejetée. Email de notification envoyé.'))
    return redirect('cms:enrollment_detail', pk=pk)


@login_required(login_url=_LOGIN_URL)
@require_POST
def enrollment_refund(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    enrollment.status = 'refunded'
    enrollment.save(update_fields=['status', 'updated_at'])
    # Send refund email to student
    from marketing.notifications import notify_enrollment_refunded
    notify_enrollment_refunded(enrollment, user=request.user)
    messages.success(request, _('Inscription marquée comme remboursée. Email de notification envoyé.'))
    return redirect('cms:enrollment_detail', pk=pk)


# ──────────────────────────────────────────────
# Cohorts CRUD
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def cohort_list(request):
    cohorts = (
        Cohort.objects
        .select_related('category', 'language', 'format')
        .annotate(
            enrollment_count=Count('enrollments'),
            confirmed_count=Count('enrollments', filter=Q(enrollments__status='confirmed')),
        )
        .order_by('-is_active', 'order', 'start_date')
    )
    return render(request, 'cms/cohorts/list.html', {'cohorts': cohorts})


@login_required(login_url=_LOGIN_URL)
def cohort_create(request):
    if request.method == 'POST':
        form = CohortForm(request.POST, request.FILES)
        if form.is_valid():
            cohort = form.save()
            messages.success(request, _('Cohorte créée.'))
            return redirect('cms:cohort_edit', pk=cohort.pk)
    else:
        form = CohortForm()
    return render(request, 'cms/cohorts/form.html', {
        'form': form,
        'title': _('Nouvelle cohorte'),
        'is_new': True,
    })


@login_required(login_url=_LOGIN_URL)
def cohort_edit(request, pk):
    cohort = get_object_or_404(Cohort, pk=pk)
    ScheduleFormSet = inlineformset_factory(
        Cohort, CohortSchedule, form=CohortScheduleForm,
        extra=1, can_delete=True,
    )
    if request.method == 'POST':
        form = CohortForm(request.POST, request.FILES, instance=cohort)
        formset = ScheduleFormSet(request.POST, instance=cohort, prefix='schedules')
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, _('Cohorte mise à jour.'))
            return redirect('cms:cohort_edit', pk=pk)
    else:
        form = CohortForm(instance=cohort)
        formset = ScheduleFormSet(instance=cohort, prefix='schedules')

    stats = {
        'confirmed': cohort.enrollments.filter(status='confirmed').count(),
        'pending': cohort.enrollments.filter(status='pending').count(),
        'total': cohort.enrollments.filter(status__in=['confirmed', 'pending']).count(),
    }
    return render(request, 'cms/cohorts/form.html', {
        'form': form,
        'formset': formset,
        'cohort': cohort,
        'stats': stats,
        'title': f'Modifier : {cohort.name}',
        'is_new': False,
    })


@login_required(login_url=_LOGIN_URL)
@require_POST
def cohort_delete(request, pk):
    cohort = get_object_or_404(Cohort, pk=pk)
    if cohort.enrollments.exists():
        messages.error(request, _('Impossible de supprimer : des inscriptions existent.'))
        return redirect('cms:cohort_edit', pk=pk)
    cohort.delete()
    messages.success(request, _('Cohorte supprimée.'))
    return redirect('cms:cohort_list')


@login_required(login_url=_LOGIN_URL)
@require_POST
def cohort_toggle(request, pk):
    cohort = get_object_or_404(Cohort, pk=pk)
    cohort.is_active = not cohort.is_active
    cohort.save(update_fields=['is_active'])
    label = _('activée') if cohort.is_active else _('désactivée')
    messages.success(request, f'Cohorte {label}.')
    return redirect('cms:cohort_list')


# ──────────────────────────────────────────────
# Categories, Languages, Formats
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def catalog_settings(request):
    categories = Category.objects.annotate(cohort_count=Count('cohorts'))
    languages = Language.objects.annotate(cohort_count=Count('cohorts'))
    formats = CourseFormat.objects.annotate(cohort_count=Count('cohorts'))
    return render(request, 'cms/catalog/settings.html', {
        'categories': categories,
        'languages': languages,
        'formats': formats,
    })


@login_required(login_url=_LOGIN_URL)
def category_form(request, pk=None):
    instance = get_object_or_404(Category, pk=pk) if pk else None
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _('Catégorie enregistrée.'))
            return redirect('cms:catalog_settings')
    else:
        form = CategoryForm(instance=instance)
    return render(request, 'cms/catalog/item_form.html', {
        'form': form, 'title': _('Catégorie'), 'instance': instance,
    })


@login_required(login_url=_LOGIN_URL)
def language_form(request, pk=None):
    instance = get_object_or_404(Language, pk=pk) if pk else None
    if request.method == 'POST':
        form = LanguageForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _('Langue enregistrée.'))
            return redirect('cms:catalog_settings')
    else:
        form = LanguageForm(instance=instance)
    return render(request, 'cms/catalog/item_form.html', {
        'form': form, 'title': _('Langue'), 'instance': instance,
    })


@login_required(login_url=_LOGIN_URL)
def format_form(request, pk=None):
    instance = get_object_or_404(CourseFormat, pk=pk) if pk else None
    if request.method == 'POST':
        form = CourseFormatForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _('Format enregistré.'))
            return redirect('cms:catalog_settings')
    else:
        form = CourseFormatForm(instance=instance)
    return render(request, 'cms/catalog/item_form.html', {
        'form': form, 'title': _('Format de cours'), 'instance': instance,
    })


# ──────────────────────────────────────────────
# Content (HomePage + SiteSettings)
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def edit_homepage(request):
    obj = HomePage.load()
    if request.method == 'POST':
        form = HomePageForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, _("Page d'accueil mise à jour."))
            return redirect('cms:edit_homepage')
    else:
        form = HomePageForm(instance=obj)
    return render(request, 'cms/content/homepage.html', {'form': form})


@login_required(login_url=_LOGIN_URL)
def edit_settings(request):
    obj = SiteSettings.load()
    if request.method == 'POST':
        form = SiteSettingsForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, _('Paramètres mis à jour.'))
            return redirect('cms:edit_settings')
    else:
        form = SiteSettingsForm(instance=obj)
    return render(request, 'cms/content/settings.html', {'form': form})


# ──────────────────────────────────────────────
# Analytics
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def analytics(request):
    """Server-side analytics dashboard with date range filtering."""
    try:
        return _analytics_inner(request)
    except Exception:
        logger.exception('Analytics view crashed')
        raise


def _analytics_inner(request):
    now = timezone.now()

    # Date range from query params (default: last 30 days)
    try:
        days = int(request.GET.get('days', 30))
    except (ValueError, TypeError):
        days = 30
    if days not in (7, 14, 30, 90):
        days = 30
    start_date = now - timezone.timedelta(days=days)

    qs = PageView.objects.filter(timestamp__gte=start_date)

    # Exclude bots for clean metrics
    qs_no_bots = qs.exclude(device_type='bot')
    bot_count = qs.filter(device_type='bot').count()

    # ── KPIs ──
    total_views = qs_no_bots.count()
    unique_visitors = qs_no_bots.values('visitor_hash').distinct().count()
    unique_sessions = qs_no_bots.exclude(session_key='').values('session_key').distinct().count()

    # Average pages per session
    if unique_sessions > 0:
        pages_per_session = round(total_views / unique_sessions, 1)
    else:
        pages_per_session = 0

    # ── Traffic over time (daily) ──
    daily_views = list(
        qs_no_bots
        .filter(timestamp__isnull=False)
        .annotate(date=TruncDate('timestamp'))
        .values('date')
        .annotate(views=Count('id'), visitors=Count('visitor_hash', distinct=True))
        .order_by('date')
    )

    # ── Top pages ──
    top_pages = list(
        qs_no_bots
        .values('path')
        .annotate(views=Count('id'), visitors=Count('visitor_hash', distinct=True))
        .order_by('-views')[:15]
    )

    # ── Referrer sources ──
    referrer_sources = list(
        qs_no_bots
        .exclude(referrer_domain='')
        .values('referrer_domain')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # ── Direct vs Referral vs UTM breakdown ──
    direct_count = qs_no_bots.filter(referrer_domain='', utm_source='').count()
    referral_count = qs_no_bots.exclude(referrer_domain='').filter(utm_source='').count()
    utm_count = qs_no_bots.exclude(utm_source='').count()

    # ── UTM Campaigns ──
    utm_campaigns = list(
        qs_no_bots
        .exclude(utm_source='')
        .values('utm_source', 'utm_medium', 'utm_campaign')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # ── Device types ──
    device_breakdown = list(
        qs_no_bots
        .values('device_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # ── Browsers ──
    browser_breakdown = list(
        qs_no_bots
        .exclude(browser='')
        .values('browser')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )

    # ── Operating systems ──
    os_breakdown = list(
        qs_no_bots
        .exclude(os='')
        .values('os')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )

    # ── Conversion funnel (page → contact → enrollment) ──
    funnel_homepage = qs_no_bots.filter(path='/').count()
    funnel_courses = qs_no_bots.filter(path__startswith='/courses/').count()
    funnel_contact = qs_no_bots.filter(path__startswith='/contact/').count()
    funnel_register = qs_no_bots.filter(path__startswith='/register/').count()

    # ── Peak hours (which hours get the most traffic) ──
    hourly_views = list(
        qs_no_bots
        .annotate(hour=ExtractHour('timestamp'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('hour')
    )

    # ── Helper: merge domain breakdown into platform names ──
    def _merge_platforms(raw_qs, classifier):
        merged = {}
        for item in raw_qs:
            platform = classifier(item['referrer_domain'])
            if not platform:
                continue
            if platform not in merged:
                merged[platform] = {'platform': platform, 'count': 0, 'visitors': 0}
            merged[platform]['count'] += item['count']
            merged[platform]['visitors'] += item['visitors']
        return sorted(merged.values(), key=lambda x: x['count'], reverse=True)

    def _source_stats(domain_dict, classifier):
        domains = list(domain_dict.keys())
        source_qs = qs_no_bots.filter(referrer_domain__in=domains)
        total = source_qs.count()
        visitors = source_qs.values('visitor_hash').distinct().count()
        raw = list(
            source_qs
            .values('referrer_domain')
            .annotate(count=Count('id'), visitors=Count('visitor_hash', distinct=True))
            .order_by('-count')
        )
        breakdown = _merge_platforms(raw, classifier)
        top_pages = list(
            source_qs
            .values('path')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        return total, visitors, breakdown, top_pages

    # ── AI Traffic ──
    ai_total, ai_visitors, ai_breakdown, ai_top_pages = _source_stats(
        PageView.AI_REFERRER_DOMAINS, PageView.classify_ai_referrer,
    )

    # ── Search Engine Traffic ──
    search_total, search_visitors, search_breakdown, search_top_pages = _source_stats(
        PageView.SEARCH_ENGINE_DOMAINS, PageView.classify_search_engine,
    )

    # ── Social Media Traffic ──
    social_total, social_visitors, social_breakdown, social_top_pages = _source_stats(
        PageView.SOCIAL_MEDIA_DOMAINS, PageView.classify_social_media,
    )

    # For the daily chart — prepare JSON-safe data for Alpine.js
    # Filter out entries where date is None (can happen on MySQL with NULL timestamps)
    valid_daily = [d for d in daily_views if d.get('date') is not None]
    chart_labels = json.dumps([d['date'].strftime('%d/%m') for d in valid_daily])
    chart_views = json.dumps([d['views'] for d in valid_daily])
    chart_visitors = json.dumps([d['visitors'] for d in valid_daily])

    # Convert hourly_views to proper JSON (hour is int from ExtractHour)
    hourly_views_json = json.dumps([
        {'hour': int(h['hour']), 'count': h['count']}
        for h in hourly_views if h.get('hour') is not None
    ])

    return render(request, 'cms/analytics.html', {
        'days': days,
        'total_views': total_views,
        'unique_visitors': unique_visitors,
        'unique_sessions': unique_sessions,
        'pages_per_session': pages_per_session,
        'bot_count': bot_count,
        'daily_views': daily_views,
        'top_pages': top_pages,
        'referrer_sources': referrer_sources,
        'direct_count': direct_count,
        'referral_count': referral_count,
        'utm_count': utm_count,
        'utm_campaigns': utm_campaigns,
        'device_breakdown': device_breakdown,
        'browser_breakdown': browser_breakdown,
        'os_breakdown': os_breakdown,
        'funnel_homepage': funnel_homepage,
        'funnel_courses': funnel_courses,
        'funnel_contact': funnel_contact,
        'funnel_register': funnel_register,
        'hourly_views_json': hourly_views_json,
        'chart_labels': chart_labels,
        'chart_views': chart_views,
        'chart_visitors': chart_visitors,
        'ai_total': ai_total,
        'ai_visitors': ai_visitors,
        'ai_breakdown': ai_breakdown,
        'ai_top_pages': ai_top_pages,
        'search_total': search_total,
        'search_visitors': search_visitors,
        'search_breakdown': search_breakdown,
        'search_top_pages': search_top_pages,
        'social_total': social_total,
        'social_visitors': social_visitors,
        'social_breakdown': social_breakdown,
        'social_top_pages': social_top_pages,
    })


# ──────────────────────────────────────────────
# Protected media (payment receipts)
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def serve_receipt(request, path):
    """Serve payment receipt files only to authenticated CMS users."""
    import os
    from django.conf import settings

    file_path = os.path.join(settings.MEDIA_ROOT, 'receipts', path)
    file_path = os.path.normpath(file_path)

    # Prevent path traversal
    receipts_root = os.path.normpath(os.path.join(settings.MEDIA_ROOT, 'receipts'))
    if not file_path.startswith(receipts_root):
        raise Http404

    if not os.path.isfile(file_path):
        raise Http404

    import mimetypes
    content_type, _ = mimetypes.guess_type(file_path)
    return FileResponse(open(file_path, 'rb'), content_type=content_type or 'application/octet-stream')


# ──────────────────────────────────────────────
# Appointments
# ──────────────────────────────────────────────

@login_required(login_url=_LOGIN_URL)
def appointment_list(request):
    """Liste de tous les rendez-vous."""
    appointments = Appointment.objects.select_related('timeslot', 'timeslot__category').all()

    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('q', '').strip()

    if status_filter:
        appointments = appointments.filter(status=status_filter)
    if category_filter:
        appointments = appointments.filter(timeslot__category__pk=category_filter)
    if search_query:
        appointments = appointments.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(appointment_code__icontains=search_query)
        )

    categories = AppointmentCategory.objects.filter(is_active=True)

    return render(request, 'cms/appointments/list.html', {
        'appointments': appointments,
        'categories': categories,
        'current_status': status_filter,
        'current_category': category_filter,
        'search_query': search_query,
    })


@login_required(login_url=_LOGIN_URL)
def appointment_detail(request, pk):
    """Détail d'un rendez-vous avec mise à jour du statut et notes."""
    appt = get_object_or_404(Appointment.objects.select_related('timeslot', 'timeslot__category'), pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status', appt.status)
        admin_notes = request.POST.get('admin_notes', appt.admin_notes)
        appt.status = new_status
        appt.admin_notes = admin_notes
        appt.save(update_fields=['status', 'admin_notes', 'updated_at'])
        messages.success(request, _('Rendez-vous mis à jour.'))
        return redirect('cms:appointment_detail', pk=pk)

    return render(request, 'cms/appointments/detail.html', {
        'appointment': appt,
    })


@login_required(login_url=_LOGIN_URL)
@require_POST
def appointment_delete(request, pk):
    """Supprimer un rendez-vous."""
    appt = get_object_or_404(Appointment, pk=pk)
    appt.delete()
    messages.success(request, _('Rendez-vous supprimé.'))
    return redirect('cms:appointment_list')


@login_required(login_url=_LOGIN_URL)
def appointment_category_list(request):
    """Gestion des catégories et créneaux."""
    categories = AppointmentCategory.objects.prefetch_related('timeslots').all()
    return render(request, 'cms/appointments/categories.html', {
        'categories': categories,
    })


@login_required(login_url=_LOGIN_URL)
def appointment_category_form(request, pk=None):
    """Créer ou éditer une catégorie de rendez-vous."""
    from django import forms as django_forms

    class AppointmentCategoryForm(django_forms.ModelForm):
        class Meta:
            model = AppointmentCategory
            fields = ['name', 'slug', 'description', 'icon', 'duration_minutes', 'is_active', 'order']
            widgets = {
                'name': django_forms.TextInput(attrs={'class': 'w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none'}),
                'slug': django_forms.TextInput(attrs={'class': 'w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none', 'placeholder': 'Laissez vide pour auto-générer'}),
                'description': django_forms.Textarea(attrs={'class': 'w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none resize-none', 'rows': 3}),
                'icon': django_forms.TextInput(attrs={'class': 'w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none', 'placeholder': '📅'}),
                'duration_minutes': django_forms.NumberInput(attrs={'class': 'w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none'}),
                'order': django_forms.NumberInput(attrs={'class': 'w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none'}),
                'is_active': django_forms.CheckboxInput(attrs={'class': 'rounded bg-zinc-800 border-zinc-700 text-red-500 focus:ring-red-500'}),
            }

    instance = get_object_or_404(AppointmentCategory, pk=pk) if pk else None
    if request.method == 'POST':
        form = AppointmentCategoryForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _('Catégorie enregistrée.'))
            return redirect('cms:appointment_category_list')
    else:
        form = AppointmentCategoryForm(instance=instance)

    return render(request, 'cms/appointments/category_form.html', {
        'form': form,
        'instance': instance,
    })


@login_required(login_url=_LOGIN_URL)
@require_POST
def appointment_category_delete(request, pk):
    """Supprimer une catégorie."""
    cat = get_object_or_404(AppointmentCategory, pk=pk)
    cat.delete()
    messages.success(request, _('Catégorie supprimée.'))
    return redirect('cms:appointment_category_list')


@login_required(login_url=_LOGIN_URL)
def timeslot_form(request, category_pk, pk=None):
    """Créer ou éditer un créneau horaire."""
    from django import forms as django_forms

    category = get_object_or_404(AppointmentCategory, pk=category_pk)

    class TimeSlotForm(django_forms.ModelForm):
        class Meta:
            model = TimeSlot
            fields = ['date', 'start_time', 'end_time', 'max_bookings', 'is_active']
            widgets = {
                'date': django_forms.DateInput(attrs={'class': 'w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none', 'type': 'date'}),
                'start_time': django_forms.TimeInput(attrs={'class': 'w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none', 'type': 'time'}),
                'end_time': django_forms.TimeInput(attrs={'class': 'w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none', 'type': 'time'}),
                'max_bookings': django_forms.NumberInput(attrs={'class': 'w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none', 'min': '1'}),
                'is_active': django_forms.CheckboxInput(attrs={'class': 'rounded bg-zinc-800 border-zinc-700 text-red-500 focus:ring-red-500'}),
            }

    instance = get_object_or_404(TimeSlot, pk=pk, category=category) if pk else None
    if request.method == 'POST':
        form = TimeSlotForm(request.POST, instance=instance)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.category = category
            slot.save()
            messages.success(request, _('Créneau enregistré.'))
            return redirect('cms:appointment_category_list')
    else:
        form = TimeSlotForm(instance=instance)

    return render(request, 'cms/appointments/timeslot_form.html', {
        'form': form,
        'category': category,
        'instance': instance,
    })


@login_required(login_url=_LOGIN_URL)
@require_POST
def timeslot_delete(request, pk):
    """Supprimer un créneau."""
    slot = get_object_or_404(TimeSlot, pk=pk)
    slot.delete()
    messages.success(request, _('Créneau supprimé.'))
    return redirect('cms:appointment_category_list')


@login_required(login_url=_LOGIN_URL)
def timeslot_bulk_create(request, category_pk):
    """Créer plusieurs créneaux en une fois (plage de dates + jours + horaires)."""
    from datetime import timedelta

    category = get_object_or_404(AppointmentCategory, pk=category_pk)

    WEEKDAY_CHOICES = [
        (0, _('Lundi')),
        (1, _('Mardi')),
        (2, _('Mercredi')),
        (3, _('Jeudi')),
        (4, _('Vendredi')),
        (5, _('Samedi')),
        (6, _('Dimanche')),
    ]

    if request.method == 'POST':
        start_date_str = request.POST.get('start_date', '')
        end_date_str = request.POST.get('end_date', '')
        weekdays = request.POST.getlist('weekdays')
        start_times = request.POST.getlist('start_times')
        end_times = request.POST.getlist('end_times')
        max_bookings = request.POST.get('max_bookings', '1')

        # Validation
        from datetime import date as date_cls, time as time_cls

        errors = []
        try:
            start_date = date_cls.fromisoformat(start_date_str)
            end_date = date_cls.fromisoformat(end_date_str)
            if end_date < start_date:
                errors.append(_('La date de fin doit être après la date de début.'))
        except (ValueError, TypeError):
            errors.append(_('Dates invalides.'))
            start_date = end_date = None

        weekday_ints = []
        for w in weekdays:
            try:
                weekday_ints.append(int(w))
            except (ValueError, TypeError):
                pass
        if not weekday_ints:
            errors.append(_('Sélectionnez au moins un jour de la semaine.'))

        time_pairs = []
        for st, et in zip(start_times, end_times):
            try:
                s = time_cls.fromisoformat(st)
                e = time_cls.fromisoformat(et)
                if e <= s:
                    errors.append(_(f'L\'heure de fin ({et}) doit être après l\'heure de début ({st}).'))
                else:
                    time_pairs.append((s, e))
            except (ValueError, TypeError):
                pass
        if not time_pairs:
            errors.append(_('Ajoutez au moins un horaire valide.'))

        try:
            max_bookings_int = max(1, int(max_bookings))
        except (ValueError, TypeError):
            max_bookings_int = 1

        if not errors and start_date and end_date:
            created = 0
            skipped = 0
            current = start_date
            while current <= end_date:
                if current.weekday() in weekday_ints:
                    for s, e in time_pairs:
                        obj, was_created = TimeSlot.objects.get_or_create(
                            category=category,
                            date=current,
                            start_time=s,
                            defaults={
                                'end_time': e,
                                'max_bookings': max_bookings_int,
                                'is_active': True,
                            },
                        )
                        if was_created:
                            created += 1
                        else:
                            skipped += 1
                current += timedelta(days=1)

            msg = f'{created} créneau(x) créé(s).'
            if skipped:
                msg += f' {skipped} ignoré(s) (déjà existants).'
            messages.success(request, msg)
            return redirect('cms:appointment_category_list')

        return render(request, 'cms/appointments/timeslot_bulk.html', {
            'category': category,
            'weekday_choices': WEEKDAY_CHOICES,
            'errors': errors,
            'posted': request.POST,
        })

    return render(request, 'cms/appointments/timeslot_bulk.html', {
        'category': category,
        'weekday_choices': WEEKDAY_CHOICES,
        'errors': [],
        'posted': {},
    })
