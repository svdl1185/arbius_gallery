from django.core.management.base import BaseCommand, CommandError
from gallery.token_tracking_service import token_tracker
from gallery.models import MinerAddress, MinerTokenEarnings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Analyze miner wallets for AIUS token movements and sales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--miner',
            type=str,
            help='Analyze a specific miner wallet address',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reanalysis even if recently analyzed',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Analyze all known miners',
        )

    def handle(self, *args, **options):
        if options['miner']:
            # Analyze specific miner
            miner_address = options['miner']
            self.stdout.write(f"Analyzing miner: {miner_address}")
            
            try:
                earnings = token_tracker.process_miner_wallet(miner_address)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Analysis complete for {miner_address}:\n"
                        f"   - AIUS Earned: {earnings.total_aius_earned}\n"
                        f"   - AIUS Sold: {earnings.total_aius_sold}\n"
                        f"   - USD from Sales: ${earnings.total_usd_from_sales}"
                    )
                )
            except Exception as e:
                raise CommandError(f"Error analyzing miner {miner_address}: {e}")
                
        elif options['all']:
            # Analyze all miners
            self.stdout.write("Starting analysis of all known miners...")
            
            try:
                results = token_tracker.analyze_all_miners(force_reanalysis=options['force'])
                
                total_miners = len(results)
                total_aius_earned = sum(r.total_aius_earned for r in results)
                total_usd_from_sales = sum(r.total_usd_from_sales for r in results)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Analysis complete for {total_miners} miners:\n"
                        f"   - Total AIUS Earned: {total_aius_earned}\n"
                        f"   - Total USD from Sales: ${total_usd_from_sales}"
                    )
                )
                
                # Show top earners
                top_earners = sorted(results, key=lambda x: x.total_usd_from_sales, reverse=True)[:5]
                if top_earners:
                    self.stdout.write("\n🏆 Top 5 earners by USD sales:")
                    for i, earner in enumerate(top_earners, 1):
                        self.stdout.write(
                            f"   {i}. {earner.miner_address[:8]}...{earner.miner_address[-6:]}: "
                            f"${earner.total_usd_from_sales:.2f}"
                        )
                        
            except Exception as e:
                raise CommandError(f"Error during bulk analysis: {e}")
                
        else:
            # Show current status
            self.stdout.write("Current Token Analysis Status:")
            
            total_miners = MinerAddress.objects.count()
            analyzed_miners = MinerTokenEarnings.objects.count()
            
            self.stdout.write(f"📊 Total known miners: {total_miners}")
            self.stdout.write(f"📊 Analyzed miners: {analyzed_miners}")
            
            if analyzed_miners > 0:
                summary = token_tracker.get_miner_earnings_summary()
                self.stdout.write(f"💰 Total AIUS earned: {summary['total_aius_earned']}")
                self.stdout.write(f"💵 Total USD from sales: ${summary['total_usd_from_sales']}")
                
                # Show miners needing analysis
                needs_analysis = total_miners - analyzed_miners
                if needs_analysis > 0:
                    self.stdout.write(f"⚠️  {needs_analysis} miners need analysis")
                    self.stdout.write("Run with --all to analyze all miners")
            else:
                self.stdout.write("⚠️  No miners have been analyzed yet")
                self.stdout.write("Run with --all to start analysis") 