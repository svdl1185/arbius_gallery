from django.core.management.base import BaseCommand
from django.utils import timezone
from gallery.models import ArbiusImage, MinerAddress
from gallery.services import ArbitrumScanner
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scan historical blockchain data to identify miners based on solution submissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-block',
            type=int,
            help='Starting block number for historical scan'
        )
        parser.add_argument(
            '--end-block',
            type=int,
            help='Ending block number for historical scan'
        )
        parser.add_argument(
            '--from-database',
            action='store_true',
            help='Use the block range from existing images in database'
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=10000,
            help='Number of blocks to scan per chunk (default: 10000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be found without adding to database'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress detailed output'
        )

    def handle(self, *args, **options):
        scanner = ArbitrumScanner()
        
        if not options['quiet']:
            self.stdout.write('🔍 Scanning historical blockchain for miner solution submissions...')
        
        # Determine block range
        if options['from_database']:
            # Use the range from existing images
            oldest_image = ArbiusImage.objects.order_by('block_number').first()
            newest_image = ArbiusImage.objects.order_by('-block_number').first()
            
            if not oldest_image or not newest_image:
                self.stdout.write(self.style.ERROR('❌ No images found in database'))
                return
            
            start_block = oldest_image.block_number
            end_block = newest_image.block_number
            
            if not options['quiet']:
                self.stdout.write(f'📊 Using database range: blocks {start_block} to {end_block}')
                self.stdout.write(f'   Oldest image: {oldest_image.timestamp.date()}')
                self.stdout.write(f'   Newest image: {newest_image.timestamp.date()}')
        
        elif options['start_block'] and options['end_block']:
            start_block = options['start_block']
            end_block = options['end_block']
            
            if not options['quiet']:
                self.stdout.write(f'📊 Using specified range: blocks {start_block} to {end_block}')
        
        else:
            # Default: scan last 100k blocks
            try:
                latest_block = scanner.get_latest_block()
                if not latest_block:
                    self.stdout.write(self.style.ERROR('❌ Could not get latest block number'))
                    return
                
                start_block = latest_block - 100000
                end_block = latest_block
                
                if not options['quiet']:
                    self.stdout.write(f'📊 Using default range: last 100k blocks ({start_block} to {end_block})')
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error getting latest block: {e}'))
                return
        
        if start_block >= end_block:
            self.stdout.write(self.style.ERROR('❌ Invalid block range'))
            return
        
        total_blocks = end_block - start_block + 1
        chunk_size = options['chunk_size']
        total_chunks = (total_blocks + chunk_size - 1) // chunk_size
        
        if not options['quiet']:
            self.stdout.write(f'📦 Will scan {total_blocks:,} blocks in {total_chunks} chunks of {chunk_size:,}')
        
        all_miners_found = set()
        new_miners_added = 0
        
        # Scan in chunks
        for chunk_num in range(total_chunks):
            chunk_start = start_block + (chunk_num * chunk_size)
            chunk_end = min(chunk_start + chunk_size - 1, end_block)
            
            if not options['quiet']:
                progress = ((chunk_num + 1) / total_chunks) * 100
                self.stdout.write(f'\n📦 Chunk {chunk_num + 1}/{total_chunks} ({progress:.1f}%): blocks {chunk_start:,} to {chunk_end:,}')
            
            try:
                # Identify miners in this block range
                miners_in_chunk = scanner.identify_miners_in_range(chunk_start, chunk_end)
                
                if miners_in_chunk:
                    all_miners_found.update(miners_in_chunk)
                    
                    if not options['quiet']:
                        self.stdout.write(f'   🔍 Found {len(miners_in_chunk)} miners in this chunk')
                        
                        # Show some details
                        for miner in miners_in_chunk[:3]:  # Show first 3
                            self.stdout.write(f'      • {miner[:10]}...')
                
                # Process the found miners
                if not options['dry_run']:
                    for miner_address in miners_in_chunk:
                        # Check if already exists
                        miner_obj, created = MinerAddress.objects.get_or_create(
                            wallet_address=miner_address.lower(),
                            defaults={
                                'first_seen': timezone.now(),
                                'last_seen': timezone.now(),
                                'total_solutions': 1,  # At least one solution found
                                'total_commitments': 0,
                                'is_active': True
                            }
                        )
                        
                        if created:
                            new_miners_added += 1
                            if not options['quiet']:
                                self.stdout.write(f'      ✅ Added {miner_address[:10]}... to miner database')
                        else:
                            # Update activity if already exists
                            miner_obj.last_seen = timezone.now()
                            miner_obj.total_solutions += 1
                            miner_obj.save()
                            
                            if not options['quiet']:
                                self.stdout.write(f'      🔄 Updated {miner_address[:10]}... activity')
                
                else:
                    if not options['quiet'] and miners_in_chunk:
                        self.stdout.write(f'   🔍 Would add {len(miners_in_chunk)} miners from this chunk')
            
            except Exception as e:
                self.stdout.write(f'   ❌ Error processing chunk {chunk_num + 1}: {e}')
                continue
        
        # Summary
        if not options['quiet']:
            self.stdout.write(f'\n🎉 Historical blockchain scan complete!')
            self.stdout.write(f'📊 Total unique miners found: {len(all_miners_found)}')
            
            if not options['dry_run']:
                self.stdout.write(f'✅ New miners added to database: {new_miners_added}')
                self.stdout.write(f'🔍 Total miners in database: {MinerAddress.objects.count()}')
                
                # Show some statistics
                active_miners = MinerAddress.objects.filter(is_active=True).count()
                self.stdout.write(f'📈 Active miners: {active_miners}')
                
                # Show activity distribution
                high_activity = MinerAddress.objects.filter(total_solutions__gte=100).count()
                medium_activity = MinerAddress.objects.filter(total_solutions__gte=10, total_solutions__lt=100).count()
                low_activity = MinerAddress.objects.filter(total_solutions__lt=10).count()
                
                self.stdout.write(f'📊 Activity distribution:')
                self.stdout.write(f'   • High (100+ solutions): {high_activity}')
                self.stdout.write(f'   • Medium (10-99 solutions): {medium_activity}')
                self.stdout.write(f'   • Low (1-9 solutions): {low_activity}')
            
            else:
                self.stdout.write(self.style.WARNING('🔍 Dry run - no changes made to database'))
                self.stdout.write('Run without --dry-run to add miners to the database')
        
        # Show impact on filtering
        if not options['dry_run'] and new_miners_added > 0:
            # Count images that would now be filtered
            all_miner_addresses = list(MinerAddress.objects.values_list('wallet_address', flat=True))
            filtered_images = ArbiusImage.objects.filter(
                task_submitter__in=all_miner_addresses
            ).count()
            
            total_images = ArbiusImage.objects.count()
            filter_percentage = (filtered_images / total_images) * 100 if total_images > 0 else 0
            
            if not options['quiet']:
                self.stdout.write(f'\n📊 Automine filter impact:')
                self.stdout.write(f'   • Images that will be filtered: {filtered_images:,} ({filter_percentage:.1f}%)')
                self.stdout.write(f'   • Images remaining: {total_images - filtered_images:,}')
        
        return len(all_miners_found) 