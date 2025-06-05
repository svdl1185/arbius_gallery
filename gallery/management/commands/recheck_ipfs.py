from django.core.management.base import BaseCommand
from gallery.services import ArbitrumScanner


class Command(BaseCommand):
    help = 'Recheck IPFS accessibility for images marked as not accessible'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of images to check in this batch (default: 50)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Check all pending images (ignores batch-size)'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔄 Starting IPFS accessibility recheck...')
        )
        
        scanner = ArbitrumScanner()
        
        if options['all']:
            # Check all pending images
            from gallery.models import ArbiusImage
            pending_count = ArbiusImage.objects.filter(is_accessible=False).count()
            self.stdout.write(f"Checking all {pending_count} pending images...")
            
            # Process in batches to avoid overwhelming the system
            batch_size = 20
            total_updated = 0
            
            for i in range(0, pending_count, batch_size):
                updated = scanner.recheck_accessibility(batch_size)
                total_updated += updated
                
                if updated > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f"Batch {i//batch_size + 1}: {updated} images became accessible")
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Complete! {total_updated} images are now accessible')
            )
        else:
            # Check specified batch size
            updated = scanner.recheck_accessibility(options['batch_size'])
            
            if updated > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {updated} images became accessible')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⏳ No images became accessible in this batch')
                ) 