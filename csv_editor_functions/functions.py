from bokeh import themes
from bokeh.embed import file_html, components
from bokeh.plotting import figure, Column, reset_output
from bokeh.models import DateFormatter, Button, CustomJS, DataTable, TableColumn, PointDrawTool, ColumnDataSource, HoverTool
import pandas as pd
from bokeh.io import curdoc
from bokeh.palettes import Spectral10 as color_palet
import datetime

from bokeh.resources import CDN, INLINE

JS_CODE = """
function exportData(table) {
        var item = localStorage.csv=table;

        var ary = localStorage.getItem( "csv" ); //csv as a string
        var blob = new Blob([ary], {type: "text/csv"});
        var url = URL.createObjectURL(blob);
        var a = document.querySelector("#results"); // id of the <a> element to render the download link
        a.href = url;
        a.download = "file.csv";

    }
function table_to_csv(source) {
    const columns = Object.keys(source.data)
    const nrows = source.get_length()
    const lines = [columns.join(',')]

    for (let i = 0; i < nrows; i++) {
        let row = [];
        for (let j = 0; j < columns.length; j++) {
            const column = columns[j]
            row.push(source.data[column][i].toString())
        }
        lines.push(row.join(','))
    }
    return lines.join('\\n').concat('\\n')
}


const filename = 'data_result.csv'
const filetext = table_to_csv(source)
const blob = new Blob([filetext], { type: 'text/csv;charset=utf-8;' })
//navigator.msSaveBlob(blob, filename)
//addresses IE
if (navigator.msSaveBlob) {
    navigator.msSaveBlob(blob, filename)
} else {
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.target = '_blank'
    link.style.visibility = 'hidden'
    link.dispatchEvent(new MouseEvent('click'))
}"""


def join_csv(edited_csv_file_name: str,
             depended_csv_file_name: str,
             cut_dates: bool = False,
             output_csv_file_name: str = 'joined_csv_file.csv'):
    file_names_table_map = {}

    melted_data_tags = ['datetime', 'item_id', 'value']

    for file_name in [edited_csv_file_name, depended_csv_file_name]:
        csv_file_name = file_name
        if not csv_file_name.endswith('.csv'):
            csv_file_name = file_name + '.csv'
        table = pd.read_csv(csv_file_name, parse_dates=True)

        is_melted_data = len([tag for tag in melted_data_tags if tag in table.columns]) == 3

        if is_melted_data:
            table = pivot_table(table)
        else:
            table.index = table['datetime']
        table.index.name = 'datetime'
        table = index_to_datetime(data=table)
        file_names_table_map[file_name] = table

    main_csv_file = file_names_table_map[edited_csv_file_name]
    depended_csv_file = file_names_table_map[depended_csv_file_name]
    columns_to_drop = [col for col in main_csv_file.columns if col in depended_csv_file.columns]
    if cut_dates:
        result = main_csv_file.join(depended_csv_file.drop(columns_to_drop, axis=1), how='left')
    else:
        result = main_csv_file.join(depended_csv_file.drop(columns_to_drop, axis=1), how='outer')
    result.sort_index(inplace=True)
    result.index.drop_duplicates(keep='first')
    result.dropna(inplace=True)
    result.to_csv(output_csv_file_name)
    return result


def index_to_datetime(data: pd.DataFrame):
    if isinstance(data.index[0], str):
        data.index = pd.to_datetime(data.index, format='%Y-%m-%d %H:%M:%S')
    elif not((type(data.index[0]) is datetime.datetime) or (type(data.index[0]) is pd.Timestamp)):
        index_series = pd.DataFrame()
        index_series['datetime_index'] = data.index
        data.index = index_series['datetime_index'].apply(
            lambda x: pd.to_datetime('1970-01-01') + datetime.timedelta(milliseconds=float(x)))
    data.sort_index(inplace=True)
    data.index.drop_duplicates(keep='first')

    return data


def pivot_table(data, **kwargs):
    if kwargs.get('cut_tag'):
        data['item_id'] = data['item_id'].apply(lambda x: kwargs['cut_tag'](x))
    if kwargs.get('tags'):
        data = data[(data['item_id'].isin(kwargs.get('tags')))]
    data = pd.pivot_table(data,
                          values='value',
                          index=['datetime'],
                          columns=['item_id'],
                          fill_value=-123,
                          aggfunc='first').replace(-123, method='ffill').replace(-123, method='bfill')
    data.sort_values(by=['datetime'], inplace=True)

    return data


