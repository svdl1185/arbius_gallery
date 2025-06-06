import requests
import time
import re
import base58
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import ArbiusImage, ScanStatus
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
        
    def get_latest_block(self):
        """Get the latest block number from Arbitrum"""
        try:
            response = requests.get(f"{self.base_url}?module=proxy&action=eth_blockNumber&apikey={self.api_key}", timeout=30)
            data = response.json()
            return int(data['result'], 16)
        except Exception as e:
            print(f"Error getting latest block: {e}")
            return None
    
    def get_contract_transactions(self, start_block, end_block):
        """Get all transactions to the engine contract in a block range"""
        try:
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
            params = {
                'module': 'logs',
                'action': 'getLogs',
                'address': self.engine_address,
                'topic0': topic,
                'fromBlock': start_block,
                'toBlock': end_block,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            data = response.json()
            
            if data.get('status') == '1':
                return data.get('result', [])
            else:
                print(f"API Error getting logs: {data}")
                return []
                
        except Exception as e:
            print(f"Error getting event logs: {e}")
            return []
    
    def parse_task_submitted_event(self, log):
        """Parse TaskSubmitted event log to extract task information"""
        try:
            # TaskSubmitted event structure: TaskSubmitted(bytes32 indexed taskid, address indexed submitter, bytes32 indexed model, uint256 fee, bytes input)
            task_id = log['topics'][1] if len(log['topics']) > 1 else None
            submitter = '0x' + log['topics'][2][-40:] if len(log['topics']) > 2 else None  # Get address from topic
            model_id = log['topics'][3] if len(log['topics']) > 3 else None
            
            # Parse the data for fee and input
            data = log['data'][2:]  # Remove '0x' prefix
            
            # Fee is the first 32 bytes (64 hex chars)
            fee_hex = data[:64] if len(data) >= 64 else '0'
            fee = int(fee_hex, 16) if fee_hex != '0' else 0
            
            # Input data starts after fee and offset information
            # The input is hex-encoded JSON
            input_data = None
            prompt = None
            input_parameters = None
            
            try:
                # Skip fee (64 chars) and two offset fields (64 chars each) = 192 chars
                if len(data) > 192:
                    # Find the input data length and content
                    input_start = 192
                    # Next 64 chars are the length of the input data
                    input_length_hex = data[input_start:input_start+64]
                    input_length = int(input_length_hex, 16) * 2  # Convert to hex chars
                    
                    # Extract the actual input data
                    input_hex_start = input_start + 64
                    input_hex = data[input_hex_start:input_hex_start+input_length]
                    
                    # Convert hex to bytes, then to string
                    input_bytes = bytes.fromhex(input_hex)
                    input_string = input_bytes.decode('utf-8', errors='ignore')
                    
                    # Parse JSON input
                    input_parameters = json.loads(input_string)
                    prompt = input_parameters.get('prompt', '')
                    
            except Exception as e:
                logger.warning(f"Could not parse input data from task {task_id}: {e}")
            
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
            
            cids = []
            for match in matches:
                try:
                    # Reconstruct the full multihash
                    multihash_hex = "1220" + match
                    multihash_bytes = bytes.fromhex(multihash_hex)
                    
                    # Convert to base58 (CIDv0 format)
                    cid = base58.b58encode(multihash_bytes).decode('ascii')
                    
                    # Validate CID format with our improved validation
                    if self.is_valid_cid(cid):
                        if cid not in cids:
                            cids.append(cid)
                            print(f"      Found valid CID: {cid}")
                        
                except Exception:
                    continue
            
            print(f"      Extracted {len(cids)} valid CIDs from batch solution")
            return cids
            
        except Exception as e:
            print(f"      Error extracting CIDs from batch solution: {e}")
            return []

    def extract_cids_from_single_solution(self, transaction):
        """Extract CID from single solution transaction"""
        try:
            input_data = transaction['input']
            
            # Remove function signature (first 10 characters)
            param_data = input_data[10:]
            
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
                        print(f"      Found valid CID: {cid}")
                        return [cid]  # Return as list for consistency
                        
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
    
    def scan_blocks(self, start_block, end_block):
        """Scan a range of blocks for Arbius images"""
        print(f"🔍 Scanning blocks {start_block} to {end_block}")
        
        # Get task information from events first
        task_info = self.get_task_information(start_block, end_block)
        
        # Get all transactions in the range
        transactions = self.get_contract_transactions(start_block, end_block)
        
        # Filter for BOTH types of submitSolution transactions
        batch_solutions = [tx for tx in transactions if tx.get('input', '').startswith(self.submit_solution_batch_sig)]
        single_solutions = [tx for tx in transactions if tx.get('input', '').startswith(self.submit_solution_single_sig)]
        
        print(f"   Found {len(batch_solutions)} batch solutions, {len(single_solutions)} single solutions")
        
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
        
        # Process batch solutions
        for tx in batch_solutions:
            try:
                cids = self.extract_cids_from_batch_solution(tx)
                print(f"   Batch transaction {tx['hash'][:20]}... extracted {len(cids)} CIDs")
                
                for cid in cids:
                    if not ArbiusImage.objects.filter(cid=cid).exists():
                        # Extract task ID from transaction data
                        task_id = '0x0000000000000000000000000000000000000000000000000000000000000000'
                        try:
                            hex_data = tx['input'][10:]  # Remove 0x and function selector
                            if len(hex_data) >= 64:
                                task_id = '0x' + hex_data[:64]
                        except:
                            pass
                        
                        # Get task information if available
                        task_data = task_info.get(task_id, {})
                        model_id = task_data.get('model_id')
                        prompt = task_data.get('prompt')
                        input_parameters = task_data.get('input_parameters')
                        
                        # ONLY save if we have a prompt (indicating it's a real image)
                        if prompt and prompt.strip():
                            # Check IPFS accessibility
                            is_accessible, gateway = self.check_ipfs_accessibility(cid)
                            
                            # Construct proper IPFS URLs
                            ipfs_url = f"{self.ipfs_gateways[0]}{cid}"
                            image_url = f"{self.ipfs_gateways[0]}{cid}/out-1.png"
                            
                            # Convert block number properly
                            block_number = convert_block_number(tx['blockNumber'])
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
                                miner_address=tx['from'],
                                gas_used=int(tx['gasUsed']) if tx.get('gasUsed') else None,
                                is_accessible=is_accessible,
                                ipfs_gateway=gateway or '',
                                model_id=model_id,
                                prompt=prompt,
                                input_parameters=input_parameters
                            )
                            new_images.append(image)
                            
                            print(f"      ✅ Saved image with prompt: \"{prompt[:50]}...\"")
                        else:
                            print(f"      ⏭️ Skipping {cid[:20]}... (no prompt - likely not an image)")
                        
            except Exception as e:
                print(f"   Error processing batch transaction {tx['hash']}: {e}")
        
        # Process single solutions
        for tx in single_solutions:
            try:
                cids = self.extract_cids_from_single_solution(tx)
                if cids:
                    cid = cids[0]  # Single CID
                    print(f"   Single transaction {tx['hash'][:20]}... extracted CID: {cid}")
                    
                    if not ArbiusImage.objects.filter(cid=cid).exists():
                        # Extract task ID from transaction data
                        task_id = '0x0000000000000000000000000000000000000000000000000000000000000000'
                        try:
                            hex_data = tx['input'][10:]  # Remove 0x and function selector
                            if len(hex_data) >= 64:
                                task_id = '0x' + hex_data[:64]
                        except:
                            pass
                        
                        # Get task information if available
                        task_data = task_info.get(task_id, {})
                        model_id = task_data.get('model_id')
                        prompt = task_data.get('prompt')
                        input_parameters = task_data.get('input_parameters')
                        
                        # ONLY save if we have a prompt (indicating it's a real image)
                        if prompt and prompt.strip():
                            # Check IPFS accessibility
                            is_accessible, gateway = self.check_ipfs_accessibility(cid)
                            
                            # Construct proper IPFS URLs
                            ipfs_url = f"{self.ipfs_gateways[0]}{cid}"
                            image_url = f"{self.ipfs_gateways[0]}{cid}/out-1.png"
                            
                            # Convert block number properly
                            block_number = convert_block_number(tx['blockNumber'])
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
                                miner_address=tx['from'],
                                gas_used=int(tx['gasUsed']) if tx.get('gasUsed') else None,
                                is_accessible=is_accessible,
                                ipfs_gateway=gateway or '',
                                model_id=model_id,
                                prompt=prompt,
                                input_parameters=input_parameters
                            )
                            new_images.append(image)
                            
                            print(f"      ✅ Saved image with prompt: \"{prompt[:50]}...\"")
                        else:
                            print(f"      ⏭️ Skipping {cid[:20]}... (no prompt - likely not an image)")
                        
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
                miner_address=tx['from'],
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