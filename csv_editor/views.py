from threading import Thread

import pandas as pd
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
from csv_editor.csv_editor_tornado import run_tornado_with_bokeh, pivot_table
from django.http import HttpResponse, JsonResponse
import requests
from bokeh.embed import server_session
from bokeh.client import pull_session

from csv_editor.models import CSVEditorDatasetModel, CSVEditorTempDatasetModel

user = settings.DATABASES['default']['USER']
password = settings.DATABASES['default']['PASSWORD']
database_name = settings.DATABASES['default']['NAME']

database_url = f'postgresql://{user}:{password}@localhost:5432/{database_name}'


# def prepare_table(dataframe: pd.DataFrame):
#     tags_not_allowed = [tag for tag in ['datetime', 'item_id', 'value'] if tag in dataframe]
#     if 'index' in dataframe.columns:
#         dataframe.drop(columns='index', inplace=True)
#
#     print('tags_not_allowed')
#     print(tags_not_allowed)
#     if len(tags_not_allowed) == 3:
#         print('here')
#         if 'datetime' in tags_not_allowed:
#             dataframe.set_index('datetime', inplace=True)
#         dataframe = pivot_table(dataframe)
#     else:
#         dataframe = melt_table(dataframe)
#     print(dataframe.columns)
#     return dataframe


def csv_editor_view(request):
    engine = create_engine(database_url, echo=False)
    full_table = pd.read_sql(f'SELECT index, datetime, value, item_id FROM csv_editor_table', con=engine)

    chosen_tags = request.session.get('chosen_tags') or full_table['item_id'].unique().tolist()

    temp_table = full_table[full_table['item_id'].isin(chosen_tags)]

    temp_table.to_sql(name='csv_editor_temp_table', con=engine, if_exists='replace', chunksize=100000)
    Thread(target=run_tornado_with_bokeh).start()
    session = pull_session(url="http://127.0.0.1:5006/csv_editor")

    script = server_session(model=None,
                            session_id=session.id,
                            url="http://127.0.0.1:5006/csv_editor",
                            )
    return render(request, 'templates/csv_editor/embed.html', {'script': script})


def index(request):
    context = {}
    return render(request, 'templates/csv_editor/csv_editor_index.html', context)


def settings_index(request):
    context = {}
    context['chosen_tags'] = request.session.get('chosen_tags') or []
    request.session['chosen_tags'] = context['chosen_tags']
    tags = request.session.get('tags', [])
    context['tags'] = [tag for tag in tags if tag not in context['chosen_tags']]
    request.session['tags'] = context['tags']
    return render(request, 'templates/csv_editor/csv_editor_settings.html', context)


def add_tag(request):
    tags = request.session['tags']
    chosen_tags = request.session.get('chosen_tags') or []
    new_tag = request.POST.get('add_tag', None)
    request.session['tags'] = [tag for tag in tags if tag not in chosen_tags]
    if new_tag:
        chosen_tags.append(new_tag)
        request.session['chosen_tags'] = chosen_tags
    return redirect('csv_editor:settings')


def reset(request):
    for key in ['chosen_tags']:
        try:
            del request.session[key]
        except BaseException as e:
            print(e)
    return redirect('csv_editor:settings')


def save_dataframe(request):

    context = {}
    context['next_to'] = request.session.get('next_to')

    table_name = request.POST.get('table_name') or 'csv_editor_table'
    # try:
    csv_file = request.FILES["csv_file"]
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'File is not CSV type')
        return HttpResponseRedirect(reverse("datasets:upload_csv"))
    # if file is too large, return
    # if csv_file.multiple_chunks():
    # messages.error(request, "Uploaded file is too big (%.2f MB)." % (csv_file.size / (1000 * 1000),))
    # return HttpResponseRedirect(reverse("myapp:upload_csv"))
    file_data = read_csv(csv_file, parse_dates=True, index_col='datetime')
    request.session['chosen_tag'] = []
    smoothing_window = request.session.get('smoothing_window')
    if smoothing_window:
        data_for_smooth = pivot_table(file_data)
        data_for_smooth = data_for_smooth.rolling(window=f'{smoothing_window}min').mean()
        file_data = melt_table(data_for_smooth)

    tags_not_allowed = [tag for tag in ['datetime', 'item_id', 'value'] if tag not in file_data]

    if tags_not_allowed:
        if 'datetime' not in tags_not_allowed:
            file_data.index = file_data['datetime']
        file_data = melt_table(file_data)
    request.session['tags'] = file_data['item_id'].unique().tolist()

    model_ = CSVEditorDatasetModel()
    model_.truncate()
    engine = create_engine(database_url, echo=False)
    file_data.to_sql(name=table_name, con=engine, if_exists='replace', chunksize=100000)

    status = f'Table is saved with name: {table_name}'
    context['error'] = status
    return redirect('csv_editor:settings')
    # except BaseException as error:
    #     context['error'] = str(error)
    #     return render(request, 'templates/csv_editor/csv_editor_index.html', context)


def melt_table(data: DataFrame):
    copy_data = data.copy()
    copy_data['datetime'] = copy_data.index
    versed_data = copy_data.melt(id_vars=['datetime'],
                                 value_vars=data.columns,
                                 var_name='item_id',
                                 ignore_index=True)

    return versed_data


