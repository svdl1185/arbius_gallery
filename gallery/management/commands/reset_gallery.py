from django.core.management.base import BaseCommand
from gallery.models import ArbiusImage, ScanStatus
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reset the gallery by clearing all images and scan status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all gallery data'
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING('⚠️  This will delete ALL images and scan status from the gallery!')
            )
            self.stdout.write(
                self.style.WARNING('Run with --confirm flag if you are sure you want to proceed.')
            )
            return
        
        try:
            # Count existing data
            image_count = ArbiusImage.objects.count()
            
            self.stdout.write(f'🗑️  Deleting {image_count} existing images...')
            
            # Delete all images
            ArbiusImage.objects.all().delete()
            
            # Reset scan status
            ScanStatus.objects.all().delete()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Gallery reset complete!')
            )
            self.stdout.write(
                self.style.SUCCESS(f'   - Deleted {image_count} images')
            )
            self.stdout.write(
                self.style.SUCCESS(f'   - Reset scan status')
            )
            self.stdout.write(
                self.style.WARNING(f'💡 Run a deep scan to repopulate with valid images:')
            )
            self.stdout.write(
                self.style.WARNING(f'   python manage.py scan_arbius --deep-scan')
            )
            
        except Exception as e:
            error_msg = f'Error resetting gallery: {e}'
            self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
            logger.error(error_msg) 