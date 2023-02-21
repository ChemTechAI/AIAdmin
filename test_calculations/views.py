import os
import inspect
import traceback
import json

import pandas as pd

from git import Repo
from celery.result import AsyncResult
from sqlalchemy import create_engine

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponse

from .tasks import calculate_from_dataframe_delayed, calculate_from_dict_delayed, calculate_from_file_delayed, \
    calculate_one_option
from .functions import get_function_object_by_name, get_all_functions_with_location, find_function_config_using, \
    generate_recursive_html_for_dict, update_config_from_request, generate_data_from_manual, prepare_html_for_config,\
    prepare_dataframe
from plotly_graph.views import plot_result_to_html

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DIR_WITH_PROJECTS = os.path.join(BASE_DIR, 'git_projects')


@login_required(login_url='signin')
def get_progress(request, task_id):
    result = AsyncResult(task_id)
    response_data = {
        'state': result.state,
        'details': result.info,
    }
    print(response_data)
    return HttpResponse(json.dumps(response_data), content_type='application/json')


def load_last_calculations() -> pd.DataFrame:
    user = settings.DATABASES['default']['USER']
    password = settings.DATABASES['default']['PASSWORD']
    database_name = settings.DATABASES['default']['NAME']

    database_url = f'postgresql://{user}:{password}@localhost:5432/{database_name}'

    engine = create_engine(database_url, echo=False)

    try:
        data = pd.read_sql('SELECT * FROM test_calculations', con=engine)
        if 'datetime' in data.columns:
            data.set_index('datetime', inplace=True)
        elif 'index' in data.columns:
            data.set_index('index', inplace=True)
        return data
    except BaseException as e:
        print(e)


@login_required(login_url='signin')
def reset(request):
    try:
        projects_list = os.listdir(DIR_WITH_PROJECTS)
    except BaseException as result:
        return render(request,
                      "templates/test_calculations/test_calculations_index.html",
                      {"result": result,
                       })
    for key in ['chosen_project_name', 'chosen_function_name', 'chosen_function_params',
                'chosen_function_config', 'last_saved_result', 'current_branch']:
        try:
            del request.session[key]
        except BaseException as e:
            print(e)
    return redirect('test_calculations:index')


@login_required(login_url='signin')
def load_csv(request):
    last_saved_result = load_last_calculations()
    if last_saved_result is not None and type(last_saved_result) == pd.DataFrame:

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=export.csv'

        last_saved_result.to_csv(path_or_buf=response)
        return response
    else:
        return render(request,
                      "templates/test_calculations/test_calculations_index.html")


@login_required(login_url='signin')
def add_project(request):
    git_http = request.POST.get('git_http')
    if not os.path.exists(DIR_WITH_PROJECTS):
        os.makedirs(DIR_WITH_PROJECTS)
    git_project_name = git_http.split('/')[-1].replace('.git', '')
    try:
        origin = Repo.clone_from(url=git_http,
                                 to_path=os.path.join(DIR_WITH_PROJECTS, git_project_name))

    except BaseException as error:
        return render(request,
                      "templates/test_calculations/test_calculations_index.html",
                      {"last_saved_result": error,
                       })
    return render(request,
                  "templates/test_calculations/test_calculations_index.html",
                  {"last_saved_result": "Success",
                   })