def melt_table(data: pd.DataFrame):
    copy_data = data.copy()
    copy_data['datetime'] = copy_data.index
    versed_data = copy_data.melt(id_vars=['datetime'],
                                 value_vars=data.columns,
                                 var_name='item_id',
                                 ignore_index=True)

    return versed_data


def plot_csv_editor(data: pd.DataFrame,
                    tags: list = None,
                    show_table: bool = False,
                    smoothing_window: int = None):

    data_to_plot = data.copy()
    curdoc().clear()
    melted_data_tags = ['datetime', 'item_id', 'value']
    is_melted_data = len([tag for tag in melted_data_tags if tag in data_to_plot.columns]) == 3

    if not is_melted_data:

        if 'datetime' in data_to_plot.columns:
            data_to_plot.set_index('datetime', inplace=True)
        if smoothing_window:
            data_to_plot = index_to_datetime(data=data_to_plot)
            print(data_to_plot.index[data_to_plot.index.duplicated()])
            data_to_plot = data_to_plot.rolling(window=f'{smoothing_window}min').mean().ffill().bfill()
        if tags:
            data_to_plot = data_to_plot[tags]
        data_to_plot = melt_table(data_to_plot)
    else:
        if 'datetime' in data_to_plot.columns:
            data_to_plot['datetime'] = data_to_plot['datetime'].rolling(
                window=f'{smoothing_window}min').mean().ffill().bfill()

    if 'id' in data_to_plot.columns:
        data_to_plot.drop(['id'], axis=1, inplace=True)
    data_to_plot.index.name = 'id'

    # ADD AUTO COLOR FROMSPECTRA
    for name, color in zip(set(data_to_plot['item_id']), color_palet):
        data_to_plot.loc[data_to_plot['item_id'] == name, 'color'] = color
    source = ColumnDataSource(
        data_to_plot
    )

    ploted_figure = figure(sizing_mode='stretch_both',
                           toolbar_location='above',
                           width_policy='fit',
                           min_height=900,
                           height_policy='fit',
                           x_axis_type="datetime",
                           title='Table editor',
                           tools='box_zoom,undo,xbox_select, box_select,pan, reset, crosshair')

    renderer = ploted_figure.scatter(x='datetime', y='value', source=source,
                                     size=7, color='color',
                                     legend_field='item_id'
                                     )

    columns = [TableColumn(field="datetime", title="datetime",
                           formatter=DateFormatter(format="%d.%m.%y %H:%M:%S")),
               TableColumn(field="item_id", title="Item_id"),
               TableColumn(field='value', title='Value'),
               TableColumn(field='color', title='Color'),
               ]
    table = DataTable(source=source, columns=columns, editable=True, height=200,
                      name='result_table')

    ploted_figure.legend.location = "center_left"

    draw_tool = PointDrawTool(renderers=[renderer], empty_value='white', add=False)

    tooltips = [
        ("Value", "@value"),
        ("ItemID", "@item_id"),
        ("Datetime", "@datetime{%d.%m.%y %H:%M:%S}"),
    ]

    formatters = {"@datetime": "datetime",
                  "$x": "datetime", }

    points_hover_tool = HoverTool(renderers=[renderer],
                                  tooltips=tooltips, mode='mouse',
                                  formatters=formatters)

    ploted_figure.add_tools(draw_tool, points_hover_tool)

    ploted_figure.toolbar.active_tap = draw_tool

    def save_df(new):
        df = source.to_df()
    #     source.data = ColumnDataSource(
    #     data_to_plot
    # )
        df.to_csv('edited_csv.csv')
        print('Sucsesss')
        # print(1/0)

    download_button = Button(label="Download csv file", button_type="success")
    download_button.on_event("button_click", save_df)
    # download_button.js_on_event("button_click", CustomJS(args=dict(source=source),
    #                                                      code=JS_CODE))
    curdoc().theme = 'dark_minimal'

    show_content = Column(children=[ploted_figure, download_button], sizing_mode='stretch_both')
    if show_table:
        show_content = Column(children=[ploted_figure, download_button, table], sizing_mode='stretch_both')
    reset_output()

    # return file_html(show_content, resources=INLINE, title='CSV Editor', theme=themes.DARK_MINIMAL)
    return components(show_content,  theme=themes.DARK_MINIMAL)
