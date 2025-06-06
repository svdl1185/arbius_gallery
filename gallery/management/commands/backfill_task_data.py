from django.core.management.base import BaseCommand
from gallery.services import ArbitrumScanner
from gallery.models import ArbiusImage
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill missing task data (submitter, model, prompt) for existing images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Number of images to process per run (default: 50)'
        )
        parser.add_argument(
            '--missing-only',
            action='store_true',
            help='Only process images missing task_submitter or model_id'
        )
        parser.add_argument(
            '--lookback-blocks',
            type=int,
            default=50000,
            help='How many blocks to look back for task information (default: 10000)'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress output (for scheduled runs)'
        )

    def handle(self, *args, **options):
        scanner = ArbitrumScanner()
        
        if not options['quiet']:
            self.stdout.write('🔍 Starting backfill of missing task data...')
        
        # Build query for images to process
        queryset = ArbiusImage.objects.all()
        
        if options['missing_only']:
            # Only process images missing critical task data
            from django.db.models import Q
            queryset = queryset.filter(
                Q(task_submitter__isnull=True) | 
                Q(task_submitter='') | 
                Q(model_id__isnull=True) | 
                Q(model_id='') |
                Q(prompt__isnull=True) |
                Q(prompt='')
            )
            if not options['quiet']:
                self.stdout.write(f'📊 Found {queryset.count()} images missing task data')
        
        # Order by newest first, limit results
        images_to_process = queryset.order_by('-timestamp')[:options['limit']]
        
        if not images_to_process:
            if not options['quiet']:
                self.stdout.write(self.style.SUCCESS('✅ No images need task data backfill'))
            return
        
        if not options['quiet']:
            self.stdout.write(f'🔄 Processing {len(images_to_process)} images...')
        
        updated_count = 0
        
        for image in images_to_process:
            try:
                # Use smaller, more targeted search ranges
                search_ranges = [
                    (image.block_number - 5000, image.block_number + 100),   # Close range first
                    (image.block_number - options['lookback_blocks'], image.block_number - 5000)  # Extended range if needed
                ]
                
                if not options['quiet']:
                    self.stdout.write(f'   📦 Processing {image.cid[:20]}... (Block {image.block_number})')
                
                task_data = None
                
                # Try each search range until we find task data
                for search_start, search_end in search_ranges:
                    if search_start >= search_end:
                        continue
                        
                    try:
                        if not options['quiet']:
                            self.stdout.write(f'      🔍 Searching blocks {search_start} to {search_end}...')
                        
                        # Get task information for this smaller block range
                        task_info = scanner.get_task_information(search_start, search_end)
                        
                        if image.task_id and image.task_id in task_info:
                            task_data = task_info[image.task_id]
                            if not options['quiet']:
                                self.stdout.write(f'      ✅ Found task data in range!')
                            break
                            
                    except Exception as e:
                        if not options['quiet']:
                            self.stdout.write(f'      ⚠️ Search range {search_start}-{search_end} failed: {e}')
                        continue
                
                if task_data:
                    updated = False
                    
                    # Update missing fields
                    if not image.task_submitter and task_data.get('submitter'):
                        image.task_submitter = task_data['submitter']
                        updated = True
                        if not options['quiet']:
                            self.stdout.write(f'      ✅ Found task submitter: {task_data["submitter"][:20]}...')
                    
                    if not image.model_id and task_data.get('model_id'):
                        image.model_id = task_data['model_id']
                        updated = True
                        if not options['quiet']:
                            self.stdout.write(f'      ✅ Found model ID: {task_data["model_id"][:20]}...')
                    
                    if not image.prompt and task_data.get('prompt'):
                        image.prompt = task_data['prompt']
                        updated = True
                        if not options['quiet']:
                            prompt_preview = task_data['prompt'][:50] + "..." if len(task_data['prompt']) > 50 else task_data['prompt']
                            self.stdout.write(f'      ✅ Found prompt: "{prompt_preview}"')
                    
                    if not image.input_parameters and task_data.get('input_parameters'):
                        image.input_parameters = task_data['input_parameters']
                        updated = True
                    
                    if updated:
                        image.save()
                        updated_count += 1
                        if not options['quiet']:
                            self.stdout.write(f'      💾 Updated image record')
                    else:
                        if not options['quiet']:
                            self.stdout.write(f'      ⏭️ No new data found')
                else:
                    if not options['quiet']:
                        self.stdout.write(f'      ❌ No task data found for task {image.task_id}')
                
            except Exception as e:
                error_msg = f'Error processing image {image.cid}: {e}'
                if not options['quiet']:
                    self.stdout.write(self.style.ERROR(f'      ❌ {error_msg}'))
                logger.error(error_msg)
                continue
        
        # Final summary
        if not options['quiet']:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Backfill complete! Updated {updated_count} images with task data')
            )
        else:
            logger.info(f'Backfilled task data for {updated_count} images')
        
        # Show updated stats
        total_images = ArbiusImage.objects.count()
        images_with_submitter = ArbiusImage.objects.exclude(task_submitter__isnull=True).exclude(task_submitter='').count()
        images_with_model = ArbiusImage.objects.exclude(model_id__isnull=True).exclude(model_id='').count()
        images_with_prompt = ArbiusImage.objects.exclude(prompt__isnull=True).exclude(prompt='').count()
        
        if not options['quiet']:
            self.stdout.write(f'📊 Current stats:')
            self.stdout.write(f'   Total images: {total_images}')
            self.stdout.write(f'   With task submitter: {images_with_submitter}')
            self.stdout.write(f'   With model ID: {images_with_model}')
            self.stdout.write(f'   With prompt: {images_with_prompt}') 