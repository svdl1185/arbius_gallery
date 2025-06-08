from django.core.management.base import BaseCommand
from gallery.models import ArbiusImage
from gallery.services import ArbitrumScanner
from django.db import transaction

class Command(BaseCommand):
    help = 'Fix model_id and task_submitter data by re-parsing task transactions'

    def handle(self, *args, **options):
        scanner = ArbitrumScanner()
        
        # Get all images that have task_ids
        images_with_tasks = ArbiusImage.objects.filter(
            task_id__isnull=False
        ).exclude(task_id='').exclude(task_id='0x0000000000000000000000000000000000000000000000000000000000000000')
        
        total_images = images_with_tasks.count()
        self.stdout.write(f"🔍 Found {total_images} images with task IDs to fix")
        
        updated_count = 0
        error_count = 0
        
        for i, image in enumerate(images_with_tasks, 1):
            if i % 50 == 0:
                self.stdout.write(f"Progress: {i}/{total_images} ({i/total_images*100:.1f}%)")
            
            try:
                # Get the correct task data using the fixed parsing
                task_data = scanner.find_task_by_id_optimized(image.task_id, image.block_number)
                
                if task_data:
                    # Check if we need to update the data
                    needs_update = (
                        image.model_id != task_data.get('model_id') or
                        image.task_submitter != task_data.get('submitter')
                    )
                    
                    if needs_update:
                        old_model = image.model_id
                        old_submitter = image.task_submitter
                        
                        # Update with the correct data
                        with transaction.atomic():
                            image.model_id = task_data.get('model_id')
                            image.task_submitter = task_data.get('submitter')
                            # Also update prompt if it's missing or different
                            if not image.prompt and task_data.get('prompt'):
                                image.prompt = task_data.get('prompt')
                            image.save()
                        
                        updated_count += 1
                        self.stdout.write(f"  ✅ Updated image {image.id}:")
                        self.stdout.write(f"     Model: {old_model} → {image.model_id}")
                        self.stdout.write(f"     Submitter: {old_submitter} → {image.task_submitter}")
                    # else:
                    #     self.stdout.write(f"  ✓ Image {image.id} already correct")
                else:
                    self.stdout.write(f"  ⚠️ Could not find task data for image {image.id} (task: {image.task_id[:20]}...)")
                    error_count += 1
                    
            except Exception as e:
                self.stdout.write(f"  ❌ Error processing image {image.id}: {e}")
                error_count += 1
        
        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"   Total images processed: {total_images}")
        self.stdout.write(f"   Successfully updated: {updated_count}")
        self.stdout.write(f"   Errors: {error_count}")
        self.stdout.write(f"   Already correct: {total_images - updated_count - error_count}")
        
        # Show summary of unique models after fix
        from django.db.models import Count
        model_stats = (ArbiusImage.objects
                      .exclude(model_id__isnull=True)
                      .exclude(model_id='')
                      .values('model_id')
                      .annotate(count=Count('id'))
                      .order_by('-count'))
        
        self.stdout.write(f"\n🎯 Model distribution after fix:")
        for i, stat in enumerate(model_stats[:10], 1):  # Top 10
            self.stdout.write(f"   {i}. {stat['model_id']}: {stat['count']} images") 