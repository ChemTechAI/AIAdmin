from django.urls import path

from . import views

app_name = 'test_calculations'

urlpatterns = [
        path('', views.index, name='index'),
        path('set_function_params', views.index, name='set_function_params'),
        path('calculate_result', views.calculate, name='calculate_result'),
        path('reset', views.reset, name='reset'),
        path('add_project', views.add_project, name='add_project'),
        path('load', views.load_csv, name='load'),
             ]
