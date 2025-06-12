import requests
import time
import json
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from .models import ArbiusImage, MinerAddress, TokenTransaction, MinerTokenEarnings

logger = logging.getLogger(__name__)


class AIUSTokenTracker:
    """Service to track AIUS token movements and identify sales"""
    
    def __init__(self):
        self.api_key = "RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D"
        self.base_url = "https://api.arbiscan.io/api"
        
        # AIUS token contract address on Arbitrum One (v5)
        self.aius_token_address = "0x4a24b101728e07a52053c13fb4db2bcf490cabc3"
        
        # Known exchange addresses (add more as identified)
        self.exchange_addresses = {
            "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45": "Uniswap V3 Router",  # Uniswap V3
            "0xE592427A0AEce92De3Edee1F18E0157C05861564": "Uniswap V3 Router 1", 
            "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD": "Uniswap Universal Router",
            "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D": "Uniswap V2 Router",
            "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F": "SushiSwap Router",
            "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506": "SushiSwap Router V2",
            # Add more exchange addresses as needed
        }
        
        # Rate limiting
        self.last_api_call = 0
        self.min_call_interval = 0.25  # 250ms between calls
        
    def _rate_limit(self):
        """Ensure we don't exceed the API rate limit"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        
        if time_since_last_call < self.min_call_interval:
            sleep_time = self.min_call_interval - time_since_last_call
            time.sleep(sleep_time)
        
        self.last_api_call = time.time()
    
    def get_token_transfers(self, wallet_address, start_block=0, end_block=99999999):
        """Get all AIUS token transfers for a wallet address"""
        try:
            self._rate_limit()
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': self.aius_token_address,
                'address': wallet_address,
                'startblock': start_block,
                'endblock': end_block,
                'page': 1,
                'offset': 10000,  # Get up to 10k transactions
                'sort': 'desc',
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            data = response.json()
            
            if data.get('status') == '1':
                return data.get('result', [])
            else:
                logger.warning(f"API Warning for {wallet_address}: {data}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting token transfers for {wallet_address}: {e}")
            return []
    
    def get_usd_price_at_time(self, timestamp):
        """Get AIUS price in USD at a specific timestamp"""
        # For now, we'll use a simplified approach
        # In production, you'd want to integrate with price APIs like CoinGecko or DEX price feeds
        
        # These are example prices - replace with real price data
        # You could integrate with Dexscreener API, CoinGecko, or on-chain price oracles
        price_estimates = {
            datetime(2024, 1, 1): 0.25,   # Example prices
            datetime(2024, 6, 1): 0.18,
            datetime(2024, 12, 1): 0.15,
        }
        
        # Find closest price
        target_date = datetime.fromtimestamp(timestamp)
        closest_date = min(price_estimates.keys(), key=lambda x: abs((x - target_date).total_seconds()))
        
        return Decimal(str(price_estimates[closest_date]))
    
    def analyze_transaction_for_sale(self, tx):
        """Analyze a transaction to determine if it's a sale"""
        to_address = tx['to'].lower()
        
        # Check if it's a transfer to a known exchange
        if to_address in [addr.lower() for addr in self.exchange_addresses.keys()]:
            return True, self.exchange_addresses.get(to_address, "Unknown Exchange")
        
        # Check for other sale indicators
        # Look for DEX contract interactions, liquidity provision, etc.
        # This is a simplified check - you'd want more sophisticated analysis
        
        # Check for common DEX router patterns
        dex_patterns = [
            "swap", "exchange", "trade", "router", "pool", 
            "liquidity", "dex", "pancake", "uniswap", "sushi"
        ]
        
        # This would require more sophisticated analysis in practice
        return False, None
    
    def process_miner_wallet(self, miner_address):
        """Analyze a single miner wallet for token movements and sales"""
        logger.info(f"Processing miner wallet: {miner_address}")
        
        # Get all AIUS token transfers for this wallet
        transfers = self.get_token_transfers(miner_address)
        
        total_earned = Decimal('0')
        total_sold = Decimal('0')
        total_usd_from_sales = Decimal('0')
        
        first_earning = None
        last_earning = None
        last_sale = None
        
        for tx in transfers:
            try:
                # Convert values
                amount = Decimal(tx['value']) / Decimal('10') ** Decimal(tx['tokenDecimal'])
                timestamp = int(tx['timeStamp'])
                tx_datetime = datetime.fromtimestamp(timestamp)
                
                # Check if this is an incoming transfer (earning)
                if tx['to'].lower() == miner_address.lower():
                    total_earned += amount
                    
                    if not first_earning or tx_datetime < first_earning:
                        first_earning = tx_datetime
                    if not last_earning or tx_datetime > last_earning:
                        last_earning = tx_datetime
                
                # Check if this is an outgoing transfer (potential sale)
                elif tx['from'].lower() == miner_address.lower():
                    is_sale, exchange_name = self.analyze_transaction_for_sale(tx)
                    
                    if is_sale:
                        total_sold += amount
                        
                        # Get USD price at the time of sale
                        usd_price = self.get_usd_price_at_time(timestamp)
                        sale_value_usd = amount * usd_price
                        total_usd_from_sales += sale_value_usd
                        
                        if not last_sale or tx_datetime > last_sale:
                            last_sale = tx_datetime
                        
                        logger.info(f"Found sale: {amount} AIUS for ~${sale_value_usd} on {exchange_name}")
                
                # Store the transaction record
                TokenTransaction.objects.update_or_create(
                    transaction_hash=tx['hash'],
                    defaults={
                        'from_address': tx['from'].lower(),
                        'to_address': tx['to'].lower(),
                        'amount': amount,
                        'block_number': int(tx['blockNumber']),
                        'timestamp': tx_datetime,
                        'gas_price': int(tx['gasPrice']) if tx.get('gasPrice') else None,
                        'gas_used': int(tx['gasUsed']) if tx.get('gasUsed') else None,
                    }
                )
                
            except Exception as e:
                logger.error(f"Error processing transaction {tx.get('hash', 'unknown')}: {e}")
                continue
        
        # Update or create miner earnings record
        earnings, created = MinerTokenEarnings.objects.update_or_create(
            miner_address=miner_address.lower(),
            defaults={
                'total_aius_earned': total_earned,
                'total_aius_sold': total_sold,
                'total_usd_from_sales': total_usd_from_sales,
                'first_earning_date': first_earning,
                'last_earning_date': last_earning,
                'last_sale_date': last_sale,
                'last_analyzed': timezone.now(),
                'needs_reanalysis': False,
            }
        )
        
        logger.info(f"Processed {miner_address}: Earned {total_earned} AIUS, Sold {total_sold} AIUS for ${total_usd_from_sales}")
        return earnings
    
    def analyze_all_miners(self, force_reanalysis=False):
        """Analyze all known miners for token movements and sales"""
        logger.info("Starting comprehensive miner token analysis...")
        
        # Get all known miners
        miners = MinerAddress.objects.all()
        
        results = []
        for miner in miners:
            try:
                # Skip if recently analyzed unless forced
                if not force_reanalysis:
                    try:
                        earnings = MinerTokenEarnings.objects.get(miner_address=miner.wallet_address.lower())
                        if (earnings.last_analyzed and 
                            earnings.last_analyzed > timezone.now() - timedelta(hours=24) and
                            not earnings.needs_reanalysis):
                            logger.info(f"Skipping {miner.wallet_address} - recently analyzed")
                            results.append(earnings)
                            continue
                    except MinerTokenEarnings.DoesNotExist:
                        pass
                
                # Process the miner wallet
                earnings = self.process_miner_wallet(miner.wallet_address)
                results.append(earnings)
                
                # Add delay to respect rate limits
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error analyzing miner {miner.wallet_address}: {e}")
                continue
        
        logger.info(f"Completed analysis of {len(results)} miners")
        return results
    
    def get_miner_earnings_summary(self):
        """Get a summary of all miner earnings"""
        earnings = MinerTokenEarnings.objects.all().order_by('-total_usd_from_sales')
        
        summary = {
            'total_miners': earnings.count(),
            'total_aius_earned': sum(e.total_aius_earned for e in earnings),
            'total_aius_sold': sum(e.total_aius_sold for e in earnings),
            'total_usd_from_sales': sum(e.total_usd_from_sales for e in earnings),
            'miners': earnings
        }
        
        return summary


# Initialize the tracker service
token_tracker = AIUSTokenTracker() 