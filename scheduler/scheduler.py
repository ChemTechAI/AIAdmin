from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
from django.utils import timezone
import sys
import cv2
# import numpy as np
import dbr
# import time
import os
import re
import glob

import pandas as pd
import sqlite3

#from graph_creating import plot_result_to_html

reader = dbr.BarcodeReader()

reader.init_license(
    "DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ==")

FEATURES_IN_QR_CODE = ["F101N_smooth", "f101n_opt_smooth", "F102N_smooth", "f102n_opt_smooth", "FC104_smooth",
                       "fc104_opt_smooth", "FC107_smooth", "fc107_opt", "oxy_remain_vol_percent_opt_smooth",
                       "QS101_smooth", "air_ammonia_ratio_opt_smooth", "FC110_smooth", "FC110_opt", "F111_2_smooth",
                       "F111_2_opt", "HNO3_10_pred_smooth", "NO_NO2_pred_smooth", "oxy_remain_vol_percent",
                       "FC106_opt_smooth", "FC106_1_smooth",
                       ]


def detect(image, pixel_format, first_try: bool = True):
    buffer = image.tobytes()
    height = image.shape[0]
    width = image.shape[1]
    stride = image.strides[0]
    results = reader.decode_buffer_manually(buffer, width, height, stride, pixel_format, "")
    if results:
        for result in results:
            if '*' in result.barcode_text and first_try:
                localization_points = result.localization_result.localization_points
                return localization_points
            else:
                return result.barcode_text


def qr_code_photo_reader(photo_path: str, crop_frame: list = None, first_try: bool = True):
    image = cv2.imread(photo_path)

    if crop_frame is not None:
        image = image[crop_frame[0][1] - 50:crop_frame[2][1] + 50,
                      crop_frame[0][0] - 50:crop_frame[1][0] + 50]

    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(image)
    if data:
        return data

    inverted_image = cv2.bitwise_not(image)
    data, _, _ = detector.detectAndDecode(inverted_image)

    if data:
        return data

    grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    ret, thresh = cv2.threshold(grayscale_image, 80, 255, cv2.THRESH_BINARY)
    data = detect(image=thresh, pixel_format=dbr.EnumImagePixelFormat.IPF_GRAYSCALED, first_try=first_try)
    if data:
        if type(data) == str:
            return data
        if type(data) == list:
            return qr_code_photo_reader(photo_path=photo_path, crop_frame=data, first_try=False)

    grayscale_inverted_image = cv2.cvtColor(inverted_image, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(grayscale_inverted_image, 80, 255, cv2.THRESH_BINARY)
    data = detect(image=thresh, pixel_format=dbr.EnumImagePixelFormat.IPF_GRAYSCALED, first_try=first_try)
    if data:
        if type(data) == str:
            return data
        if type(data) == list:
            return qr_code_photo_reader(photo_path=photo_path, crop_frame=data, first_try=False)


def transform_string_to_dataframe(string: str) -> pd.DataFrame:
    if string is None:
        return pd.DataFrame()
    pattern = re.compile(r"\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d")
    string_beginning = string.split(',')[0]
    if not pattern.match(string_beginning):
        print('QRCode text do not match format')
        return pd.DataFrame()
    if '[' in string:
        return pd.DataFrame()
    print(string)

    data_dict = {'datetime': string.split(',')[0]}
    data_dict.update({FEATURES_IN_QR_CODE[index - 1]: float(string.split(',')[index])
                      for index in range(1, len(string.split(',')))})

    dataframe = pd.DataFrame(data_dict, index=[0])
    return dataframe


def read_photo_from_folder():
    list_of_folders = glob.glob('/var/www/ftp_eurochem/*')
    dates_folders = []
    date_pattern = re.compile(r'^\d\d\d\d\d\d\d\d$')
    for i in list_of_folders:
        if date_pattern.match(i.split('/')[-1]):
            dates_folders.append(int(i.split('/')[-1]))
    list_of_folders = glob.glob(f'/var/www/ftp_eurochem/{max(dates_folders)}/images/*')
    latest_photos = sorted(list_of_folders, key=os.path.getctime, reverse=True)
    latest_photos = latest_photos[:15]
    print(latest_photos)
    data_set = pd.concat([transform_string_to_dataframe(qr_code_photo_reader(file_name))
                          for file_name in latest_photos])
    if data_set.empty:
        print('Nothing readed')
        return

    data_set.drop_duplicates(subset='datetime', inplace=True)
    data_set['datetime'] = pd.to_datetime(data_set['datetime'], format='%Y-%m-%d %H:%M:%S')
    data_set.sort_index(inplace=True)
    print(data_set)
    print(data_set.info())

    data_set = data_set.melt(id_vars=['datetime'],
                             value_vars=data_set.columns,
                             var_name='item_id',
                             ignore_index=True)

    conn = sqlite3.connect('./var/www/django_project/ai_database')
    data_set.to_sql(name='eurochem_data', con=conn, if_exists='append')


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(read_photo_from_folder, 'interval', minutes=3, name='clean_accounts', jobstore='default')
    register_events(scheduler)
    scheduler.start()
    print("Scheduler started...", file=sys.stdout)
