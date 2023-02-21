import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

from plotly.offline import plot
from plotly.subplots import make_subplots


def add_static_traces(figure, data, tags=None, filled_feature=None):
    tags = tags or data.columns
    for feature in data[tags]:
        fill_value = None
        if feature == filled_feature:
            fill_value = 'tonexty'
        figure.add_trace(
            go.Scatter(visible=True,
                       y=data[feature],
                       x=data.index,
                       name=str(feature),
                       mode="lines",
                       fill=fill_value)
        )
    return figure


def add_slider_traces(figure,
                      data,
                      expression,
                      slider_start_stop_step):
    if not (expression and slider_start_stop_step):
        return figure
    # TODO: add cycle for more than one slider_tag values
    slider_tag = list(slider_start_stop_step.keys())[0]
    slider_diapasons = list(slider_start_stop_step.values())[0]

    round_precision = max([len(str(float(i)).split('.')[1]) for i in slider_diapasons])
    len_before = len(figure.data)
    for step in np.arange(*slider_diapasons):
        # Add traces, one for each slider step
        eval_tag = expression.replace(slider_tag, str(round(step, round_precision)))

        figure.add_trace(
            go.Scatter(
                visible=False,
                line=dict(color="#00CED1", width=2),
                name=eval_tag,
                x=data.index,
                y=data.eval(eval_tag)))

    figure.data[-1].visible = True
    steps = []
    for i in range(len_before, len(figure.data)):
        visible_mask = [True] * len_before
        visible_mask.extend([False] * len(figure.data[len_before:]))
        step = dict(
            method="update",
            args=[{"visible": visible_mask}],
        )
        step["args"][0]["visible"][i] = True

        step["args"][0]["visible"][:len_before] = [True] * len_before
        steps.append(step)

    sliders = [dict(
        active=10,
        currentvalue={"prefix": f"{slider_tag}: "},
        pad={"t": 30},
        steps=steps
    )  # , dict(
        #         active=10,
        #         currentvalue={"prefix": "var_y: "},
        #         pad={"t": 25},
        #         steps=steps
        #     )
    ]

    figure.update_layout(
        sliders=sliders
    )
    return figure


def slider_expression(data: pd.DataFrame, filled_feature: str = None, title: str = "",
                      expression: str = '',
                      slider_start_stop_step: dict = None,
                      tags_to_display: list = None):
    """Function for print plot with features values from dataset.

    Parameters
    ----------
    data: pd.DataFrame
        Dataset for plot.
    title: str
        Title of plot.
    """

    # create Plotly figure with subplots
    fig = make_subplots()
    # insert feature to figure
    fig = add_static_traces(figure=fig, data=data, tags=tags_to_display, filled_feature=filled_feature)
    fig = add_slider_traces(figure=fig,
                            data=data,
                            expression=expression,
                            slider_start_stop_step=slider_start_stop_step)

    # set parameters for layout
    fig.update_layout(
        title_text=title,
        paper_bgcolor="rgb(33, 33, 33)",
        plot_bgcolor="rgb(33, 33, 33)",
    )
    return plot(fig, output_type='div')

# if __name__ == '__main__':
#     raw_data = pd.read_csv(r'C:\Users\User\Desktop\all_data_with_meteo.csv', index_col=0, parse_dates=True)
#     print(slider_expression(raw_data[['TB5', 'HNO3_10']], expression='(TB5*var_z)+var_z',
#                             slider_start_stop_step={'var_z': (0.9, 1.1, 0.05)}))