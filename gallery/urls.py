from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.index, name='index'),
    path('image/<int:image_id>/', views.image_detail, name='image_detail'),
    path('stats/', views.stats, name='stats'),
] 