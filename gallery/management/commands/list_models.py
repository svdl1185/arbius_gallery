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
                # Show solution transaction (where the image was submitted)
                solution_tx_hash = sample_image.transaction_hash
                solution_arbiscan_url = f"https://arbiscan.io/tx/{solution_tx_hash}"
                self.stdout.write(f"   Sample Solution Transaction: {solution_arbiscan_url}")
                
                # Show task transaction (where the model ID was specified)
                if sample_image.task_id and sample_image.task_id != '0x0000000000000000000000000000000000000000000000000000000000000000':
                    # The task_id is the task transaction hash (though system tries to find it via events)
                    # For now, let's show the task_id which should link to the task
                    self.stdout.write(f"   Task ID: {sample_image.task_id}")
                    self.stdout.write(f"   ⚠️  To find task transaction, search for TaskSubmitted events with this task_id")
                
                if sample_image.prompt:
                    prompt_preview = sample_image.prompt[:60] + "..." if len(sample_image.prompt) > 60 else sample_image.prompt
                    self.stdout.write(f"   Sample Prompt: \"{prompt_preview}\"")
                
                if sample_image.task_submitter:
                    self.stdout.write(f"   Task Submitter: {sample_image.task_submitter}")
                if sample_image.solution_provider:
                    self.stdout.write(f"   Solution Provider: {sample_image.solution_provider}")
            
            self.stdout.write("")  # Empty line for readability
        
        # Also show stats for images without model IDs
        no_model_count = ArbiusImage.objects.filter(model_id__isnull=True).count() + ArbiusImage.objects.filter(model_id='').count()
        if no_model_count > 0:
            self.stdout.write(f"⚠️  {no_model_count} images have no model ID")
        
        total_images = ArbiusImage.objects.count()
        self.stdout.write(f"\n📊 Total images in database: {total_images}")
        self.stdout.write(f"\n💡 Note: Solution transactions contain the generated images (CIDs)")
        self.stdout.write(f"💡 Task transactions contain the model IDs and original prompts")
        self.stdout.write(f"💡 To find task transactions, search Arbiscan for TaskSubmitted events with the task_id") 