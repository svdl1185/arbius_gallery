#!/usr/bin/env python
"""
Management command for periodic blockchain scanning
Run this with: python manage.py scan_periodic
"""

import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from gallery.services import ArbitrumScanner
from gallery.models import ScanStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scan blockchain for new Arbius images periodically'

    def add_arguments(self, parser):
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously with periodic scanning (every 5 minutes)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=300,  # 5 minutes
            help='Interval between scans in seconds (default: 300)',
        )
        parser.add_argument(
            '--initial-weeks',
            type=int,
            default=0,
            help='Scan this many weeks back on first run (0 = skip initial scan)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting Arbius periodic scanner...')
        )
        
        scanner = ArbitrumScanner()
        continuous = options['continuous']
        interval = options['interval']
        initial_weeks = options['initial_weeks']
        
        # Check if this is the first run
        scan_status, created = ScanStatus.objects.get_or_create(
            id=1,
            defaults={'last_scanned_block': 0}
        )
        
        # Initial historical scan if requested
        if initial_weeks > 0:
            self.stdout.write(
                self.style.WARNING(f'📅 Running historical scan ({initial_weeks} weeks)...')
            )
            try:
                new_images = scanner.scan_recent_weeks(initial_weeks)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Historical scan complete! Found {new_images} images')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Historical scan failed: {e}')
                )
        
        if continuous:
            self.stdout.write(
                self.style.SUCCESS(f'🔄 Starting continuous scanning (every {interval} seconds)...')
            )
            self.stdout.write(
                self.style.WARNING('Press Ctrl+C to stop')
            )
            
            scan_count = 0
            try:
                while True:
                    scan_count += 1
                    current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    self.stdout.write(f'\n🔍 Scan #{scan_count} at {current_time}')
                    
                    try:
                        new_images = scanner.scan_new_blocks()
                        
                        if new_images > 0:
                            self.stdout.write(
                                self.style.SUCCESS(f'🎉 Found {new_images} new images!')
                            )
                        else:
                            self.stdout.write('✅ No new images found')
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'❌ Scan failed: {e}')
                        )
                        logger.error(f"Periodic scan error: {e}")
                    
                    self.stdout.write(f'⏰ Waiting {interval} seconds until next scan...')
                    time.sleep(interval)
                    
            except KeyboardInterrupt:
                self.stdout.write(
                    self.style.WARNING('\n🛑 Stopped by user')
                )
        else:
            # Single scan (only if no historical scan was requested)
            if initial_weeks == 0:
                self.stdout.write('🔍 Running single scan...')
                try:
                    new_images = scanner.scan_new_blocks()
                    
                    if new_images > 0:
                        self.stdout.write(
                            self.style.SUCCESS(f'🎉 Single scan complete! Found {new_images} new images')
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS('✅ Single scan complete. No new images found.')
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Single scan failed: {e}')
                    )
                    logger.error(f"Single scan error: {e}")
        
        self.stdout.write(
            self.style.SUCCESS('🏁 Scanner finished')
        ) 