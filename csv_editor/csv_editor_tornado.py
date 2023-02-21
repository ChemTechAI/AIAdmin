import os
from django.conf import settings
import pandas as pd
from bokeh.io import curdoc

from jinja2 import Environment, FileSystemLoader
from tornado.web import RequestHandler
from tornado.ioloop import IOLoop

from bokeh.embed import server_document
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Slider, Column, HoverTool, PointDrawTool, DataTable, TableColumn, \
    DateFormatter, Button, CustomJS
from bokeh.plotting import figure
from bokeh.sampledata.sea_surface_temperature import sea_surface_temperature
from bokeh.server.server import Server
from bokeh.themes import Theme
from bokeh.palettes import Spectral10 as color_palet
from bokeh.util.browser import view

from bokeh import themes
from bokeh.embed import file_html, components
from bokeh.plotting import figure, Column, reset_output
from bokeh.models import DateFormatter, Button, CustomJS, DataTable, TableColumn, PointDrawTool, ColumnDataSource, HoverTool
import pandas as pd
from bokeh.io import curdoc
from bokeh.palettes import Spectral10 as color_palet
import datetime

from sqlalchemy import create_engine

from bokeh.resources import CDN, INLINE


user = settings.DATABASES['default']['USER']
password = settings.DATABASES['default']['PASSWORD']
database_name = settings.DATABASES['default']['NAME']

database_url = f'postgresql://{user}:{password}@localhost:5432/{database_name}'


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


env = Environment(loader=FileSystemLoader('templates'))


class IndexHandler(RequestHandler):
    def get(self):
        template = env.get_template('embed.html')
        script = server_document('http://localhost:5006/bkapp')
        self.write(template.render(script=script, template="Tornado"))


def bkapp(doc):
    df = sea_surface_temperature.copy()
    source = ColumnDataSource(data=df)

    plot = figure(x_axis_type='datetime', y_range=(0, 25), y_axis_label='Temperature (Celsius)',
                  title="Sea Surface Temperature at 43.18, -70.43")
    plot.line('time', 'temperature', source=source)

    def callback(attr, old, new):
        if new == 0:
            data = df
        else:
            data = df.rolling(f"{new}D").mean()
        source.data = ColumnDataSource.from_df(data)

    slider = Slider(start=0, end=30, value=0, step=1, title="Smoothing by N Days")
    slider.on_change('value', callback)

    doc.add_root(column(slider, plot))

    doc.theme = Theme(filename=os.path.join(settings.BASE_DIR, 'csv_editor', 'theme.yaml'))


def plot_csv_editor(doc):
    engine = create_engine(database_url)
    data = pd.read_sql(sql='SELECT * FROM data_for_test_calc', con=engine)
    data['datetime'] = pd.to_datetime(data['datetime'])
    data.set_index('datetime', inplace=True)
    tags = None
    show_table = False
    smoothing_window = None
    
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
        df.to_csv('edited_csv.csv')
        print('Sucsesss')

    sync_button = Button(label="Download csv file",
                             button_type="success")
    download_button = Button(label="Synchronize csv file",
                             button_type="success")
    download_button.on_event("button_click", save_df)
    sync_button.js_on_event("button_click", CustomJS(args=dict(source=source),
                                                         code=JS_CODE))
    curdoc().theme = 'dark_minimal'

    show_content = Column(children=[ploted_figure, download_button, sync_button], sizing_mode='stretch_both')
    if show_table:
        show_content = Column(children=[ploted_figure, download_button, sync_button, table], sizing_mode='stretch_both')
    doc.add_root(show_content)

  #  doc.theme = Theme(filename=r'C:\Users\nozar\PycharmProjects\-Observer\csv_editor\theme.yaml')
    doc.theme = curdoc().theme

# Setting num_procs here means we can't touch the IOLoop before now, we must
# let Server handle that. If you need to explicitly handle IOLoops then you
# will need to use the lower level BaseServer class.
# The `static/` end point is reserved for Bokeh resources, as specified in
# bokeh.server.urls. In order to make your own end point for static resources,
# add the following to the `extra_patterns` argument, replacing `DIR` with the desired directory.
# (r'/DIR/(.*)', StaticFileHandler, {'path': os.path.normpath(os.path.dirname(__file__) + '/DIR')})


def run_bokeh_server():
    # server = Server({'/bkapp': bkapp},
    server = Server({'/csv_editor': plot_csv_editor},
                    io_loop=IOLoop(),
                    extra_patterns=[('/', IndexHandler)],
                    allow_websocket_origin=["127.0.0.1:5006",
                                            "127.0.0.1:8000"])
    server.start()
    return server


def run_tornado_with_bokeh():
    print('Opening Tornado app with embedded Bokeh application on http://localhost:5006/')
    server = run_bokeh_server()
    server.io_loop.add_callback(view, "http://localhost:5006/csv_editor")
    server.io_loop.start()
    return server


if __name__ == '__main__':
    run_tornado_with_bokeh()
