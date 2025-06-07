from django.core.management.base import BaseCommand
from django.db import models
from gallery.models import ArbiusImage
from gallery.services import ArbitrumScanner


class Command(BaseCommand):
    help = 'Identify and optionally remove text model outputs from the gallery'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be removed without actually removing anything'
        )
        parser.add_argument(
            '--check-content',
            action='store_true',
            help='Also check IPFS content to validate images (slower but more thorough)'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🧹 Starting cleanup of text model outputs...')
        )
        
        # Find potential text outputs based on prompt patterns
        text_outputs = ArbiusImage.objects.filter(
            models.Q(prompt__startswith="<|begin_of_text|>") |
            models.Q(prompt__startswith="<|end_of_text|>") |
            models.Q(prompt__length__gt=5000)  # Extremely long prompts
        )
        
        self.stdout.write(f"Found {text_outputs.count()} potential text outputs based on prompt patterns")
        
        if options['check_content']:
            scanner = ArbitrumScanner()
            invalid_images = []
            
            # Check a sample of images for content validation
            sample_images = ArbiusImage.objects.filter(is_accessible=True)[:100]
            self.stdout.write(f"Checking {sample_images.count()} accessible images for valid content...")
            
            for image in sample_images:
                if not scanner.is_valid_image_content(image.cid):
                    invalid_images.append(image)
                    self.stdout.write(f"  ❌ Invalid content: {image.cid[:20]}...")
            
            self.stdout.write(f"Found {len(invalid_images)} images with invalid content")
            
            if options['dry_run']:
                self.stdout.write("Would remove these invalid content entries:")
                for img in invalid_images:
                    self.stdout.write(f"  • {img.cid} - {img.prompt[:50] if img.prompt else 'No prompt'}...")
            else:
                # Remove invalid content images
                for img in invalid_images:
                    img.delete()
                self.stdout.write(f"✅ Removed {len(invalid_images)} invalid content entries")
        
        if options['dry_run']:
            self.stdout.write("Would remove these text output entries:")
            for output in text_outputs[:10]:  # Show first 10
                prompt_preview = output.prompt[:100] if output.prompt else "No prompt"
                self.stdout.write(f"  • {output.cid} - {prompt_preview}...")
            if text_outputs.count() > 10:
                self.stdout.write(f"  ... and {text_outputs.count() - 10} more")
        else:
            # Actually remove text outputs
            removed_count = text_outputs.count()
            text_outputs.delete()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Removed {removed_count} text model outputs')
            )
        
        # Show final statistics
        remaining_images = ArbiusImage.objects.exclude(
            prompt__startswith="<|begin_of_text|>"
        ).exclude(
            prompt__startswith="<|end_of_text|>"
        ).exclude(
            prompt__length__gt=5000
        ).filter(is_accessible=True).count()
        
        self.stdout.write(f"📊 Gallery now has {remaining_images} valid images") 