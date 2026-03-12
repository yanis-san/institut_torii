from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Appointment, AppointmentCategory, TimeSlot


class AppointmentCategoryModelTest(TestCase):

    def test_str(self):
        cat = AppointmentCategory.objects.create(name='Test de niveau', slug='test-de-niveau')
        self.assertEqual(str(cat), 'Test de niveau')


class TimeSlotModelTest(TestCase):

    def setUp(self):
        self.cat = AppointmentCategory.objects.create(name='Cat', slug='cat')
        self.slot = TimeSlot.objects.create(
            category=self.cat,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(10, 30),
            max_bookings=2,
        )

    def test_str(self):
        self.assertIn('10:00', str(self.slot))

    def test_is_available_when_empty(self):
        self.assertTrue(self.slot.is_available)

    def test_remaining_spots(self):
        self.assertEqual(self.slot.remaining_spots, 2)

    def test_is_available_when_full(self):
        for _ in range(2):
            Appointment.objects.create(
                timeslot=self.slot,
                first_name='A', last_name='B',
                email='a@b.com', status=Appointment.Status.CONFIRMED,
            )
        self.assertFalse(self.slot.is_available)
        self.assertEqual(self.slot.remaining_spots, 0)


class AppointmentModelTest(TestCase):

    def setUp(self):
        self.cat = AppointmentCategory.objects.create(name='Cat', slug='cat')
        self.slot = TimeSlot.objects.create(
            category=self.cat,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(10, 30),
        )

    def test_auto_code(self):
        appt = Appointment.objects.create(
            timeslot=self.slot,
            first_name='Jean', last_name='Dupont',
            email='jean@test.com',
        )
        self.assertEqual(len(appt.appointment_code), 8)

    def test_category_property(self):
        appt = Appointment.objects.create(
            timeslot=self.slot,
            first_name='Jean', last_name='Dupont',
            email='jean@test.com',
        )
        self.assertEqual(appt.category, self.cat)


# ──────────────────────────────────────────────
# Public views
# ──────────────────────────────────────────────

class PublicViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.cat = AppointmentCategory.objects.create(
            name='Test de niveau', slug='test-de-niveau', is_active=True,
        )
        self.slot = TimeSlot.objects.create(
            category=self.cat,
            date=date.today() + timedelta(days=1),
            start_time=time(14, 0),
            end_time=time(14, 30),
            max_bookings=2,
        )

    def test_book_page(self):
        response = self.client.get(reverse('appointments:book'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test de niveau')

    def test_available_dates(self):
        response = self.client.get(reverse('appointments:available_dates', args=['test-de-niveau']))
        self.assertEqual(response.status_code, 200)

    def test_available_slots(self):
        target_date = (date.today() + timedelta(days=1)).isoformat()
        response = self.client.get(
            reverse('appointments:available_slots', args=['test-de-niveau']),
            {'date': target_date},
        )
        self.assertEqual(response.status_code, 200)

    def test_booking_form(self):
        response = self.client.get(reverse('appointments:booking_form', args=[self.slot.pk]))
        self.assertEqual(response.status_code, 200)

    def test_confirm_booking(self):
        response = self.client.post(reverse('appointments:confirm_booking', args=[self.slot.pk]), {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'jean@test.com',
            'phone': '0555123456',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Appointment.objects.count(), 1)
        appt = Appointment.objects.first()
        self.assertEqual(appt.first_name, 'Jean')
        self.assertEqual(appt.timeslot, self.slot)

    def test_confirm_booking_invalid_form(self):
        response = self.client.post(reverse('appointments:confirm_booking', args=[self.slot.pk]), {
            'first_name': '',
            'last_name': '',
            'email': 'invalid',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_confirm_booking_full_slot(self):
        for _ in range(2):
            Appointment.objects.create(
                timeslot=self.slot, first_name='A', last_name='B',
                email='a@b.com', status=Appointment.Status.CONFIRMED,
            )
        response = self.client.post(reverse('appointments:confirm_booking', args=[self.slot.pk]), {
            'first_name': 'Jean', 'last_name': 'Dupont',
            'email': 'jean@test.com',
        })
        self.assertEqual(response.status_code, 200)
        # Should not create another appointment
        self.assertEqual(Appointment.objects.count(), 2)

    def test_success_page(self):
        appt = Appointment.objects.create(
            timeslot=self.slot,
            first_name='Jean', last_name='Dupont',
            email='jean@test.com',
        )
        response = self.client.get(reverse('appointments:success', args=[appt.appointment_code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, appt.appointment_code)


# ──────────────────────────────────────────────
# CMS views
# ──────────────────────────────────────────────

class CMSAppointmentViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='testpass123')
        self.client.login(username='admin', password='testpass123')
        self.cat = AppointmentCategory.objects.create(
            name='Entretien', slug='entretien', is_active=True,
        )
        self.slot = TimeSlot.objects.create(
            category=self.cat,
            date=date.today() + timedelta(days=3),
            start_time=time(9, 0),
            end_time=time(9, 30),
            max_bookings=1,
        )
        self.appt = Appointment.objects.create(
            timeslot=self.slot,
            first_name='Marie', last_name='Martin',
            email='marie@test.com',
        )

    def test_appointment_list(self):
        response = self.client.get(reverse('cms:appointment_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.appt.appointment_code)

    def test_appointment_list_filter_status(self):
        response = self.client.get(reverse('cms:appointment_list'), {'status': 'confirmed'})
        self.assertEqual(response.status_code, 200)

    def test_appointment_list_search(self):
        response = self.client.get(reverse('cms:appointment_list'), {'q': 'Marie'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Marie')

    def test_appointment_detail(self):
        response = self.client.get(reverse('cms:appointment_detail', args=[self.appt.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Marie')

    def test_appointment_update_status(self):
        response = self.client.post(reverse('cms:appointment_detail', args=[self.appt.pk]), {
            'status': 'completed',
            'admin_notes': 'Bien passé',
        })
        self.assertEqual(response.status_code, 302)
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status, 'completed')
        self.assertEqual(self.appt.admin_notes, 'Bien passé')

    def test_appointment_delete(self):
        response = self.client.post(reverse('cms:appointment_delete', args=[self.appt.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_category_list(self):
        response = self.client.get(reverse('cms:appointment_category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Entretien')

    def test_category_create(self):
        response = self.client.post(reverse('cms:appointment_category_create'), {
            'name': 'Consultation',
            'slug': 'consultation',
            'duration_minutes': 45,
            'is_active': True,
            'order': 1,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AppointmentCategory.objects.filter(slug='consultation').exists())

    def test_category_edit(self):
        response = self.client.post(reverse('cms:appointment_category_edit', args=[self.cat.pk]), {
            'name': 'Entretien modifié',
            'slug': 'entretien',
            'duration_minutes': 30,
            'is_active': True,
            'order': 0,
        })
        self.assertEqual(response.status_code, 302)
        self.cat.refresh_from_db()
        self.assertEqual(self.cat.name, 'Entretien modifié')

    def test_category_delete(self):
        cat2 = AppointmentCategory.objects.create(name='Temp', slug='temp')
        response = self.client.post(reverse('cms:appointment_category_delete', args=[cat2.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(AppointmentCategory.objects.filter(pk=cat2.pk).exists())

    def test_timeslot_create(self):
        response = self.client.post(reverse('cms:timeslot_create', args=[self.cat.pk]), {
            'date': (date.today() + timedelta(days=5)).isoformat(),
            'start_time': '15:00',
            'end_time': '15:30',
            'max_bookings': 3,
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TimeSlot.objects.filter(category=self.cat).count(), 2)

    def test_timeslot_edit(self):
        response = self.client.post(
            reverse('cms:timeslot_edit', args=[self.cat.pk, self.slot.pk]),
            {
                'date': self.slot.date.isoformat(),
                'start_time': '10:00',
                'end_time': '10:30',
                'max_bookings': 5,
                'is_active': True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.max_bookings, 5)

    def test_timeslot_delete(self):
        slot2 = TimeSlot.objects.create(
            category=self.cat, date=date.today() + timedelta(days=10),
            start_time=time(11, 0), end_time=time(11, 30),
        )
        response = self.client.post(reverse('cms:timeslot_delete', args=[slot2.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TimeSlot.objects.filter(pk=slot2.pk).exists())

    def test_requires_auth(self):
        """CMS views redirect when not authenticated."""
        self.client.logout()
        response = self.client.get(reverse('cms:appointment_list'))
        self.assertEqual(response.status_code, 302)
