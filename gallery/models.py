from django.db import models
from django.utils import timezone


class ArbiusImage(models.Model):
    """Model to store information about Arbius generated images"""
    
    # Transaction details
    transaction_hash = models.CharField(max_length=66, unique=True, db_index=True)
    task_id = models.CharField(max_length=66, db_index=True)
    block_number = models.BigIntegerField()
    timestamp = models.DateTimeField()
    
    # Image details
    cid = models.CharField(max_length=100, db_index=True)
    ipfs_url = models.URLField()
    image_url = models.URLField()
    
    # AI Generation details
    model_id = models.CharField(max_length=66, blank=True, null=True, help_text="The AI model used to generate this image")
    prompt = models.TextField(blank=True, null=True, help_text="The prompt used to generate this image")
    input_parameters = models.JSONField(blank=True, null=True, help_text="Full input parameters including prompt and other settings")
    
    # Addresses - clarified for accuracy
    solution_provider = models.CharField(max_length=42, default='0x0000000000000000000000000000000000000000', help_text="Address of the miner who provided the solution/image")
    task_submitter = models.CharField(max_length=42, null=True, blank=True, help_text="Address of the user who originally submitted the task/prompt")
    
    # Legacy field for backward compatibility (will be removed later)
    miner_address = models.CharField(max_length=42, null=True, blank=True, help_text="DEPRECATED: Use solution_provider instead")
    owner_address = models.CharField(max_length=42, null=True, blank=True)
    gas_used = models.BigIntegerField(null=True, blank=True)
    
    # Tracking
    discovered_at = models.DateTimeField(default=timezone.now)
    is_accessible = models.BooleanField(default=True)
    last_checked = models.DateTimeField(default=timezone.now)
    ipfs_gateway = models.CharField(max_length=200, blank=True, default='')
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['cid']),
            models.Index(fields=['transaction_hash']),
        ]
    
    def __str__(self):
        return f"Arbius Image {self.cid[:10]}... (Block {self.block_number})"
    
    @property
    def short_cid(self):
        """Return a shortened version of the CID for display"""
        return f"{self.cid[:8]}...{self.cid[-8:]}" if len(self.cid) > 16 else self.cid
    
    @property
    def short_tx_hash(self):
        """Return a shortened version of the transaction hash for display"""
        return f"{self.transaction_hash[:10]}...{self.transaction_hash[-8:]}"
    
    @property
    def short_model_id(self):
        """Return a shortened version of the model ID for display"""
        if not self.model_id:
            return "Unknown Model"
        return f"{self.model_id[:8]}...{self.model_id[-8:]}" if len(self.model_id) > 16 else self.model_id

    @property
    def clean_prompt(self):
        """Return the prompt with additional instruction text removed"""
        if not self.prompt:
            return ""
        
        # Remove the additional instruction text that gets appended to prompts
        clean_text = self.prompt
        
        # Remove the "Additional instruction: Make sure to keep response short and consice." part
        if "Additional instruction: Make sure to keep response short and consice." in clean_text:
            clean_text = clean_text.replace("Additional instruction: Make sure to keep response short and consice.", "").strip()
        
        # Also handle slight variations in spacing/punctuation
        if "Additional instruction: Make sure to keep response short and concise." in clean_text:
            clean_text = clean_text.replace("Additional instruction: Make sure to keep response short and concise.", "").strip()
            
        return clean_text


class ScanStatus(models.Model):
    """Model to track blockchain scanning progress"""
    
    last_scanned_block = models.BigIntegerField(default=0)
    last_scan_time = models.DateTimeField(default=timezone.now)
    total_images_found = models.IntegerField(default=0)
    scan_in_progress = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Scan statuses"
    
    def __str__(self):
        return f"Scan Status - Last Block: {self.last_scanned_block}"
