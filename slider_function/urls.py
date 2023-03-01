from django.urls import path


from . import views

app_name = 'slider_function'

urlpatterns = [
        path('', views.index, name='index'),
             ]
