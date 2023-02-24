import os
import re
import sys
import itertools
import importlib
import inspect
from typing import Tuple
from collections.abc import Callable
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from django.conf import settings


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DIR_WITH_PROJECTS = os.path.join(BASE_DIR, 'git_projects')


def get_module_object_from_python_file(path_to_py_file: str, project_name: str):
    path, _ = os.path.splitext(path_to_py_file)
    file_name = path.split('.')[-1]
    path = path.replace('.' + file_name, '')
    path = path.split(project_name)[-1]

    if len(path) == 0:
        path = '.'
    if path == '.':
        file_name = file_name.replace('.', '')
    elif path[0] == '.':
        path = path[1:]
        if file_name[0] != '.':
            file_name = '.' + file_name

    module = importlib.import_module(file_name, path)

    return module


def get_function_object_by_name(project_name: str, function_name: str):
    chosen_project_path = os.path.join(DIR_WITH_PROJECTS, project_name)
    clean_projects_paths()
    sys.path.append(chosen_project_path)
    for root, _, files in os.walk(chosen_project_path, topdown=True):
        for file in files:
            if file.endswith('.py') and '__' not in file and '__pycache__' not in root:
                path_to_py_file = os.path.join(root, file).replace('\\', '/').replace('/', '.')
                module = get_module_object_from_python_file(path_to_py_file=path_to_py_file,
                                                            project_name=project_name)

                for func_name, func_obj in inspect.getmembers(module, inspect.isfunction):
                    if function_name is not None and function_name in func_name:
                        return func_obj


def clean_projects_paths():
    projects_paths = list([path for path in sys.path if os.path.normpath(DIR_WITH_PROJECTS) in path])
    for project_path in projects_paths:
        sys.path.remove(project_path)


def get_all_functions_with_location(project_name: str) -> Tuple[list, list, dict, str]:
    python_files = []
    all_functions = []
    project_config = {}
    errors = ''
    chosen_project_path = os.path.join(DIR_WITH_PROJECTS, project_name)
    clean_projects_paths()
    sys.path.append(chosen_project_path)
    for root, _, files in os.walk(chosen_project_path, topdown=True):
        for file in files:
            if '.py' in file and '__' not in file and '__pycache__' not in root:
                path_to_py_file = os.path.join(root, file).replace('\\', '/').replace('/', '.')
                try:
                    module = get_module_object_from_python_file(path_to_py_file=path_to_py_file,
                                                                project_name=project_name)
                except BaseException as error:
                    errors += str(error) + '\n'
                    continue
                for member_name, member_object in inspect.getmembers(module):
                    if ('Config' == member_name and inspect.isclass(member_object) and not project_config
                            and hasattr(member_object, 'init_config')):
                        project_config = member_object.init_config()
                        continue

                    if not inspect.isfunction(member_object):
                        continue

                    function_params = [parameter for parameter in member_object.__annotations__ if
                                       'return' not in parameter]
                    if 0 < len(function_params):
                        all_functions.append(member_name)

    all_functions = list(set(all_functions))
    return python_files, all_functions, project_config, errors


def generate_data_from_manual(params: dict):
    generators = {}
    values = {}

    for parameter, value in params.items():
        if type(value['value']) == dict:
            try:
                generators[parameter] = np.arange(start=float(value['value']['start']),
                                                  stop=float(value['value']['stop']),
                                                  step=float(value['value']['step']))
            except BaseException as e:
                print(e)
                if value['value']['start']:
                    values[parameter] = float(value['value']['start'])
        elif 'pandas.core.frame.DataFrame' in value['type']:
            values[parameter] = pd.read_json(value['value'])
        else:
            values[parameter] = value['value']

    if len(generators.keys()) > 0:
        lists = [[i for i in generator] for column, generator in generators.items()]
        columns = [column for column in generators.keys()]

        for key, value in values.items():
            lists.append([value])
            columns.append(key)
        dataframe = pd.DataFrame(list(itertools.product(*lists)), columns=columns)
        return dataframe
    else:
        return values


def find_function_config_using(source_code: str) -> list:
    config_names = []
    source_code = source_code.split('\n')
    for code_line in source_code:
        if 'config[' in code_line and code_line.split('config[')[0][-1] in ['=', ' ']:
            parsing_result = re.search(r'''config\[f?['"](.+?)['"]\]''', code_line)
            if parsing_result:
                parsing_result = parsing_result.group(1)
                if 'errors_to_steps_relation' == parsing_result:
                    internal_key = (code_line.split(parsing_result)[-1].replace('"', '')
                                                                       .replace("'", '')
                                                                       .replace('[', '')
                                                                       .replace(']', '')
                                    )
                    config_names.append([parsing_result, internal_key])
                else:
                    config_names.append(parsing_result)

    return config_names


def generate_text(key: str, value: str, levels: list) -> str:
    return f"""<b style="margin-left: {len(levels)*30}px;">{key}:</b><input type="number"
               name="config_{'&&'.join(levels)}" step=".0001" placeholder={value} style="width: 75px">
            """


