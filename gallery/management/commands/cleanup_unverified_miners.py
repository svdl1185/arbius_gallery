from django.core.management.base import BaseCommand
from django.db import models
from gallery.models import MinerAddress, ArbiusImage
from gallery.services import ArbitrumScanner
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Remove miners from database who do not have verified solution submissions to the engine contract'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be removed without actually removing'
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=10000,
            help='Block range to scan at once'
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 Cleaning up unverified miners...")
        
        # Get all current miners
        current_miners = list(MinerAddress.objects.values_list('wallet_address', flat=True))
        self.stdout.write(f"📊 Current miners in database: {len(current_miners)}")
        
        if not current_miners:
            self.stdout.write("✅ No miners to verify")
            return
        
        # Get block range from database
        block_stats = ArbiusImage.objects.aggregate(
            min_block=models.Min('block_number'),
            max_block=models.Max('block_number')
        )
        
        min_block = block_stats['min_block'] or 0
        max_block = block_stats['max_block'] or 0
        
        if min_block == 0 or max_block == 0:
            self.stdout.write("❌ No block data found")
            return
            
        self.stdout.write(f"🔍 Scanning blocks {min_block:,} to {max_block:,}")
        
        # Scan blockchain for verified miners
        scanner = ArbitrumScanner()
        verified_miners = set()
        chunk_size = options['chunk_size']
        
        for start_block in range(min_block, max_block + 1, chunk_size):
            end_block = min(start_block + chunk_size - 1, max_block)
            
            try:
                self.stdout.write(f"🔎 Scanning blocks {start_block:,} - {end_block:,}...")
                miners_in_chunk = scanner.identify_miners_in_range(start_block, end_block)
                
                for miner in miners_in_chunk:
                    verified_miners.add(miner.lower())
                
                self.stdout.write(f"   Found {len(verified_miners)} unique verified miners so far")
                
            except Exception as e:
                self.stdout.write(f"⚠️  Error scanning {start_block}-{end_block}: {e}")
                continue
        
        self.stdout.write(f"✅ Total verified miners found: {len(verified_miners)}")
        
        # Identify unverified miners
        unverified_miners = []
        for miner_address in current_miners:
            if miner_address.lower() not in verified_miners:
                unverified_miners.append(miner_address)
        
        if not unverified_miners:
            self.stdout.write("✅ All miners are verified!")
            return
        
        self.stdout.write(f"🎯 Found {len(unverified_miners)} unverified miners:")
        for miner in unverified_miners:
            self.stdout.write(f"   - {miner}")
        
        if options['dry_run']:
            self.stdout.write("🔍 DRY RUN - Would remove these miners but not actually removing")
        else:
            # Remove unverified miners
            removed_count = 0
            for miner_address in unverified_miners:
                deleted = MinerAddress.objects.filter(wallet_address__iexact=miner_address).delete()
                if deleted[0] > 0:
                    self.stdout.write(f"❌ Removed: {miner_address}")
                    removed_count += 1
            
            remaining_count = MinerAddress.objects.count()
            self.stdout.write(f"✅ Cleanup complete!")
            self.stdout.write(f"   - Removed: {removed_count} unverified miners")
            self.stdout.write(f"   - Remaining: {remaining_count} verified miners") 