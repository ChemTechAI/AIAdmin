from subprocess import Popen

from flask_apscheduler import APScheduler
from yaml import SafeLoader, load

import os
from subprocess import PIPE, Popen
from time import sleep

scheduler = APScheduler()


@scheduler.task("interval", seconds=30, max_instances=1)
def task1():
    with open(scheduler.app.config["TASK_CONG"]) as yaml_file:
        proc_list = list(load(yaml_file, Loader=SafeLoader)["task1"])