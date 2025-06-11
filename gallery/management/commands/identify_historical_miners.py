from django.core.management.base import BaseCommand
from django.db.models import Count, Q, Avg, Min, Max
from django.utils import timezone
from datetime import timedelta
from gallery.models import ArbiusImage, MinerAddress
from gallery.services import ArbitrumScanner
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Analyze existing historical image data to identify potential miners and add them to the automine filter'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-images',
            type=int,
            default=50,
            help='Minimum number of images to consider a wallet as a potential miner (default: 50)'
        )
        parser.add_argument(
            '--volume-threshold',
            type=float,
            default=10.0,
            help='Images per day threshold to consider high-volume mining (default: 10.0)'
        )
        parser.add_argument(
            '--burst-threshold',
            type=int,
            default=5,
            help='Number of images in 1 hour to consider burst mining (default: 5)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be identified without adding to database'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress detailed output'
        )
        parser.add_argument(
            '--verify-blockchain',
            action='store_true',
            help='Verify suspected miners by checking for actual solution submissions on blockchain'
        )

    def handle(self, *args, **options):
        if not options['quiet']:
            self.stdout.write('🔍 Analyzing historical image data to identify miners...')
        
        # Get all wallets with image activity
        wallets_with_activity = ArbiusImage.objects.values('task_submitter').annotate(
            image_count=Count('id'),
            first_image=Min('timestamp'),
            last_image=Max('timestamp'),
            avg_images_per_day=Count('id') / (
                (Max('timestamp') - Min('timestamp')).total_seconds() / 86400.0 + 1
            )
        ).filter(
            task_submitter__isnull=False,
            image_count__gte=options['min_images']
        ).order_by('-image_count')

        suspected_miners = []
        
        if not options['quiet']:
            self.stdout.write(f'📊 Found {len(wallets_with_activity)} wallets with {options["min_images"]}+ images')
        
        # Analyze each wallet for mining patterns
        for wallet_data in wallets_with_activity:
            wallet_address = wallet_data['task_submitter']
            image_count = wallet_data['image_count']
            avg_per_day = wallet_data['avg_images_per_day']
            
            # Check if already in miner database
            if MinerAddress.objects.filter(wallet_address__iexact=wallet_address).exists():
                if not options['quiet']:
                    self.stdout.write(f'   ⏭️  {wallet_address[:10]}... already identified as miner')
                continue
            
            mining_score = 0
            reasons = []
            
            # Scoring criteria for mining behavior
            
            # 1. High volume threshold
            if avg_per_day >= options['volume_threshold']:
                mining_score += 3
                reasons.append(f"High volume: {avg_per_day:.1f} images/day")
            
            # 2. Very high total volume
            if image_count >= 200:
                mining_score += 2
                reasons.append(f"High total: {image_count} images")
            elif image_count >= 100:
                mining_score += 1
                reasons.append(f"Moderate volume: {image_count} images")
            
            # 3. Check for burst patterns (many images in short time)
            wallet_images = ArbiusImage.objects.filter(
                task_submitter__iexact=wallet_address
            ).order_by('timestamp')
            
            burst_count = 0
            for i, image in enumerate(wallet_images):
                # Check images within 1 hour window
                one_hour_later = image.timestamp + timedelta(hours=1)
                burst_images = wallet_images.filter(
                    timestamp__gte=image.timestamp,
                    timestamp__lte=one_hour_later
                ).count()
                
                if burst_images >= options['burst_threshold']:
                    burst_count += 1
                    if burst_count >= 3:  # Multiple burst periods
                        mining_score += 2
                        reasons.append(f"Burst pattern: {burst_images} images in 1 hour")
                        break
            
            # 4. Check for regular patterns (consistent daily activity)
            if image_count >= 50:
                # Calculate activity spread over days
                days_active = (wallet_data['last_image'] - wallet_data['first_image']).days + 1
                activity_consistency = image_count / days_active
                
                if activity_consistency >= 5:  # 5+ images per day consistently
                    mining_score += 1
                    reasons.append(f"Consistent activity: {activity_consistency:.1f} images/day")
            
            # 5. Check for automated prompts (repetitive or simple patterns)
            sample_prompts = list(ArbiusImage.objects.filter(
                task_submitter__iexact=wallet_address,
                prompt__isnull=False
            ).exclude(prompt='').values_list('prompt', flat=True)[:20])
            
            if sample_prompts:
                # Check for very repetitive prompts
                unique_prompts = len(set(sample_prompts))
                if unique_prompts <= 3 and len(sample_prompts) >= 10:
                    mining_score += 2
                    reasons.append("Repetitive prompts detected")
                
                # Check for very simple prompts (potential automation)
                simple_prompts = sum(1 for p in sample_prompts if len(p.split()) <= 3)
                if simple_prompts >= len(sample_prompts) * 0.8:
                    mining_score += 1
                    reasons.append("Simple/automated prompts")
            
            # 6. Check for solution provider pattern (if they're also providing solutions)
            solution_count = ArbiusImage.objects.filter(
                solution_provider__iexact=wallet_address
            ).count()
            
            if solution_count >= 20:
                mining_score += 3
                reasons.append(f"Solution provider: {solution_count} solutions")
            
            # Decision threshold
            if mining_score >= 4:  # Minimum score to be considered a miner
                suspected_miners.append({
                    'wallet_address': wallet_address,
                    'image_count': image_count,
                    'avg_per_day': avg_per_day,
                    'mining_score': mining_score,
                    'reasons': reasons,
                    'first_image': wallet_data['first_image'],
                    'last_image': wallet_data['last_image']
                })
        
        if not options['quiet']:
            self.stdout.write(f'\n🎯 Identified {len(suspected_miners)} suspected historical miners:')
            
            for miner in suspected_miners:
                self.stdout.write(f'\n📍 {miner["wallet_address"]}')
                self.stdout.write(f'   Images: {miner["image_count"]} ({miner["avg_per_day"]:.1f}/day)')
                self.stdout.write(f'   Mining Score: {miner["mining_score"]}/10')
                self.stdout.write(f'   Active: {miner["first_image"].date()} to {miner["last_image"].date()}')
                for reason in miner['reasons']:
                    self.stdout.write(f'   • {reason}')
        
        # Verify with blockchain if requested
        if options['verify_blockchain'] and suspected_miners:
            if not options['quiet']:
                self.stdout.write(f'\n🔍 Verifying suspected miners against blockchain...')
            
            scanner = ArbitrumScanner()
            verified_miners = []
            
            for miner in suspected_miners:
                wallet_address = miner['wallet_address']
                
                # Check if this wallet has submitted solutions on blockchain
                # We'll check their image time range for solution submissions
                first_block = ArbiusImage.objects.filter(
                    task_submitter__iexact=wallet_address
                ).order_by('block_number').first().block_number
                
                last_block = ArbiusImage.objects.filter(
                    task_submitter__iexact=wallet_address
                ).order_by('-block_number').first().block_number
                
                try:
                    # Look for solution submissions from this wallet
                    miners_found = scanner.identify_miners_in_range(first_block, last_block)
                    
                    if wallet_address.lower() in [m.lower() for m in miners_found]:
                        verified_miners.append(miner)
                        miner['blockchain_verified'] = True
                        if not options['quiet']:
                            self.stdout.write(f'   ✅ {wallet_address[:10]}... verified on blockchain')
                    else:
                        miner['blockchain_verified'] = False
                        if not options['quiet']:
                            self.stdout.write(f'   ❌ {wallet_address[:10]}... not found on blockchain')
                
                except Exception as e:
                    if not options['quiet']:
                        self.stdout.write(f'   ⚠️  {wallet_address[:10]}... verification failed: {e}')
                    miner['blockchain_verified'] = None
            
            if verified_miners:
                if not options['quiet']:
                    self.stdout.write(f'\n✅ {len(verified_miners)} miners verified against blockchain')
                suspected_miners = verified_miners
            else:
                if not options['quiet']:
                    self.stdout.write(f'\n⚠️  No miners could be verified against blockchain')
        
        # Add to database unless dry run
        if not options['dry_run'] and suspected_miners:
            added_count = 0
            
            for miner in suspected_miners:
                # Skip if verification was requested but failed
                if options['verify_blockchain'] and not miner.get('blockchain_verified'):
                    continue
                
                wallet_address = miner['wallet_address']
                
                # Create MinerAddress record
                miner_obj, created = MinerAddress.objects.get_or_create(
                    wallet_address=wallet_address.lower(),
                    defaults={
                        'first_seen': miner['first_image'],
                        'last_seen': miner['last_image'],
                        'total_solutions': 0,  # Will be updated by future scans
                        'total_commitments': 0,
                        'is_active': True  # Assume active until proven otherwise
                    }
                )
                
                if created:
                    added_count += 1
                    if not options['quiet']:
                        self.stdout.write(f'   ✅ Added {wallet_address[:10]}... to miner database')
                else:
                    if not options['quiet']:
                        self.stdout.write(f'   ⏭️  {wallet_address[:10]}... already in database')
            
            if not options['quiet']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n🎉 Historical miner analysis complete!\n'
                        f'📊 Added {added_count} new miners to automine filter\n'
                        f'🔍 Total miners now: {MinerAddress.objects.count()}'
                    )
                )
        
        elif options['dry_run']:
            if not options['quiet']:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n🔍 Dry run complete - {len(suspected_miners)} miners would be added\n'
                        f'Run without --dry-run to actually add them to the database'
                    )
                )
        
        else:
            if not options['quiet']:
                self.stdout.write('❓ No historical miners identified with current criteria')
        
        return len(suspected_miners) 