from django.test import TestCase, Client
from django.urls import reverse
from contact.models import Prospect
from contact.forms import ProspectForm
from courses.models import Category, Language, CourseFormat, Cohort


class ProspectModelTest(TestCase):
    def test_create_prospect(self):
        p = Prospect.objects.create(
            first_name='Amina',
            last_name='Kebir',
            email='amina@example.com',
            phone='+213555123456',
        )
        # save() standardizes: last_name → UPPER, first_name → Title
        self.assertEqual(p.last_name, 'KEBIR')
        self.assertEqual(p.first_name, 'Amina')

    def test_name_standardization(self):
        """last_name → UPPER, first_name → Title Case"""
        p = Prospect.objects.create(
            first_name='  amina  ',
            last_name='  kebir  ',
            email='a@test.com',
        )
        self.assertEqual(p.last_name, 'KEBIR')
        self.assertEqual(p.first_name, 'Amina')

    def test_phone_standardization(self):
        """Phone: remove spaces/dashes, strip leading 0 after country code"""
        p = Prospect.objects.create(
            first_name='Test', last_name='User',
            email='t@test.com',
            phone='+2130666123456',
        )
        self.assertEqual(p.phone, '+213666123456')

    def test_phone_with_spaces(self):
        p = Prospect.objects.create(
            first_name='Test', last_name='User',
            email='t@test.com',
            phone='+213 666 12 34 56',
        )
        self.assertEqual(p.phone, '+213666123456')

    def test_prospect_with_interests(self):
        cat = Category.objects.create(name='Cours', slug='cours', type='language')
        lang = Language.objects.create(name='Japonais', slug='japanese')
        fmt = CourseFormat.objects.create(name='Groupe', slug='group')
        cohort = Cohort.objects.create(
            category=cat, language=lang, format=fmt,
            name='N5 Été', slug='n5-ete', price=16000, duration_value=3,
        )
        p = Prospect.objects.create(
            first_name='Mohamed',
            last_name='Rami',
            email='mohamed@example.com',
            interested_category=cat,
            interested_language=lang,
            interested_cohort=cohort,
        )
        self.assertEqual(p.interested_language.name, 'Japonais')
        self.assertEqual(p.interested_cohort.name, 'N5 Été')

    def test_contact_preferences_json(self):
        p = Prospect.objects.create(
            first_name='Sarah',
            last_name='Lari',
            email='sarah@example.com',
            contact_preferences=['email', 'whatsapp'],
        )
        self.assertIn('whatsapp', p.contact_preferences)

    def test_email_not_unique_allows_multiple(self):
        Prospect.objects.create(
            first_name='Test1', last_name='User', email='same@example.com',
        )
        Prospect.objects.create(
            first_name='Test2', last_name='User', email='same@example.com',
        )
        self.assertEqual(
            Prospect.objects.filter(email='same@example.com').count(), 2
        )

    def test_ordering_most_recent_first(self):
        p1 = Prospect.objects.create(
            first_name='A', last_name='A', email='a@test.com',
        )
        p2 = Prospect.objects.create(
            first_name='B', last_name='B', email='b@test.com',
        )
        prospects = list(Prospect.objects.all())
        self.assertEqual(prospects[0], p2)
        self.assertEqual(prospects[1], p1)

    def test_rating_field_defaults_blank(self):
        """Rating field defaults to empty string."""
        p = Prospect.objects.create(
            first_name='Test', last_name='User', email='r@test.com',
        )
        self.assertEqual(p.rating, '')

    def test_rating_choices_valid(self):
        """Can set valid rating values."""
        for value in ['hot', 'warm', 'cold', 'unqualified']:
            p = Prospect.objects.create(
                first_name='Test', last_name='User',
                email=f'{value}@test.com', rating=value,
            )
            self.assertEqual(p.rating, value)

    def test_rating_display(self):
        """Rating display returns correct French label."""
        p = Prospect.objects.create(
            first_name='Test', last_name='User',
            email='hot@test.com', rating='hot',
        )
        self.assertEqual(p.get_rating_display(), 'Sérieux')


class ProspectFormValidationTest(TestCase):
    """Test server-side form validation."""

    def _base_data(self, **overrides):
        data = {
            'first_name': 'Amina',
            'last_name': 'Kebir',
            'email': 'amina@example.com',
            'phone': '555123456',
            'country_code': '+213',
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = ProspectForm(data=self._base_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_latin_only_last_name_rejects_arabic(self):
        form = ProspectForm(data=self._base_data(last_name='كبير'))
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)

    def test_latin_only_first_name_rejects_chinese(self):
        form = ProspectForm(data=self._base_data(first_name='美奈'))
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_latin_accented_names_accepted(self):
        form = ProspectForm(data=self._base_data(
            first_name='François-Émile',
            last_name="O'Brien",
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_email_format(self):
        form = ProspectForm(data=self._base_data(email='notanemail'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_email_lowercased(self):
        form = ProspectForm(data=self._base_data(email='Test@Example.COM'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['email'], 'test@example.com')

    def test_phone_too_short(self):
        form = ProspectForm(data=self._base_data(phone='123'))
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_phone_merged_with_country_code(self):
        form = ProspectForm(data=self._base_data(
            phone='0666123456',
            country_code='+213',
        ))
        self.assertTrue(form.is_valid(), form.errors)
        # Leading 0 stripped, country code prepended
        self.assertEqual(form.cleaned_data['phone'], '+213666123456')

    def test_empty_phone_is_ok(self):
        form = ProspectForm(data=self._base_data(phone=''))
        self.assertTrue(form.is_valid(), form.errors)

    def test_names_with_digits_rejected(self):
        form = ProspectForm(data=self._base_data(first_name='Am1na'))
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)


class ContactViewTest(TestCase):
    def test_contact_page_renders(self):
        response = self.client.get(reverse('contact:contact'))
        self.assertEqual(response.status_code, 200)

    def test_contact_success_page_renders(self):
        response = self.client.get(reverse('contact:success'))
        self.assertEqual(response.status_code, 200)

    def test_successful_submission_redirects(self):
        response = self.client.post(reverse('contact:contact'), {
            'first_name': 'Amina',
            'last_name': 'Kebir',
            'email': 'amina@example.com',
            'phone': '555123456',
            'country_code': '+213',
        })
        self.assertRedirects(response, reverse('contact:success'))
        self.assertEqual(Prospect.objects.count(), 1)
        p = Prospect.objects.first()
        self.assertEqual(p.last_name, 'KEBIR')
        self.assertEqual(p.phone, '+213555123456')

    def test_invalid_submission_stays_on_page(self):
        response = self.client.post(reverse('contact:contact'), {
            'first_name': '',
            'last_name': '',
            'email': 'bad-email',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Prospect.objects.count(), 0)
