from django.urls import path


from . import views

app_name = 'csv_editor'

urlpatterns = [
        path('csv_editor_plot', views.csv_editor_view, name='csv_editor_plot'),
        path('', views.CSVEditorDatasets.as_view(), name='index'),
        path('csv_editor_settings', views.CSVEditorTempDatasets.as_view(), name='settings')
             ]
