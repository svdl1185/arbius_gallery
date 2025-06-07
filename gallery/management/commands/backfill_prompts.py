from django.core.management.base import BaseCommand
from gallery.models import ArbiusImage
from gallery.services import ArbitrumScanner


class Command(BaseCommand):
    help = 'Backfill missing prompts for images that don\'t have them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating anything'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of images to process (default: 50)'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Starting prompt backfill...')
        )
        
        # Find images without prompts
        images_without_prompts = ArbiusImage.objects.filter(
            is_accessible=True,
            prompt__in=['', None]
        ).exclude(
            task_id__isnull=True
        ).exclude(
            task_id=''
        )[:options['limit']]
        
        self.stdout.write(f"Found {images_without_prompts.count()} images without prompts (processing {len(images_without_prompts)} in this batch)")
        
        scanner = ArbitrumScanner()
        updated_count = 0
        
        for image in images_without_prompts:
            try:
                self.stdout.write(f"Processing image {image.cid[:20]}... (Block {image.block_number})")
                
                # Try a more extensive search for the task
                task_data = scanner.find_task_by_id_optimized(
                    image.task_id, 
                    image.block_number, 
                    max_search_range=50000  # Larger search range
                )
                
                if task_data and task_data.get('prompt'):
                    prompt = task_data['prompt']
                    model_id = task_data.get('model_id')
                    task_submitter = task_data.get('submitter')
                    
                    # Skip if it's a text model output
                    if (prompt.strip().startswith('<|begin_of_text|>') or 
                        prompt.strip().startswith('<|end_of_text|>') or
                        len(prompt.strip()) > 5000):
                        self.stdout.write(f"  ⏭️ Skipping {image.cid[:20]}... (text model output)")
                        continue
                    
                    if options['dry_run']:
                        prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
                        self.stdout.write(f"  ✅ Would update with prompt: \"{prompt_preview}\"")
                        if model_id:
                            self.stdout.write(f"      Model: {model_id[:20]}...")
                        if task_submitter:
                            self.stdout.write(f"      Submitter: {task_submitter}")
                    else:
                        # Update the image
                        image.prompt = prompt
                        if model_id:
                            image.model_id = model_id
                        if task_submitter:
                            image.task_submitter = task_submitter
                        image.save()
                        
                        prompt_preview = prompt[:50] + "..." if len(prompt) > 50 else prompt
                        self.stdout.write(f"  ✅ Updated with prompt: \"{prompt_preview}\"")
                        updated_count += 1
                else:
                    self.stdout.write(f"  ❌ No task data found for {image.cid[:20]}...")
                    
            except Exception as e:
                self.stdout.write(f"  ⚠️ Error processing {image.cid[:20]}...: {e}")
                continue
        
        if options['dry_run']:
            self.stdout.write(f"📊 Dry run complete - found prompts for several images")
        else:
            self.stdout.write(f"✅ Backfill complete! Updated {updated_count} images with prompts")
        
        # Show updated statistics
        if not options['dry_run']:
            remaining_without_prompts = ArbiusImage.objects.filter(
                is_accessible=True,
                prompt__in=['', None]
            ).count()
            
            total_accessible = ArbiusImage.objects.filter(is_accessible=True).count()
            with_prompts = total_accessible - remaining_without_prompts
            
            self.stdout.write(f"📈 Gallery statistics:")
            self.stdout.write(f"  • Total accessible images: {total_accessible}")
            self.stdout.write(f"  • Images with prompts: {with_prompts} ({with_prompts/total_accessible*100:.1f}%)")
            self.stdout.write(f"  • Images without prompts: {remaining_without_prompts} ({remaining_without_prompts/total_accessible*100:.1f}%)") 