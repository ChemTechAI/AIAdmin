from django.urls import path

from . import views

app_name = 'plotly_graph'

urlpatterns = [
        path('', views.index, name='index')
             ]
