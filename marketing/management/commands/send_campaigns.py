"""
Management command to process scheduled email campaigns.

Usage:
    python manage.py send_campaigns          # Process all due campaigns
    python manage.py send_campaigns --dry    # Preview without sending

Can be added to a cron job for automated sending:
    */5 * * * * cd /path/to/project && python manage.py send_campaigns
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from marketing.models import EmailCampaign
from marketing.services import populate_campaign_recipients, send_campaign


class Command(BaseCommand):
    help = 'Process and send scheduled email campaigns that are due.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry',
            action='store_true',
            help='Dry run — show what would be sent without actually sending.',
        )
        parser.add_argument(
            '--campaign-id',
            type=int,
            help='Send a specific campaign by ID (regardless of schedule).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry']
        campaign_id = options.get('campaign_id')
        now = timezone.now()

        if campaign_id:
            campaigns = EmailCampaign.objects.filter(pk=campaign_id)
        else:
            # Find campaigns that are scheduled and due
            campaigns = EmailCampaign.objects.filter(
                status=EmailCampaign.Status.SCHEDULED,
                scheduled_at__lte=now,
            )

        if not campaigns.exists():
            self.stdout.write(self.style.NOTICE('Aucune campagne à envoyer.'))
            return

        for campaign in campaigns:
            self.stdout.write(f'\n📧 Campagne : {campaign.name}')
            self.stdout.write(f'   Statut : {campaign.get_status_display()}')
            self.stdout.write(f'   Segment : {campaign.get_segment_type_display()}')

            # Ensure recipients are populated
            if campaign.total_recipients == 0:
                self.stdout.write('   → Préparation des destinataires...')
                count = populate_campaign_recipients(campaign)
                self.stdout.write(f'   → {count} destinataires préparés.')

            self.stdout.write(f'   → {campaign.total_recipients} destinataires au total.')

            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f'   ⚠️  Mode dry-run : aucun email envoyé.'
                ))
                continue

            if campaign.total_recipients == 0:
                self.stdout.write(self.style.WARNING(
                    '   ⚠️  Aucun destinataire — campagne ignorée.'
                ))
                continue

            self.stdout.write('   → Envoi en cours...')
            sent, failed = send_campaign(campaign)
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Terminé : {sent} envoyés, {failed} échoués.'
            ))

        self.stdout.write(self.style.SUCCESS('\nTraitement terminé.'))
