from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.html import format_html
from .models import (
    ArbiusImage, UserProfile, ImageUpvote, ImageComment, ScanStatus, 
    MinerAddress, TokenTransaction, MinerTokenEarnings
)


@admin.register(ArbiusImage)
class ArbiusImageAdmin(admin.ModelAdmin):
    list_display = ['short_cid', 'short_tx_hash', 'block_number', 'timestamp', 'solution_provider', 'task_submitter', 'is_accessible', 'upvote_count_display', 'comment_count_display']
    list_filter = ['is_accessible', 'timestamp', 'model_id']
    search_fields = ['cid', 'transaction_hash', 'task_id', 'prompt', 'solution_provider', 'task_submitter']
    readonly_fields = ['transaction_hash', 'task_id', 'block_number', 'cid', 'discovered_at', 'upvote_count_display', 'comment_count_display']
    ordering = ['-timestamp']
    
    def upvote_count_display(self, obj):
        return obj.upvote_count
    upvote_count_display.short_description = 'Upvotes'
    
    def comment_count_display(self, obj):
        return obj.comment_count
    comment_count_display.short_description = 'Comments'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('upvotes', 'comments')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['wallet_address', 'display_name', 'total_images_created', 'total_upvotes_received', 'created_at']
    search_fields = ['wallet_address', 'display_name']
    readonly_fields = ['total_images_created', 'total_upvotes_received']
    ordering = ['-total_images_created']


@admin.register(ImageUpvote)
class ImageUpvoteAdmin(admin.ModelAdmin):
    list_display = ['image', 'wallet_address', 'created_at']
    list_filter = ['created_at']
    search_fields = ['wallet_address', 'image__cid']
    ordering = ['-created_at']


@admin.register(ImageComment)
class ImageCommentAdmin(admin.ModelAdmin):
    list_display = ['image', 'wallet_address', 'short_content', 'created_at']
    list_filter = ['created_at']
    search_fields = ['wallet_address', 'content', 'image__cid']
    ordering = ['-created_at']


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


@admin.register(MinerAddress)
class MinerAddressAdmin(admin.ModelAdmin):
    list_display = ['wallet_address', 'total_solutions', 'total_commitments', 'first_seen', 'last_seen', 'is_active']
    list_filter = ['is_active', 'first_seen', 'last_seen']
    search_fields = ['wallet_address']
    readonly_fields = ['first_seen']
    ordering = ['-last_seen']
    
    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(TokenTransaction)
class TokenTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_hash', 'from_address_short', 'to_address_short', 'amount', 'timestamp', 'is_sale', 'sale_price_usd']
    list_filter = ['is_sale', 'timestamp', 'exchange_address']
    search_fields = ['transaction_hash', 'from_address', 'to_address', 'exchange_address']
    readonly_fields = ['transaction_hash', 'block_number', 'timestamp', 'gas_price', 'gas_used', 'created_at']
    ordering = ['-timestamp']
    
    def from_address_short(self, obj):
        return f"{obj.from_address[:8]}...{obj.from_address[-6:]}"
    from_address_short.short_description = 'From'
    
    def to_address_short(self, obj):
        return f"{obj.to_address[:8]}...{obj.to_address[-6:]}"
    to_address_short.short_description = 'To'
    
    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(MinerTokenEarnings)
class MinerTokenEarningsAdmin(admin.ModelAdmin):
    list_display = [
        'miner_address_short', 'total_aius_earned', 'total_aius_sold', 
        'total_usd_from_sales', 'last_analyzed', 'needs_reanalysis'
    ]
    list_filter = ['needs_reanalysis', 'last_analyzed', 'last_sale_date']
    search_fields = ['miner_address']
    readonly_fields = ['last_analyzed', 'updated_at']
    ordering = ['-total_usd_from_sales']
    
    def miner_address_short(self, obj):
        return format_html(
            '<a href="https://arbiscan.io/address/{}" target="_blank">{}</a>',
            obj.miner_address,
            f"{obj.miner_address[:8]}...{obj.miner_address[-6:]}"
        )
    miner_address_short.short_description = 'Miner Address'
    
    def get_queryset(self, request):
        return super().get_queryset(request)
    
    # Add some useful actions
    actions = ['mark_for_reanalysis']
    
    def mark_for_reanalysis(self, request, queryset):
        updated = queryset.update(needs_reanalysis=True)
        self.message_user(request, f"{updated} miners marked for reanalysis.")
    mark_for_reanalysis.short_description = "Mark selected miners for reanalysis"
