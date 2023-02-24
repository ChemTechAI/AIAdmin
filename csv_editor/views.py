from threading import Thread
from bokeh.server.server import Server
from bokeh.util.browser import view
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http.response import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.conf import settings

from sqlalchemy import create_engine
from pandas import DataFrame, read_csv

# Create your views here.
from csv_editor.csv_editor_tornado import run_tornado_with_bokeh, plot_csv_editor, IndexHandler
from django.http import HttpResponse, JsonResponse
import requests
from bokeh.embed import server_session
from bokeh.client import pull_session

from csv_editor.models import CSVEditorDatasetModel, CSVEditorTempDatasetModel

user = settings.DATABASES['default']['USER']
password = settings.DATABASES['default']['PASSWORD']
database_name = settings.DATABASES['default']['NAME']

database_url = f'postgresql://{user}:{password}@localhost:5432/{database_name}'


def csv_editor_view(request):
    Thread(target=run_tornado_with_bokeh).start()
    session = pull_session(url="http://127.0.0.1:5006/csv_editor")

    script = server_session(model=None,
                            session_id=session.id,
                            url="http://127.0.0.1:5006/csv_editor",
                            )
    return render(request, 'templates/csv_editor/embed.html', {'script': script})


class CSVEditorDatasets(View):

    def get(self, request):
        request.session['next_to'] = request.META.get('HTTP_REFERER')
        engine = create_engine(database_url, echo=False)
        table_names = [table_name for table_name in engine.table_names()
                       if 'auth' not in table_name and 'django' not in table_name]

        return render(request, 'templates/csv_editor/csv_editor_index.html', {'table_names': table_names})

    def post(self, request):
        context = {}
        context['next_to'] = request.session.get('next_to')

        table_name = request.POST.get('table_name') or 'csv_editor_table'

        try:
            csv_file = request.FILES["csv_file"]
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'File is not CSV type')
                return HttpResponseRedirect(reverse("datasets:upload_csv"))
            # if file is too large, return
            # if csv_file.multiple_chunks():
                # messages.error(request, "Uploaded file is too big (%.2f MB)." % (csv_file.size / (1000 * 1000),))
                # return HttpResponseRedirect(reverse("myapp:upload_csv"))
            file_data = read_csv(csv_file, parse_dates=True, index_col='datetime')
            # smoothing_window = 1
            # file_data = file_data.rolling(window=f'{smoothing_window}min').mean()
            tags_not_allowed = [tag for tag in ['datetime', 'item_id', 'value'] if tag not in file_data]

            if tags_not_allowed:
                if 'datetime' not in tags_not_allowed:
                    file_data.index = file_data['datetime']
                file_data = melt_table(file_data)
            # print(len(set(file_data.item_id)))

            model_ = CSVEditorDatasetModel()
            model_.truncate()
            engine = create_engine(database_url, echo=False)
            file_data.to_sql(name=table_name, con=engine, if_exists='replace', chunksize=100000)

            status = f'Table is saved with name: {table_name}'
            context['error'] = status
            return render(request, 'templates/csv_editor/csv_editor_index.html', context)
        except BaseException as error:
            context['error'] = str(error)
            return render(request, 'templates/csv_editor/csv_editor_index.html', context)

class CSVEditorTempDatasets(View):

    def get(self, request):
        request.session['next_to'] = request.META.get('HTTP_REFERER')
        engine = create_engine(database_url, echo=False)
        table_names = [table_name for table_name in engine.table_names()
                       if 'auth' not in table_name and 'django' not in table_name]

        return render(request, 'templates/csv_editor/csv_editor_settings.html', {'table_names': table_names})

    def post(self, request):
        context = {}
        context['next_to'] = request.session.get('next_to')
        table_name = 'csv_editor_temp_table'
        tags = request.POST.get('tags')

        try:
            full_table = 1#######################################################################
            tags = tags or full_table.columns
            temp_table = full_table[tags]
            model_ = CSVEditorTempDatasetModel()
            model_.truncate()
            engine = create_engine(database_url, echo=False)
            temp_table.to_sql(name=table_name, con=engine, if_exists='replace', chunksize=100000)

            status = f'Table is saved with name: {table_name}'
            context['error'] = status
            return render(request, 'templates/csv_editor/csv_editor_settings.html', context)
        except BaseException as error:
            context['error'] = str(error)
            return render(request, 'templates/csv_editor/csv_editor_settings.html', context)


def melt_table(data: DataFrame):
    copy_data = data.copy()
    copy_data['datetime'] = copy_data.index
    versed_data = copy_data.melt(id_vars=['datetime'],
                                 value_vars=data.columns,
                                 var_name='item_id',
                                 ignore_index=True)

    return versed_data


