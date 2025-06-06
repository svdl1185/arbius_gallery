from django.core.management.base import BaseCommand
from gallery.services import ArbitrumScanner
from gallery.models import ArbiusImage
import logging
import requests
import time

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Enhanced backfill using direct event lookup instead of block scanning'

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
            '--method',
            choices=['direct', 'batch', 'hybrid'],
            default='hybrid',
            help='Lookup method: direct (1-by-1), batch (group by blocks), hybrid (try direct first)'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress output (for scheduled runs)'
        )

    def handle(self, *args, **options):
        scanner = ArbitrumScanner()
        
        if not options['quiet']:
            self.stdout.write('🚀 Starting enhanced backfill with better lookup methods...')
        
        # Build query for images to process
        queryset = ArbiusImage.objects.all()
        
        if options['missing_only']:
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
            self.stdout.write(f'🔄 Processing {len(images_to_process)} images using {options["method"]} method...')
        
        if options['method'] == 'direct':
            updated_count = self._direct_lookup_method(scanner, images_to_process, options['quiet'])
        elif options['method'] == 'batch':
            updated_count = self._batch_lookup_method(scanner, images_to_process, options['quiet'])
        else:  # hybrid
            updated_count = self._hybrid_lookup_method(scanner, images_to_process, options['quiet'])
        
        # Final summary
        if not options['quiet']:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Enhanced backfill complete! Updated {updated_count} images with task data')
            )
        else:
            logger.info(f'Enhanced backfilled task data for {updated_count} images')

    def _direct_lookup_method(self, scanner, images, quiet):
        """Method 1: Direct event lookup by task ID - most efficient for individual lookups"""
        updated_count = 0
        
        for image in images:
            if not image.task_id:
                continue
                
            try:
                if not quiet:
                    self.stdout.write(f'   🔍 Direct lookup for {image.cid[:20]}... (Task: {image.task_id[:20]}...)')
                
                task_data = self._direct_event_lookup(scanner, image.task_id)
                
                if task_data:
                    if self._update_image_with_task_data(image, task_data, quiet):
                        updated_count += 1
                else:
                    if not quiet:
                        self.stdout.write(f'      ❌ No task data found')
                        
            except Exception as e:
                if not quiet:
                    self.stdout.write(self.style.ERROR(f'      ❌ Error: {e}'))
                logger.error(f'Error in direct lookup for {image.cid}: {e}')
        
        return updated_count

    def _batch_lookup_method(self, scanner, images, quiet):
        """Method 2: Batch lookup by grouping images by block ranges"""
        updated_count = 0
        
        # Group images by block ranges
        block_ranges = {}
        for image in images:
            if not image.task_id:
                continue
            block_range = (image.block_number // 5000) * 5000  # 5000-block chunks
            if block_range not in block_ranges:
                block_ranges[block_range] = []
            block_ranges[block_range].append(image)
        
        if not quiet:
            self.stdout.write(f'   📦 Grouped {len(images)} images into {len(block_ranges)} block ranges')
        
        for block_start, range_images in block_ranges.items():
            if not quiet:
                self.stdout.write(f'   🔍 Processing block range {block_start} to {block_start + 4999}')
            
            try:
                # Get all task info for this range at once
                task_info = scanner.get_task_information(block_start - 2000, block_start + 4999)
                
                if not quiet:
                    self.stdout.write(f'      Found {len(task_info)} task submissions in range')
                
                # Update all images in this range
                for image in range_images:
                    if image.task_id in task_info:
                        if self._update_image_with_task_data(image, task_info[image.task_id], quiet):
                            updated_count += 1
                    else:
                        if not quiet:
                            self.stdout.write(f'      ❌ No data for {image.cid[:20]}...')
                            
            except Exception as e:
                if not quiet:
                    self.stdout.write(self.style.ERROR(f'      ❌ Error processing range: {e}'))
                logger.error(f'Error in batch lookup for range {block_start}: {e}')
        
        return updated_count

    def _hybrid_lookup_method(self, scanner, images, quiet):
        """Method 3: Hybrid - try direct lookup first, fall back to batch for failures"""
        updated_count = 0
        failed_images = []
        
        # First pass: Direct lookups
        if not quiet:
            self.stdout.write('   🎯 Phase 1: Direct lookups')
        
        for image in images:
            if not image.task_id:
                continue
                
            try:
                task_data = self._direct_event_lookup(scanner, image.task_id)
                
                if task_data:
                    if self._update_image_with_task_data(image, task_data, quiet):
                        updated_count += 1
                else:
                    failed_images.append(image)
                    
            except Exception as e:
                failed_images.append(image)
                if not quiet:
                    self.stdout.write(f'      ⚠️ Direct lookup failed for {image.cid[:20]}..., will retry in batch')
        
        # Second pass: Batch lookup for failures
        if failed_images:
            if not quiet:
                self.stdout.write(f'   📦 Phase 2: Batch lookup for {len(failed_images)} remaining images')
            
            batch_updated = self._batch_lookup_method(scanner, failed_images, quiet)
            updated_count += batch_updated
        
        return updated_count

    def _direct_event_lookup(self, scanner, task_id):
        """Perform direct event lookup for a specific task ID"""
        try:
            scanner._rate_limit()
            
            # Use the most recent blocks - tasks are usually recent
            latest_block = scanner.get_latest_block()
            search_blocks = 50000  # Much smaller than old approach
            
            params = {
                'module': 'logs',
                'action': 'getLogs',
                'address': scanner.engine_address,
                'topic0': scanner.task_submitted_topic,
                'topic1': task_id,  # Direct filtering by task ID
                'fromBlock': latest_block - search_blocks,
                'toBlock': latest_block,
                'apikey': scanner.api_key
            }
            
            response = requests.get(scanner.base_url, params=params, timeout=15)
            data = response.json()
            
            if data.get('status') == '1' and data.get('result'):
                log = data['result'][0]  # Should be exactly one result
                return scanner.parse_task_submitted_event(log)
            
            return None
            
        except Exception as e:
            logger.warning(f'Direct event lookup failed for task {task_id}: {e}')
            return None

    def _update_image_with_task_data(self, image, task_data, quiet):
        """Update image with task data and return True if any updates were made"""
        updated = False
        
        # Update missing fields
        if not image.task_submitter and task_data.get('submitter'):
            image.task_submitter = task_data['submitter']
            updated = True
            if not quiet:
                self.stdout.write(f'      ✅ Found submitter: {task_data["submitter"][:20]}...')
        
        if not image.model_id and task_data.get('model_id'):
            image.model_id = task_data['model_id']
            updated = True
            if not quiet:
                self.stdout.write(f'      ✅ Found model: {task_data["model_id"][:20]}...')
        
        if not image.prompt and task_data.get('prompt'):
            image.prompt = task_data['prompt']
            updated = True
            if not quiet:
                prompt_preview = task_data['prompt'][:50] + "..." if len(task_data['prompt']) > 50 else task_data['prompt']
                self.stdout.write(f'      ✅ Found prompt: "{prompt_preview}"')
        
        if not image.input_parameters and task_data.get('input_parameters'):
            image.input_parameters = task_data['input_parameters']
            updated = True
        
        if updated:
            image.save()
            if not quiet:
                self.stdout.write(f'      💾 Updated {image.cid[:20]}...')
        
        return updated 