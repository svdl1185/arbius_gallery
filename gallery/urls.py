from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('info/', views.info, name='info'),
    path('top-users/', views.top_users, name='top_users'),
    path('image/<int:image_id>/', views.image_detail, name='image_detail'),
    
    # Secure wallet authentication endpoints
    path('api/auth/nonce/', views.get_auth_nonce, name='get_auth_nonce'),
    path('api/connect-wallet/', views.connect_wallet, name='connect_wallet'),
    path('api/disconnect-wallet/', views.disconnect_wallet, name='disconnect_wallet'),
    
    path('api/image/<int:image_id>/upvote/', views.toggle_upvote, name='toggle_upvote'),
    path('api/image/<int:image_id>/comment/', views.add_comment, name='add_comment'),
    
    path('user/<str:wallet_address>/', views.user_profile, name='user_profile'),
    path('api/profile/update/', views.update_profile, name='update_profile'),
] 