from django.http import HttpResponse

import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from plotly.offline import plot
from plotly.subplots import make_subplots


GRAPH_FEATURES_RENAME = {
        "F101N_smooth": "F101N_real",
        "f101n_opt_smooth": "F101N_opt",
        "F102N_smooth": "F102N_real",
        "f102n_opt_smooth": "F102N_opt",
        "FC104_smooth": "FC104_real",
        "fc104_opt_smooth": "FC104_opt",
        "FC107_smooth": "FC107_real",
        "fc107_opt_smooth": "FC107_opt",
        "HNO3_10_pred_smooth": "HNO3_pred",
        "NO_NO2_pred_smooth": "NO_NO2_pred",
        "oxy_remain_vol_percent_smooth": "O2_pred",
        "oxy_remain_vol_percent_opt_smooth": "O2_opt",
        "QS101_smooth": "QS101_real",
        "air_ammonia_ratio_opt_smooth": "QS101_opt",
        "FC110_smooth": "FC110_real",
        "FC110_opt_smooth": "FC110_opt",
        "FC106_opt_smooth": "FC106_real",
        "FC106_smooth": "FC106_opt",
        "F111_2_smooth": "FC111_2_real",
        "F111_2_opt_smooth": "FC111_2_opt",
        }

pd.options.plotting.backend = "plotly"
pio.templates.default = "plotly_dark"


def plot_result_to_html(data: pd.DataFrame):
    """Function for print plot with features values from dataset.

    Parameters
    ----------
    data: pd.DataFrame
        Dataset for plot.
    file_name: str
        Result name of the plot file.
    """
    # create Plotly figure with subplots
    fig = make_subplots()
    # insert feature to figure
    for feature in data:
        # set parameters for trace
        feature_name = str(feature)
        if feature_name in GRAPH_FEATURES_RENAME.keys():
            feature_name = GRAPH_FEATURES_RENAME[str(feature)]
        fig.add_trace(
            go.Scatter(
                y=data[feature], x=data.index, name=feature_name, mode="lines"
            )
        )
    # set parameters for layout
    fig.update_layout(
        # title_text=f'target:{target_name} {title}, Model: {model_name}')
        paper_bgcolor="rgb(33, 33, 33)",
        plot_bgcolor="rgb(33, 33, 33)",
    )

    return plot(fig, output_type='div')


def index(request):
    try:
        conn = sqlite3.connect('./var/www/django_project/ai_database')

        full_data = pd.read_sql('SELECT * FROM eurochem_data', con=conn)
        full_data['datetime'] = pd.to_datetime(full_data['datetime'], format='%Y-%m-%d %H:%M:%S')
        full_data = pd.pivot_table(full_data,
                                   values='value',
                                   index=['datetime'],
                                   columns=['item_id'],
                                   fill_value=0,
                                   aggfunc='first').replace(0, method='ffill').replace(0, method='bfill')

        full_data.sort_index(inplace=True)

        return HttpResponse(f'''<html>
                             <head>
                            </head>
                            <body>
                            {plot_result_to_html(data=full_data)}
                            </body>
                            APH_FEATURES_RENAME''')
    except BaseException as error:
        return HttpResponse(error)
