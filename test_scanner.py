#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.services import ArbitrumScanner
from gallery.models import ScanStatus

def test_scanner():
    print("🔍 Testing Arbius Scanner...")
    
    scanner = ArbitrumScanner()
    
    # Test API connectivity
    print("\n1. Testing API connectivity...")
    latest_block = scanner.get_latest_block()
    print(f"Latest block: {latest_block}")
    
    if not latest_block:
        print("❌ API connectivity failed!")
        return
    
    # Check current scan status
    print("\n2. Checking scan status...")
    status, created = ScanStatus.objects.get_or_create(id=1, defaults={'last_scanned_block': 0})
    print(f"Last scanned block: {status.last_scanned_block}")
    print(f"Scan in progress: {status.scan_in_progress}")
    
    # Test getting recent transactions
    print("\n3. Testing transaction retrieval...")
    start_block = max(latest_block - 1000, status.last_scanned_block)
    end_block = latest_block
    
    print(f"Looking for transactions in blocks {start_block} to {end_block}")
    transactions = scanner.get_contract_transactions(start_block, end_block)
    print(f"Found {len(transactions)} transactions")
    
    # Analyze function signatures
    if transactions:
        print("\n4. Analyzing function signatures...")
        signatures = {}
        submit_solution_count = 0
        
        for tx in transactions:
            sig = tx.get('input', '')[:10] if tx.get('input') else 'no_input'
            signatures[sig] = signatures.get(sig, 0) + 1
            
            if sig == scanner.submit_solution_sig:
                submit_solution_count += 1
        
        print(f"Function signature breakdown:")
        for sig, count in signatures.items():
            print(f"  {sig}: {count} transactions")
            
        print(f"\nSubmitSolution transactions: {submit_solution_count}")
        
        # Test CID extraction on a few submitSolution transactions
        if submit_solution_count > 0:
            print("\n5. Testing CID extraction...")
            solution_count = 0
            for tx in transactions:
                if tx.get('input', '').startswith(scanner.submit_solution_sig):
                    solution_count += 1
                    if solution_count <= 3:  # Test first 3
                        print(f"\nTesting transaction {tx['hash']}")
                        cids = scanner.extract_cids_from_solution(tx)
                        print(f"  Found {len(cids)} CIDs: {cids}")
                        
                        if len(cids) > 0:
                            print("✅ CID extraction is working!")
                            return
    
    # Try a historical scan with smaller range
    print("\n6. Testing historical scan (smaller range)...")
    try:
        new_images = scanner.scan_recent_weeks(weeks_back=1)
        print(f"Historical scan result: {new_images} new images")
    except Exception as e:
        print(f"Historical scan error: {e}")
    
    print("\n✅ Scanner test complete!")

if __name__ == "__main__":
    test_scanner() 