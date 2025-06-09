import requests
import time
import re
import base58
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import ArbiusImage, ScanStatus, MinerAddress
import logging

logger = logging.getLogger(__name__)


class ArbiusTask:
    """Represents a task submission that we're tracking for completion"""
    def __init__(self, task_id, tx_hash, block_number, timestamp, submitter, model, fee):
        self.task_id = task_id
        self.tx_hash = tx_hash
        self.block_number = block_number
        self.timestamp = timestamp
        self.submitter = submitter
        self.model = model
        self.fee = fee
        self.discovered_at = timezone.now()


class ArbitrumScanner:
    """Service to scan Arbitrum blockchain for Arbius images"""
    
    def __init__(self):
        self.api_key = "RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D"
        self.base_url = "https://api.arbiscan.io/api"
        self.engine_address = "0x9b51Ef044d3486A1fB0A2D55A6e0CeeAdd323E66"
        
        # Rate limiting - max 5 calls per second as per the error message
        self.last_api_call = 0
        self.min_call_interval = 0.25  # 250ms between calls = 4 calls per second
        
        # Function signatures
        self.submit_task_sig = "0x08745dd1"
        self.submit_solution_batch_sig = "0x65d445fb"  # Batch submissions (25 CIDs)
        self.submit_solution_single_sig = "0x56914caf"  # Single submissions (1 CID)
        
        # IPFS gateways to check (in order of preference)
        self.ipfs_gateways = [
            "https://ipfs.arbius.org/ipfs/",
            "https://4everland.io/ipfs/",
            "https://dweb.link/ipfs/", 
            "https://gateway.ipfs.io/ipfs/"
        ]
        
        # TaskSubmitted event signature
        self.task_submitted_topic = "0xc3d3e0544c80e3bb83f62659259ae1574f72a91515ab3cae3dd75cf77e1b0aea"
        
    def _rate_limit(self):
        """Ensure we don't exceed the API rate limit"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        
        if time_since_last_call < self.min_call_interval:
            sleep_time = self.min_call_interval - time_since_last_call
            time.sleep(sleep_time)
        
        self.last_api_call = time.time()
        
    def get_latest_block(self):
        """Get the latest block number from Arbitrum"""
        try:
            self._rate_limit()
            response = requests.get(f"{self.base_url}?module=proxy&action=eth_blockNumber&apikey={self.api_key}", timeout=30)
            data = response.json()
            return int(data['result'], 16)
        except Exception as e:
            print(f"Error getting latest block: {e}")
            return None
    
    def get_contract_transactions(self, start_block, end_block):
        """Get all transactions to the engine contract in a block range"""
        try:
            self._rate_limit()
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': self.engine_address,
                'startblock': start_block,
                'endblock': end_block,
                'page': 1,
                'offset': 100,
                'sort': 'desc',
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            data = response.json()
            
            if data.get('status') == '1':
                return data.get('result', [])
            else:
                print(f"API Error: {data}")
                return []
                
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []
    
    def get_contract_logs(self, start_block, end_block, topic):
        """Get event logs from the engine contract in a block range"""
        try:
            self._rate_limit()
            params = {
                'module': 'logs',
                'action': 'getLogs',
                'address': self.engine_address,
                'topic0': topic,
                'fromBlock': start_block,
                'toBlock': end_block,
                'apikey': self.api_key
            }
            
            # Add timeout to prevent hanging - increased from default
            response = requests.get(self.base_url, params=params, timeout=15)
            data = response.json()
            
            if data.get('status') == '1':
                return data.get('result', [])
            else:
                print(f"API Error getting logs: {data}")
                return []
                
        except requests.exceptions.Timeout:
            print(f"Timeout getting logs for blocks {start_block} to {end_block}")
            return []
        except Exception as e:
            print(f"Error getting event logs: {e}")
            return []
    
    def parse_task_submitted_event(self, log):
        """Parse TaskSubmitted event log to extract task information"""
        try:
            # TaskSubmitted event structure: TaskSubmitted(bytes32 indexed taskid, address indexed submitter, bytes32 indexed model, uint256 fee, bytes input)
            task_id = log['topics'][1] if len(log['topics']) > 1 else None
            
            # Parse the data for fee (the event data only contains fee, not the input)
            data = log['data'][2:]  # Remove '0x' prefix
            
            # Fee is the first 32 bytes (64 hex chars)
            fee_hex = data[:64] if len(data) >= 64 else '0'
            fee = int(fee_hex, 16) if fee_hex != '0' else 0
            
            # Initialize defaults
            submitter = None
            model_id = None
            input_data = None
            prompt = None
            input_parameters = None
            
            try:
                # Get the transaction data to extract the correct parameters
                self._rate_limit()
                response = requests.get(f"https://api.arbiscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={log['transactionHash']}&apikey={self.api_key}")
                if response.status_code == 200:
                    tx_data = response.json()
                    
                    # Validate response structure before proceeding
                    if (isinstance(tx_data, dict) and 
                        tx_data.get('result') and 
                        isinstance(tx_data['result'], dict) and 
                        tx_data['result'].get('input')):
                        
                        tx_input = tx_data['result']['input']
                        
                        # Parse the transaction input to extract ALL task parameters properly
                        if tx_input.startswith('0x') and len(tx_input) > 10:
                            param_data = tx_input[10:]  # Remove function signature
                            
                            # For submitTask, parameters are: version, owner, model, fee, input
                            if len(param_data) >= 320:  # At least 5*64 chars
                                # Parse the owner (submitter) and model from transaction input
                                version_hex = param_data[0:64]
                                owner_hex = param_data[64:128]
                                model_hex = param_data[128:192]
                                fee_hex_tx = param_data[192:256]
                                input_offset_hex = param_data[256:320]  # 5th parameter (input offset)
                                
                                # Extract submitter (owner) and model_id correctly
                                submitter = "0x" + owner_hex[-40:]  # Last 20 bytes as address
                                model_id = "0x" + model_hex
                                
                                try:
                                    offset = int(input_offset_hex, 16) * 2  # Convert to hex chars
                                    
                                    if len(param_data) > offset + 64:
                                        # Get input data length and content
                                        input_length_hex = param_data[offset:offset+64]
                                        input_length = int(input_length_hex, 16) * 2  # Convert to hex chars
                                        
                                        input_hex_start = offset + 64
                                        input_hex = param_data[input_hex_start:input_hex_start+input_length]
                                        
                                        if input_hex:
                                            input_bytes = bytes.fromhex(input_hex)
                                            input_string = input_bytes.decode('utf-8', errors='ignore')
                                            
                                            # Parse JSON input
                                            input_parameters = json.loads(input_string)
                                            prompt = input_parameters.get('prompt', '')
                                            
                                except (ValueError, json.JSONDecodeError) as e:
                                    logger.debug(f"Could not parse input data from transaction {log['transactionHash']}: {e}")
                    else:
                        # Handle API error responses
                        if isinstance(tx_data, dict) and tx_data.get('result') and isinstance(tx_data['result'], str):
                            logger.debug(f"API returned error for transaction {log['transactionHash']}: {tx_data['result']}")
                        else:
                            logger.debug(f"Invalid response structure for transaction {log['transactionHash']}")
                            
            except Exception as e:
                logger.warning(f"Could not get transaction data for task {task_id}: {e}")
                # Fallback to event topics if transaction parsing fails (less reliable)
                submitter = '0x' + log['topics'][2][-40:] if len(log['topics']) > 2 else None
                model_id = log['topics'][3] if len(log['topics']) > 3 else None
            
            return {
                'task_id': task_id,
                'submitter': submitter,
                'model_id': model_id,
                'fee': fee,
                'prompt': prompt,
                'input_parameters': input_parameters,
                'block_number': int(log['blockNumber'], 16),
                'transaction_hash': log['transactionHash']
            }
            
        except Exception as e:
            logger.error(f"Error parsing TaskSubmitted event: {e}")
            return None
    
    def get_task_information(self, start_block, end_block):
        """Get task information from TaskSubmitted events"""
        print(f"   Getting task information from events...")
        
        logs = self.get_contract_logs(start_block, end_block, self.task_submitted_topic)
        task_info = {}
        
        for log in logs:
            task_data = self.parse_task_submitted_event(log)
            if task_data and task_data['task_id']:
                task_info[task_data['task_id']] = task_data
        
        print(f"   Found {len(task_info)} task submissions")
        return task_info
    
    def is_valid_cid(self, cid):
        """Validate if a string is a valid IPFS CID"""
        if not cid or len(cid) < 46:  # Minimum CID length
            return False
        
        # Check if it starts with Qm (CIDv0) or other valid prefixes
        if not (cid.startswith('Qm') or cid.startswith('bafy') or cid.startswith('baf')):
            return False
        
        # Check length - typical CID lengths
        if not (40 <= len(cid) <= 62):
            return False
        
        # Check if it contains only valid base58 characters for Qm CIDs
        if cid.startswith('Qm'):
            valid_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
            if not all(c in valid_chars for c in cid):
                return False
        
        return True

    def extract_cids_from_batch_solution(self, transaction):
        """Extract CIDs from batch solution transaction"""
        try:
            input_data = transaction['input']
            
            # Remove function signature (first 10 characters)
            param_data = input_data[10:]
            
            # Find all multihash patterns (0x1220 followed by 32 bytes)
            multihash_pattern = re.compile(r'1220([a-fA-F0-9]{64})')
            matches = multihash_pattern.findall(param_data)
            
            # Also extract task IDs from the batch solution
            # Batch solutions contain task IDs in the first part of the data
            task_id_pattern = re.compile(r'([a-fA-F0-9]{64})')
            task_id_matches = task_id_pattern.findall(param_data[:len(matches)*64*2])  # Look for task IDs in first part
            
            cids_with_task_ids = []
            for i, match in enumerate(matches):
                try:
                    # Reconstruct the full multihash
                    multihash_hex = "1220" + match
                    multihash_bytes = bytes.fromhex(multihash_hex)
                    
                    # Convert to base58 (CIDv0 format)
                    cid = base58.b58encode(multihash_bytes).decode('ascii')
                    
                    # Validate CID format with our improved validation
                    if self.is_valid_cid(cid):
                        # Try to get corresponding task ID
                        task_id = None
                        if i < len(task_id_matches):
                            task_id = '0x' + task_id_matches[i]
                        
                        cids_with_task_ids.append((cid, task_id))
                        print(f"      Found valid CID: {cid} (task: {task_id})")
                        
                except Exception:
                    continue
            
            print(f"      Extracted {len(cids_with_task_ids)} valid CIDs from batch solution")
            return cids_with_task_ids
            
        except Exception as e:
            print(f"      Error extracting CIDs from batch solution: {e}")
            return []

    def extract_cids_from_single_solution(self, transaction):
        """Extract CID from single solution transaction"""
        try:
            input_data = transaction['input']
            
            # Remove function signature (first 10 characters)
            param_data = input_data[10:]
            
            # For single solutions, task ID is typically the first 64 characters
            task_id = None
            if len(param_data) >= 64:
                task_id = '0x' + param_data[:64]
            
            # Find multihash pattern
            multihash_pos = param_data.find('1220')
            
            if multihash_pos >= 0:
                # Extract multihash (34 bytes = 68 hex chars)
                multihash_hex = param_data[multihash_pos:multihash_pos+68]
                
                try:
                    multihash_bytes = bytes.fromhex(multihash_hex)
                    cid = base58.b58encode(multihash_bytes).decode('ascii')
                    
                    # Validate CID format with our improved validation
                    if self.is_valid_cid(cid):
                        print(f"      Found valid CID: {cid} (task: {task_id})")
                        return [(cid, task_id)]  # Return as list of tuples for consistency
                        
                except Exception:
                    pass
            
            print(f"      No valid CID found in single solution")
            return []
            
        except Exception as e:
            print(f"      Error extracting CID from single solution: {e}")
            return []
    
    def extract_cids_from_solution(self, transaction):
        """Extract CIDs from any submitSolution transaction (batch or single)"""
        input_data = transaction.get('input', '')
        
        if input_data.startswith(self.submit_solution_batch_sig):
            return self.extract_cids_from_batch_solution(transaction)
        elif input_data.startswith(self.submit_solution_single_sig):
            return self.extract_cids_from_single_solution(transaction)
        else:
            return []
    
    def check_ipfs_accessibility(self, cid):
        """Check if a CID is accessible via IPFS gateways"""
        for gateway in self.ipfs_gateways:
            try:
                url = f"{gateway}{cid}/out-1.png"
                response = requests.head(url, timeout=10)
                
                # Accept various success status codes
                if response.status_code in [200, 301, 302]:
                    return True, gateway
                    
            except Exception:
                continue
        
        return False, None
    
    def is_valid_image_content(self, cid):
        """Check if CID actually contains valid image content (not text)"""
        for gateway in self.ipfs_gateways:
            try:
                url = f"{gateway}{cid}/out-1.png"
                response = requests.head(url, timeout=10)
                
                if response.status_code in [200, 301, 302]:
                    # Check content type
                    content_type = response.headers.get('content-type', '').lower()
                    if content_type.startswith('image/'):
                        return True
                    
                    # If no content-type header, try to fetch first few bytes to check image magic numbers
                    try:
                        partial_response = requests.get(url, headers={'Range': 'bytes=0-10'}, timeout=5)
                        if partial_response.status_code in [200, 206]:
                            content = partial_response.content
                            
                            # Check for common image magic numbers
                            if (content.startswith(b'\x89PNG') or  # PNG
                                content.startswith(b'\xff\xd8\xff') or  # JPEG
                                content.startswith(b'GIF8') or  # GIF
                                content.startswith(b'RIFF') and b'WEBP' in content[:12]):  # WebP
                                return True
                    except:
                        pass
                        
            except Exception:
                continue
        
        return False
    
    def find_task_by_id_optimized(self, task_id, solution_block, max_search_range=10000):
        """Find TaskSubmitted event using task ID with optimized block range search
        This is the efficient method that uses direct task ID filtering instead of scanning all events"""
        
        # Use progressively larger search ranges - most tasks are found quickly
        search_ranges = [
            (solution_block - 1000, solution_block),              # Very close: 1k blocks
            (solution_block - 5000, solution_block - 1000),       # Medium: 4k blocks  
            (solution_block - max_search_range, solution_block - 5000),  # Wider: remaining blocks
        ]
        
        for start_block, end_block in search_ranges:
            if start_block < 0:
                start_block = 0
                
            if start_block >= end_block:
                continue
                
            try:
                self._rate_limit()
                
                # Direct lookup using task ID filter - this is the key optimization!
                params = {
                    'module': 'logs',
                    'action': 'getLogs',
                    'address': self.engine_address,
                    'topic0': self.task_submitted_topic,
                    'topic1': task_id,  # Direct filter by task ID - no scanning needed!
                    'fromBlock': start_block,
                    'toBlock': end_block,
                    'apikey': self.api_key
                }
                
                response = requests.get(self.base_url, params=params, timeout=15)
                data = response.json()
                
                if data.get('status') == '1' and data.get('result'):
                    log = data['result'][0]  # Should be exactly one result
                    logger.info(f"Found task {task_id[:20]}... in range {start_block}-{end_block}")
                    
                    # Parse the complete task data
                    task_data = self.parse_task_submitted_event(log)
                    return task_data
                    
            except Exception as e:
                logger.warning(f"Error searching range {start_block}-{end_block} for task {task_id[:20]}...: {e}")
                continue
        
        return None

    def scan_blocks(self, start_block, end_block):
        """Scan a range of blocks for Arbius images with integrated optimized task lookup"""
        print(f"🔍 Scanning blocks {start_block} to {end_block}")
        
        # Get all transactions in the range
        transactions = self.get_contract_transactions(start_block, end_block)
        
        # ONLY process single submitSolution transactions (skip bulk submissions)
        # Bulk submissions don't contain actual images
        single_solutions = [tx for tx in transactions if tx.get('input', '').startswith(self.submit_solution_single_sig)]
        
        print(f"   Found {len(single_solutions)} single solution transactions (skipping bulk submissions)")
        
        new_images = []
        
        # Helper function to convert block number properly
        def convert_block_number(block_num_str):
            """Convert block number string to integer, handling both hex and decimal formats"""
            if isinstance(block_num_str, int):
                return block_num_str
            if block_num_str.startswith('0x'):
                return int(block_num_str, 16)
            else:
                return int(block_num_str)
        
        # Process ONLY single solutions (real images) with optimized task lookup
        for tx in single_solutions:
            try:
                cids = self.extract_cids_from_single_solution(tx)
                if cids:
                    cid, task_id = cids[0]  # Single CID and task ID
                    print(f"   Single transaction {tx['hash'][:20]}... extracted CID: {cid}")
                    
                    if not ArbiusImage.objects.filter(cid=cid).exists():
                        # Convert block number properly
                        block_number = convert_block_number(tx['blockNumber'])
                        
                        # Use optimized task lookup instead of broad range search
                        task_data = None
                        if task_id:
                            task_data = self.find_task_by_id_optimized(task_id, block_number)
                        
                        # Extract task information
                        model_id = task_data.get('model_id') if task_data else None
                        prompt = task_data.get('prompt') if task_data else None
                        input_parameters = task_data.get('input_parameters') if task_data else None
                        task_submitter = task_data.get('submitter') if task_data else None
                        
                        # Check IPFS accessibility first
                        is_accessible, gateway = self.check_ipfs_accessibility(cid)
                        
                        if is_accessible:
                            # Additional validation to ensure it's actually an image, not text
                            is_valid_image = self.is_valid_image_content(cid)
                            
                            # Skip if it's not a valid image or contains text model output markers
                            if not is_valid_image:
                                print(f"      ⏭️ Skipping {cid[:20]}... (not valid image content)")
                                continue
                            
                            # Skip if prompt indicates it's from a text model
                            if prompt and (prompt.strip().startswith("<|begin_of_text|>") or 
                                         prompt.strip().startswith("<|end_of_text|>") or
                                         len(prompt.strip()) > 5000):  # Extremely long prompts are likely text outputs
                                print(f"      ⏭️ Skipping {cid[:20]}... (text model output detected)")
                                continue
                            
                            # Save image with task data found via optimized lookup
                            
                            # Construct proper IPFS URLs
                            ipfs_url = f"{self.ipfs_gateways[0]}{cid}"
                            image_url = f"{self.ipfs_gateways[0]}{cid}/out-1.png"
                            
                            timestamp = datetime.fromtimestamp(int(tx['timeStamp']), tz=timezone.get_current_timezone())
                            
                            # Create image record with all required fields
                            image = ArbiusImage.objects.create(
                                cid=cid,
                                transaction_hash=tx['hash'],
                                task_id=task_id,
                                block_number=block_number,
                                timestamp=timestamp,
                                ipfs_url=ipfs_url,
                                image_url=image_url,
                                solution_provider=tx['from'],  # Miner who provided the solution
                                miner_address=tx['from'],  # Keep for backward compatibility
                                gas_used=int(tx['gasUsed']) if tx.get('gasUsed') else None,
                                is_accessible=is_accessible,
                                ipfs_gateway=gateway or '',
                                model_id=model_id,
                                prompt=prompt or '',  # Store empty string if no prompt
                                input_parameters=input_parameters,
                                task_submitter=task_submitter  # Original task requester
                            )
                            new_images.append(image)
                            
                            # Enhanced logging to show the distinction and task data found
                            if task_submitter and task_submitter != tx['from']:
                                print(f"      ✅ Saved image - Task by: {task_submitter[:10]}..., Solution by: {tx['from'][:10]}...")
                            else:
                                print(f"      ✅ Saved image - Solution by: {tx['from'][:10]}... (task submitter unknown)")
                            
                            if prompt and prompt.strip():
                                prompt_preview = prompt[:50] + "..." if len(prompt) > 50 else prompt
                                print(f"         📝 Prompt: \"{prompt_preview}\"")
                            else:
                                print(f"         ⚠️ No prompt found for task {task_id[:20]}...")
                                
                            if task_data:
                                print(f"         🎯 Task data found via optimized lookup (1-3 API calls vs 100+)")
                            else:
                                print(f"         📊 No task data found - may be older task")
                        else:
                            print(f"      ⏭️ Skipping {cid[:20]}... (not accessible via IPFS)")
                        
            except Exception as e:
                print(f"   Error processing single transaction {tx['hash']}: {e}")
        
        return new_images
    
    def scan_recent_blocks(self, num_blocks):
        """Scan the most recent blocks for new images"""
        latest_block = self.get_latest_block()
        if not latest_block:
            return []
        
        start_block = latest_block - num_blocks
        return self.scan_blocks(start_block, latest_block)
    
    def create_image_from_solution(self, tx, cid, task_id=None):
        """Create an ArbiusImage record from solution transaction data and CID"""
        try:
            # Check if we already have this transaction or CID
            if ArbiusImage.objects.filter(transaction_hash=tx['hash']).exists():
                logger.info(f"Transaction {tx['hash']} already exists, skipping")
                return None
                
            if ArbiusImage.objects.filter(cid=cid).exists():
                logger.info(f"CID {cid} already exists, skipping")
                return None
            
            # Helper function to convert block number properly
            def convert_block_number(block_num_str):
                """Convert block number string to integer, handling both hex and decimal formats"""
                if isinstance(block_num_str, int):
                    return block_num_str
                if block_num_str.startswith('0x'):
                    return int(block_num_str, 16)
                else:
                    return int(block_num_str)
            
            # Create the image record
            timestamp = datetime.fromtimestamp(int(tx['timeStamp']), tz=timezone.get_current_timezone())
            ipfs_url = f"{self.ipfs_gateways[0]}{cid}/out-1.png"
            image_url = f"{self.ipfs_gateways[0]}{cid}/out-1.png"
            
            # Try to extract task ID from transaction data if not provided
            if not task_id:
                try:
                    hex_data = tx['input'][10:]  # Remove 0x and function selector
                    if len(hex_data) >= 64:
                        task_id = '0x' + hex_data[:64]
                except:
                    task_id = '0x0000000000000000000000000000000000000000000000000000000000000000'
            
            # Quick IPFS validation to set accessibility flag
            is_accessible, gateway = self.check_ipfs_accessibility(cid)
            
            image = ArbiusImage.objects.create(
                transaction_hash=tx['hash'],
                task_id=task_id,
                block_number=convert_block_number(tx['blockNumber']),
                timestamp=timestamp,
                cid=cid,
                ipfs_url=ipfs_url,
                image_url=image_url,
                solution_provider=tx['from'],  # Miner who provided the solution
                miner_address=tx['from'],  # Keep for backward compatibility
                gas_used=int(tx['gasUsed']) if tx.get('gasUsed') else None,
                is_accessible=is_accessible,
                ipfs_gateway=gateway or ''
            )
            
            status_msg = "✅ accessible" if is_accessible else "⚠️ not accessible yet"
            logger.info(f"🎉 Created new Arbius image: {cid} from transaction {tx['hash']} ({status_msg})")
            return image
            
        except Exception as e:
            logger.error(f"Error creating image from solution transaction {tx.get('hash', 'unknown')}: {e}")
            return None
    
    def recheck_accessibility(self, batch_size=10):
        """Background task to recheck accessibility of pending images"""
        logger.info("🔄 Rechecking IPFS accessibility for pending images...")
        
        # Get images that aren't accessible yet
        pending_images = ArbiusImage.objects.filter(is_accessible=False)[:batch_size]
        
        updated_count = 0
        for image in pending_images:
            try:
                # Recheck with longer timeout
                is_accessible, gateway = self.check_ipfs_accessibility(image.cid)
                image.is_accessible = is_accessible
                image.ipfs_gateway = gateway or ''
                image.save()
                updated_count += 1
                logger.info(f"✅ Image {image.cid} is now accessible!")
                
            except Exception as e:
                logger.error(f"Error rechecking {image.cid}: {e}")
                continue
        
        logger.info(f"🔄 Accessibility recheck complete: {updated_count} images became accessible")
        return updated_count
    
    def scan_recent_weeks(self, weeks_back=3):
        """Scan the last few weeks for images"""
        try:
            logger.info(f"Starting scan of last {weeks_back} weeks...")
            
            # Get current scan status
            status, created = ScanStatus.objects.get_or_create(
                id=1,
                defaults={'last_scanned_block': 0}
            )
            
            if status.scan_in_progress:
                logger.warning("Scan already in progress, skipping...")
                return 0
            
            # Set scan in progress
            status.scan_in_progress = True
            status.save()
            
            latest_block = self.get_latest_block()
            if not latest_block:
                logger.error("Could not get latest block number")
                status.scan_in_progress = False
                status.save()
                return 0
            
            # CORRECTED: Use actual Arbitrum block timing (much faster than we thought)
            # Arbitrum produces blocks much faster than we calculated
            # Based on findings: significant activity in last 1000 blocks
            if weeks_back == 1:
                blocks_to_scan = 10000  # Last 10k blocks for 1 week
            elif weeks_back == 3:
                blocks_to_scan = 50000  # Last 50k blocks for 3 weeks  
            elif weeks_back == 6:
                blocks_to_scan = 100000  # Last 100k blocks for 6 weeks
            else:
                blocks_to_scan = weeks_back * 15000  # General approximation
            
            # For historical scans, always scan the full requested range
            start_block = latest_block - blocks_to_scan
            end_block = latest_block
            
            logger.info(f"Scanning from block {start_block} to {end_block} ({weeks_back} weeks = {blocks_to_scan} blocks)")
            
            # Scan in smaller chunks - submitSolution transactions are less frequent
            chunk_size = 1000  # Smaller chunks since we found activity in 1k block range
            total_new_images = 0
            
            for chunk_start in range(start_block, end_block + 1, chunk_size):
                chunk_end = min(chunk_start + chunk_size - 1, end_block)
                logger.info(f"Scanning chunk: {chunk_start} to {chunk_end}")
                
                new_images = self.scan_blocks(chunk_start, chunk_end)
                total_new_images += len(new_images)
                
                # Update progress
                if len(new_images) > 0:
                    logger.info(f"Found {len(new_images)} new images in chunk")
                
                # Shorter delay since chunks are smaller
                time.sleep(0.2)
            
            # Update scan status
            self.update_scan_status(end_block, total_new_images)
            
            logger.info(f"🎉 Historical scan complete! Found {total_new_images} new images")
            return total_new_images
            
        except Exception as e:
            logger.error(f"Error during historical scan: {e}")
            # Make sure to reset scan in progress
            try:
                status = ScanStatus.objects.get(id=1)
                status.scan_in_progress = False
                status.save()
            except:
                pass 
            return 0
    
    def scan_new_blocks(self, block_limit=100):
        """Scan for new blocks since last scan (for periodic updates)"""
        try:
            # Get current scan status
            status, created = ScanStatus.objects.get_or_create(
                id=1,
                defaults={'last_scanned_block': 0}
            )
            
            if status.scan_in_progress:
                logger.info("Scan already in progress, skipping periodic scan...")
                return 0
            
            # Set scan in progress
            status.scan_in_progress = True
            status.save()
            
            latest_block = self.get_latest_block()
            if not latest_block:
                logger.error("Could not get latest block number")
                status.scan_in_progress = False
                status.save()
                return 0
            
            start_block = max(status.last_scanned_block + 1, latest_block - block_limit)
            end_block = latest_block
            
            if start_block > end_block:
                logger.info("No new blocks to scan")
                status.scan_in_progress = False
                status.save()
                return 0
            
            logger.info(f"Periodic scan from block {start_block} to {end_block}")
            
            new_images = self.scan_blocks(start_block, end_block)
            
            # Update scan status
            self.update_scan_status(end_block, len(new_images))
            
            if len(new_images) > 0:
                logger.info(f"🎉 Periodic scan found {len(new_images)} new images")
            
            return len(new_images)
            
        except Exception as e:
            logger.error(f"Error during periodic scan: {e}")
            # Make sure to reset scan in progress
            try:
                status = ScanStatus.objects.get(id=1)
                status.scan_in_progress = False
                status.save()
            except:
                pass
            return 0 

    def update_scan_status(self, last_block, images_found):
        """Update the scan status"""
        status, created = ScanStatus.objects.get_or_create(
            id=1,
            defaults={
                'last_scanned_block': last_block,
                'total_images_found': images_found
            }
        )
        
        if not created:
            status.last_scanned_block = last_block
            status.last_scan_time = timezone.now()
            status.total_images_found = ArbiusImage.objects.count()
            status.scan_in_progress = False
            status.save() 

    def scan_recent_minutes(self, minutes=30):
        """Scan the last N minutes for new images with prompts only"""
        try:
            logger.info(f"Starting scan of last {minutes} minutes...")
            
            # Get current scan status
            status, created = ScanStatus.objects.get_or_create(
                id=1,
                defaults={'last_scanned_block': 0}
            )
            
            if status.scan_in_progress:
                logger.warning("Scan already in progress, skipping...")
                return 0
            
            # Set scan in progress
            status.scan_in_progress = True
            status.save()
            
            latest_block = self.get_latest_block()
            if not latest_block:
                logger.error("Could not get latest block number")
                status.scan_in_progress = False
                status.save()
                return 0
            
            # Calculate blocks for the time period
            # Arbitrum produces blocks very frequently - approximately 1 block every 0.25-2 seconds
            # For safety, we'll use 1 block per second as estimate for 30 minutes = 1800 blocks
            # But we'll scan a bit more to be safe
            blocks_for_period = minutes * 60 * 2  # 2 blocks per second estimate
            
            start_block = latest_block - blocks_for_period
            end_block = latest_block
            
            logger.info(f"Scanning last {minutes} minutes: blocks {start_block} to {end_block} ({blocks_for_period} blocks)")
            
            new_images = self.scan_blocks(start_block, end_block)
            
            # Update scan status
            self.update_scan_status(end_block, len(new_images))
            
            logger.info(f"🎉 Recent scan complete! Found {len(new_images)} new images with prompts")
            return len(new_images)
            
        except Exception as e:
            logger.error(f"Error during recent scan: {e}")
            # Make sure to reset scan in progress
            try:
                status = ScanStatus.objects.get(id=1)
                status.scan_in_progress = False
                status.save()
            except:
                pass
            return 0 

    def scan_with_overlap_detection(self, block_range=1000):
        """Scan with overlap detection to ensure no blocks are missed"""
        try:
            logger.info(f"Starting overlap-detecting scan with {block_range} block range...")
            
            # Get current scan status
            status, created = ScanStatus.objects.get_or_create(
                id=1,
                defaults={'last_scanned_block': 0}
            )
            
            if status.scan_in_progress:
                logger.warning("Scan already in progress, skipping...")
                return []
            
            # Set scan in progress
            status.scan_in_progress = True
            status.save()
            
            latest_block = self.get_latest_block()
            if not latest_block:
                logger.error("Could not get latest block number")
                status.scan_in_progress = False
                status.save()
                return []
            
            # Calculate scan range with overlap detection
            if status.last_scanned_block == 0:
                # First run - scan recent blocks
                start_block = latest_block - block_range
            else:
                # Subsequent runs - start from last scanned block minus overlap
                overlap_blocks = 100  # 100 block overlap to ensure we don't miss anything
                start_block = max(0, status.last_scanned_block - overlap_blocks)
            
            end_block = latest_block
            
            if start_block >= end_block:
                logger.info("No new blocks to scan")
                status.scan_in_progress = False
                status.save()
                return []
            
            logger.info(f"Overlap-detecting scan from block {start_block} to {end_block} (range: {end_block - start_block} blocks)")
            
            new_images = self.scan_blocks(start_block, end_block)
            
            # Update scan status
            self.update_scan_status(end_block, len(new_images))
            
            if len(new_images) > 0:
                logger.info(f"🎉 Overlap-detecting scan found {len(new_images)} new images")
            
            return new_images
            
        except Exception as e:
            logger.error(f"Error during overlap-detecting scan: {e}")
            # Make sure to reset scan in progress
            try:
                status = ScanStatus.objects.get(id=1)
                status.scan_in_progress = False
                status.save()
            except:
                pass
            return []

    def scan_recent_days(self, days=3):
        """Deep scan for the last N days to catch missed historical images"""
        try:
            logger.info(f"Starting deep scan of last {days} days...")
            
            # Get current scan status
            status, created = ScanStatus.objects.get_or_create(
                id=1,
                defaults={'last_scanned_block': 0}
            )
            
            if status.scan_in_progress:
                logger.warning("Scan already in progress, skipping deep scan...")
                return []
            
            # Set scan in progress
            status.scan_in_progress = True
            status.save()
            
            latest_block = self.get_latest_block()
            if not latest_block:
                logger.error("Could not get latest block number")
                status.scan_in_progress = False
                status.save()
                return []
            
            # Calculate blocks for time period
            # Arbitrum: ~1 block per second average, so:
            # 1 day = 86,400 seconds ≈ 86,400 blocks
            # 3 days ≈ 259,200 blocks
            blocks_for_period = days * 86400  # Conservative estimate
            
            start_block = latest_block - blocks_for_period
            end_block = latest_block
            
            logger.info(f"Deep scanning last {days} days: blocks {start_block} to {end_block} ({blocks_for_period} blocks)")
            
            # Scan in chunks to handle large ranges
            chunk_size = 2000  # Larger chunks for deep scan
            total_new_images = 0
            
            for chunk_start in range(start_block, end_block + 1, chunk_size):
                chunk_end = min(chunk_start + chunk_size - 1, end_block)
                logger.info(f"Deep scanning chunk: {chunk_start} to {chunk_end}")
                
                new_images = self.scan_blocks(chunk_start, chunk_end)
                total_new_images += len(new_images)
                
                # Update progress
                if len(new_images) > 0:
                    logger.info(f"Found {len(new_images)} new images in deep scan chunk")
                
                # Shorter delay for deep scans
                time.sleep(0.1)
            
            # Update scan status
            self.update_scan_status(end_block, total_new_images)
            
            logger.info(f"🎉 Deep scan complete! Found {total_new_images} new images")
            return total_new_images
            
        except Exception as e:
            logger.error(f"Error during deep scan: {e}")
            # Make sure to reset scan in progress
            try:
                status = ScanStatus.objects.get(id=1)
                status.scan_in_progress = False
                status.save()
            except:
                pass 
            return []
    
    def identify_miners_in_range(self, start_block, end_block):
        """Identify miners by scanning for solution and commitment submissions in a block range"""
        logger.info(f"🔍 Identifying miners in blocks {start_block} to {end_block}")
        
        # Get all transactions to the engine contract
        transactions = self.get_contract_transactions(start_block, end_block)
        
        # Look for solution submissions (both batch and single)
        solution_transactions = [
            tx for tx in transactions 
            if tx.get('input', '').startswith(self.submit_solution_batch_sig) or 
               tx.get('input', '').startswith(self.submit_solution_single_sig)
        ]
        
        # TODO: Add commitment submission signatures when available
        # commitment_transactions = [tx for tx in transactions if tx.get('input', '').startswith(commitment_sig)]
        
        miners_found = set()
        
        # Process solution submissions
        for tx in solution_transactions:
            miner_address = tx['from'].lower()
            miners_found.add(miner_address)
            
            # Get or create miner record
            miner, created = MinerAddress.objects.get_or_create(
                wallet_address=miner_address,
                defaults={
                    'first_seen': timezone.now(),
                    'last_seen': timezone.now(),
                    'total_solutions': 0,
                    'total_commitments': 0,
                    'is_active': True
                }
            )
            
            # Update activity
            miner.update_activity('solution')
            
            if created:
                logger.info(f"🆕 New miner identified: {miner_address}")
            else:
                logger.debug(f"🔄 Updated miner activity: {miner_address}")
        
        logger.info(f"✅ Identified {len(miners_found)} unique miners in block range")
        return list(miners_found)
    
    def scan_for_miners(self, hours_back=1, mark_inactive=False):
        """Scan recent blocks to identify active miners"""
        try:
            latest_block = self.get_latest_block()
            if not latest_block:
                logger.error("Could not get latest block number")
                return []
            
            # Calculate blocks for time period (approximately 1 block per second on Arbitrum)
            blocks_for_period = hours_back * 3600  # hours * seconds
            start_block = latest_block - blocks_for_period
            end_block = latest_block
            
            logger.info(f"🔍 Scanning last {hours_back} hour(s) for miner activity...")
            logger.info(f"Scanning blocks {start_block} to {end_block} ({blocks_for_period} blocks)")
            
            miners = self.identify_miners_in_range(start_block, end_block)
            
            # Only mark inactive miners if explicitly requested
            # By default, miners stay on the filter list permanently once identified
            if mark_inactive:
                from datetime import timedelta
                
                cutoff_date = timezone.now() - timedelta(days=7)
                inactive_count = MinerAddress.objects.filter(
                    last_seen__lt=cutoff_date,
                    is_active=True
                ).update(is_active=False)
                
                if inactive_count > 0:
                    logger.info(f"📉 Marked {inactive_count} miners as inactive (no activity for 7+ days)")
            
            return miners
            
        except Exception as e:
            logger.error(f"Error scanning for miners: {e}")
            return []
    
    def get_current_miners(self):
        """Get list of currently identified miner addresses"""
        from .models import MinerAddress
        
        active_miners = MinerAddress.objects.filter(is_active=True).values_list('wallet_address', flat=True)
        return list(active_miners) 