@login_required(login_url='signin')
def index(request):
    context = {}
    try:
        context['projects_list'] = os.listdir(DIR_WITH_PROJECTS)
    except BaseException as result:
        return render(request,
                      "templates/test_calculations/test_calculations_index.html",
                      {"result": result,
                       })

    last_saved_result = load_last_calculations()
    if last_saved_result is not None and type(last_saved_result) == pd.DataFrame:
        context['html_table'] = last_saved_result.head(15).to_html()
        context['last_saved_result'] = plot_result_to_html(last_saved_result)

    if request.POST.get('project_name', None):
        request.session['chosen_project_name'] = request.POST.get('project_name', None)
        for key in ['chosen_function_name', 'chosen_function_config', 'chosen_function_params', 'current_branch']:
            try:
                del request.session[key]
            except BaseException as e:
                print(e)
    chosen_project_name = request.session.get('chosen_project_name', None)

    if not chosen_project_name:
        return render(request,
                      "templates/test_calculations/test_calculations_index.html",
                      context)

    repo = Repo(path=os.path.join(DIR_WITH_PROJECTS, chosen_project_name))

    remotes_branches = repo.remote().refs
    context["remotes_branches_names"] = [branch.name for branch in remotes_branches]

    current_branch = request.POST.get('git_branch_name', None)
    if current_branch:
        current_branch = request.POST.get('git_branch_name')
        request.session['current_branch'] = current_branch
        repo.git.checkout(current_branch)
        # origin = repo.remotes.origin
        # origin.pull(current_branch.split('/')[-1])
        for key in ['chosen_function_name', 'chosen_function_config', 'chosen_function_params']:
            try:
                del request.session[key]
            except BaseException as e:
                print(e)
    context["chosen_project_name"] = chosen_project_name

    if not request.session.get('current_branch', None):
        return render(request,
                      "templates/test_calculations/test_calculations_index.html",
                      context)

    python_files, functions_list, project_config, errors = get_all_functions_with_location(
        project_name=chosen_project_name)
    context['error'] = errors

    request.session['chosen_project_config'] = project_config
    request.session['chosen_project_functions_list'] = functions_list
    context["functions_list"] = functions_list

    if request.POST.get('function_name', None):
        request.session['chosen_function_name'] = request.POST.get('function_name', None)

        for key in ['chosen_function_config', 'chosen_function_params']:
            try:
                del request.session[key]
            except BaseException as e:
                print(e)

    chosen_function_name = request.session.get('chosen_function_name', None)
    context['chosen_function_name'] = chosen_function_name
    if not chosen_function_name:
        return render(request,
                      "templates/test_calculations/test_calculations_index.html",
                      context)

    function_object = get_function_object_by_name(project_name=chosen_project_name,
                                                  function_name=chosen_function_name)

    chosen_function_params = request.session.get('chosen_function_params', {})
    chosen_function_config = request.session.get('chosen_function_config', {})

    if not chosen_function_params:
        chosen_function_params = {}
        for parameter, parameter_type in function_object.__annotations__.items():
            if 'return' in parameter or 'config' in parameter:
                continue
            if parameter_type in [str, bool, pd.DataFrame]:
                chosen_function_params[parameter] = {'value': None,
                                                     'type': str(parameter_type)}
            else:
                chosen_function_params[parameter] = {'value': {'start': None, 'stop': None, 'step': None},
                                                     'type': str(parameter_type)}

        request.session['chosen_function_params'] = chosen_function_params
    if not chosen_function_config:
        if 'config' in function_object.__annotations__:
            config_names = find_function_config_using(inspect.getsource(function_object))
            chosen_function_config = {}
            if chosen_function_name not in config_names:
                chosen_function_config = project_config.get(chosen_function_name, {})
                for key in chosen_function_config.keys():
                    if key in config_names:
                        config_names.remove(key)

            for config_name in config_names:
                if type(config_name) == list:
                    chosen_function_config[config_name[0]] = {}
                    chosen_function_config[config_name[0]][config_name[1]] = \
                        project_config[config_name[0]][config_name[1]]
                else:
                    chosen_function_config[config_name] = project_config[config_name]

            if not chosen_function_config:
                chosen_function_config = project_config.copy()

            request.session['chosen_function_config'] = chosen_function_config

    context["function_params"] = chosen_function_params
    context["config_params_html"] = prepare_html_for_config(request=request, config=chosen_function_config)

    return render(request,
                  "templates/test_calculations/test_calculations_index.html",
                  context)


@login_required(login_url='signin')
def calculate(request):
    context = {}
    context.update(request.session)
    chosen_function_config = request.session['chosen_function_config']
    chosen_function_params = request.session['chosen_function_params']
    chosen_function_name = request.session['chosen_function_name']
    chosen_project_name = request.session['chosen_function_name']

    context["config_params_html"] = prepare_html_for_config(request=request, config=chosen_function_config)

    csv_file = request.FILES['file'] if 'file' in request.FILES.keys() else None

    task_id = None
    if csv_file is None:
        # try:
        for parameter, param_value in chosen_function_params.items():

            if 'pandas.core.frame.DataFrame' in param_value['type']:
                value = request.FILES[parameter] if parameter in request.FILES else None
                chosen_function_params[parameter]['value'] = pd.read_csv(value, parse_dates=True,
                                                                         index_col='datetime').to_json()
            elif 'str' in param_value['type']:
                value = request.POST.get(parameter, None)
                chosen_function_params[parameter]['value'] = value
            else:
                for part_of_value in ['start', 'step', 'stop']:
                    value = request.POST.get(parameter + f'_{part_of_value}', None)
                    chosen_function_params[parameter]['value'][part_of_value] = value

        request.session['chosen_function_params'] = chosen_function_params
        context["function_params"] = chosen_function_params

        prepared_input = generate_data_from_manual(params=chosen_function_params)

        if type(prepared_input) == pd.DataFrame:
            task = calculate_from_dict_delayed.delay(
                function_name=chosen_function_name,
                project_name=chosen_project_name,
                params_dict=prepared_input.to_json(),
                config=chosen_function_config
            )
            task_id = task.task_id

        elif pd.DataFrame in [type(parameter) for parameter in prepared_input.values()]:
            task = calculate_from_dataframe_delayed.delay(
                function_name=chosen_function_name,
                project_name=chosen_project_name,
                params_with_dataframe=prepared_input,
                config=chosen_function_config
            )
            task_id = task.task_id

        else:

            result = calculate_one_option(
                function_name=chosen_function_name,
                project_name=chosen_project_name,
                params=prepared_input,
                config=chosen_function_config,
            )
            if result is not None:
                context["last_saved_result"] = result
                context["html_table"] = None
    else:
        # try:
        file_data = pd.read_csv(csv_file, parse_dates=True)
        dataframe = prepare_dataframe(dataframe=file_data)
        if dataframe is None:
            context["last_saved_result"] = 'Something wrong with input file'
            return render(request,
                          "templates/test_calculations/test_calculations_index.html",
                          context)
        dict_to_rename_columns = {key.lower(): key for key in chosen_function_params.keys()}
        for key in file_data.columns.str.lower():
            if key in dict_to_rename_columns.keys():
                file_data.rename(columns={key: dict_to_rename_columns[key]}, inplace=True)

        task = calculate_from_file_delayed.delay(
            function_name=chosen_function_name,
            project_name=chosen_project_name,
            file_json=file_data[list(chosen_function_params.keys())].to_json(),
            config=chosen_function_config
        )
        task_id = task.task_id
    context['task_id'] = task_id

    return render(request,
                  "templates/test_calculations/test_calculations_index.html",
                  context)
