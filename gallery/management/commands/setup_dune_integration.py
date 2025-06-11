"""
Management command to set up and test Dune Analytics integration for Arbius mining data.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from gallery.dune_service import dune_service
import os


class Command(BaseCommand):
    help = 'Set up and test Dune Analytics integration for Arbius mining earnings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-query',
            type=int,
            help='Test a specific Dune query ID',
        )
        parser.add_argument(
            '--check-setup',
            action='store_true',
            help='Check if Dune integration is properly set up',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 Checking Dune Analytics Integration...')
        
        # Check if dune-client is installed
        try:
            from dune_client.client import DuneClient
            self.stdout.write(self.style.SUCCESS('✅ dune-client package is installed'))
        except ImportError:
            self.stdout.write(self.style.ERROR('❌ dune-client package not found'))
            self.stdout.write('Install with: pip install dune-client')
            return
        
        # Check API key
        api_key = getattr(settings, 'DUNE_API_KEY', None)
        if not api_key:
            self.stdout.write(self.style.WARNING('⚠️  DUNE_API_KEY not set in settings'))
            self.stdout.write('\nTo set up Dune Analytics integration:')
            self.stdout.write('1. Get a Dune API key from https://dune.com/settings/api')
            self.stdout.write('2. Add DUNE_API_KEY to your environment variables or settings.py')
            self.stdout.write('3. Example: export DUNE_API_KEY="your_api_key_here"')
            return
        else:
            masked_key = api_key[:8] + '***' + api_key[-4:]
            self.stdout.write(self.style.SUCCESS(f'✅ DUNE_API_KEY found: {masked_key}'))
        
        # Test service availability
        if dune_service.is_available():
            self.stdout.write(self.style.SUCCESS('✅ Dune service is available'))
        else:
            self.stdout.write(self.style.ERROR('❌ Dune service is not available'))
            return
        
        if options['check_setup']:
            self.stdout.write('\n📊 Testing basic connection...')
            try:
                # Try to get earnings data (will be empty for now)
                data = dune_service.get_miner_earnings_data()
                if data:
                    self.stdout.write(self.style.SUCCESS('✅ Connection successful'))
                    self.stdout.write(f"Data structure: {list(data.keys())}")
                else:
                    self.stdout.write(self.style.WARNING('⚠️  No data returned (expected for now)'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Connection failed: {e}'))
        
        if options['test_query']:
            query_id = options['test_query']
            self.stdout.write(f'\n🔍 Testing query {query_id}...')
            
            try:
                results = dune_service.execute_custom_query(query_id)
                if results:
                    self.stdout.write(self.style.SUCCESS(f'✅ Query executed successfully'))
                    self.stdout.write(f'Returned {len(results)} rows')
                    if results:
                        self.stdout.write(f'Sample row: {results[0]}')
                else:
                    self.stdout.write(self.style.WARNING('⚠️  Query returned no data'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Query failed: {e}'))
        
        self.stdout.write('\n📝 Next Steps:')
        self.stdout.write('1. Find the Arbius dashboard query IDs from: https://dune.com/missingno69420/arbius')
        self.stdout.write('2. Update gallery/dune_service.py with the actual query IDs')
        self.stdout.write('3. Test specific queries with: ./manage.py setup_dune_integration --test-query QUERY_ID')
        self.stdout.write('4. The mining dashboard will automatically use real data when available!')
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Dune Analytics integration is ready!')) 