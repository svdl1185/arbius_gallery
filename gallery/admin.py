from django.contrib import admin
from .models import ArbiusImage, ScanStatus


@admin.register(ArbiusImage)
class ArbiusImageAdmin(admin.ModelAdmin):
    list_display = ['short_cid', 'block_number', 'timestamp', 'miner_address', 'is_accessible']
    list_filter = ['is_accessible', 'timestamp', 'discovered_at']
    search_fields = ['cid', 'transaction_hash', 'task_id', 'miner_address']
    readonly_fields = ['transaction_hash', 'task_id', 'block_number', 'timestamp', 'cid', 'discovered_at']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_hash', 'task_id', 'block_number', 'timestamp')
        }),
        ('Image Information', {
            'fields': ('cid', 'ipfs_url', 'image_url', 'is_accessible')
        }),
        ('Metadata', {
            'fields': ('miner_address', 'owner_address', 'gas_used')
        }),
        ('Tracking', {
            'fields': ('discovered_at', 'last_checked')
        }),
    )
    
    def short_cid(self, obj):
        return obj.short_cid
    short_cid.short_description = 'CID'


@admin.register(ScanStatus)
class ScanStatusAdmin(admin.ModelAdmin):
    list_display = ['id', 'last_scanned_block', 'last_scan_time', 'total_images_found', 'scan_in_progress']
    readonly_fields = ['last_scan_time']
    
    def has_add_permission(self, request):
        # Only allow one ScanStatus object
        return not ScanStatus.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of ScanStatus
        return False
