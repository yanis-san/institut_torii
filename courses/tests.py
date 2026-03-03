from django.test import TestCase
from courses.models import Category, Language, CourseFormat, Cohort, CohortSchedule
from datetime import time, date


class CategoryModelTest(TestCase):
    def test_create_category(self):
        cat = Category.objects.create(
            name='Cours linguistique',
            slug='cours-linguistique',
            type=Category.Type.LANGUAGE_COURSE,
        )
        self.assertEqual(str(cat), 'Cours linguistique')
        self.assertEqual(cat.type, 'language')

    def test_ordering_by_order_then_name(self):
        cat_b = Category.objects.create(name='B', slug='b', type='language', order=1)
        cat_a = Category.objects.create(name='A', slug='a', type='artistic', order=0)
        cats = list(Category.objects.all())
        self.assertEqual(cats[0], cat_a)
        self.assertEqual(cats[1], cat_b)


class LanguageModelTest(TestCase):
    def test_create_language(self):
        lang = Language.objects.create(
            name='Japonais', slug='japanese', flag_emoji='🇯🇵',
        )
        self.assertEqual(str(lang), 'Japonais')

    def test_slug_unique(self):
        Language.objects.create(name='Japonais', slug='japanese')
        with self.assertRaises(Exception):
            Language.objects.create(name='Japonais 2', slug='japanese')


class CourseFormatModelTest(TestCase):
    def test_create_format(self):
        fmt = CourseFormat.objects.create(
            name='En ligne groupe',
            slug='en-ligne-groupe',
            is_online=True,
            is_individual=False,
        )
        self.assertEqual(str(fmt), 'En ligne groupe')
        self.assertTrue(fmt.is_online)
        self.assertFalse(fmt.is_individual)


class CohortModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Cours linguistique',
            slug='cours-linguistique',
            type=Category.Type.LANGUAGE_COURSE,
        )
        self.language = Language.objects.create(
            name='Japonais', slug='japanese',
        )
        self.format = CourseFormat.objects.create(
            name='Présentiel groupe',
            slug='in-person-group',
        )

    def test_create_cohort(self):
        cohort = Cohort.objects.create(
            category=self.category,
            language=self.language,
            format=self.format,
            name='Japonais N5 - Session Été 2026',
            slug='japanese-n5-summer-2026',
            price=16000,
            duration_value=3,
            duration_unit=Cohort.DurationUnit.MONTHS,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 31),
        )
        self.assertEqual(str(cohort), 'Japonais N5 - Session Été 2026')
        self.assertEqual(cohort.duration_display, '3 mois')

    def test_duration_display_weeks(self):
        cohort = Cohort.objects.create(
            category=self.category,
            format=self.format,
            name='Stage intensif',
            slug='stage-intensif',
            price=8000,
            duration_value=4,
            duration_unit=Cohort.DurationUnit.WEEKS,
        )
        self.assertEqual(cohort.duration_display, '4 semaines')

    def test_featured_cohort(self):
        Cohort.objects.create(
            category=self.category,
            format=self.format,
            name='Featured',
            slug='featured',
            price=16000,
            duration_value=3,
            is_featured=True,
        )
        Cohort.objects.create(
            category=self.category,
            format=self.format,
            name='Not Featured',
            slug='not-featured',
            price=16000,
            duration_value=3,
            is_featured=False,
        )
        featured = Cohort.objects.filter(is_featured=True)
        self.assertEqual(featured.count(), 1)
        self.assertEqual(featured.first().name, 'Featured')

    def test_language_nullable_for_workshops(self):
        workshop_cat = Category.objects.create(
            name='Atelier artistique',
            slug='atelier-artistique',
            type=Category.Type.ARTISTIC_WORKSHOP,
        )
        cohort = Cohort.objects.create(
            category=workshop_cat,
            language=None,
            format=self.format,
            name='Calligraphie',
            slug='calligraphie',
            price=5000,
            duration_value=1,
        )
        self.assertIsNone(cohort.language)


class CohortScheduleModelTest(TestCase):
    def setUp(self):
        cat = Category.objects.create(name='C', slug='c', type='language')
        fmt = CourseFormat.objects.create(name='F', slug='f')
        self.cohort = Cohort.objects.create(
            category=cat, format=fmt,
            name='Test', slug='test', price=1000, duration_value=1,
        )

    def test_create_schedule(self):
        sched = CohortSchedule.objects.create(
            cohort=self.cohort,
            day=CohortSchedule.DayOfWeek.TUESDAY,
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
        self.assertIn('Mardi', str(sched))
        self.assertIn('14:00', str(sched))

    def test_multiple_days_per_cohort(self):
        CohortSchedule.objects.create(
            cohort=self.cohort,
            day=CohortSchedule.DayOfWeek.MONDAY,
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
        CohortSchedule.objects.create(
            cohort=self.cohort,
            day=CohortSchedule.DayOfWeek.THURSDAY,
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
        self.assertEqual(self.cohort.schedules.count(), 2)

    def test_unique_together(self):
        CohortSchedule.objects.create(
            cohort=self.cohort,
            day=CohortSchedule.DayOfWeek.MONDAY,
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
        with self.assertRaises(Exception):
            CohortSchedule.objects.create(
                cohort=self.cohort,
                day=CohortSchedule.DayOfWeek.MONDAY,
                start_time=time(10, 0),
                end_time=time(13, 0),
            )
