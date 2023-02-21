from django.urls import path
from . import views
from django.conf.urls.static import static


app_name = 'emulator'

urlpatterns = [
    path('launched',  views.emulator_view, name='launched'),
    path('',  views.index, name='index'),
    path('stop_container/<container_id>',  views.stop_container, name='stop_container'),
    path('start_container/<container_id>',  views.start_container, name='start_container'),
    path('change_branch/<project_name>',  views.change_branch, name='change_branch'),
    path('cnahge_frontend',  views.change_frontend, name='change_frontend'),
] + static('static', view=views.load_static)
