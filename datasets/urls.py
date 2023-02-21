from django.urls import path

from . import views

app_name = 'datasets'

urlpatterns = [
        path('', views.Datasets.as_view(), name='index')
             ]
