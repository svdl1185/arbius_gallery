from django.core.management.base import BaseCommand
from gallery.models import ArbiusImage, ScanStatus


class Command(BaseCommand):
    help = 'Clean the database by removing all image records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all records'
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING('⚠️  This will delete ALL image records from the database!')
            )
            self.stdout.write('Run with --confirm to proceed')
            return

        # Get counts before deletion
        image_count = ArbiusImage.objects.count()
        
        # Delete all records
        ArbiusImage.objects.all().delete()
        ScanStatus.objects.all().delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Deleted {image_count} image records')
        )
        self.stdout.write('📊 Database cleaned successfully!') 