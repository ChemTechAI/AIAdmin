import os
from threading import Thread

from flask import Flask, render_template
from flask_cors import CORS
from tendo import singleton
from tornado.ioloop import IOLoop

from bokeh.embed import server_document
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Slider
from bokeh.plotting import figure
from bokeh.sampledata.sea_surface_temperature import sea_surface_temperature
from bokeh.server.server import Server
from bokeh.themes import Theme
from waitress import serve
import importlib

from django.conf import settings


def create_app():
    singleton.SingleInstance()
    app = Flask(__name__)
    CORS(app)
    register_blueprints(['csv_editor_gui.bp'], app)
    return app

def main() -> None:
    app = create_app()
    print(app)
    serve(app, listen="localhost:9090")


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


def bk_worker():
    # Can't pass num_procs > 1 in this configuration. If you need to run multiple
    # processes, see e.g. flask_gunicorn_embed.py
    # server = Server({'/bkapp': bkapp}, io_loop=IOLoop(), allow_websocket_origin=["localhost:8000"])
    server = Server({'/bkapp': bkapp}, allow_websocket_origin=["localhost:8000"], io_loop=IOLoop(),
                    # add this argument:
                    port=9090)
    server.start()

    server.io_loop.start()


def register_blueprints(bp_modules, flask_app: Flask) -> None:
    """Register all blueprints.

    Import blueprints from modules where blueprints stored as bp variable.

    Args:
        bp_modules: List of blueprint modules
        flask_app: Flask app instance

    Returns:
        None
    """
    for module in bp_modules:
        bp = importlib.import_module(module).bp
        flask_app.register_blueprint(bp)

Thread(target=bk_worker).start()

if __name__ == '__main__':
    # app = create_app()
    # app.debug = True
    # print('Opening single process Flask app with embedded Bokeh application on http://localhost:8000/')
    # print()
    # print('Multiple connections may block the Bokeh app in this configuration!')
    # print('See "flask_gunicorn_embed.py" for one way to run multi-process')
    # app.run(port=8000)
    main()
