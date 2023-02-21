from threading import Thread
from bokeh.server.server import Server
from bokeh.util.browser import view
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http.response import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.conf import settings

from sqlalchemy import create_engine
from pandas import DataFrame, read_csv
from datasets.models import TestDataset

# Create your views here.
from csv_editor.csv_editor_tornado import run_tornado_with_bokeh, plot_csv_editor, IndexHandler
from django.http import HttpResponse, JsonResponse
import requests
from bokeh.embed import server_session
from bokeh.client import pull_session


user = settings.DATABASES['default']['USER']
password = settings.DATABASES['default']['PASSWORD']
database_name = settings.DATABASES['default']['NAME']

database_url = f'postgresql://{user}:{password}@localhost:5432/{database_name}'


def csv_editor_view(request):
    Thread(target=run_tornado_with_bokeh).start()
    session = pull_session(url="http://localhost:5006/csv_editor")

    script = server_session(model=None,
                            session_id=session.id,
                            url="http://localhost:5006/csv_editor",
                            )
    return render(request, 'templates/csv_editor/embed1.html', {'script': script})


class Datasets(View):

    def get(self, request):
        request.session['next_to'] = request.META.get('HTTP_REFERER')
        engine = create_engine(database_url, echo=False)
        table_names = [table_name for table_name in engine.table_names()
                       if 'auth' not in table_name and 'django' not in table_name]

        return render(request, 'templates/datasets/dataset_index.html', {'table_names': table_names})

    def post(self, request):
        context = {}
        context['next_to'] = request.session.get('next_to', None)

        table_name = request.POST.get('table_name', None)
        #
        # status = 'Choose project name'
        # if project_name:
        try:
            csv_file = request.FILES["csv_file"]
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'File is not CSV type')
                return HttpResponseRedirect(reverse("datasets:upload_csv"))
            # if file is too large, return
            # if csv_file.multiple_chunks():
                # messages.error(request, "Uploaded file is too big (%.2f MB)." % (csv_file.size / (1000 * 1000),))
                # return HttpResponseRedirect(reverse("myapp:upload_csv"))

            file_data = read_csv(csv_file, parse_dates=True)
            tags_not_allowed = [tag for tag in ['datetime', 'item_id', 'value'] if tag not in file_data]

            if tags_not_allowed:
                if 'datetime' not in tags_not_allowed:
                    file_data.index = file_data['datetime']
                file_data = melt_table(file_data)

            if table_name:

                engine = create_engine(database_url, echo=False)
                file_data.to_sql(name=table_name, con=engine, if_exists='replace')

            else:
                table_name = 'historytable'

                model_ = TestDataset()
                model_.truncate()

                if 'id' not in file_data:
                    file_data.index = list(range(file_data.shape[0]))

                for id in file_data.index:
                    form = TestDataset()
                    form.id = id
                    form.datetime = file_data.loc[id, 'datetime']
                    form.item_id = file_data.loc[id, 'item_id']
                    form.value = file_data.loc[id, 'value']
                        # try:
                    form.save()
                #         except Exception as e:
                #             logging.getLogger("error_logger").error(repr(e))
                # except Exception as e:
                #     logging.getLogger("error_logger").error("Unable to upload file. " + repr(e))
                #     messages.error(request, "Unable to upload file. " + repr(e))

            status = f'Table is saved with name: {table_name}'
            context['error'] = status
            return render(request, 'templates/datasets/dataset_index.html', context)
        except BaseException as error:
            context['error'] = str(error)
            return render(request, 'templates/datasets/dataset_index.html', context)


def melt_table(data: DataFrame):
    copy_data = data.copy()
    copy_data['datetime'] = copy_data.index
    versed_data = copy_data.melt(id_vars=['datetime'],
                                 value_vars=data.columns,
                                 var_name='item_id',
                                 ignore_index=True)

    return versed_data

# if __name__ == '__main__':
#     # file_data = pd.read_csv(r'C:\Users\User\PycharmProjects\EuroChem\BackEnd_EUCH\tests\test_data\eurochem_test_data — копия.csv',
#
#     file_data = pd.read_csv(
#             r'C:\Users\User\PycharmProjects\EuroChem\BackEnd_EUCH\tests\test_data\calculated — копия.csv',
#             parse_dates=True)
#
#     tags_not_allowed = [tag for tag in ['datetime', 'item_id', 'values'] if tag not in file_data]
#     if tags_not_allowed:
#         if 'datetime' not in tags_not_allowed:
#             file_data.index = file_data['datetime']
#         file_data = melt_table(file_data)
#
#     if 'id' not in file_data:
#         file_data.index = list(range(file_data.shape[0]))
#
#     print(file_data)

