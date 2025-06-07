from django.core.management.base import BaseCommand
from gallery.models import ArbiusImage
from django.db.models import Count


class Command(BaseCommand):
    help = 'List all unique model IDs and their transaction examples'

    def handle(self, *args, **options):
        # Get all unique model IDs with counts
        model_stats = (ArbiusImage.objects
                      .exclude(model_id__isnull=True)
                      .exclude(model_id='')
                      .values('model_id')
                      .annotate(count=Count('id'))
                      .order_by('-count'))
        
        self.stdout.write(f"\n🎯 Found {len(model_stats)} unique model IDs:\n")
        
        for i, stat in enumerate(model_stats, 1):
            model_id = stat['model_id']
            count = stat['count']
            
            # Get a sample transaction for this model
            sample_image = ArbiusImage.objects.filter(model_id=model_id).first()
            
            self.stdout.write(f"{i}. Model ID: {model_id}")
            self.stdout.write(f"   Images: {count}")
            
            if sample_image:
                tx_hash = sample_image.transaction_hash
                arbiscan_url = f"https://arbiscan.io/tx/{tx_hash}"
                self.stdout.write(f"   Sample Transaction: {arbiscan_url}")
                
                if sample_image.prompt:
                    prompt_preview = sample_image.prompt[:60] + "..." if len(sample_image.prompt) > 60 else sample_image.prompt
                    self.stdout.write(f"   Sample Prompt: \"{prompt_preview}\"")
            
            self.stdout.write("")  # Empty line for readability
        
        # Also show stats for images without model IDs
        no_model_count = ArbiusImage.objects.filter(model_id__isnull=True).count() + ArbiusImage.objects.filter(model_id='').count()
        if no_model_count > 0:
            self.stdout.write(f"⚠️  {no_model_count} images have no model ID")
        
        total_images = ArbiusImage.objects.count()
        self.stdout.write(f"\n📊 Total images in database: {total_images}") 