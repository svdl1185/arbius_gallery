import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.models import ArbiusImage
from gallery.services import ArbitrumScanner

scanner = ArbitrumScanner()

# Get all existing images that don't have prompt data
images_without_prompts = ArbiusImage.objects.filter(prompt__isnull=True)
print(f"Found {images_without_prompts.count()} images without prompts")

for image in images_without_prompts[:5]:  # Process a few at a time
    print(f"\n🔍 Processing image: {image.cid}")
    print(f"   Transaction: {image.transaction_hash}")
    print(f"   Block: {image.block_number}")
    print(f"   Task ID: {image.task_id}")
    
    # Search for TaskSubmitted events in a range around this block
    # Tasks are usually submitted before solutions, so search backwards
    search_start = max(0, image.block_number - 1000)  # Search 1000 blocks back
    search_end = image.block_number + 100  # And a bit forward
    
    print(f"   Searching for TaskSubmitted events in blocks {search_start} to {search_end}...")
    
    task_info = scanner.get_task_information(search_start, search_end)
    print(f"   Found {len(task_info)} TaskSubmitted events in range")
    
    # Check if we can find this specific task
    if image.task_id in task_info:
        task_data = task_info[image.task_id]
        print(f"   🎯 FOUND task data for {image.task_id}!")
        print(f"      Model: {task_data.get('model_id')}")
        print(f"      Prompt: {task_data.get('prompt')}")
        print(f"      Input: {task_data.get('input_parameters')}")
        
        # Update the image with the found data
        image.model_id = task_data.get('model_id')
        image.prompt = task_data.get('prompt')
        image.input_parameters = task_data.get('input_parameters')
        image.save()
        
        print(f"   ✅ Updated image with task data")
    else:
        print(f"   ❌ Task {image.task_id} not found in events")
        
        # Let's see what tasks we did find
        if task_info:
            print(f"   Found these tasks instead:")
            for task_id, data in list(task_info.items())[:3]:
                print(f"     - {task_id}: {data.get('prompt', 'No prompt')[:50]}...")

print(f"\n📊 Processing complete!") 