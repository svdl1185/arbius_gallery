from django.core.management.base import BaseCommand
from gallery.services import ArbitrumScanner
import requests

class Command(BaseCommand):
    help = 'Test parsing of specific task transaction'

    def handle(self, *args, **options):
        scanner = ArbitrumScanner()
        
        # Test the specific transaction the user pointed out
        task_tx = "0xf078d085112a6dd9c7071cfa861a5fe52b5b3315fb50b348ee1171002b155776"
        
        self.stdout.write(f"Testing transaction: {task_tx}")
        
        # Get the transaction data directly
        try:
            response = requests.get(f"https://api.arbiscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={task_tx}&apikey={scanner.api_key}")
            if response.status_code == 200:
                tx_data = response.json()
                
                if tx_data.get('result'):
                    tx_input = tx_data['result']['input']
                    self.stdout.write(f"Raw input: {tx_input[:100]}...")
                    
                    # Parse the transaction input manually
                    if tx_input.startswith('0x') and len(tx_input) > 10:
                        param_data = tx_input[10:]  # Remove function signature
                        self.stdout.write(f"Function signature: {tx_input[:10]}")
                        
                        if len(param_data) >= 320:  # At least 5*64 chars for 5 parameters
                            # Parse each parameter
                            version = param_data[0:64]
                            owner = param_data[64:128]
                            model = param_data[128:192]
                            fee = param_data[192:256]
                            input_offset = param_data[256:320]
                            
                            self.stdout.write(f"Parameter 0 (version): 0x{version}")
                            self.stdout.write(f"Parameter 1 (owner): 0x{owner}")
                            self.stdout.write(f"Parameter 2 (model): 0x{model}")
                            self.stdout.write(f"Parameter 3 (fee): 0x{fee}")
                            self.stdout.write(f"Parameter 4 (input_offset): 0x{input_offset}")
                            
                            # Convert to proper format
                            owner_addr = "0x" + owner[-40:]  # Last 20 bytes as address
                            model_id = "0x" + model
                            fee_amount = int(fee, 16) / 1e18
                            
                            self.stdout.write(f"\nFormatted:")
                            self.stdout.write(f"Owner (task submitter): {owner_addr}")
                            self.stdout.write(f"Model ID: {model_id}")
                            self.stdout.write(f"Fee: {fee_amount} ETH")
                            
                            # Expected values from user:
                            expected_owner = "0x708816d665eb09e5a86ba82a774dabb550bc8af5"
                            expected_model = "0xa473c70e9d7c872ac948d20546bc79db55fa64ca325a4b229aaffddb7f86aae0"
                            
                            self.stdout.write(f"\nExpected:")
                            self.stdout.write(f"Owner: {expected_owner}")
                            self.stdout.write(f"Model: {expected_model}")
                            
                            self.stdout.write(f"\nMatch check:")
                            self.stdout.write(f"Owner matches: {owner_addr.lower() == expected_owner.lower()}")
                            self.stdout.write(f"Model matches: {model_id.lower() == expected_model.lower()}")
                            
        except Exception as e:
            self.stdout.write(f"Error: {e}") 