from django.core.management.base import BaseCommand
from gallery.models import ArbiusImage
from gallery.services import ArbitrumScanner
from django.db.models import Count


class Command(BaseCommand):
    help = 'List all unique model IDs and find their task transactions'

    def handle(self, *args, **options):
        # Initialize the scanner to search for task transactions
        scanner = ArbitrumScanner()
        
        # Get all unique model IDs with counts
        model_stats = (ArbiusImage.objects
                      .exclude(model_id__isnull=True)
                      .exclude(model_id='')
                      .values('model_id')
                      .annotate(count=Count('id'))
                      .order_by('-count'))
        
        self.stdout.write(f"\n🎯 Found {len(model_stats)} unique model IDs:\n")
        self.stdout.write("🔍 Searching for task transactions...\n")
        
        for i, stat in enumerate(model_stats, 1):
            model_id = stat['model_id']
            count = stat['count']
            
            # Get a sample transaction for this model
            sample_image = ArbiusImage.objects.filter(model_id=model_id).first()
            
            self.stdout.write(f"{i}. Model ID: {model_id}")
            self.stdout.write(f"   Images: {count}")
            
            if sample_image:
                # Show solution transaction (where the image was submitted)
                solution_tx_hash = sample_image.transaction_hash
                solution_arbiscan_url = f"https://arbiscan.io/tx/{solution_tx_hash}"
                self.stdout.write(f"   Sample Solution Transaction: {solution_arbiscan_url}")
                
                # Try to find the actual task transaction
                if sample_image.task_id and sample_image.task_id != '0x0000000000000000000000000000000000000000000000000000000000000000':
                    self.stdout.write(f"   Task ID: {sample_image.task_id}")
                    
                    # Search for the task transaction using the scanner
                    try:
                        self.stdout.write("   🔍 Searching for task transaction...")
                        task_data = scanner.find_task_by_id_optimized(
                            sample_image.task_id, 
                            sample_image.block_number,
                            max_search_range=20000  # Search back 20k blocks
                        )
                        
                        if task_data and task_data.get('transaction_hash'):
                            task_tx_hash = task_data['transaction_hash']
                            task_arbiscan_url = f"https://arbiscan.io/tx/{task_tx_hash}"
                            self.stdout.write(f"   ✅ Task Transaction: {task_arbiscan_url}")
                            
                            if task_data.get('submitter'):
                                self.stdout.write(f"   Task Submitter: {task_data['submitter']}")
                            if task_data.get('fee'):
                                fee_eth = int(task_data['fee']) / 1e18
                                self.stdout.write(f"   Fee: {fee_eth:.6f} ETH")
                        else:
                            self.stdout.write(f"   ❌ Task transaction not found (may be too old)")
                            
                    except Exception as e:
                        self.stdout.write(f"   ❌ Error searching for task: {str(e)}")
                
                if sample_image.prompt:
                    prompt_preview = sample_image.prompt[:60] + "..." if len(sample_image.prompt) > 60 else sample_image.prompt
                    self.stdout.write(f"   Sample Prompt: \"{prompt_preview}\"")
                
                if sample_image.solution_provider:
                    self.stdout.write(f"   Solution Provider: {sample_image.solution_provider}")
            
            self.stdout.write("")  # Empty line for readability
        
        # Also show stats for images without model IDs
        no_model_count = ArbiusImage.objects.filter(model_id__isnull=True).count() + ArbiusImage.objects.filter(model_id='').count()
        if no_model_count > 0:
            self.stdout.write(f"⚠️  {no_model_count} images have no model ID")
        
        total_images = ArbiusImage.objects.count()
        self.stdout.write(f"\n📊 Total images in database: {total_images}")
        self.stdout.write(f"\n💡 Note: Solution transactions contain the generated images (CIDs)")
        self.stdout.write(f"💡 Task transactions contain the model IDs and original prompts")
        self.stdout.write(f"💡 This command searches for actual task transactions using the Arbiscan API") 