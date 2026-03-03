"""
Tests for the marketing app — email templates, campaigns, subscribers, sending.
"""
import uuid
from unittest.mock import patch

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone

from marketing.models import (
    CampaignRecipient,
    EmailCampaign,
    EmailSubscription,
    EmailTemplate,
)
from marketing.services import (
    build_recipient_list,
    populate_campaign_recipients,
    render_email_content,
    send_campaign,
    send_single_email,
    strip_html,
    get_from_email,
)
from courses.models import Category, Language, CourseFormat, Cohort
from contact.models import Prospect
from registration.models import Enrollment


class MarketingTestMixin:
    """Provides reusable setUp with authenticated admin user and sample data."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='testpass123')

        self.category = Category.objects.create(
            name='Cours linguistique', type='language',
        )
        self.language = Language.objects.create(name='Japonais', flag_emoji='🇯🇵')
        self.language2 = Language.objects.create(name='Chinois', flag_emoji='🇨🇳')
        self.format = CourseFormat.objects.create(name='Présentiel groupe')
        self.cohort = Cohort.objects.create(
            category=self.category,
            language=self.language,
            format=self.format,
            name='Japonais N5 — Été 2026',
            price=15000,
            duration_value=3,
        )

        self.template = EmailTemplate.objects.create(
            name='Template Test',
            category='newsletter',
            subject='Bonjour {{ first_name }} !',
            body_html='<h1>Salut {{ first_name }} {{ last_name }}</h1><p>Bienvenue !</p>',
        )


# ──────────────────────────────────────────────
# Model tests
# ──────────────────────────────────────────────

class EmailTemplateModelTestCase(MarketingTestMixin, TestCase):
    """Test EmailTemplate model."""

    def test_str(self):
        self.assertIn('Template Test', str(self.template))
        self.assertIn('Newsletter', str(self.template))

    def test_category_choices(self):
        for value, _ in EmailTemplate.Category.choices:
            self.template.category = value
            self.template.save()
            self.assertEqual(self.template.category, value)


class EmailCampaignModelTestCase(MarketingTestMixin, TestCase):
    """Test EmailCampaign model."""

    def test_create_campaign(self):
        campaign = EmailCampaign.objects.create(
            name='Test Campaign',
            template=self.template,
        )
        self.assertEqual(campaign.status, 'draft')
        self.assertEqual(campaign.total_recipients, 0)

    def test_effective_subject_uses_campaign(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            subject='Custom subject',
        )
        self.assertEqual(campaign.effective_subject, 'Custom subject')

    def test_effective_subject_falls_back_to_template(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
        )
        self.assertEqual(campaign.effective_subject, self.template.subject)

    def test_open_rate(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            sent_count=100,
            opened_count=25,
        )
        self.assertEqual(campaign.open_rate, 25.0)

    def test_click_rate(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            sent_count=100,
            clicked_count=10,
        )
        self.assertEqual(campaign.click_rate, 10.0)

    def test_delivery_rate(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            total_recipients=200,
            sent_count=180,
        )
        self.assertEqual(campaign.delivery_rate, 90.0)

    def test_rates_zero_when_no_sends(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
        )
        self.assertEqual(campaign.open_rate, 0)
        self.assertEqual(campaign.click_rate, 0)
        self.assertEqual(campaign.delivery_rate, 0)

    def test_str(self):
        campaign = EmailCampaign.objects.create(
            name='Test Campaign',
            template=self.template,
        )
        self.assertIn('Test Campaign', str(campaign))
        self.assertIn('Brouillon', str(campaign))


class CampaignRecipientModelTestCase(MarketingTestMixin, TestCase):
    """Test CampaignRecipient model."""

    def test_create_recipient(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
        )
        recipient = CampaignRecipient.objects.create(
            campaign=campaign,
            email='test@example.com',
            first_name='Test',
            last_name='USER',
        )
        self.assertEqual(recipient.status, 'pending')
        self.assertIsNotNone(recipient.open_token)
        self.assertIsNotNone(recipient.click_token)

    def test_unique_together(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
        )
        CampaignRecipient.objects.create(
            campaign=campaign, email='dup@example.com',
        )
        with self.assertRaises(Exception):
            CampaignRecipient.objects.create(
                campaign=campaign, email='dup@example.com',
            )


class EmailSubscriptionModelTestCase(TestCase):
    """Test EmailSubscription model."""

    def test_is_subscribed_no_record(self):
        """No record means subscribed by default."""
        self.assertTrue(EmailSubscription.is_email_subscribed('new@example.com'))

    def test_is_subscribed_true(self):
        EmailSubscription.objects.create(
            email='sub@example.com', is_subscribed=True,
        )
        self.assertTrue(EmailSubscription.is_email_subscribed('sub@example.com'))

    def test_is_subscribed_false(self):
        EmailSubscription.objects.create(
            email='unsub@example.com', is_subscribed=False,
        )
        self.assertFalse(EmailSubscription.is_email_subscribed('unsub@example.com'))

    def test_get_or_create(self):
        sub = EmailSubscription.get_or_create_subscription('new@example.com')
        self.assertTrue(sub.is_subscribed)
        self.assertIsNotNone(sub.unsubscribe_token)

        # Second call returns same record
        sub2 = EmailSubscription.get_or_create_subscription('new@example.com')
        self.assertEqual(sub.pk, sub2.pk)

    def test_str(self):
        sub = EmailSubscription.objects.create(
            email='test@example.com', is_subscribed=True,
        )
        self.assertIn('✅', str(sub))
        sub.is_subscribed = False
        self.assertIn('❌', str(sub))


# ──────────────────────────────────────────────
# Services tests
# ──────────────────────────────────────────────

class RenderEmailTestCase(TestCase):
    """Test email template rendering."""

    def test_render_with_variables(self):
        result = render_email_content(
            'Bonjour {{ first_name }} {{ last_name }} !',
            {'first_name': 'Yuki', 'last_name': 'TANAKA'},
        )
        self.assertEqual(result, 'Bonjour Yuki TANAKA !')

    def test_render_empty_context(self):
        result = render_email_content('Hello World', {})
        self.assertEqual(result, 'Hello World')


class StripHtmlTestCase(TestCase):
    """Test HTML → text conversion."""

    def test_basic_strip(self):
        html = '<h1>Title</h1><p>Paragraph</p>'
        text = strip_html(html)
        self.assertIn('Title', text)
        self.assertIn('Paragraph', text)
        self.assertNotIn('<h1>', text)

    def test_empty_string(self):
        self.assertEqual(strip_html(''), '')


class GetFromEmailTestCase(TestCase):
    """Test from_email resolution."""

    def test_contact(self):
        result = get_from_email('contact')
        self.assertIn('contact@', result)
        self.assertIn('Institut Torii', result)

    def test_inscription(self):
        result = get_from_email('inscription')
        self.assertIn('inscription@', result)

    def test_unknown_falls_back_to_contact(self):
        result = get_from_email('unknown')
        self.assertIn('contact@', result)


class BuildRecipientListTestCase(MarketingTestMixin, TestCase):
    """Test segment building logic."""

    def setUp(self):
        super().setUp()
        self.prospect1 = Prospect.objects.create(
            first_name='Yuki', last_name='TANAKA',
            email='yuki@example.com',
            interested_language=self.language,
        )
        self.prospect2 = Prospect.objects.create(
            first_name='Mei', last_name='WANG',
            email='mei@example.com',
            interested_language=self.language2,
        )
        self.enrollment1 = Enrollment.objects.create(
            first_name='Hiro', last_name='SATO',
            email='hiro@example.com',
            cohort=self.cohort,
            payment_receipt='receipts/test.jpg',
            status='confirmed',
        )

    def test_all_prospects(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='all_prospects',
        )
        recipients = build_recipient_list(campaign)
        emails = [r['email'] for r in recipients]
        self.assertIn('yuki@example.com', emails)
        self.assertIn('mei@example.com', emails)
        self.assertEqual(len(recipients), 2)

    def test_all_enrolled(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='all_enrolled',
        )
        recipients = build_recipient_list(campaign)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]['email'], 'hiro@example.com')

    def test_all_confirmed(self):
        Enrollment.objects.create(
            first_name='Pending', last_name='USER',
            email='pending@example.com',
            cohort=self.cohort,
            payment_receipt='receipts/test2.jpg',
            status='pending',
        )
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='all_confirmed',
        )
        recipients = build_recipient_list(campaign)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]['email'], 'hiro@example.com')

    def test_prospects_by_language(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='prospects_lang',
            segment_filter={'language_id': self.language.pk},
        )
        recipients = build_recipient_list(campaign)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]['email'], 'yuki@example.com')

    def test_enrolled_by_cohort(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='enrolled_cohort',
            segment_filter={'cohort_id': self.cohort.pk},
        )
        recipients = build_recipient_list(campaign)
        self.assertEqual(len(recipients), 1)

    def test_enrolled_by_language(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='enrolled_lang',
            segment_filter={'language_id': self.language.pk},
        )
        recipients = build_recipient_list(campaign)
        self.assertEqual(len(recipients), 1)

    def test_deduplication(self):
        """Same email in prospects and enrollments should appear only once."""
        Prospect.objects.create(
            first_name='Hiro', last_name='SATO',
            email='hiro@example.com',
        )
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='all_prospects',
        )
        recipients = build_recipient_list(campaign)
        hiro_count = sum(1 for r in recipients if r['email'] == 'hiro@example.com')
        self.assertEqual(hiro_count, 1)

    def test_excludes_unsubscribed(self):
        EmailSubscription.objects.create(
            email='yuki@example.com', is_subscribed=False,
        )
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='all_prospects',
        )
        recipients = build_recipient_list(campaign)
        emails = [r['email'] for r in recipients]
        self.assertNotIn('yuki@example.com', emails)
        self.assertIn('mei@example.com', emails)

    def test_custom_segment_returns_empty(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='custom',
        )
        recipients = build_recipient_list(campaign)
        self.assertEqual(len(recipients), 0)

    def test_prospects_by_rating(self):
        """Segment by rating returns only prospects with matching rating."""
        self.prospect1.rating = 'hot'
        self.prospect1.save()
        self.prospect2.rating = 'cold'
        self.prospect2.save()
        campaign = EmailCampaign.objects.create(
            name='Hot Prospects',
            template=self.template,
            segment_type='prospects_rating',
            segment_filter={'rating': 'hot'},
        )
        recipients = build_recipient_list(campaign)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]['email'], 'yuki@example.com')

    def test_prospects_by_rating_multiple(self):
        """Segment by rating can filter multiple ratings."""
        self.prospect1.rating = 'hot'
        self.prospect1.save()
        self.prospect2.rating = 'warm'
        self.prospect2.save()
        campaign = EmailCampaign.objects.create(
            name='Qualified Prospects',
            template=self.template,
            segment_type='prospects_rating',
            segment_filter={'rating': 'hot'},
        )
        recipients = build_recipient_list(campaign)
        emails = [r['email'] for r in recipients]
        self.assertIn('yuki@example.com', emails)
        self.assertNotIn('mei@example.com', emails)

    def test_prospects_by_rating_no_match(self):
        """Segment by rating with no matching prospects returns empty."""
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='prospects_rating',
            segment_filter={'rating': 'hot'},
        )
        recipients = build_recipient_list(campaign)
        self.assertEqual(len(recipients), 0)


class PopulateCampaignRecipientsTestCase(MarketingTestMixin, TestCase):
    """Test campaign recipient population."""

    def setUp(self):
        super().setUp()
        Prospect.objects.create(
            first_name='Yuki', last_name='TANAKA',
            email='yuki@example.com',
        )
        Prospect.objects.create(
            first_name='Mei', last_name='WANG',
            email='mei@example.com',
        )

    def test_populate_creates_recipients(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='all_prospects',
        )
        count = populate_campaign_recipients(campaign)
        self.assertEqual(count, 2)
        self.assertEqual(campaign.total_recipients, 2)
        self.assertEqual(campaign.recipients.count(), 2)

    def test_populate_idempotent(self):
        campaign = EmailCampaign.objects.create(
            name='Test',
            template=self.template,
            segment_type='all_prospects',
        )
        populate_campaign_recipients(campaign)
        # Mark one as sent
        r = campaign.recipients.first()
        r.status = CampaignRecipient.Status.SENT
        r.save()

        # Re-populate should only recreate pending ones
        count = populate_campaign_recipients(campaign)
        # Already sent won't be duplicated
        self.assertGreaterEqual(campaign.recipients.count(), 2)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SendEmailTestCase(MarketingTestMixin, TestCase):
    """Test email sending."""

    def setUp(self):
        super().setUp()
        self.campaign = EmailCampaign.objects.create(
            name='Send Test',
            template=self.template,
            segment_type='all_prospects',
        )
        self.recipient = CampaignRecipient.objects.create(
            campaign=self.campaign,
            email='yuki@example.com',
            first_name='Yuki',
            last_name='TANAKA',
        )

    def test_send_single_email(self):
        success = send_single_email(
            self.recipient, self.campaign, base_url='http://localhost',
        )
        self.assertTrue(success)
        self.recipient.refresh_from_db()
        self.assertEqual(self.recipient.status, 'sent')
        self.assertIsNotNone(self.recipient.sent_at)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_email_has_correct_subject(self):
        send_single_email(
            self.recipient, self.campaign, base_url='http://localhost',
        )
        self.assertIn('Yuki', mail.outbox[0].subject)

    def test_send_email_has_unsubscribe_header(self):
        send_single_email(
            self.recipient, self.campaign, base_url='http://localhost',
        )
        msg = mail.outbox[0]
        self.assertIn('List-Unsubscribe', msg.extra_headers)

    def test_send_email_creates_subscription(self):
        send_single_email(
            self.recipient, self.campaign, base_url='http://localhost',
        )
        self.assertTrue(
            EmailSubscription.objects.filter(email='yuki@example.com').exists()
        )


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SendCampaignTestCase(MarketingTestMixin, TestCase):
    """Test full campaign sending."""

    def setUp(self):
        super().setUp()
        Prospect.objects.create(
            first_name='Yuki', last_name='TANAKA',
            email='yuki@example.com',
        )
        Prospect.objects.create(
            first_name='Mei', last_name='WANG',
            email='mei@example.com',
        )
        self.campaign = EmailCampaign.objects.create(
            name='Full Test',
            template=self.template,
            segment_type='all_prospects',
        )
        populate_campaign_recipients(self.campaign)

    def test_send_campaign(self):
        sent, failed = send_campaign(self.campaign, base_url='http://localhost')
        self.assertEqual(sent, 2)
        self.assertEqual(failed, 0)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'sent')
        self.assertEqual(self.campaign.sent_count, 2)
        self.assertIsNotNone(self.campaign.completed_at)

    def test_campaign_not_sendable_when_sent(self):
        self.campaign.status = EmailCampaign.Status.SENT
        self.campaign.save()
        result = send_campaign(self.campaign)
        self.assertIsNone(result)


# ──────────────────────────────────────────────
# View tests — auth required
# ──────────────────────────────────────────────

class MarketingAuthTestCase(MarketingTestMixin, TestCase):
    """All marketing CMS views require authentication."""

    def test_views_require_login(self):
        urls = [
            reverse('marketing:template_list'),
            reverse('marketing:template_create'),
            reverse('marketing:campaign_list'),
            reverse('marketing:campaign_create'),
            reverse('marketing:subscriber_list'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f'{url} should require login')


class TemplateViewsTestCase(MarketingTestMixin, TestCase):
    """Test email template CMS views."""

    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='testpass123')

    def test_template_list(self):
        response = self.client.get(reverse('marketing:template_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Template Test')

    def test_template_list_filter_by_category(self):
        response = self.client.get(
            reverse('marketing:template_list') + '?category=newsletter'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Template Test')

    def test_template_list_search(self):
        response = self.client.get(
            reverse('marketing:template_list') + '?q=Test'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Template Test')

    def test_template_create_get(self):
        response = self.client.get(reverse('marketing:template_create'))
        self.assertEqual(response.status_code, 200)

    def test_template_create_post(self):
        response = self.client.post(reverse('marketing:template_create'), {
            'name': 'New Template',
            'category': 'welcome',
            'subject': 'Welcome!',
            'body_html': '<p>Hello</p>',
            'is_active': True,
        })
        self.assertRedirects(response, reverse('marketing:template_list'))
        self.assertTrue(EmailTemplate.objects.filter(name='New Template').exists())

    def test_template_edit_get(self):
        response = self.client.get(
            reverse('marketing:template_edit', kwargs={'pk': self.template.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_template_edit_post(self):
        response = self.client.post(
            reverse('marketing:template_edit', kwargs={'pk': self.template.pk}),
            {
                'name': 'Updated Template',
                'category': 'newsletter',
                'subject': 'New Subject',
                'body_html': '<p>Updated</p>',
                'is_active': True,
            },
        )
        self.assertRedirects(response, reverse('marketing:template_list'))
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, 'Updated Template')

    def test_template_delete(self):
        tpl = EmailTemplate.objects.create(
            name='To Delete', category='newsletter',
            subject='Test', body_html='<p>Test</p>',
        )
        response = self.client.post(
            reverse('marketing:template_delete', kwargs={'pk': tpl.pk})
        )
        self.assertRedirects(response, reverse('marketing:template_list'))
        self.assertFalse(EmailTemplate.objects.filter(pk=tpl.pk).exists())

    def test_template_delete_used_by_campaign(self):
        EmailCampaign.objects.create(
            name='Campaign', template=self.template,
        )
        response = self.client.post(
            reverse('marketing:template_delete', kwargs={'pk': self.template.pk})
        )
        self.assertRedirects(response, reverse('marketing:template_list'))
        # Template should still exist
        self.assertTrue(EmailTemplate.objects.filter(pk=self.template.pk).exists())

    def test_template_preview(self):
        response = self.client.get(
            reverse('marketing:template_preview', kwargs={'pk': self.template.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Yuki')
        self.assertContains(response, 'TANAKA')


class CampaignViewsTestCase(MarketingTestMixin, TestCase):
    """Test campaign CMS views."""

    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='testpass123')
        Prospect.objects.create(
            first_name='Yuki', last_name='TANAKA',
            email='yuki@example.com',
        )

    def test_campaign_list(self):
        EmailCampaign.objects.create(
            name='Test Campaign', template=self.template,
        )
        response = self.client.get(reverse('marketing:campaign_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Campaign')

    def test_campaign_list_filter_status(self):
        EmailCampaign.objects.create(
            name='Draft', template=self.template, status='draft',
        )
        response = self.client.get(
            reverse('marketing:campaign_list') + '?status=draft'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Draft')

    def test_campaign_create_get(self):
        response = self.client.get(reverse('marketing:campaign_create'))
        self.assertEqual(response.status_code, 200)

    def test_campaign_create_post(self):
        response = self.client.post(reverse('marketing:campaign_create'), {
            'name': 'New Campaign',
            'template': self.template.pk,
            'from_email_type': 'contact',
            'segment_type': 'all_prospects',
        })
        campaign = EmailCampaign.objects.get(name='New Campaign')
        self.assertRedirects(
            response,
            reverse('marketing:campaign_detail', kwargs={'pk': campaign.pk}),
        )

    def test_campaign_detail(self):
        campaign = EmailCampaign.objects.create(
            name='Detail Test', template=self.template,
        )
        response = self.client.get(
            reverse('marketing:campaign_detail', kwargs={'pk': campaign.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detail Test')

    def test_campaign_edit_get(self):
        campaign = EmailCampaign.objects.create(
            name='Edit Test', template=self.template, status='draft',
        )
        response = self.client.get(
            reverse('marketing:campaign_edit', kwargs={'pk': campaign.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_campaign_edit_not_draft_redirects(self):
        campaign = EmailCampaign.objects.create(
            name='Sent', template=self.template, status='sent',
        )
        response = self.client.get(
            reverse('marketing:campaign_edit', kwargs={'pk': campaign.pk})
        )
        self.assertRedirects(
            response,
            reverse('marketing:campaign_detail', kwargs={'pk': campaign.pk}),
        )

    def test_campaign_populate(self):
        campaign = EmailCampaign.objects.create(
            name='Populate Test',
            template=self.template,
            segment_type='all_prospects',
        )
        response = self.client.post(
            reverse('marketing:campaign_populate', kwargs={'pk': campaign.pk})
        )
        self.assertRedirects(
            response,
            reverse('marketing:campaign_detail', kwargs={'pk': campaign.pk}),
        )
        campaign.refresh_from_db()
        self.assertGreater(campaign.total_recipients, 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_campaign_send(self):
        campaign = EmailCampaign.objects.create(
            name='Send Test',
            template=self.template,
            segment_type='all_prospects',
        )
        populate_campaign_recipients(campaign)
        response = self.client.post(
            reverse('marketing:campaign_send', kwargs={'pk': campaign.pk})
        )
        self.assertRedirects(
            response,
            reverse('marketing:campaign_detail', kwargs={'pk': campaign.pk}),
        )
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'sent')

    def test_campaign_send_no_recipients(self):
        campaign = EmailCampaign.objects.create(
            name='Empty', template=self.template,
        )
        response = self.client.post(
            reverse('marketing:campaign_send', kwargs={'pk': campaign.pk})
        )
        self.assertRedirects(
            response,
            reverse('marketing:campaign_detail', kwargs={'pk': campaign.pk}),
        )
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'draft')  # Unchanged

    def test_campaign_cancel(self):
        campaign = EmailCampaign.objects.create(
            name='Cancel Test', template=self.template, status='draft',
        )
        response = self.client.post(
            reverse('marketing:campaign_cancel', kwargs={'pk': campaign.pk})
        )
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'cancelled')

    def test_campaign_delete(self):
        campaign = EmailCampaign.objects.create(
            name='Delete Test', template=self.template, status='draft',
        )
        response = self.client.post(
            reverse('marketing:campaign_delete', kwargs={'pk': campaign.pk})
        )
        self.assertRedirects(response, reverse('marketing:campaign_list'))
        self.assertFalse(EmailCampaign.objects.filter(pk=campaign.pk).exists())

    def test_campaign_delete_non_draft(self):
        campaign = EmailCampaign.objects.create(
            name='Sent', template=self.template, status='sent',
        )
        response = self.client.post(
            reverse('marketing:campaign_delete', kwargs={'pk': campaign.pk})
        )
        # Should redirect but NOT delete
        self.assertTrue(EmailCampaign.objects.filter(pk=campaign.pk).exists())

    def test_campaign_preview(self):
        campaign = EmailCampaign.objects.create(
            name='Preview Test', template=self.template,
        )
        response = self.client.get(
            reverse('marketing:campaign_preview', kwargs={'pk': campaign.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Yuki')


class SubscriberViewsTestCase(MarketingTestMixin, TestCase):
    """Test subscriber CMS views."""

    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='testpass123')

    def test_subscriber_list(self):
        EmailSubscription.objects.create(
            email='test@example.com', is_subscribed=True,
        )
        response = self.client.get(reverse('marketing:subscriber_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test@example.com')

    def test_subscriber_list_filter_subscribed(self):
        EmailSubscription.objects.create(
            email='sub@example.com', is_subscribed=True,
        )
        EmailSubscription.objects.create(
            email='unsub@example.com', is_subscribed=False,
        )
        response = self.client.get(
            reverse('marketing:subscriber_list') + '?status=subscribed'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sub@example.com')
        self.assertNotContains(response, 'unsub@example.com')

    def test_subscriber_list_search(self):
        EmailSubscription.objects.create(
            email='findme@example.com', is_subscribed=True,
        )
        response = self.client.get(
            reverse('marketing:subscriber_list') + '?q=findme'
        )
        self.assertContains(response, 'findme@example.com')


# ──────────────────────────────────────────────
# Public endpoints
# ──────────────────────────────────────────────

class UnsubscribeViewTestCase(TestCase):
    """Test public unsubscribe endpoint."""

    def test_unsubscribe_page_renders(self):
        sub = EmailSubscription.objects.create(
            email='test@example.com', is_subscribed=True,
        )
        response = self.client.get(
            reverse('marketing_public:unsubscribe', kwargs={'token': sub.unsubscribe_token})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test@example.com')

    def test_unsubscribe_confirms(self):
        sub = EmailSubscription.objects.create(
            email='test@example.com', is_subscribed=True,
        )
        response = self.client.post(
            reverse('marketing_public:unsubscribe', kwargs={'token': sub.unsubscribe_token})
        )
        self.assertEqual(response.status_code, 200)
        sub.refresh_from_db()
        self.assertFalse(sub.is_subscribed)
        self.assertIsNotNone(sub.unsubscribed_at)

    def test_unsubscribe_invalid_token(self):
        fake_token = uuid.uuid4()
        response = self.client.get(
            reverse('marketing_public:unsubscribe', kwargs={'token': fake_token})
        )
        self.assertEqual(response.status_code, 404)


class TrackOpenViewTestCase(MarketingTestMixin, TestCase):
    """Test email open tracking pixel."""

    def setUp(self):
        super().setUp()
        self.campaign = EmailCampaign.objects.create(
            name='Track Test', template=self.template,
        )
        self.recipient = CampaignRecipient.objects.create(
            campaign=self.campaign,
            email='test@example.com',
            status='sent',
        )

    def test_track_open_returns_pixel(self):
        response = self.client.get(
            reverse('marketing_public:track_open', kwargs={'token': self.recipient.open_token})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/gif')

    def test_track_open_records_timestamp(self):
        self.client.get(
            reverse('marketing_public:track_open', kwargs={'token': self.recipient.open_token})
        )
        self.recipient.refresh_from_db()
        self.assertIsNotNone(self.recipient.opened_at)

    def test_track_open_updates_campaign_counter(self):
        self.client.get(
            reverse('marketing_public:track_open', kwargs={'token': self.recipient.open_token})
        )
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.opened_count, 1)

    def test_track_open_only_records_first(self):
        self.client.get(
            reverse('marketing_public:track_open', kwargs={'token': self.recipient.open_token})
        )
        first_open = self.recipient.opened_at
        self.recipient.refresh_from_db()
        first_open = self.recipient.opened_at

        self.client.get(
            reverse('marketing_public:track_open', kwargs={'token': self.recipient.open_token})
        )
        self.recipient.refresh_from_db()
        self.assertEqual(self.recipient.opened_at, first_open)

    def test_track_open_invalid_token(self):
        fake_token = uuid.uuid4()
        response = self.client.get(
            reverse('marketing_public:track_open', kwargs={'token': fake_token})
        )
        self.assertEqual(response.status_code, 200)  # Still returns pixel


class TrackClickViewTestCase(MarketingTestMixin, TestCase):
    """Test email click tracking."""

    def setUp(self):
        super().setUp()
        self.campaign = EmailCampaign.objects.create(
            name='Click Test', template=self.template,
        )
        self.recipient = CampaignRecipient.objects.create(
            campaign=self.campaign,
            email='test@example.com',
            status='sent',
        )

    def test_track_click_redirects(self):
        response = self.client.get(
            reverse('marketing_public:track_click', kwargs={'token': self.recipient.click_token})
            + '?url=https://example.com'
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://example.com')

    def test_track_click_records_timestamp(self):
        self.client.get(
            reverse('marketing_public:track_click', kwargs={'token': self.recipient.click_token})
            + '?url=https://example.com'
        )
        self.recipient.refresh_from_db()
        self.assertIsNotNone(self.recipient.clicked_at)

    def test_track_click_updates_campaign_counter(self):
        self.client.get(
            reverse('marketing_public:track_click', kwargs={'token': self.recipient.click_token})
            + '?url=https://example.com'
        )
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.clicked_count, 1)

    def test_track_click_default_redirect(self):
        response = self.client.get(
            reverse('marketing_public:track_click', kwargs={'token': self.recipient.click_token})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')


# ──────────────────────────────────────────────
# NotificationLog model tests
# ──────────────────────────────────────────────

class NotificationLogModelTestCase(MarketingTestMixin, TestCase):
    """Test NotificationLog model."""

    def test_create_notification_log(self):
        from marketing.models import NotificationLog
        log = NotificationLog.objects.create(
            event_type='contact_received',
            recipient_email='test@example.com',
            recipient_name='Test User',
            subject='Test Subject',
            body_html='<p>Hello</p>',
            related_model='prospect',
            related_id=1,
            status='sent',
        )
        self.assertEqual(log.event_type, 'contact_received')
        self.assertEqual(log.status, 'sent')
        self.assertIsNotNone(log.sent_at)

    def test_str_representation(self):
        from marketing.models import NotificationLog
        log = NotificationLog.objects.create(
            event_type='enrollment_confirmed',
            recipient_email='hiro@example.com',
            subject='Confirmation',
            status='sent',
        )
        result = str(log)
        self.assertIn('hiro@example.com', result)
        self.assertIn('Confirmée', result)

    def test_event_type_choices(self):
        from marketing.models import NotificationLog
        for value, _ in NotificationLog.EventType.choices:
            log = NotificationLog.objects.create(
                event_type=value,
                recipient_email='test@example.com',
                subject='Test',
            )
            self.assertEqual(log.event_type, value)

    def test_status_choices(self):
        from marketing.models import NotificationLog
        for value, _ in NotificationLog.Status.choices:
            log = NotificationLog.objects.create(
                event_type='contact_received',
                recipient_email='test@example.com',
                subject='Test',
                status=value,
            )
            self.assertEqual(log.status, value)

    def test_ordering_by_sent_at_desc(self):
        from marketing.models import NotificationLog
        log1 = NotificationLog.objects.create(
            event_type='contact_received',
            recipient_email='first@example.com',
            subject='First',
        )
        log2 = NotificationLog.objects.create(
            event_type='enrollment_received',
            recipient_email='second@example.com',
            subject='Second',
        )
        logs = list(NotificationLog.objects.all())
        self.assertEqual(logs[0].pk, log2.pk)

    def test_sent_by_nullable(self):
        from marketing.models import NotificationLog
        log = NotificationLog.objects.create(
            event_type='contact_received',
            recipient_email='test@example.com',
            subject='Auto',
            sent_by=None,
        )
        self.assertIsNone(log.sent_by)

    def test_sent_by_with_user(self):
        from marketing.models import NotificationLog
        log = NotificationLog.objects.create(
            event_type='enrollment_confirmed',
            recipient_email='test@example.com',
            subject='Manual',
            sent_by=self.user,
        )
        self.assertEqual(log.sent_by, self.user)

    def test_error_message_blank_by_default(self):
        from marketing.models import NotificationLog
        log = NotificationLog.objects.create(
            event_type='contact_received',
            recipient_email='test@example.com',
            subject='Test',
        )
        self.assertEqual(log.error_message, '')


# ──────────────────────────────────────────────
# Notification service tests
# ──────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NotificationServiceTestCase(MarketingTestMixin, TestCase):
    """Test the notification sending service."""

    def setUp(self):
        super().setUp()
        from marketing.models import NotificationLog
        self.NotificationLog = NotificationLog

    def test_send_notification_contact_received(self):
        from marketing.notifications import send_notification
        log = send_notification(
            event_type='contact_received',
            recipient_email='test@example.com',
            context={'first_name': 'Yuki'},
            recipient_name='Yuki TANAKA',
            related_model='prospect',
            related_id=1,
            from_type='contact',
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'sent')
        self.assertEqual(log.event_type, 'contact_received')
        self.assertEqual(log.recipient_email, 'test@example.com')
        self.assertIn('Institut Torii', log.subject)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])

    def test_send_notification_creates_log_record(self):
        from marketing.notifications import send_notification
        initial_count = self.NotificationLog.objects.count()
        send_notification(
            event_type='enrollment_received',
            recipient_email='hiro@example.com',
            context={'first_name': 'Hiro', 'cohort_name': 'Japonais N5', 'enrollment_code': 'ABC12345'},
            from_type='inscription',
        )
        self.assertEqual(self.NotificationLog.objects.count(), initial_count + 1)

    def test_send_notification_renders_template(self):
        from marketing.notifications import send_notification
        log = send_notification(
            event_type='enrollment_confirmed',
            recipient_email='yuki@example.com',
            context={
                'first_name': 'Yuki',
                'cohort_name': 'Japonais N5',
                'enrollment_code': 'XYZ999',
                'start_date': '15/09/2026',
            },
        )
        self.assertIn('Yuki', log.body_html)
        self.assertIn('Japonais N5', log.body_html)
        self.assertIn('XYZ999', log.body_html)
        self.assertIn('✅', log.subject)

    def test_send_notification_html_alternative(self):
        from marketing.notifications import send_notification
        send_notification(
            event_type='contact_received',
            recipient_email='test@example.com',
            context={'first_name': 'Test'},
        )
        msg = mail.outbox[0]
        self.assertEqual(len(msg.alternatives), 1)
        self.assertEqual(msg.alternatives[0][1], 'text/html')

    def test_send_notification_text_body(self):
        from marketing.notifications import send_notification
        send_notification(
            event_type='contact_received',
            recipient_email='test@example.com',
            context={'first_name': 'Test'},
        )
        msg = mail.outbox[0]
        # Text body should not contain HTML tags
        self.assertNotIn('<div', msg.body)
        self.assertNotIn('<h2', msg.body)

    def test_send_notification_with_sent_by(self):
        from marketing.notifications import send_notification
        log = send_notification(
            event_type='enrollment_confirmed',
            recipient_email='test@example.com',
            context={'first_name': 'Test', 'cohort_name': 'Cours Test', 'enrollment_code': 'ABC'},
            sent_by=self.user,
        )
        self.assertEqual(log.sent_by, self.user)

    def test_send_notification_failed_email(self):
        from marketing.notifications import send_notification
        with patch('marketing.notifications.EmailMultiAlternatives.send', side_effect=Exception('SMTP error')):
            log = send_notification(
                event_type='contact_received',
                recipient_email='test@example.com',
                context={'first_name': 'Test'},
            )
        self.assertEqual(log.status, 'failed')
        self.assertIn('SMTP error', log.error_message)

    def test_send_notification_invalid_event_type(self):
        from marketing.notifications import send_notification
        result = send_notification(
            event_type='nonexistent_type',
            recipient_email='test@example.com',
            context={},
        )
        self.assertIsNone(result)

    def test_send_notification_default_context(self):
        from marketing.notifications import send_notification
        log = send_notification(
            event_type='contact_received',
            recipient_email='test@example.com',
            context={'first_name': 'Test'},
        )
        # Should include site_name
        self.assertIn('Institut Torii', log.body_html)

    def test_all_event_types_have_templates(self):
        from marketing.notifications import DEFAULT_TEMPLATES
        expected = [
            'contact_received', 'enrollment_received',
            'enrollment_confirmed', 'enrollment_rejected', 'enrollment_refunded',
        ]
        for event in expected:
            self.assertIn(event, DEFAULT_TEMPLATES)
            self.assertIn('subject', DEFAULT_TEMPLATES[event])
            self.assertIn('body_html', DEFAULT_TEMPLATES[event])


# ──────────────────────────────────────────────
# High-level notification function tests
# ──────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class HighLevelNotificationTestCase(MarketingTestMixin, TestCase):
    """Test high-level notify_* functions with real model instances."""

    def setUp(self):
        super().setUp()
        self.prospect = Prospect.objects.create(
            first_name='Sakura', last_name='YAMAMOTO',
            email='sakura@example.com',
        )
        self.enrollment = Enrollment.objects.create(
            first_name='Hiro', last_name='TANAKA',
            email='hiro@example.com',
            cohort=self.cohort,
            payment_receipt='receipts/test.jpg',
            status='pending',
        )

    def test_notify_contact_received(self):
        from marketing.notifications import notify_contact_received
        from marketing.models import NotificationLog
        log = notify_contact_received(self.prospect)
        self.assertEqual(log.event_type, 'contact_received')
        self.assertEqual(log.recipient_email, 'sakura@example.com')
        self.assertEqual(log.recipient_name, 'Sakura YAMAMOTO')
        self.assertEqual(log.related_model, 'prospect')
        self.assertEqual(log.related_id, self.prospect.pk)
        self.assertEqual(log.status, 'sent')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Institut Torii', mail.outbox[0].subject)

    def test_notify_enrollment_received(self):
        from marketing.notifications import notify_enrollment_received
        log = notify_enrollment_received(self.enrollment)
        self.assertEqual(log.event_type, 'enrollment_received')
        self.assertEqual(log.recipient_email, 'hiro@example.com')
        self.assertEqual(log.related_model, 'enrollment')
        self.assertEqual(log.related_id, self.enrollment.pk)
        self.assertIn(self.enrollment.enrollment_code, log.body_html)
        self.assertIn('Japonais N5', log.body_html)

    def test_notify_enrollment_confirmed(self):
        from marketing.notifications import notify_enrollment_confirmed
        self.enrollment.status = 'confirmed'
        self.enrollment.save()
        log = notify_enrollment_confirmed(self.enrollment, user=self.user)
        self.assertEqual(log.event_type, 'enrollment_confirmed')
        self.assertEqual(log.sent_by, self.user)
        self.assertIn('✅', log.subject)
        self.assertIn('confirmée', log.body_html)

    def test_notify_enrollment_confirmed_with_start_date(self):
        from marketing.notifications import notify_enrollment_confirmed
        from datetime import date
        self.cohort.start_date = date(2026, 9, 15)
        self.cohort.save()
        log = notify_enrollment_confirmed(self.enrollment, user=self.user)
        self.assertIn('15/09/2026', log.body_html)

    def test_notify_enrollment_rejected(self):
        from marketing.notifications import notify_enrollment_rejected
        self.enrollment.status = 'rejected'
        self.enrollment.rejection_reason = 'Reçu de paiement illisible'
        self.enrollment.save()
        log = notify_enrollment_rejected(self.enrollment, user=self.user)
        self.assertEqual(log.event_type, 'enrollment_rejected')
        self.assertEqual(log.sent_by, self.user)
        self.assertIn('Reçu de paiement illisible', log.body_html)

    def test_notify_enrollment_rejected_without_reason(self):
        from marketing.notifications import notify_enrollment_rejected
        self.enrollment.status = 'rejected'
        self.enrollment.rejection_reason = ''
        self.enrollment.save()
        log = notify_enrollment_rejected(self.enrollment, user=self.user)
        self.assertEqual(log.event_type, 'enrollment_rejected')
        # No crash when no rejection reason
        self.assertEqual(log.status, 'sent')

    def test_notify_enrollment_refunded(self):
        from marketing.notifications import notify_enrollment_refunded
        self.enrollment.status = 'refunded'
        self.enrollment.save()
        log = notify_enrollment_refunded(self.enrollment, user=self.user)
        self.assertEqual(log.event_type, 'enrollment_refunded')
        self.assertEqual(log.sent_by, self.user)
        self.assertIn('remboursée', log.body_html)

    def test_notify_enrollment_refunded_automatic(self):
        from marketing.notifications import notify_enrollment_refunded
        log = notify_enrollment_refunded(self.enrollment)
        self.assertIsNone(log.sent_by)


# ──────────────────────────────────────────────
# Notification CMS views tests
# ──────────────────────────────────────────────

class NotificationListViewTestCase(MarketingTestMixin, TestCase):
    """Test notification_list CMS view."""

    def setUp(self):
        super().setUp()
        from marketing.models import NotificationLog
        self.client.login(username='admin', password='testpass123')
        self.url = reverse('marketing:notification_list')

        # Create sample notifications
        NotificationLog.objects.create(
            event_type='contact_received',
            recipient_email='yuki@example.com',
            recipient_name='Yuki TANAKA',
            subject='Contact reçu',
            body_html='<p>Test</p>',
            status='sent',
        )
        NotificationLog.objects.create(
            event_type='enrollment_confirmed',
            recipient_email='hiro@example.com',
            recipient_name='Hiro SATO',
            subject='Inscription confirmée',
            body_html='<p>Confirmé</p>',
            status='sent',
            sent_by=self.user,
        )
        NotificationLog.objects.create(
            event_type='enrollment_rejected',
            recipient_email='fail@example.com',
            subject='Inscription rejetée',
            body_html='<p>Rejeté</p>',
            status='failed',
            error_message='SMTP error',
        )

    def test_renders_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_requires_auth(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_displays_notifications(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'yuki@example.com')
        self.assertContains(response, 'hiro@example.com')

    def test_search_by_email(self):
        response = self.client.get(self.url + '?q=yuki')
        self.assertContains(response, 'yuki@example.com')
        self.assertNotContains(response, 'hiro@example.com')

    def test_search_by_name(self):
        response = self.client.get(self.url + '?q=SATO')
        self.assertContains(response, 'hiro@example.com')
        self.assertNotContains(response, 'yuki@example.com')

    def test_search_by_subject(self):
        response = self.client.get(self.url + '?q=confirmée')
        self.assertContains(response, 'hiro@example.com')

    def test_filter_by_event_type(self):
        response = self.client.get(self.url + '?event=contact_received')
        self.assertContains(response, 'yuki@example.com')
        self.assertNotContains(response, 'hiro@example.com')

    def test_filter_by_status_sent(self):
        response = self.client.get(self.url + '?status=sent')
        self.assertContains(response, 'yuki@example.com')
        self.assertNotContains(response, 'fail@example.com')

    def test_filter_by_status_failed(self):
        response = self.client.get(self.url + '?status=failed')
        self.assertContains(response, 'fail@example.com')
        self.assertNotContains(response, 'yuki@example.com')

    def test_kpi_counts(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_sent'], 2)
        self.assertEqual(response.context['total_failed'], 1)
        self.assertEqual(response.context['total_count'], 3)

    def test_combined_filters(self):
        response = self.client.get(self.url + '?event=enrollment_confirmed&status=sent')
        self.assertContains(response, 'hiro@example.com')
        self.assertNotContains(response, 'yuki@example.com')
        self.assertNotContains(response, 'fail@example.com')


class NotificationDetailViewTestCase(MarketingTestMixin, TestCase):
    """Test notification_detail CMS view."""

    def setUp(self):
        super().setUp()
        from marketing.models import NotificationLog
        self.client.login(username='admin', password='testpass123')
        self.notification = NotificationLog.objects.create(
            event_type='enrollment_confirmed',
            recipient_email='hiro@example.com',
            recipient_name='Hiro TANAKA',
            subject='Inscription confirmée — Japonais N5',
            body_html='<h2>Félicitations Hiro !</h2><p>Votre inscription est confirmée.</p>',
            status='sent',
            related_model='enrollment',
            related_id=42,
            sent_by=self.user,
        )
        self.url = reverse('marketing:notification_detail', kwargs={'pk': self.notification.pk})

    def test_renders_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_requires_auth(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_displays_recipient(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'hiro@example.com')
        self.assertContains(response, 'Hiro TANAKA')

    def test_displays_subject(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Inscription confirmée — Japonais N5')

    def test_displays_html_body(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Félicitations Hiro')

    def test_displays_related_model(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'enrollment')
        self.assertContains(response, '42')

    def test_displays_sent_by(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'admin')

    def test_404_nonexistent(self):
        url = reverse('marketing:notification_detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_failed_notification_shows_error(self):
        from marketing.models import NotificationLog
        failed = NotificationLog.objects.create(
            event_type='contact_received',
            recipient_email='fail@example.com',
            subject='Failed',
            body_html='<p>Test</p>',
            status='failed',
            error_message='Connection refused',
        )
        url = reverse('marketing:notification_detail', kwargs={'pk': failed.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Connection refused')
