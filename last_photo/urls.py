from django.urls import path

from . import views

app_name = 'last_photo'

urlpatterns = [
        path('', views.index, name='index')
             ]
