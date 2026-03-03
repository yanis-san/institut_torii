from django.test import TestCase, Client
from django.urls import reverse
from courses.models import Category, Language, CourseFormat, Cohort


class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_page_renders(self):
        response = self.client.get(reverse('home:home'))
        self.assertEqual(response.status_code, 200)

    def test_about_page_renders(self):
        response = self.client.get(reverse('home:about'))
        self.assertEqual(response.status_code, 200)

    def test_home_shows_featured_cohorts(self):
        cat = Category.objects.create(name='C', slug='c', type='language')
        fmt = CourseFormat.objects.create(name='F', slug='f')
        lang = Language.objects.create(name='Japonais', slug='japanese')
        Cohort.objects.create(
            category=cat, language=lang, format=fmt,
            name='Featured Cohort', slug='featured', price=16000,
            duration_value=3, is_featured=True, is_active=True,
        )
        Cohort.objects.create(
            category=cat, format=fmt,
            name='Not Featured', slug='not-featured', price=8000,
            duration_value=1, is_featured=False, is_active=True,
        )
        response = self.client.get(reverse('home:home'))
        self.assertContains(response, 'Featured Cohort')


class ContactViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_contact_page_renders(self):
        response = self.client.get(reverse('contact:contact'))
        self.assertEqual(response.status_code, 200)

    def test_contact_success_page_renders(self):
        response = self.client.get(reverse('contact:success'))
        self.assertEqual(response.status_code, 200)

    def test_contact_form_submission(self):
        response = self.client.post(reverse('contact:contact'), {
            'first_name': 'Amina',
            'last_name': 'Kebir',
            'email': 'amina@example.com',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('contact:success'))

    def test_contact_form_invalid(self):
        response = self.client.post(reverse('contact:contact'), {
            'first_name': '',
            'last_name': '',
            'email': 'not-an-email',
        })
        self.assertEqual(response.status_code, 200)


class LanguagePageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='C', slug='c', type='language')
        self.fmt = CourseFormat.objects.create(name='F', slug='f')

    def test_japanese_page_renders(self):
        Language.objects.create(name='Japonais', slug='japanese')
        response = self.client.get(reverse('courses:japanese'))
        self.assertEqual(response.status_code, 200)

    def test_chinese_page_renders(self):
        Language.objects.create(name='Chinois', slug='chinese')
        response = self.client.get(reverse('courses:chinese'))
        self.assertEqual(response.status_code, 200)

    def test_korean_page_renders(self):
        Language.objects.create(name='Coréen', slug='korean')
        response = self.client.get(reverse('courses:korean'))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_language_renders_gracefully(self):
        """Page renders with 200 even without DB data (graceful fallback)."""
        response = self.client.get(reverse('courses:japanese'))
        self.assertEqual(response.status_code, 200)


class WorkshopPageTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_artistic_workshop_page_renders(self):
        response = self.client.get(reverse('courses:workshops_artistic'))
        self.assertEqual(response.status_code, 200)

    def test_culinary_workshop_page_renders(self):
        response = self.client.get(reverse('courses:workshops_culinary'))
        self.assertEqual(response.status_code, 200)


class CohortAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='C', slug='c', type='language')
        self.fmt = CourseFormat.objects.create(name='F', slug='f')
        self.lang = Language.objects.create(name='J', slug='j')

    def test_api_returns_json(self):
        Cohort.objects.create(
            category=self.cat, language=self.lang, format=self.fmt,
            name='Test', slug='test', price=1000, duration_value=1,
        )
        response = self.client.get(reverse('courses:api_cohorts'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_api_filters_by_category(self):
        Cohort.objects.create(
            category=self.cat, format=self.fmt,
            name='C1', slug='c1', price=1000, duration_value=1,
        )
        cat2 = Category.objects.create(name='C2', slug='c2', type='artistic')
        Cohort.objects.create(
            category=cat2, format=self.fmt,
            name='C2', slug='c2c', price=1000, duration_value=1,
        )
        response = self.client.get(
            reverse('courses:api_cohorts') + f'?category={self.cat.id}'
        )
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'C1')
