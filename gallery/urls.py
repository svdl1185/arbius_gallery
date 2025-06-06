from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.index, name='index'),
    path('info/', views.info, name='info'),
    path('image/<int:image_id>/', views.image_detail, name='image_detail'),
] 