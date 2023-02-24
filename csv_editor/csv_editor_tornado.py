import datetime
import os

import js2py as js2py
import pandas as pd
from asgiref.sync import sync_to_async
from bokeh.embed import server_document
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import DateFormatter, Button, CustomJS, DataTable, TableColumn, PointDrawTool, ColumnDataSource, \
    HoverTool
from bokeh.models import Slider
from bokeh.palettes import Spectral10 as color_palet
from bokeh.plotting import figure, Column
from bokeh.sampledata.sea_surface_temperature import sea_surface_temperature
from bokeh.server.server import Server
from bokeh.themes import Theme, built_in_themes
from bokeh.util.browser import view
from django.conf import settings
from django.db import connection
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import create_engine
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler

from csv_editor.models import CSVEditorDatasetModel

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
    elif not ((type(data.index[0]) is datetime.datetime) or (type(data.index[0]) is pd.Timestamp)):
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
        script = server_document('http://127.0.0.1:5006/csv_editor')
        self.write(template.render(script=script, template="Tornado"))


def prepare_dataset_to_plot():
    engine = create_engine(database_url)
    data = pd.read_sql(sql='SELECT index as id, datetime, item_id, value FROM csv_editor_temp_table', con=engine)
    data['datetime'] = pd.to_datetime(data['datetime'])
    data.set_index('id', inplace=True)
    for name, color in zip(set(data['item_id']), color_palet):
        data.loc[data['item_id'] == name, 'color'] = color

    return data

def prepare_dataset_to_download():
    engine = create_engine(database_url)
    data = pd.read_sql(sql='SELECT datetime, item_id, value FROM csv_editor_table', con=engine)
    data = pivot_table(data)
    data.index = data.index.astype(str)
    print(data.index)
    return data


def create_hover_tool(renderer):
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
    return points_hover_tool


def create_table_to_plot(source):
    columns = [TableColumn(field="datetime", title="datetime",
                           formatter=DateFormatter(format="%d.%m.%y %H:%M:%S")),
               TableColumn(field="item_id", title="Item_id"),
               TableColumn(field='value', title='Value'),
               TableColumn(field='color', title='Color'),
               ]
    table = DataTable(source=source, columns=columns, editable=True, height=200,
                      name='result_table')
    return table


def save_changes(changed_df: pd.DataFrame):
    engine = create_engine(database_url)
    main_data = pd.read_sql(sql='SELECT index, datetime, item_id, value FROM csv_editor_table', con=engine)
    changed_df.rename(columns={'id':"index"}, inplace=True)
    if isinstance(changed_df['datetime'].iloc[-1], int):
        changed_df['datetime'] = changed_df['datetime'].apply(
            lambda x: pd.to_datetime('1970-01-01') + datetime.timedelta(milliseconds=float(x)))
    old_idx = main_data.loc[main_data['item_id'].isin(set(changed_df['item_id']))].index
    main_data = main_data.drop(old_idx)
    main_data = pd.concat([main_data, changed_df[['index','datetime', 'item_id', 'value']]])
    main_data.sort_values(by='index')
    engine = create_engine(database_url, echo=False)
    main_data.to_sql(name='csv_editor_table', con=engine, if_exists='replace', chunksize=100000)


def previous_page_view():
    pass


def plot_csv_editor(doc):

    data_to_plot = prepare_dataset_to_plot()
    curdoc().clear()

    source = ColumnDataSource(data_to_plot)

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

    table = create_table_to_plot(source)

    draw_tool = PointDrawTool(renderers=[renderer], empty_value='white', add=False)
    points_hover_tool = create_hover_tool(renderer=renderer)

    ploted_figure.add_tools(draw_tool, points_hover_tool)
    ploted_figure.toolbar.active_tap = draw_tool
    ploted_figure.legend.location = "center_left"

    # EVENT FUNCTIONS
    def save_df(new):
        df = source.to_df()
        save_changes(changed_df=df)
        print('Successfully synchronized')

    def return_button_callback(new):
        df = source.to_df()
        save_changes(changed_df=df)
        js2py.eval_js('window.open("http://127.0.0.1:8000/csv_editor/")')
        js2py.eval_js('history.back()')
        js2py.eval_js('console.log("_self")')
        # driver = webdriver.PhantomJS()
        # driver.get(url)
        # result = driver.execute_script(myscript)
        # driver.quit()
        # js2py.eval_js(CustomJS(args=dict(urls=['http://127.0.0.1:8000/csv_editor/']),
        #                    code="urls.forEach(url => window.open(url,'_self'))").to_json())


    # CREATE BUTTONS
    download_button = Button(label="Download main table",
                         button_type="success")
    synchronize_button = Button(label="Synchronize with main table",
                             button_type="success")
    return_button = Button(label="Return",
                                button_type="success")
    # SET EVENTS TO EACH BUTTONS
    synchronize_button.on_event("button_click", save_df)
    return_button.on_event("button_click", return_button_callback)
    # return_button.js_on_click(CustomJS(args=dict(urls=['http://127.0.0.1:8000/csv_editor/']),
    #                        code="urls.forEach(url => window.open(url,'_self'))"))
    # download_button.on_event("button_click", download_callback)
    download_button.js_on_event("button_click", CustomJS(args=dict(source=source),
    # download_button.js_on_event("button_click", CustomJS(args=dict(source=ColumnDataSource(prepare_dataset_to_download())),
                                                         code=JS_CODE))

    show_content = Column(children=[ploted_figure, row(download_button, synchronize_button, return_button)], sizing_mode='stretch_both')

    doc.add_root(show_content)
    doc.theme = built_in_themes['dark_minimal']


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
    # print('Opening Tornado app with embedded Bokeh application on http://localhost:5006/')
    server = run_bokeh_server()
    server.io_loop.add_callback(view, "http://127.0.0.1:5006/csv_editor/")
    server.io_loop.start()
    return server


if __name__ == '__main__':
    run_tornado_with_bokeh()
