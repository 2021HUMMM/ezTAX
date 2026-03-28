from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/search/', views.search_api, name='search_api'),
]
