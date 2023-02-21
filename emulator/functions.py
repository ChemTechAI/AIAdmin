import os

import docker
import pandas as pd
import yaml

from django.conf import settings


def get_docker_client():
    try:
        return docker.DockerClient()
    except BaseException as e:
        print(e)


def extract_data_about_containers_to_dict(containers_list):
    containers_status_dict = {}
    for container in containers_list:
        container_id = container.attrs['Config']['Hostname']
        try:
            container_name = container.attrs['Config']['Labels']['com.docker.compose.project']
        except BaseException as e:
            print(e)
            container_name = None
        try:
            container_location = container.attrs['Config']['Labels']['com.docker.compose.project.working_dir']
        except BaseException as e:
            print(e)
            container_location = None
        try:
            container_start_date = pd.to_datetime(container.attrs['State']['StartedAt'])
            container_start_date_str = container_start_date.strftime('%d %B %Y %H:%M:%S')
        except BaseException as e:
            print(e)
            container_start_date_str = None
        one_container_status_dict = {'StartedAt': container_start_date_str,
                                     'Type': container.attrs['Args'][0],
                                     'Name': container_name,
                                     'Image': container.attrs['Config']['Image'],
                                     'Location': container_location,
                                     'Status': container.attrs['State']['Running'],
                                     }
        containers_status_dict[container_id] = one_container_status_dict
    return containers_status_dict


def get_container_object_by_id(container_id: str):
    docker_client = get_docker_client()
    return docker_client.containers.get(container_id)


def detect_worked_emulator(containers_data: dict, project_data: dict):
    if not containers_data or not project_data:
        return 'Emulator not working'
    started_containers = [container for container in containers_data.values() if container['Status']]
    if not started_containers:
        return 'Emulator not working'
    started_project = os.path.basename(os.path.normpath(started_containers[0]['Location']))
    if started_project in project_data.keys():
        started_branch = project_data[started_project]['Status']
    else:
        started_branch = 'Unknown'
    return f'Emulator working with project: {started_project} with status {started_branch}'


def get_current_frontend_from_config():
    with open(os.path.join(settings.BASE_DIR, 'emulator', 'project_config.yaml')) as file:
        data = yaml.load(file, Loader=yaml.SafeLoader)
        return data['project_name']


def set_current_frontend_from_config(new_frontend_name: str):
    new_config = {'project_name': new_frontend_name}
    with open(os.path.join(settings.BASE_DIR, 'emulator', 'project_config.yaml'), "w") as file:
        yaml.dump(new_config, stream=file, sort_keys=False)
