import io
from datetime import timedelta

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from courses.models import Category, Language, CourseFormat, Cohort
from registration.models import Enrollment
from registration.forms import EnrollmentForm


def _make_test_image(name='receipt.jpg', fmt='JPEG'):
    """Generate a tiny in-memory test image."""
    img = Image.new('RGB', (100, 100), color='red')
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type=f'image/{fmt.lower()}')


def _create_open_cohort(**kwargs):
    """Helper: create a Cohort with registration open."""
    cat = Category.objects.create(name='Cours', slug='cours', type='language')
    lang = Language.objects.create(name='Japonais', slug='japanese')
    fmt = CourseFormat.objects.create(name='Groupe', slug='group')
    defaults = dict(
        category=cat, language=lang, format=fmt,
        name='N5 Automne', slug='n5-automne',
        price=16000, duration_value=3,
        registration_open_date=timezone.now() - timedelta(days=1),
        registration_close_date=timezone.now() + timedelta(days=30),
        max_capacity=20,
        min_students=5,
        payment_instructions='CCP: 123456 clé 78\nRIP: 007999...',
    )
    defaults.update(kwargs)
    return Cohort.objects.create(**defaults)


# ──────────────────────────────────────────────
# Model Tests
# ──────────────────────────────────────────────


class EnrollmentModelTest(TestCase):
    def setUp(self):
        self.cohort = _create_open_cohort()

    def test_create_enrollment(self):
        e = Enrollment.objects.create(
            first_name='Amina', last_name='Kebir',
            email='amina@test.com', phone='+213666123456',
            cohort=self.cohort,
            payment_receipt=_make_test_image(),
        )
        self.assertEqual(e.status, 'pending')
        self.assertEqual(len(e.enrollment_code), 8)
        self.assertEqual(e.last_name, 'KEBIR')
        self.assertEqual(e.first_name, 'Amina')

    def test_enrollment_code_unique(self):
        e1 = Enrollment.objects.create(
            first_name='A', last_name='A', email='a@test.com',
            cohort=self.cohort, payment_receipt=_make_test_image(),
        )
        e2 = Enrollment.objects.create(
            first_name='B', last_name='B', email='b@test.com',
            cohort=self.cohort, payment_receipt=_make_test_image(),
        )
        self.assertNotEqual(e1.enrollment_code, e2.enrollment_code)

    def test_confirm_method(self):
        e = Enrollment.objects.create(
            first_name='Test', last_name='User', email='t@test.com',
            cohort=self.cohort, payment_receipt=_make_test_image(),
        )
        e.confirm()
        e.refresh_from_db()
        self.assertEqual(e.status, 'confirmed')
        self.assertIsNotNone(e.confirmed_at)

    def test_reject_method(self):
        e = Enrollment.objects.create(
            first_name='Test', last_name='User', email='t@test.com',
            cohort=self.cohort, payment_receipt=_make_test_image(),
        )
        e.reject(reason='Reçu illisible')
        e.refresh_from_db()
        self.assertEqual(e.status, 'rejected')
        self.assertEqual(e.rejection_reason, 'Reçu illisible')

    def test_name_standardization(self):
        e = Enrollment.objects.create(
            first_name='  amina  ', last_name='  kebir  ',
            email='a@test.com', cohort=self.cohort,
            payment_receipt=_make_test_image(),
        )
        self.assertEqual(e.last_name, 'KEBIR')
        self.assertEqual(e.first_name, 'Amina')

    def test_phone_standardization(self):
        e = Enrollment.objects.create(
            first_name='T', last_name='U', email='t@test.com',
            phone='+213 0666 12 34 56',
            cohort=self.cohort, payment_receipt=_make_test_image(),
        )
        self.assertEqual(e.phone, '+213666123456')

    @override_settings(MEDIA_ROOT=None)
    def test_receipt_compressed_to_webp_no_resize(self):
        """Payment receipt is converted to WebP without resizing."""
        import tempfile, shutil, os
        tmpdir = tempfile.mkdtemp()
        try:
            with self.settings(MEDIA_ROOT=tmpdir):
                # Create a large PNG image (2000x3000)
                big_img = Image.new('RGB', (2000, 3000), color='blue')
                buf = io.BytesIO()
                big_img.save(buf, format='PNG')
                buf.seek(0)
                receipt = SimpleUploadedFile('big_receipt.png', buf.read(), content_type='image/png')

                e = Enrollment.objects.create(
                    first_name='Test', last_name='Optim',
                    email='optim@test.com', cohort=self.cohort,
                    payment_receipt=receipt,
                )
                # File should now be WebP
                self.assertTrue(e.payment_receipt.name.endswith('.webp'))
                # Dimensions must be preserved (no resize)
                saved_img = Image.open(e.payment_receipt.path)
                self.assertEqual(saved_img.width, 2000)
                self.assertEqual(saved_img.height, 3000)
                saved_img.close()
                # Close Django's file handle before cleanup
                e.payment_receipt.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ──────────────────────────────────────────────
# Form Tests
# ──────────────────────────────────────────────


