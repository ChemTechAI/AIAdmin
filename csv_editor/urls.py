from django.urls import path


from . import views

app_name = 'csv_editor'

urlpatterns = [
        path('csv_editor_plot', views.csv_editor_view, name='csv_editor_plot'),
        path('', views.index, name='index'),
        path('upload_dataframe', views.upload_dataframe, name='upload_dataframe'),
        path('csv_editor_settings', views.settings_index, name='settings'),
        path('add_tag', views.add_tag, name='add_tag'),
        path('reset', views.reset, name='reset'),
        path('load_dataframe', views.load_full_table, name='load_dataframe'),
             ]
