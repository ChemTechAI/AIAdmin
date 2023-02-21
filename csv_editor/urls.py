from django.urls import path


from . import views

app_name = 'csv_editor'

urlpatterns = [
        path('', views.csv_editor_view, name='index'),
             ]