class EnrollmentFormTest(TestCase):
    def setUp(self):
        self.cohort = _create_open_cohort()

    def _base_data(self, **overrides):
        data = {
            'first_name': 'Amina',
            'last_name': 'Kebir',
            'email': 'amina@test.com',
            'phone': '666123456',
            'country_code': '+213',
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = EnrollmentForm(
            data=self._base_data(),
            files={'payment_receipt': _make_test_image()},
            cohort=self.cohort,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_arabic_name(self):
        form = EnrollmentForm(
            data=self._base_data(last_name='كبير'),
            files={'payment_receipt': _make_test_image()},
            cohort=self.cohort,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)

    def test_rejects_without_receipt(self):
        form = EnrollmentForm(
            data=self._base_data(),
            files={},
            cohort=self.cohort,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('payment_receipt', form.errors)

    def test_phone_merged_with_country_code(self):
        form = EnrollmentForm(
            data=self._base_data(phone='0666123456', country_code='+213'),
            files={'payment_receipt': _make_test_image()},
            cohort=self.cohort,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['phone'], '+213666123456')


# ──────────────────────────────────────────────
# Cohort Model Tests
# ──────────────────────────────────────────────


class CohortRegistrationTest(TestCase):
    def test_registration_open(self):
        cohort = _create_open_cohort()
        self.assertTrue(cohort.is_registration_open)

    def test_registration_closed_past(self):
        cohort = _create_open_cohort(
            registration_close_date=timezone.now() - timedelta(hours=1),
        )
        self.assertFalse(cohort.is_registration_open)

    def test_registration_closed_no_dates(self):
        cat = Category.objects.create(name='Cours', slug='cours', type='language')
        lang = Language.objects.create(name='Japonais', slug='japanese')
        fmt = CourseFormat.objects.create(name='Groupe', slug='group')
        cohort = Cohort.objects.create(
            category=cat, language=lang, format=fmt,
            name='No dates', slug='no-dates',
            price=10000, duration_value=2,
        )
        self.assertFalse(cohort.is_registration_open)


# ──────────────────────────────────────────────
# View Tests
# ──────────────────────────────────────────────


@override_settings(MEDIA_ROOT='/tmp/test_media/')
class RegistrationViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cohort = _create_open_cohort()

    def test_cohort_list_renders(self):
        response = self.client.get(reverse('registration:cohort_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'N5 Automne')

    def test_enroll_page_renders(self):
        response = self.client.get(
            reverse('registration:enroll', kwargs={'slug': 'n5-automne'})
        )
        self.assertEqual(response.status_code, 200)

    def test_enroll_closed_shows_closed_page(self):
        self.cohort.registration_close_date = timezone.now() - timedelta(hours=1)
        self.cohort.save()
        response = self.client.get(
            reverse('registration:enroll', kwargs={'slug': 'n5-automne'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inscriptions fermées')

    def test_successful_enrollment(self):
        response = self.client.post(
            reverse('registration:enroll', kwargs={'slug': 'n5-automne'}),
            data={
                'first_name': 'Amina',
                'last_name': 'Kebir',
                'email': 'amina@test.com',
                'phone': '666123456',
                'country_code': '+213',
                'payment_receipt': _make_test_image(),
            },
        )
        self.assertEqual(Enrollment.objects.count(), 1)
        enrollment = Enrollment.objects.first()
        self.assertRedirects(
            response,
            reverse('registration:success', kwargs={'code': enrollment.enrollment_code}),
        )

    def test_success_page_shows_code(self):
        e = Enrollment.objects.create(
            first_name='Test', last_name='User', email='t@test.com',
            cohort=self.cohort, payment_receipt=_make_test_image(),
        )
        response = self.client.get(
            reverse('registration:success', kwargs={'code': e.enrollment_code})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, e.enrollment_code)

    def test_check_status_page_renders(self):
        response = self.client.get(reverse('registration:check_status'))
        self.assertEqual(response.status_code, 200)

    def test_check_status_with_valid_code(self):
        e = Enrollment.objects.create(
            first_name='Test', last_name='User', email='t@test.com',
            cohort=self.cohort, payment_receipt=_make_test_image(),
        )
        response = self.client.post(
            reverse('registration:check_status'),
            {'code': e.enrollment_code},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'USER')  # last_name uppercased
        self.assertContains(response, 'Test')  # first_name title-cased

    def test_check_status_invalid_code(self):
        response = self.client.post(
            reverse('registration:check_status'),
            {'code': 'DEADBEEF'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'introuvable')

    def test_cohort_status_api(self):
        Enrollment.objects.create(
            first_name='A', last_name='A', email='a@test.com',
            cohort=self.cohort, payment_receipt=_make_test_image(),
            status='confirmed',
        )
        Enrollment.objects.create(
            first_name='B', last_name='B', email='b@test.com',
            cohort=self.cohort, payment_receipt=_make_test_image(),
            status='pending',
        )
        response = self.client.get(
            reverse('registration:cohort_status_api', kwargs={'slug': 'n5-automne'})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['confirmed'], 1)
        self.assertEqual(data['pending'], 1)
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['min_students'], 5)

    def test_cohort_status_api_closed_returns_403(self):
        self.cohort.registration_close_date = timezone.now() - timedelta(hours=1)
        self.cohort.save()
        response = self.client.get(
            reverse('registration:cohort_status_api', kwargs={'slug': 'n5-automne'})
        )
        self.assertEqual(response.status_code, 403)

    def test_check_status_shows_frozen_stats_when_closed(self):
        e = Enrollment.objects.create(
            first_name='Test', last_name='User', email='t@test.com',
            cohort=self.cohort, payment_receipt=_make_test_image(),
        )
        # Close registration
        self.cohort.registration_close_date = timezone.now() - timedelta(hours=1)
        self.cohort.save()
        response = self.client.post(
            reverse('registration:check_status'),
            {'code': e.enrollment_code},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'État final du groupe')
        self.assertNotContains(response, 'temps réel')
