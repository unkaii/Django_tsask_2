from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_view, name='upload'),
    path('file/<str:folder>/<str:filename>/', views.file_detail, name='file_detail'),
]