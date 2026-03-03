"""
Tests for the CMS app — auth, dashboard, CRUD operations.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from cms.models import HomePage, PageView, SiteSettings
from courses.models import Category, Language, CourseFormat, Cohort
from contact.models import Prospect
from registration.models import Enrollment


class CMSTestMixin:
    """Provides reusable setUp with authenticated admin user and sample data."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='testpass123')

        self.category = Category.objects.create(
            name='Cours linguistique', type='language',
        )
        self.language = Language.objects.create(name='Japonais', flag_emoji='🇯🇵')
        self.format = CourseFormat.objects.create(name='Présentiel groupe')
        self.cohort = Cohort.objects.create(
            category=self.category,
            language=self.language,
            format=self.format,
            name='Japonais N5 — Été 2026',
            price=15000,
            duration_value=3,
        )


class CMSAuthTestCase(CMSTestMixin, TestCase):
    """Test CMS authentication."""

    def test_login_page_renders(self):
        response = self.client.get(reverse('cms:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Se connecter')

    def test_login_success_redirects_to_dashboard(self):
        response = self.client.post(reverse('cms:login'), {
            'username': 'admin', 'password': 'testpass123',
        })
        self.assertRedirects(response, reverse('cms:dashboard'))

    def test_login_bad_credentials(self):
        response = self.client.post(reverse('cms:login'), {
            'username': 'admin', 'password': 'wrong',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'incorrects')

    def test_dashboard_requires_auth(self):
        response = self.client.get(reverse('cms:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_redirect_from_login(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:login'))
        self.assertRedirects(response, reverse('cms:dashboard'))

    def test_logout(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('cms:logout'))
        self.assertRedirects(response, reverse('cms:login'))
        # Verify logged out
        response = self.client.get(reverse('cms:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_logout_rejects_get(self):
        """Logout must be POST only."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:logout'))
        self.assertEqual(response.status_code, 405)


class CMSDashboardTestCase(CMSTestMixin, TestCase):
    """Test dashboard view."""

    def test_dashboard_renders(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_dashboard_shows_stats(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:dashboard'))
        self.assertIn('total_active_enrollments', response.context)
        self.assertIn('total_prospects', response.context)
        self.assertIn('active_cohorts', response.context)
        self.assertIn('revenue', response.context)
        self.assertIn('rejected_enrollments', response.context)
        self.assertIn('refunded_enrollments', response.context)


class CMSSingletonTestCase(CMSTestMixin, TestCase):
    """Test singleton models."""

    def test_homepage_load_creates_singleton(self):
        hp = HomePage.load()
        self.assertEqual(hp.pk, 1)
        # Load again — same instance
        hp2 = HomePage.load()
        self.assertEqual(hp2.pk, 1)
        self.assertEqual(HomePage.objects.count(), 1)

    def test_site_settings_load_creates_singleton(self):
        ss = SiteSettings.load()
        self.assertEqual(ss.pk, 1)
        ss2 = SiteSettings.load()
        self.assertEqual(ss2.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)


class CMSProspectsTestCase(CMSTestMixin, TestCase):
    """Test prospects management."""

    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='testpass123')
        self.prospect = Prospect.objects.create(
            first_name='Test', last_name='User',
            email='test@example.com',
            interested_language=self.language,
        )

    def test_prospect_list_renders(self):
        response = self.client.get(reverse('cms:prospect_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'USER')  # last_name uppercased

    def test_prospect_list_filter_by_language(self):
        response = self.client.get(reverse('cms:prospect_list'), {'language': self.language.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'USER')

    def test_prospect_list_search(self):
        response = self.client.get(reverse('cms:prospect_list'), {'q': 'test@example'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'USER')

    def test_prospect_detail_renders(self):
        response = self.client.get(reverse('cms:prospect_detail', args=[self.prospect.pk]))
        self.assertEqual(response.status_code, 200)

    def test_prospect_update_notes(self):
        response = self.client.post(
            reverse('cms:prospect_detail', args=[self.prospect.pk]),
            {'notes': 'Suivre ce prospect', 'converted': ''},
        )
        self.assertRedirects(response, reverse('cms:prospect_detail', args=[self.prospect.pk]))
        self.prospect.refresh_from_db()
        self.assertEqual(self.prospect.notes, 'Suivre ce prospect')

    def test_prospect_mark_converted(self):
        response = self.client.post(
            reverse('cms:prospect_detail', args=[self.prospect.pk]),
            {'notes': '', 'converted': 'on'},
        )
        self.prospect.refresh_from_db()
        self.assertTrue(self.prospect.converted)
        self.assertIsNotNone(self.prospect.converted_date)

    def test_prospect_delete(self):
        response = self.client.post(reverse('cms:prospect_delete', args=[self.prospect.pk]))
        self.assertRedirects(response, reverse('cms:prospect_list'))
        self.assertFalse(Prospect.objects.filter(pk=self.prospect.pk).exists())

    # --- Rating ---

    def test_prospect_update_rating(self):
        """Can set rating from prospect detail page."""
        response = self.client.post(
            reverse('cms:prospect_detail', args=[self.prospect.pk]),
            {'notes': '', 'converted': '', 'rating': 'hot'},
        )
        self.assertRedirects(response, reverse('cms:prospect_detail', args=[self.prospect.pk]))
        self.prospect.refresh_from_db()
        self.assertEqual(self.prospect.rating, 'hot')

    def test_prospect_clear_rating(self):
        """Can clear rating by sending empty value."""
        self.prospect.rating = 'hot'
        self.prospect.save()
        self.client.post(
            reverse('cms:prospect_detail', args=[self.prospect.pk]),
            {'notes': '', 'converted': '', 'rating': ''},
        )
        self.prospect.refresh_from_db()
        self.assertEqual(self.prospect.rating, '')

    def test_prospect_rating_inline_htmx(self):
        """HTMX endpoint to update rating inline returns partial."""
        url = reverse('cms:prospect_set_rating', args=[self.prospect.pk])
        response = self.client.post(url, {'rating': 'warm'},
                                    HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.prospect.refresh_from_db()
        self.assertEqual(self.prospect.rating, 'warm')

    def test_prospect_rating_inline_bad_value(self):
        """HTMX endpoint rejects invalid rating values."""
        url = reverse('cms:prospect_set_rating', args=[self.prospect.pk])
        response = self.client.post(url, {'rating': 'invalid_value'},
                                    HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.prospect.refresh_from_db()
        self.assertEqual(self.prospect.rating, '')  # unchanged

    def test_prospect_list_filter_by_rating(self):
        """Can filter prospects by rating."""
        self.prospect.rating = 'hot'
        self.prospect.save()
        Prospect.objects.create(
            first_name='Cold', last_name='PERSON',
            email='cold@example.com', rating='cold',
        )
        response = self.client.get(reverse('cms:prospect_list'), {'rating': 'hot'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'USER')
        self.assertNotContains(response, 'PERSON')


class CMSEnrollmentsTestCase(CMSTestMixin, TestCase):
    """Test enrollment management."""

    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='testpass123')
        self.enrollment = Enrollment.objects.create(
            first_name='Étudiant', last_name='Test',
            email='etudiant@example.com',
            cohort=self.cohort,
            payment_receipt='receipts/test.jpg',
        )

    def test_enrollment_list_renders(self):
        response = self.client.get(reverse('cms:enrollment_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST')

    def test_enrollment_list_filter_by_status(self):
        response = self.client.get(reverse('cms:enrollment_list'), {'status': 'pending'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST')

    def test_enrollment_detail_renders(self):
        response = self.client.get(reverse('cms:enrollment_detail', args=[self.enrollment.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.enrollment.enrollment_code)

    def test_enrollment_confirm(self):
        response = self.client.post(reverse('cms:enrollment_confirm', args=[self.enrollment.pk]))
        self.assertRedirects(response, reverse('cms:enrollment_detail', args=[self.enrollment.pk]))
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, 'confirmed')
        self.assertIsNotNone(self.enrollment.confirmed_at)
        self.assertEqual(self.enrollment.confirmed_by, self.user)

    def test_enrollment_reject(self):
        response = self.client.post(
            reverse('cms:enrollment_reject', args=[self.enrollment.pk]),
            {'reason': 'Reçu invalide'},
        )
        self.assertRedirects(response, reverse('cms:enrollment_detail', args=[self.enrollment.pk]))
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, 'rejected')
        self.assertEqual(self.enrollment.rejection_reason, 'Reçu invalide')

    def test_enrollment_refund(self):
        self.enrollment.confirm(user=self.user)
        response = self.client.post(reverse('cms:enrollment_refund', args=[self.enrollment.pk]))
        self.assertRedirects(response, reverse('cms:enrollment_detail', args=[self.enrollment.pk]))
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, 'refunded')


class CMSCohortsTestCase(CMSTestMixin, TestCase):
    """Test cohort CRUD."""

    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='testpass123')

    def test_cohort_list_renders(self):
        response = self.client.get(reverse('cms:cohort_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Japonais N5')

    def test_cohort_create_form_renders(self):
        response = self.client.get(reverse('cms:cohort_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nouvelle cohorte')

    def test_cohort_create_post(self):
        response = self.client.post(reverse('cms:cohort_create'), {
            'category': self.category.pk,
            'language': self.language.pk,
            'format': self.format.pk,
            'name': 'Chinois Débutant',
            'price': 12000,
            'registration_fee': 1000,
            'duration_value': 3,
            'duration_unit': 'months',
            'hours_per_session': '2.0',
            'sessions_per_week': 2,
            'min_students': 0,
            'order': 0,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Cohort.objects.filter(name='Chinois Débutant').exists())

    def test_cohort_edit_form_renders(self):
        response = self.client.get(reverse('cms:cohort_edit', args=[self.cohort.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Japonais N5')

    def test_cohort_toggle(self):
        self.assertTrue(self.cohort.is_active)
        response = self.client.post(reverse('cms:cohort_toggle', args=[self.cohort.pk]))
        self.assertRedirects(response, reverse('cms:cohort_list'))
        self.cohort.refresh_from_db()
        self.assertFalse(self.cohort.is_active)

    def test_cohort_delete_no_enrollments(self):
        new_cohort = Cohort.objects.create(
            category=self.category, format=self.format,
            name='À supprimer', price=5000, duration_value=1,
        )
        response = self.client.post(reverse('cms:cohort_delete', args=[new_cohort.pk]))
        self.assertRedirects(response, reverse('cms:cohort_list'))
        self.assertFalse(Cohort.objects.filter(pk=new_cohort.pk).exists())

    def test_cohort_delete_with_enrollments_blocked(self):
        Enrollment.objects.create(
            first_name='Test', last_name='User',
            email='test@example.com', cohort=self.cohort,
            payment_receipt='receipts/test.jpg',
        )
        response = self.client.post(reverse('cms:cohort_delete', args=[self.cohort.pk]))
        self.assertRedirects(response, reverse('cms:cohort_edit', args=[self.cohort.pk]))
        self.assertTrue(Cohort.objects.filter(pk=self.cohort.pk).exists())


class CMSCatalogTestCase(CMSTestMixin, TestCase):
    """Test catalog management."""

    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='testpass123')

    def test_catalog_settings_renders(self):
        response = self.client.get(reverse('cms:catalog_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Japonais')
        self.assertContains(response, 'Cours linguistique')

    def test_category_create(self):
        response = self.client.post(reverse('cms:category_create'), {
            'name': 'Atelier culinaire', 'type': 'culinary', 'order': 0,
        })
        self.assertRedirects(response, reverse('cms:catalog_settings'))
        self.assertTrue(Category.objects.filter(name='Atelier culinaire').exists())

    def test_language_create(self):
        response = self.client.post(reverse('cms:language_create'), {
            'name': 'Coréen', 'flag_emoji': '🇰🇷', 'order': 0,
        })
        self.assertRedirects(response, reverse('cms:catalog_settings'))
        self.assertTrue(Language.objects.filter(name='Coréen').exists())

    def test_format_create(self):
        response = self.client.post(reverse('cms:format_create'), {
            'name': 'En ligne', 'order': 0,
        })
        self.assertRedirects(response, reverse('cms:catalog_settings'))
        self.assertTrue(CourseFormat.objects.filter(name='En ligne').exists())

    def test_category_edit(self):
        response = self.client.post(
            reverse('cms:category_edit', args=[self.category.pk]),
            {'name': 'Cours de langue', 'type': 'language', 'order': 1},
        )
        self.assertRedirects(response, reverse('cms:catalog_settings'))
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Cours de langue')


class CMSContentTestCase(CMSTestMixin, TestCase):
    """Test content editing."""

    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='testpass123')

    def test_edit_homepage_renders(self):
        response = self.client.get(reverse('cms:edit_homepage'))
        self.assertEqual(response.status_code, 200)

    def test_edit_homepage_post(self):
        hp = HomePage.load()
        response = self.client.post(reverse('cms:edit_homepage'), {
            'hero_title': 'Nouveau titre',
            'hero_subtitle': 'Nouvelle description',
            'hero_cta_text': 'Contacter',
            'hero_cta_url': '/contact/',
            'about_title': 'À propos',
            'about_text': 'Texte',
            'stat_students': '500+',
            'stat_students_label': 'Étudiants',
            'stat_teachers': '10+',
            'stat_teachers_label': 'Profs',
            'stat_languages': '3',
            'stat_languages_label': 'Langues',
            'stat_years': '5+',
            'stat_years_label': 'Ans',
            'cta_title': 'CTA',
            'cta_text': '',
        })
        self.assertRedirects(response, reverse('cms:edit_homepage'))
        hp.refresh_from_db()
        self.assertEqual(hp.hero_title, 'Nouveau titre')

    def test_edit_settings_renders(self):
        response = self.client.get(reverse('cms:edit_settings'))
        self.assertEqual(response.status_code, 200)

    def test_edit_settings_post(self):
        ss = SiteSettings.load()
        response = self.client.post(reverse('cms:edit_settings'), {
            'phone': '+213 555 123 456',
            'email': 'contact@torii.dz',
            'address': 'Alger, Algérie',
            'site_name': 'Institut Torii',
            'meta_description': 'Cours de langues asiatiques',
            'opening_hours': 'Dim-Jeu 9h-18h',
        })
        self.assertRedirects(response, reverse('cms:edit_settings'))
        ss.refresh_from_db()
        self.assertEqual(ss.phone, '+213 555 123 456')


class CMSAllViewsRequireAuthTestCase(CMSTestMixin, TestCase):
    """Ensure all CMS views require authentication (except login)."""

    def test_all_protected_views_redirect(self):
        protected_urls = [
            reverse('cms:dashboard'),
            reverse('cms:prospect_list'),
            reverse('cms:enrollment_list'),
            reverse('cms:cohort_list'),
            reverse('cms:cohort_create'),
            reverse('cms:catalog_settings'),
            reverse('cms:edit_homepage'),
            reverse('cms:edit_settings'),
            reverse('cms:analytics'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 302,
                f'{url} should redirect unauthenticated users',
            )


# ──────────────────────────────────────────────
# Analytics
# ──────────────────────────────────────────────

class PageViewModelTestCase(TestCase):
    """Test the PageView model and its static helpers."""

    def test_make_visitor_hash(self):
        h = PageView.make_visitor_hash('1.2.3.4', 'Mozilla/5.0')
        self.assertEqual(len(h), 64)  # SHA-256 hex digest
        # Same input → same hash
        self.assertEqual(h, PageView.make_visitor_hash('1.2.3.4', 'Mozilla/5.0'))
        # Different input → different hash
        self.assertNotEqual(h, PageView.make_visitor_hash('5.6.7.8', 'Mozilla/5.0'))

    def test_parse_device_type_desktop(self):
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        self.assertEqual(PageView.parse_device_type(ua), 'desktop')

    def test_parse_device_type_mobile(self):
        ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0) AppleWebKit/605'
        self.assertEqual(PageView.parse_device_type(ua), 'mobile')

    def test_parse_device_type_tablet(self):
        ua = 'Mozilla/5.0 (iPad; CPU OS 14_0) AppleWebKit/605'
        self.assertEqual(PageView.parse_device_type(ua), 'tablet')

    def test_parse_device_type_bot(self):
        ua = 'Googlebot/2.1 (+http://www.google.com/bot.html)'
        self.assertEqual(PageView.parse_device_type(ua), 'bot')

    def test_parse_browser(self):
        self.assertEqual(PageView.parse_browser('Mozilla/5.0 Chrome/120 Safari/537'), 'Chrome')
        self.assertEqual(PageView.parse_browser('Mozilla/5.0 Firefox/120'), 'Firefox')
        self.assertEqual(PageView.parse_browser('Mozilla/5.0 Edg/120'), 'Edge')
        self.assertEqual(PageView.parse_browser('Mozilla/5.0 Safari/605'), 'Safari')

    def test_parse_os(self):
        self.assertEqual(PageView.parse_os('Windows NT 10.0'), 'Windows')
        self.assertEqual(PageView.parse_os('Macintosh; Intel Mac OS'), 'macOS')
        self.assertEqual(PageView.parse_os('Linux x86_64'), 'Linux')
        self.assertEqual(PageView.parse_os('iPhone'), 'iOS')
        self.assertEqual(PageView.parse_os('Android 14'), 'Android')

    def test_extract_domain(self):
        self.assertEqual(PageView.extract_domain('https://google.com/search?q=test'), 'google.com')
        self.assertEqual(PageView.extract_domain(''), '')
        self.assertEqual(PageView.extract_domain('https://www.facebook.com/page'), 'www.facebook.com')

    def test_str_representation(self):
        pv = PageView.objects.create(
            path='/courses/',
            visitor_hash='a' * 64,
        )
        self.assertIn('/courses/', str(pv))

    def test_create_full_record(self):
        pv = PageView.objects.create(
            path='/',
            full_url='http://localhost/',
            visitor_hash=PageView.make_visitor_hash('127.0.0.1', 'TestAgent'),
            session_key='abc123',
            referrer='https://google.com/',
            referrer_domain='google.com',
            utm_source='google',
            utm_medium='cpc',
            utm_campaign='summer',
            user_agent='TestAgent',
            device_type='desktop',
            browser='Chrome',
            os='Windows',
        )
        self.assertEqual(pv.path, '/')
        self.assertEqual(pv.utm_source, 'google')
        self.assertFalse(pv.is_authenticated)


class AnalyticsMiddlewareTestCase(TestCase):
    """Test the analytics middleware tracks page views correctly."""

    def test_get_request_creates_pageview(self):
        """A normal GET to a public page should create a PageView."""
        self.client.get('/')
        self.assertTrue(PageView.objects.filter(path='/').exists())

    def test_post_request_not_tracked(self):
        """POST requests should not create page views."""
        initial_count = PageView.objects.count()
        self.client.post('/contact/', data={})
        self.assertEqual(PageView.objects.count(), initial_count)

    def test_static_paths_not_tracked(self):
        """Requests to /static/ should not be tracked."""
        self.client.get('/static/js/htmx.min.js')
        self.assertFalse(PageView.objects.filter(path__startswith='/static/').exists())

    def test_cms_paths_not_tracked(self):
        """CMS admin paths should not be tracked."""
        from django.conf import settings
        self.client.get(f'/{settings.CMS_URL_PREFIX}/login/')
        self.assertFalse(PageView.objects.filter(path__contains=settings.CMS_URL_PREFIX).exists())

    def test_htmx_requests_not_tracked(self):
        """AJAX/htmx partial requests should not be tracked."""
        self.client.get('/', HTTP_HX_REQUEST='true')
        self.assertFalse(PageView.objects.filter(path='/').exists())

    def test_visitor_hash_populated(self):
        """The visitor_hash should be a 64-char SHA-256 hex string."""
        self.client.get('/')
        pv = PageView.objects.first()
        self.assertIsNotNone(pv)
        self.assertEqual(len(pv.visitor_hash), 64)

    def test_referrer_and_utm_tracked(self):
        """Referrer and UTM params should be stored."""
        self.client.get(
            '/?utm_source=google&utm_medium=cpc&utm_campaign=spring',
            HTTP_REFERER='https://google.com/search',
        )
        pv = PageView.objects.first()
        self.assertEqual(pv.referrer_domain, 'google.com')
        self.assertEqual(pv.utm_source, 'google')
        self.assertEqual(pv.utm_medium, 'cpc')
        self.assertEqual(pv.utm_campaign, 'spring')

    def test_device_type_detected(self):
        """Mobile user-agent should be detected as mobile."""
        self.client.get('/', HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)')
        pv = PageView.objects.first()
        self.assertEqual(pv.device_type, 'mobile')


class AnalyticsViewTestCase(CMSTestMixin, TestCase):
    """Test the analytics dashboard view."""

    def test_analytics_requires_auth(self):
        response = self.client.get(reverse('cms:analytics'))
        self.assertEqual(response.status_code, 302)

    def test_analytics_renders(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Analytics')

    def test_analytics_with_data(self):
        """Analytics page should display data when page views exist."""
        # Create some page views
        for i in range(5):
            PageView.objects.create(
                path='/',
                visitor_hash=PageView.make_visitor_hash(f'1.2.3.{i}', 'Chrome'),
                device_type='desktop',
                browser='Chrome',
                os='Windows',
            )
        PageView.objects.create(
            path='/courses/',
            visitor_hash=PageView.make_visitor_hash('5.5.5.5', 'iPhone'),
            device_type='mobile',
            browser='Safari',
            os='iOS',
        )

        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_views'], 6)
        self.assertEqual(response.context['unique_visitors'], 6)

    def test_analytics_date_filter(self):
        """Date range query param should be respected."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics') + '?days=7')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['days'], 7)

    def test_analytics_invalid_days_defaults_to_30(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics') + '?days=999')
        self.assertEqual(response.context['days'], 30)

    def test_analytics_bot_excluded_from_total(self):
        """Bot page views should not count in total_views."""
        PageView.objects.create(
            path='/',
            visitor_hash='a' * 64,
            device_type='bot',
        )
        PageView.objects.create(
            path='/',
            visitor_hash='b' * 64,
            device_type='desktop',
        )
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics'))
        self.assertEqual(response.context['total_views'], 1)
        self.assertEqual(response.context['bot_count'], 1)


class AIReferrerTestCase(TestCase):
    """Test AI referrer classification and analytics."""

    def test_classify_chatgpt(self):
        self.assertEqual(PageView.classify_ai_referrer('chatgpt.com'), 'ChatGPT')
        self.assertEqual(PageView.classify_ai_referrer('chat.openai.com'), 'ChatGPT')

    def test_classify_gemini(self):
        self.assertEqual(PageView.classify_ai_referrer('gemini.google.com'), 'Gemini')
        self.assertEqual(PageView.classify_ai_referrer('bard.google.com'), 'Gemini')

    def test_classify_perplexity(self):
        self.assertEqual(PageView.classify_ai_referrer('perplexity.ai'), 'Perplexity')
        self.assertEqual(PageView.classify_ai_referrer('www.perplexity.ai'), 'Perplexity')

    def test_classify_claude(self):
        self.assertEqual(PageView.classify_ai_referrer('claude.ai'), 'Claude')

    def test_classify_copilot(self):
        self.assertEqual(PageView.classify_ai_referrer('copilot.microsoft.com'), 'Copilot')

    def test_classify_unknown_returns_empty(self):
        self.assertEqual(PageView.classify_ai_referrer('google.com'), '')
        self.assertEqual(PageView.classify_ai_referrer(''), '')
        self.assertEqual(PageView.classify_ai_referrer('facebook.com'), '')

    def test_classify_case_insensitive(self):
        self.assertEqual(PageView.classify_ai_referrer('ChatGPT.com'), 'ChatGPT')
        self.assertEqual(PageView.classify_ai_referrer('PERPLEXITY.AI'), 'Perplexity')


class AIAnalyticsViewTestCase(CMSTestMixin, TestCase):
    """Test AI traffic data in analytics view."""

    def test_ai_traffic_in_context(self):
        """Views from AI referrers must appear in ai_breakdown."""
        PageView.objects.create(
            path='/',
            visitor_hash=PageView.make_visitor_hash('1.1.1.1', 'Chrome'),
            referrer='https://chatgpt.com/c/abc123',
            referrer_domain='chatgpt.com',
            device_type='desktop',
        )
        PageView.objects.create(
            path='/courses/',
            visitor_hash=PageView.make_visitor_hash('2.2.2.2', 'Chrome'),
            referrer='https://chat.openai.com/',
            referrer_domain='chat.openai.com',
            device_type='desktop',
        )
        PageView.objects.create(
            path='/',
            visitor_hash=PageView.make_visitor_hash('3.3.3.3', 'Safari'),
            referrer='https://gemini.google.com/',
            referrer_domain='gemini.google.com',
            device_type='mobile',
        )
        # Non-AI referrer
        PageView.objects.create(
            path='/',
            visitor_hash=PageView.make_visitor_hash('4.4.4.4', 'Firefox'),
            referrer='https://google.com/search',
            referrer_domain='google.com',
            device_type='desktop',
        )

        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics'))
        self.assertEqual(response.context['ai_total'], 3)
        self.assertEqual(response.context['ai_visitors'], 3)
        # ChatGPT domains merged
        platforms = {a['platform'] for a in response.context['ai_breakdown']}
        self.assertIn('ChatGPT', platforms)
        self.assertIn('Gemini', platforms)
        chatgpt = next(a for a in response.context['ai_breakdown'] if a['platform'] == 'ChatGPT')
        self.assertEqual(chatgpt['count'], 2)  # chatgpt.com + chat.openai.com

    def test_ai_traffic_empty(self):
        """No AI referrers → ai_total = 0."""
        PageView.objects.create(
            path='/',
            visitor_hash='a' * 64,
            referrer_domain='google.com',
            device_type='desktop',
        )
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics'))
        self.assertEqual(response.context['ai_total'], 0)
        self.assertEqual(response.context['ai_breakdown'], [])

    def test_ai_top_pages_tracked(self):
        """AI landing pages should be tracked."""
        for path in ['/', '/courses/', '/courses/', '/contact/']:
            PageView.objects.create(
                path=path,
                visitor_hash=PageView.make_visitor_hash('1.1.1.1', 'Chrome'),
                referrer_domain='perplexity.ai',
                device_type='desktop',
            )
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics'))
        ai_pages = response.context['ai_top_pages']
        self.assertEqual(ai_pages[0]['path'], '/courses/')  # 2 visits = top
        self.assertEqual(ai_pages[0]['count'], 2)


class SearchEngineReferrerTestCase(TestCase):
    """Test search engine referrer classification."""

    def test_classify_google_variants(self):
        self.assertEqual(PageView.classify_search_engine('google.com'), 'Google')
        self.assertEqual(PageView.classify_search_engine('www.google.com'), 'Google')
        self.assertEqual(PageView.classify_search_engine('google.fr'), 'Google')
        self.assertEqual(PageView.classify_search_engine('google.dz'), 'Google')
        self.assertEqual(PageView.classify_search_engine('google.co.jp'), 'Google')

    def test_classify_bing(self):
        self.assertEqual(PageView.classify_search_engine('www.bing.com'), 'Bing')

    def test_classify_duckduckgo(self):
        self.assertEqual(PageView.classify_search_engine('duckduckgo.com'), 'DuckDuckGo')

    def test_classify_naver(self):
        self.assertEqual(PageView.classify_search_engine('search.naver.com'), 'Naver')

    def test_classify_baidu(self):
        self.assertEqual(PageView.classify_search_engine('www.baidu.com'), 'Baidu')

    def test_classify_unknown_returns_empty(self):
        self.assertEqual(PageView.classify_search_engine('facebook.com'), '')
        self.assertEqual(PageView.classify_search_engine('chatgpt.com'), '')


class SocialMediaReferrerTestCase(TestCase):
    """Test social media referrer classification."""

    def test_classify_facebook_variants(self):
        self.assertEqual(PageView.classify_social_media('www.facebook.com'), 'Facebook')
        self.assertEqual(PageView.classify_social_media('m.facebook.com'), 'Facebook')
        self.assertEqual(PageView.classify_social_media('l.facebook.com'), 'Facebook')

    def test_classify_instagram(self):
        self.assertEqual(PageView.classify_social_media('www.instagram.com'), 'Instagram')
        self.assertEqual(PageView.classify_social_media('l.instagram.com'), 'Instagram')

    def test_classify_twitter_x(self):
        self.assertEqual(PageView.classify_social_media('twitter.com'), 'X (Twitter)')
        self.assertEqual(PageView.classify_social_media('x.com'), 'X (Twitter)')
        self.assertEqual(PageView.classify_social_media('t.co'), 'X (Twitter)')

    def test_classify_linkedin(self):
        self.assertEqual(PageView.classify_social_media('www.linkedin.com'), 'LinkedIn')

    def test_classify_youtube(self):
        self.assertEqual(PageView.classify_social_media('www.youtube.com'), 'YouTube')
        self.assertEqual(PageView.classify_social_media('youtu.be'), 'YouTube')

    def test_classify_tiktok(self):
        self.assertEqual(PageView.classify_social_media('www.tiktok.com'), 'TikTok')

    def test_classify_whatsapp(self):
        self.assertEqual(PageView.classify_social_media('wa.me'), 'WhatsApp')

    def test_classify_unknown_returns_empty(self):
        self.assertEqual(PageView.classify_social_media('google.com'), '')
        self.assertEqual(PageView.classify_social_media('chatgpt.com'), '')


class ReferrerCategoryTestCase(TestCase):
    """Test the classify_referrer method that returns the category."""

    def test_direct(self):
        self.assertEqual(PageView.classify_referrer(''), 'direct')

    def test_ai(self):
        self.assertEqual(PageView.classify_referrer('chatgpt.com'), 'ai')

    def test_search(self):
        self.assertEqual(PageView.classify_referrer('google.com'), 'search')

    def test_social(self):
        self.assertEqual(PageView.classify_referrer('www.facebook.com'), 'social')

    def test_other(self):
        self.assertEqual(PageView.classify_referrer('randomsite.org'), 'other')


class SearchSocialAnalyticsViewTestCase(CMSTestMixin, TestCase):
    """Test search engine and social media traffic in analytics view."""

    def test_search_traffic_in_context(self):
        PageView.objects.create(
            path='/', visitor_hash='a' * 64,
            referrer_domain='google.com', device_type='desktop',
        )
        PageView.objects.create(
            path='/courses/', visitor_hash='b' * 64,
            referrer_domain='www.google.fr', device_type='desktop',
        )
        PageView.objects.create(
            path='/', visitor_hash='c' * 64,
            referrer_domain='www.bing.com', device_type='desktop',
        )
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics'))
        self.assertEqual(response.context['search_total'], 3)
        self.assertEqual(response.context['search_visitors'], 3)
        platforms = {s['platform'] for s in response.context['search_breakdown']}
        self.assertIn('Google', platforms)
        self.assertIn('Bing', platforms)
        google = next(s for s in response.context['search_breakdown'] if s['platform'] == 'Google')
        self.assertEqual(google['count'], 2)

    def test_social_traffic_in_context(self):
        PageView.objects.create(
            path='/', visitor_hash='a' * 64,
            referrer_domain='www.facebook.com', device_type='mobile',
        )
        PageView.objects.create(
            path='/', visitor_hash='b' * 64,
            referrer_domain='m.facebook.com', device_type='mobile',
        )
        PageView.objects.create(
            path='/courses/', visitor_hash='c' * 64,
            referrer_domain='www.instagram.com', device_type='mobile',
        )
        PageView.objects.create(
            path='/', visitor_hash='d' * 64,
            referrer_domain='t.co', device_type='desktop',
        )
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics'))
        self.assertEqual(response.context['social_total'], 4)
        platforms = {s['platform'] for s in response.context['social_breakdown']}
        self.assertIn('Facebook', platforms)
        self.assertIn('Instagram', platforms)
        self.assertIn('X (Twitter)', platforms)
        fb = next(s for s in response.context['social_breakdown'] if s['platform'] == 'Facebook')
        self.assertEqual(fb['count'], 2)  # www + m

    def test_empty_search_social(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('cms:analytics'))
        self.assertEqual(response.context['search_total'], 0)
        self.assertEqual(response.context['social_total'], 0)
        self.assertEqual(response.context['search_breakdown'], [])
        self.assertEqual(response.context['social_breakdown'], [])

