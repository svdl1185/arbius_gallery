from django.contrib import admin
from .models import ArbiusImage, ScanStatus


@admin.register(ArbiusImage)
class ArbiusImageAdmin(admin.ModelAdmin):
    list_display = ['short_cid', 'block_number', 'timestamp', 'solution_provider', 'is_accessible', 'short_model_id', 'has_prompt', 'is_system_text']
    list_filter = ['is_accessible', 'timestamp', 'discovered_at', 'model_id']
    search_fields = ['cid', 'transaction_hash', 'task_id', 'solution_provider', 'task_submitter', 'prompt', 'model_id']
    readonly_fields = ['transaction_hash', 'task_id', 'block_number', 'timestamp', 'cid', 'discovered_at']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_hash', 'task_id', 'block_number', 'timestamp')
        }),
        ('Image Information', {
            'fields': ('cid', 'ipfs_url', 'image_url', 'is_accessible')
        }),
        ('AI Generation Details', {
            'fields': ('model_id', 'prompt', 'input_parameters')
        }),
        ('Addresses', {
            'fields': ('solution_provider', 'task_submitter', 'owner_address')
        }),
        ('Legacy/Metadata', {
            'fields': ('miner_address', 'gas_used')
        }),
        ('Tracking', {
            'fields': ('discovered_at', 'last_checked')
        }),
    )
    
    def short_cid(self, obj):
        return obj.short_cid
    short_cid.short_description = 'CID'
    
    def short_model_id(self, obj):
        return obj.short_model_id
    short_model_id.short_description = 'Model'
    
    def has_prompt(self, obj):
        return bool(obj.prompt)
    has_prompt.boolean = True
    has_prompt.short_description = 'Has Prompt'
    
    def is_system_text(self, obj):
        """Identify entries that are system text (not actual images)"""
        if not obj.prompt:
            return False
        return obj.prompt.strip().startswith("<|begin_of_text|>")
    is_system_text.boolean = True
    is_system_text.short_description = 'System Text'


@admin.register(ScanStatus)
class ScanStatusAdmin(admin.ModelAdmin):
    list_display = ['last_scanned_block', 'last_scan_time', 'total_images_found', 'scan_in_progress']
    readonly_fields = ['last_scanned_block', 'last_scan_time', 'total_images_found']
    
    def has_add_permission(self, request):
        # Only allow one ScanStatus object
        return not ScanStatus.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of ScanStatus
        return False
