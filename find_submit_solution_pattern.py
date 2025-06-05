#!/usr/bin/env python
"""
Find actual submitSolution transactions to understand the pattern
"""

import requests
import time

def find_submit_solution_pattern():
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    engine_address = '0x9b51ef044d3486a1fb0a2d55a6e0ceeadd323e66'
    
    print(f"=== Finding submitSolution Transaction Patterns ===")
    
    # Get latest block
    try:
        url = f"{base_url}?module=proxy&action=eth_blockNumber&apikey={api_key}"
        response = requests.get(url, timeout=30)
        data = response.json()
        latest_block = int(data['result'], 16) if data.get('result') else 344220000
        print(f"Latest block: {latest_block}")
    except Exception as e:
        print(f"Error getting latest block: {e}")
        latest_block = 344220000
    
    # Search recent blocks for ANY transactions to the engine
    search_start = latest_block - 5000  # Look at last 5000 blocks
    search_end = latest_block
    
    print(f"Searching blocks {search_start} to {search_end} for engine contract transactions...")
    
    function_signatures = {}
    submit_solution_candidates = []
    
    # Search in chunks
    chunk_size = 1000
    
    for chunk_start in range(search_start, search_end, chunk_size):
        chunk_end = min(chunk_start + chunk_size - 1, search_end)
        
        print(f"  Checking blocks {chunk_start} to {chunk_end}...")
        
        url = f'{base_url}?module=account&action=txlist'
        params = {
            'address': engine_address,
            'startblock': chunk_start,
            'endblock': chunk_end,
            'page': 1,
            'offset': 100,
            'sort': 'asc',
            'apikey': api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if not data.get('result'):
                continue
                
            transactions = data['result']
            print(f"    Found {len(transactions)} transactions")
            
            for tx in transactions:
                input_data = tx.get('input', '')
                
                if len(input_data) >= 10:
                    function_sig = input_data[:10]
                    
                    # Count function signatures
                    if function_sig in function_signatures:
                        function_signatures[function_sig] += 1
                    else:
                        function_signatures[function_sig] = 1
                    
                    # Look for anything that might be solution-related
                    # Common patterns: submit, solution, solve, commit, etc.
                    solution_patterns = ['submit', 'solution', 'solve', 'commit', 'Qm']
                    
                    try:
                        hex_data = input_data[2:]
                        decoded_bytes = bytes.fromhex(hex_data)
                        ascii_text = decoded_bytes.decode('utf-8', errors='ignore').lower()
                        
                        for pattern in solution_patterns:
                            if pattern.lower() in ascii_text:
                                submit_solution_candidates.append({
                                    'hash': tx['hash'],
                                    'block': tx['blockNumber'],
                                    'function': function_sig,
                                    'from': tx['from'],
                                    'pattern_found': pattern,
                                    'input_length': len(input_data)
                                })
                                break
                    except:
                        pass
                        
        except Exception as e:
            print(f"  Error: {e}")
            continue
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    print(f"\n=== ANALYSIS RESULTS ===")
    
    print(f"\nFunction signatures found (frequency):")
    for sig, count in sorted(function_signatures.items(), key=lambda x: x[1], reverse=True):
        print(f"  {sig}: {count} times")
    
    print(f"\nPotential solution transactions:")
    for i, candidate in enumerate(submit_solution_candidates[:10]):  # Show first 10
        print(f"\n  Candidate #{i+1}:")
        print(f"    Hash: {candidate['hash']}")
        print(f"    Block: {candidate['block']}")
        print(f"    Function: {candidate['function']}")
        print(f"    From: {candidate['from']}")
        print(f"    Pattern: '{candidate['pattern_found']}'")
        print(f"    Input length: {candidate['input_length']}")
    
    # Analyze the most common non-submitTask functions
    print(f"\n=== Detailed Analysis of Common Functions ===")
    
    known_sigs = {
        '0x08745dd1': 'submitTask',
        '0x5f2a8b8d': 'submitSolution (expected)',
        '0x3a080839': 'unknown1',
        '0xc64b9f56': 'unknown2'
    }
    
    for sig, count in sorted(function_signatures.items(), key=lambda x: x[1], reverse=True)[:5]:
        if sig == '0x08745dd1':  # Skip submitTask
            continue
            
        name = known_sigs.get(sig, 'unknown')
        print(f"\nAnalyzing {sig} ({name}) - {count} transactions:")
        
        # Get a sample transaction with this signature
        for chunk_start in range(search_start, search_end, chunk_size):
            chunk_end = min(chunk_start + chunk_size - 1, search_end)
            
            url = f'{base_url}?module=account&action=txlist'
            params = {
                'address': engine_address,
                'startblock': chunk_start,
                'endblock': chunk_end,
                'page': 1,
                'offset': 10,
                'sort': 'desc',
                'apikey': api_key
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                data = response.json()
                
                if data.get('result'):
                    for tx in data['result']:
                        if tx.get('input', '').startswith(sig):
                            print(f"  Sample transaction: {tx['hash']}")
                            print(f"  Block: {tx['blockNumber']}")
                            print(f"  From: {tx['from']}")
                            
                            # Try to decode and look for CIDs
                            input_data = tx.get('input', '')
                            try:
                                hex_data = input_data[2:]
                                decoded_bytes = bytes.fromhex(hex_data)
                                ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
                                
                                # Look for CID pattern
                                import re
                                cid_pattern = r'Qm[1-9A-HJ-NP-Za-km-z]{44}'
                                found_cids = re.findall(cid_pattern, ascii_text)
                                
                                if found_cids:
                                    print(f"  🎯 Found CIDs: {found_cids}")
                                else:
                                    print(f"  No CIDs found")
                                    # Show first 100 chars of decoded text
                                    clean_text = ''.join(c for c in ascii_text if c.isprintable())[:100]
                                    if clean_text:
                                        print(f"  Text preview: {clean_text}...")
                                        
                            except Exception as e:
                                print(f"  Could not decode: {e}")
                            
                            break
            except:
                continue
            break

if __name__ == "__main__":
    find_submit_solution_pattern() 