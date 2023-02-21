import os

import pandas as pd

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .functions import slider_expression


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DIR_WITH_PROJECTS = os.path.join(BASE_DIR, 'git_projects')


@login_required(login_url='signin')
def index(request):

    csv_file = request.FILES['file'] if 'file' in request.FILES else None

    expression = request.POST.get('expression', None)
    slider_tag = request.POST.get('var_name', 'var_x')
    value_start = request.POST.get('value_start', None)
    value_stop = request.POST.get('value_stop', None)
    value_step = request.POST.get('value_step', value_start)
    tags_to_display = request.POST.get('tags_to_display', '')

    tags_to_display = tags_to_display.replace(' ', '').split(',')
    if '' in tags_to_display:
        tags_to_display.pop(tags_to_display.index(''))

    if csv_file:
        # TODO separate stage after file loading. Return tags from Dataframe
        data = pd.read_csv(csv_file, parse_dates=True, index_col='datetime')

        tags_to_display = [tag for tag in tags_to_display if tag in data.columns]
        tags_to_display = tags_to_display or data.columns.to_list()
    else:
        # TODO: pull data from database
        return render(request, "templates/slider_function/slider_function_index.html",
                      {"result": 'Choose file, please'},
                      )

    if expression and value_start and value_stop and value_step:
        params_dict = {'data': data,
                       'expression': expression,
                       'slider_start_stop_step': {slider_tag: (float(value_start),
                                                               float(value_stop) + float(value_step),
                                                               float(value_step))},
                       'tags_to_display': tags_to_display}

        result = slider_expression(**params_dict)
        return render(request,
                      "templates/slider_function/slider_function_index.html",
                      {"result": result})
    else:
        return render(request, "templates/slider_function/slider_function_index.html")
