from django.core.management.base import BaseCommand
from gallery.services import ArbitrumScanner
from gallery.models import ArbiusImage
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scan for new Arbius images on the blockchain'

    def add_arguments(self, parser):
        parser.add_argument(
            '--blocks',
            type=int,
            default=100,
            help='Number of recent blocks to scan (default: 100)'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress output (for scheduled runs)'
        )

    def handle(self, *args, **options):
        scanner = ArbitrumScanner()
        
        if not options['quiet']:
            self.stdout.write('🔍 Scanning for new Arbius images...')
        
        try:
            # Scan recent blocks for new images
            new_images = scanner.scan_recent_blocks(options['blocks'])
            
            if new_images:
                if not options['quiet']:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Found {len(new_images)} new images!')
                    )
                    for image in new_images:
                        accessible = "✅" if image.is_accessible else "⏳"
                        self.stdout.write(f'   {accessible} {image.cid}')
                else:
                    logger.info(f'Found {len(new_images)} new Arbius images')
            else:
                if not options['quiet']:
                    self.stdout.write('📊 No new images found')
                logger.info('No new Arbius images found')
            
            # Update stats
            total_images = ArbiusImage.objects.count()
            accessible_images = ArbiusImage.objects.filter(is_accessible=True).count()
            
            if not options['quiet']:
                self.stdout.write(f'📊 Total images: {total_images} ({accessible_images} accessible)')
            
        except Exception as e:
            error_msg = f'Error scanning for images: {e}'
            if not options['quiet']:
                self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
            logger.error(error_msg) 