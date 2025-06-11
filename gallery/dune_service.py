"""
Dune Analytics integration service for Arbius mining earnings data.
"""

import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

try:
    from dune_client.client import DuneClient
    from dune_client.query import QueryBase
    DUNE_AVAILABLE = True
except ImportError:
    DUNE_AVAILABLE = False
    logger.warning("dune-client not available. Install with: pip install dune-client")


class ArbiusDuneService:
    """Service to fetch Arbius mining data from Dune Analytics"""
    
    def __init__(self):
        self.client = None
        self.available = DUNE_AVAILABLE
        
        if DUNE_AVAILABLE:
            try:
                # Try to initialize Dune client if API key is available
                api_key = getattr(settings, 'DUNE_API_KEY', None)
                if api_key:
                    self.client = DuneClient(api_key=api_key)
                    logger.info("Dune Analytics client initialized successfully")
                else:
                    logger.info("DUNE_API_KEY not set - Dune integration disabled")
                    self.available = False
            except Exception as e:
                logger.warning(f"Failed to initialize Dune client: {e}")
                self.available = False
    
    def is_available(self) -> bool:
        """Check if Dune Analytics integration is available"""
        return self.available and self.client is not None
    
    def get_miner_earnings_data(self, cache_timeout: int = 3600) -> Optional[Dict[str, Any]]:
        """
        Fetch miner earnings data from Dune Analytics.
        
        Args:
            cache_timeout: Cache timeout in seconds (default 1 hour)
            
        Returns:
            Dictionary with miner earnings data or None if not available
        """
        if not self.is_available():
            return None
        
        cache_key = "arbius_dune_miner_earnings"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info("Using cached Dune earnings data")
            return cached_data
        
        try:
            # Try to fetch from multiple known Arbius queries
            # These are example query IDs - need to be replaced with actual Arbius dashboard queries
            query_ids = [
                # 1234567,  # Miner earnings by address
                # 1234568,  # Total AIUS distributed 
                # 1234569,  # Daily mining activity
            ]
            
            earnings_data = {
                'miners': {},
                'total_distributed': 0,
                'last_updated': None,
                'source': 'dune_analytics'
            }
            
            # For now, return placeholder data structure
            # TODO: Replace with actual Dune query execution once we have the query IDs
            logger.info("Dune integration ready but needs actual Arbius query IDs")
            
            # Cache the result
            cache.set(cache_key, earnings_data, cache_timeout)
            return earnings_data
            
        except Exception as e:
            logger.error(f"Error fetching Dune earnings data: {e}")
            return None
    
    def get_miner_earnings_by_address(self, miner_address: str) -> Optional[float]:
        """
        Get total earnings for a specific miner address.
        
        Args:
            miner_address: The miner's wallet address
            
        Returns:
            Total AIUS earnings or None if not available
        """
        earnings_data = self.get_miner_earnings_data()
        
        if not earnings_data or 'miners' not in earnings_data:
            return None
        
        return earnings_data['miners'].get(miner_address.lower())
    
    def refresh_cache(self) -> bool:
        """
        Force refresh of cached Dune data.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        cache_key = "arbius_dune_miner_earnings"
        cache.delete(cache_key)
        
        # Fetch fresh data
        fresh_data = self.get_miner_earnings_data(cache_timeout=3600)
        return fresh_data is not None
    
    def execute_custom_query(self, query_id: int, max_age_hours: int = 8) -> Optional[Any]:
        """
        Execute a custom Dune query and return results.
        
        Args:
            query_id: The Dune query ID
            max_age_hours: Maximum age of cached results before re-execution
            
        Returns:
            Query results or None if failed
        """
        if not self.is_available():
            return None
        
        try:
            logger.info(f"Executing Dune query {query_id}")
            results = self.client.get_latest_result(query_id, max_age_hours=max_age_hours)
            
            if results and hasattr(results, 'result') and results.result:
                logger.info(f"Successfully fetched {len(results.result.rows)} rows from query {query_id}")
                return results.result.rows
            else:
                logger.warning(f"No data returned from query {query_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing Dune query {query_id}: {e}")
            return None


# Global service instance
dune_service = ArbiusDuneService() 