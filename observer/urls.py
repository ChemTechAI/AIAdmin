"""observer URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth
from members import views as member_views
from test_calculations import views as test_views
from . import views

urlpatterns = [
    # path(':', include('slider_function.urls')),
    path('admin/', admin.site.urls),
    path('last_photo/', include('last_photo.urls')),
    path('plotly_graph/', include('plotly_graph.urls')),
    path('datasets/', include('datasets.urls')),
    path('emulator/', include('emulator.urls')),
    path('test_calculations/', include('test_calculations.urls')),
    path('members/', include('members.urls')),
    path('slider_function/', include('slider_function.urls')),
    path('signin/', member_views.signin, name='signin'),
    path('logout/', auth.LogoutView.as_view(template_name='templates/members/member_index.html'), name='logout'),
    path('celery-progress/', include('celery_progress.urls')),
    path(r'^(?P<task_id>[\w-]+)/$', test_views.get_progress, name='task_status'),
    path('', include('home.urls')),
    path('csv_editor/', include('csv_editor.urls')),
    # Emulator urls:
    path('aio_ui/config', views.redirect_json),
    path('aio_ui/image/<file_name>', views.redirect_image),
    path('image/<file_name>', views.redirect_image),
    path('<file_name>/calculated_parameters', views.redirect_json),
    path('<file_name>/sensors', views.redirect_json),
    path('<file_name>/download', views.redirect_json_with_csv),
    path('<file_name>/recommendations', views.redirect_json),
    path('<file_name>/set_specification_and_consts', views.redirect_json),
    path('<file_name>/current_specification_and_consts', views.redirect_json),
    path('<file_name>/current_consts', views.redirect_json),
]
