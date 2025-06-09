from django.core.management.base import BaseCommand
from gallery.services import ArbitrumScanner
from gallery.models import MinerAddress
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Identify miner wallet addresses by scanning blockchain for solution submissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='Number of hours back to scan for miner activity (default: 1)'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress output (for scheduled runs)'
        )
        parser.add_argument(
            '--initial-scan',
            action='store_true',
            help='Perform initial scan of last 24 hours to populate miner database'
        )

    def handle(self, *args, **options):
        scanner = ArbitrumScanner()
        
        if not options['quiet']:
            self.stdout.write('🔍 Starting miner identification scan...')
        
        try:
            # Determine scan period
            hours_back = 24 if options['initial_scan'] else options['hours']
            
            if not options['quiet']:
                period_desc = "initial 24-hour" if options['initial_scan'] else f"last {hours_back} hour(s)"
                self.stdout.write(f'📊 Scanning {period_desc} for miner activity...')
            
            # Scan for miners
            miners = scanner.scan_for_miners(hours_back)
            
            # Get current statistics
            total_miners = MinerAddress.objects.count()
            active_miners = MinerAddress.objects.filter(is_active=True).count()
            inactive_miners = total_miners - active_miners
            
            if not options['quiet']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Miner scan complete!\n'
                        f'🔍 Found {len(miners)} miners in this scan\n'
                        f'📊 Database stats:\n'
                        f'   • Total miners: {total_miners}\n'
                        f'   • Active miners: {active_miners}\n'
                        f'   • Inactive miners: {inactive_miners}'
                    )
                )
            else:
                logger.info(f'Miner scan found {len(miners)} miners ({active_miners} active, {total_miners} total)')
                
        except Exception as e:
            error_msg = f'Error during miner scan: {e}'
            if not options['quiet']:
                self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise 