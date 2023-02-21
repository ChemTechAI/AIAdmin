from django.http import JsonResponse, HttpResponse
from pandas import DataFrame
import requests


def redirect_image(request, file_name=None):
    response = requests.get('http://localhost:5051/' + request.get_full_path())
    return HttpResponse(response.content, content_type="image/jpeg")


def redirect_json(request, file_name=None):
    response = requests.get('http://localhost:5051/' + request.get_full_path())
    return JsonResponse(response.json(), safe=False)


def redirect_json_with_csv(request, file_name=None):
    input_response = requests.get('http://localhost:5051/' + request.get_full_path().replace('download', 'save'))
    input_response = requests.get('http://localhost:5051/' + request.get_full_path())

    output_response = HttpResponse(content_type='text/csv')
    output_response['Content-Disposition'] = 'attachment; filename=export.csv'

    data = input_response.json()
    DataFrame.from_dict(data).to_csv(path_or_buf=output_response)
    return output_response