def generate_recursive_html_for_dict(dictionary: dict, levels: list = None):
    if levels is None:
        levels = []
    text = ''
    for key, value in dictionary.items():

        if type(value) == dict:
            text += generate_recursive_html_for_dict(dictionary=value, levels=levels + [key]) + '<br>'
        elif type(value) == list:
            text += "<b>errors_to_steps_relation:</b><br>"
            item_num = 0
            for index, mini_dict in enumerate(value):
                text += generate_recursive_html_for_dict(dictionary=mini_dict,
                                                         levels=levels + [key, str(index)]) + '<br>'
                item_num += 1
        else:
            text += generate_text(key=key, value=value, levels=levels + [key])
            if len(levels) == 0:
                text += '<br>'
    return text


def update_dict(dictionary: dict, list_of_keys: list, new_value):

    to_update = dictionary[list_of_keys[0]]
    if list_of_keys[-1] in dictionary.keys():
        dictionary[list_of_keys[-1]] = new_value
    elif list_of_keys[0] == 'errors_to_steps_relation':
        dictionary[list_of_keys[0]][list_of_keys[1]][list_of_keys[2]][list_of_keys[3]] = new_value
    elif type(to_update) == dict:
        new_dict = update_dict(dictionary=to_update, list_of_keys=list_of_keys[1:], new_value=new_value)
        dictionary[list_of_keys[0]] = new_dict
    else:
        dictionary[list_of_keys[0]] = new_value

    return dictionary


def update_config_from_request(request, config):
    for key in request.POST:
        value = request.POST.get(key)
        if value and 'config' in key:
            key = key.replace('config_', '')
            levels = key.split('&&')
            levels = [int(element) if element.isdigit() else element for element in levels]
            config = update_dict(dictionary=config, list_of_keys=levels, new_value=float(value))

    return config


def save_result_to_db(result: pd.DataFrame, function_name: str):

    if function_name in result.columns:
        result.sort_values(by=function_name, inplace=True)
    else:
        new_columns = list(set(result.columns) - set(result.columns))
        result.sort_values(by=new_columns, inplace=True)

    if not isinstance(result.index, pd.DatetimeIndex):
        result.reset_index(inplace=True, drop=True)

    result.sort_index(inplace=True)

    dict_to_rename = {}
    for column in result.columns:
        new_column_name = column
        for word in ['optimize_', '_optimization', 'calc_', '_calc', 'calculate']:
            new_column_name = new_column_name.replace(word, '')
        dict_to_rename[column] = new_column_name

    result.rename(columns=dict_to_rename, inplace=True)

    user = settings.DATABASES['default']['USER']
    password = settings.DATABASES['default']['PASSWORD']
    database_name = settings.DATABASES['default']['NAME']

    database_url = f'postgresql://{user}:{password}@localhost:5432/{database_name}'

    engine = create_engine(database_url, echo=False)

    result.to_sql(name='test_calculations', con=engine, if_exists='replace')


def prepare_dataframe(dataframe: pd.DataFrame):

    if 'datetime' not in dataframe.columns:
        return
    date_formats = ['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M']
    initial_date_column = dataframe['datetime']
    for date_format in date_formats:
        datetime_date_column = pd.to_datetime(dataframe['datetime'], format=date_format, errors='ignore')
        if datetime_date_column.notna().sum() != 0:
            dataframe['datetime'] = initial_date_column
            break
        elif date_formats[-1] == date_format:
            try:
                pd.to_datetime(dataframe['datetime'], format=date_format, errors=date_format)
            except BaseException as result:
                print(result)
                return
    dataframe.set_index('datetime', inplace=True)
    return dataframe


def run_through_synthetic_dataframe_and_save(dataframe: pd.DataFrame, config: dict, function_object: Callable,
                                             function_name: str, progress_recorder):
    iteration = 0
    dataframe_len = len(dataframe)

    for index, row in dataframe.iterrows():
        if config:
            row['config'] = config

        result = function_object(**row.to_dict())
        if type(result) == pd.Series:
            dataframe.loc[dataframe.index == index, result.index] = result.values
        else:
            dataframe.loc[dataframe.index == index, function_name] = result
        progress_recorder.set_progress(iteration, dataframe_len, f'On iteration {iteration}')
        iteration += 1

    return dataframe


def prepare_html_for_config(request, config: dict):
    config_html = None
    if config:
        chosen_function_config = update_config_from_request(request=request,
                                                            config=config)
        request.session['chosen_function_config'] = chosen_function_config
        config_html = ('<div class="config-block">' +
                       generate_recursive_html_for_dict(dictionary=chosen_function_config) +
                       '</div>')
    return config_html


if __name__ == '__main__':
    print(generate_recursive_html_for_dict({'forest': {'gggg': 15,
                                                       'yyyyy': 16},
                                            'loko': {'fff': 12,
                                                     'ddd': {'tttt': 24,
                                                             'dddd': 43}}}))
