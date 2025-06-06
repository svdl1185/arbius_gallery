import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.models import ArbiusImage
from gallery.services import ArbitrumScanner

# First let's check what the current block number actually is
scanner = ArbitrumScanner()
current_block = scanner.get_latest_block()
print(f"Current Arbitrum block: {current_block}")

# Look for the specific image mentioned by the user
target_cid = "QmfVfzCN8pA9dezxUj3uZg3hk7mnUVFC8JBQb49xcpnjys"

try:
    image = ArbiusImage.objects.get(cid=target_cid)
    print(f"\nFound image: {target_cid}")
    print(f"Transaction Hash: {image.transaction_hash}")
    
    # Check the raw API response to see what's going wrong
    response = requests.get(f"https://api.arbiscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={image.transaction_hash}&apikey={scanner.api_key}")
    if response.status_code == 200:
        data = response.json()
        if data.get('result'):
            tx = data['result']
            print(f"\nRaw API response for blockNumber: {tx['blockNumber']}")
            
            # Test different interpretations
            try:
                as_hex = int(tx['blockNumber'], 16)
                print(f"As hex: {as_hex}")
            except:
                print("Failed to parse as hex")
                
            try:
                as_decimal = int(tx['blockNumber'])
                print(f"As decimal: {as_decimal}")
            except:
                print("Failed to parse as decimal")
            
            # Check what we have in the transaction list API too
            print(f"\nChecking transaction list API...")
            tx_list_response = requests.get(f"https://api.arbiscan.io/api?module=account&action=txlist&address={scanner.engine_address}&startblock={as_hex-10}&endblock={as_hex+10}&sort=desc&apikey={scanner.api_key}")
            if tx_list_response.status_code == 200:
                tx_list_data = tx_list_response.json()
                if tx_list_data.get('result'):
                    for tx_item in tx_list_data['result'][:3]:
                        print(f"TX {tx_item['hash'][:20]}... blockNumber: {tx_item['blockNumber']} (type: {type(tx_item['blockNumber'])})")
                        try:
                            block_as_int = int(tx_item['blockNumber'], 16) if tx_item['blockNumber'].startswith('0x') else int(tx_item['blockNumber'])
                            print(f"  -> Converted: {block_as_int}")
                        except:
                            print(f"  -> Conversion failed")
            
            # Now try to get task information around the correct block
            actual_block = int(tx['blockNumber'], 16)
            print(f"\n🔍 Searching for TaskSubmitted events around block {actual_block}...")
            task_info = scanner.get_task_information(actual_block - 50, actual_block + 50)
            print(f"Found {len(task_info)} tasks")
            
            for task_id, task_data in task_info.items():
                print(f"\nTask {task_id}:")
                print(f"  Model: {task_data.get('model_id')}")
                print(f"  Prompt: {task_data.get('prompt')}")
                print(f"  Block: {task_data.get('block_number')}")
    
except ArbiusImage.DoesNotExist:
    print(f"Image {target_cid} not found in database")
    
# Also show all images we have
print(f"\nAll images in database:")
for img in ArbiusImage.objects.all()[:10]:
    print(f"CID: {img.cid[:20]}... TX: {img.transaction_hash[:20]}... Block: {img.block_number}") 