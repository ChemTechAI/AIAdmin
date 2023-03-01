from django.http import HttpResponse
import os
import glob
import re

# Create your views here
def index(request):
    list_of_folders = glob.glob('/var/www/ftp_eurochem/*')
    dates_folders = []
    date_pattern = re.compile(r'^\d\d\d\d\d\d\d\d$')
    for i in list_of_folders:
        if date_pattern.match(i.split('/')[-1]):
            dates_folders.append(int(i.split('/')[-1]))
    list_of_folders = glob.glob(f'/var/www/ftp_eurochem/{max(dates_folders)}/images/*')
    latest_photo = max(list_of_folders, key=os.path.getctime)
    image_data = open(latest_photo, "rb").read()
    return HttpResponse(image_data, content_type="image/png")
