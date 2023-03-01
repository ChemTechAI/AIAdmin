from django.shortcuts import HttpResponse, render, redirect
from django.conf import settings
from django.http import FileResponse
from django.contrib.auth.decorators import permission_required, login_required
from git import Repo
import yaml

import os
import mimetypes
from pathlib import Path
import posixpath

from test_calculations.views import DIR_WITH_PROJECTS
from .functions import get_docker_client, get_container_object_by_id, extract_data_about_containers_to_dict,\
    detect_worked_emulator, get_current_frontend_from_config, set_current_frontend_from_config


@permission_required(login_url='signin', perm='admin')
def index(request):
    docker_client = get_docker_client()
    context = {}
    containers_status_dict = {}
    if docker_client is None:
        context['docker_status'] = 'Docker is not available!'
    else:
        containers = docker_client.containers.list(all=True)
        containers_status_dict = extract_data_about_containers_to_dict(containers_list=containers)
        if containers_status_dict:
            context['docker_status'] = containers_status_dict
            context['columns_in_docker_status'] = ['ID', 'StartedAt', 'Type', 'Name', 'Image', 'Location', 'Status',
                                                   'Action']
        else:
            context['docker_status'] = 'No containers found'

    try:
        projects_list = os.listdir(DIR_WITH_PROJECTS)
        context["projects_list"] = projects_list
    except BaseException as error:
        context['error'] = error
        return render(request,
                      "templates/emulator/emulator_index.html",
                      context)

    projects_with_current_branch = {}
    for project in projects_list:
        project_dict = {}
        repo = Repo(path=os.path.join(DIR_WITH_PROJECTS, project))
        project_dict['Status'] = repo.git.status().split('\n')[0]
        project_dict['Branches'] = [branch.name for branch in repo.remote().refs]
        projects_with_current_branch[project] = project_dict

    context['emulator_status'] = detect_worked_emulator(project_data=projects_with_current_branch,
                                                        containers_data=containers_status_dict)
    context['projects_info'] = projects_with_current_branch
    context['columns_in_project_table'] = ['Project', 'Status', 'Branches', 'Actions']

    context['current_frontend'] = get_current_frontend_from_config()
    frontends_list = os.listdir(os.path.join(settings.BASE_DIR, 'emulator'))
    context['frontends_list'] = [file for file in frontends_list if file.startswith('build')]

    project_name = request.POST.get('project_name', None)
    if project_name:

        interval = request.POST.get('interval', None)
        datetime_start = request.POST.get('datetime_start', None)
        datetime_finish = request.POST.get('datetime_finish', None)

        if interval:
            docker_launch_config = {'project_name': project_name,
                                    'interval': interval,
                                    'datetime_start': datetime_start,
                                    'datetime_finish': datetime_finish,
                                    }
            try:
                with open(os.path.join(DIR_WITH_PROJECTS, project_name, 'instance', 'docker_launch_config.yaml'),
                          'w') as config:
                    yaml.dump(docker_launch_config, config)
                context['error'] = 'Saved'
            except BaseException as status:
                context['error'] = status
                return render(request,
                              "templates/emulator/emulator_index.html",
                              context)
        return render(request,
                      "templates/emulator/emulator_index.html",
                      context)

    return render(request,
                  "templates/emulator/emulator_index.html",
                  context)


@login_required(login_url='signin')
def emulator_view(request):
    current_build_name = get_current_frontend_from_config()
    with open(os.path.join(settings.REACT_APP_DIR, current_build_name, 'index.html')) as f:
        return HttpResponse(f.read())


@login_required(login_url='signin')
def load_static(request, path):
    path = posixpath.normpath(path).lstrip("/")

    build_folder_name = get_current_frontend_from_config()
    fullpath = Path(os.path.join(settings.BASE_DIR, 'emulator', build_folder_name, 'static', path))
    content_type, encoding = mimetypes.guess_type(str(fullpath))
    content_type = content_type or "application/octet-stream"
    response = FileResponse(fullpath.open("rb"), content_type=content_type)
    if encoding:
        response.headers["Content-Encoding"] = encoding
    return response


@permission_required(login_url='signin', perm='admin')
def stop_container(request, container_id: str):
    try:
        get_container_object_by_id(container_id).stop()
        return redirect('emulator:index')
    except BaseException as error:
        return render(request,
                      "templates/emulator/emulator_index.html",
                      {'error': error})


@permission_required(login_url='signin', perm='admin')
def start_container(request, container_id: str):
    try:
        get_container_object_by_id(container_id).start()
        return redirect('emulator:index')
    except BaseException as error:
        return render(request,
                      "templates/emulator/emulator_index.html",
                      {'error': error})


@permission_required(login_url='signin', perm='admin')
def change_branch(request, project_name: str):
    branch_name = request.POST.get('branch_name', None)
    try:
        repo = Repo(path=os.path.join(DIR_WITH_PROJECTS, project_name))
        repo.git.checkout(branch_name)
        return redirect('emulator:index')
    except BaseException as error:
        return render(request,
                      "templates/emulator/emulator_index.html",
                      {'error': error})


@permission_required(login_url='signin', perm='admin')
def change_frontend(request):
    frontend_name = request.POST.get('frontend_name', None)
    try:
        set_current_frontend_from_config(new_frontend_name=frontend_name)
        return redirect('emulator:index')
    except BaseException as error:
        return render(request,
                      "templates/emulator/emulator_index.html",
                      {'error': error})
