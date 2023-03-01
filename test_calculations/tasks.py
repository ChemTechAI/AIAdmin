import pandas as pd

from celery import shared_task
from celery_progress.backend import ProgressRecorder

from .functions import get_function_object_by_name, save_result_to_db, run_through_synthetic_dataframe_and_save


@shared_task(bind=True)
def calculate_from_file_delayed(self, function_name: str, project_name: str, file_json: pd.io.json, config: dict):

    function_object = get_function_object_by_name(function_name=function_name, project_name=project_name)
    progress_recorder = ProgressRecorder(self)

    dataframe = pd.read_json(file_json)
    if 'datetime' in dataframe.columns:
        dataframe.set_index('datetime', inplace=True)

    dataframe = run_through_synthetic_dataframe_and_save(dataframe=dataframe, function_object=function_object,
                                                         function_name=function_name,
                                                         progress_recorder=progress_recorder, config=config)
    save_result_to_db(result=dataframe, function_name=function_name)

    return dataframe.to_json()


@shared_task(bind=True)
def calculate_from_dict_delayed(self, function_name: str, project_name: str, params_dict: dict, config: dict):

    function_object = get_function_object_by_name(function_name=function_name, project_name=project_name)
    progress_recorder = ProgressRecorder(self)

    dataframe = pd.read_json(params_dict)
    if dataframe.empty:
        return

    dataframe = run_through_synthetic_dataframe_and_save(dataframe=dataframe, function_object=function_object,
                                                         function_name=function_name,
                                                         progress_recorder=progress_recorder, config=config)
    save_result_to_db(result=dataframe, function_name=function_name)
    return dataframe.to_json()


@shared_task(bind=True)
def calculate_from_dataframe_delayed(self, function_name: str, project_name: str, params_with_dataframe: dict, config: dict):

    function_object = get_function_object_by_name(function_name=function_name, project_name=project_name)
    progress_recorder = ProgressRecorder(self)
    dataframe = None
    parameter = None
    for parameter, value in params_with_dataframe.items():
        if type(value) == pd.DataFrame:
            dataframe = value
            params_with_dataframe[parameter] = None
            break

    if dataframe is None or parameter is None:
        return

    iteration = 0
    dataframe_len = len(dataframe)

    if config:
        params_with_dataframe['config'] = config

    for index in dataframe.index[1:]:

        params_with_dataframe[parameter] = dataframe.loc[:index]

        result = function_object(**params_with_dataframe)
        if type(result) == pd.Series:
            dataframe.loc[dataframe.index == index, result.index] = result.values
        else:
            dataframe.loc[dataframe.index == index, function_name] = result

        progress_recorder.set_progress(iteration, dataframe_len, f'On iteration {iteration}')
        iteration += 1

    save_result_to_db(result=dataframe, function_name=function_name)
    return dataframe.to_json()


def calculate_one_option(function_name: str, project_name: str, params: dict, config: dict):

    function_object = get_function_object_by_name(function_name=function_name, project_name=project_name)
    if config:
        params['config'] = config
    return function_object(**params)
