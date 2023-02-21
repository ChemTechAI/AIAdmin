import os
import traceback
from logging import getLogger

from flask import Blueprint, request, make_response, jsonify, send_file, render_template
from bokeh.embed import server_document

bp = Blueprint("/bkapp", __name__, url_prefix="/bkapp")

LOG = getLogger("flask.flask_gui")


@bp.route('/', methods=['GET'])
def bkapp_page():
    script = server_document('http://localhost:5006/bkapp')
    return render_template("embed.html", script=script, template="Flask")


# @bp.route("/current_consts", methods=["GET"])
# def current_consts():
#     LOG.info("Call method: GET /eurochem/current_consts")
#
#     try:
#         params = get_constants()
#     except Exception as ex:
#         traceback.print_exc()
#         return make_response(ex, 400)
#     return make_response(jsonify(params), 200)
