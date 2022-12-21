from decouple import config
from TR_Client import *
from pprint import pprint
import requests
from typing import List, Dict, Tuple
import logging


def find_zephyr_parent_folder(parent_folder_name: str, zp_folders: List, parent_of_parent) -> int:
    for i in zp_folders:
        if parent_of_parent is not None:
            if i["name"] == parent_folder_name and parent_of_parent == check_zephyr_parent_of_parent(zp_folders, i['parentId']):
                return i["id"]
        else:
            if i['name'] == parent_folder_name and i['parentId'] is None:
                return i['id']


def check_zephyr_parent_of_parent(zp_folders, parentId):
    for i in zp_folders:
        if i['id'] == parentId:
            return i['name']


def find_tr_parent_folder(parent_id: int, tr_folders) -> str:
    for i in tr_folders:
        if i["id"] == parent_id:
            parent_of_parent = find_tr_parent_of_parent_name(tr_folders, i['parent_id'])
            return i["name"], parent_of_parent


def find_tr_parent_of_parent_name(tr_folders, parent_id: int):
    if parent_id is not None:
        for i in tr_folders:
            if i['id'] == parent_id:
                return i['name']
    else:
        return None


def create_zephyr_folders(tr_folders: List, url: str, headers: Dict, created_folders):
    counter = 0
    for i in tr_folders:
        # Change TR's parent id to Zephyr's.
        if (i['name'], i['parent_id']) not in created_folders:
            if i["parent_id"] is not None:
                # Get all already existing folders in Zephyr.
                zp_parent_id = None
                while zp_parent_id is None:
                    response = requests.request(
                        "GET",
                        url,
                        headers=headers,
                    ).json()['values']
                    parent_folder_name, parent_of_parent = find_tr_parent_folder(i["parent_id"], tr_folders)
                    zp_parent_id = find_zephyr_parent_folder(parent_folder_name, response, parent_of_parent)
            else:
                zp_parent_id = None
            # Create Zephyr folder

            data = {
                "parentId": zp_parent_id,
                "name": i['name'],
                "projectKey": "XXXX",  # Project key
                "folderType": "TEST_CASE"
            }
            response = requests.request(
                "POST",
                url,
                headers=headers,
                json=data
            ).json()

            counter += 1

            logging.info(f"{counter} / {Required} {i['name']} - CREATED")
            #pprint(response)

    logging.info("All folders successfully created!")


def collect_zephyr_folders(url: str, headers: Dict):
    response = requests.request(
        "GET",
        url,
        headers=headers,
    ).json()['values']

    for i in response:
        folder = ()
        if i['parentId'] is not None:
            for j in response:
                if i['parentId'] == j['id']:
                    for z in tr_folders:
                        if j['name'] == z['name']:
                            folder = (i['name'], z['id'])  # We've got TR parent ID for created ZP folder
                            created_folders.append(folder)

        else:
            folder = (i['name'], None)
            created_folders.append(folder)


def tr_zp_mapping(tr_folders, tr_zp_ids, url: str, headers: Dict):
    response = requests.request(
        "GET",
        url,
        headers=headers,
    ).json()['values']
    # We should achieve a dict 'TR ID':'ZP ID'. For each TR folder we should check that parent is similar to ZP
    for i in tr_folders:
        folder = {}
        if i['parent_id'] is not None:
            for j in tr_folders:
                # We should find TR folder parent name to compare with ZP response
                if i['parent_id'] == j['id']:
                    for z in response:
                        # Searching potential match, TR Name == ZP Name
                        if i['name'] == z['name']:
                            for x in response:
                                # Searching parent of ZP folder and checking if the name = parent name of TR folder
                                if z['parentId'] == x['id'] and j['name'] == x['name']:
                                    folder = {i['id']: z['id']}
                                    tr_zp_ids.append(folder)
        else:
            for z in response:
                if i['name'] == z['name'] and z['parentId'] is None:
                    folder = {i['id']: z['id']}
                    tr_zp_ids.append(folder)
    return tr_zp_ids


def get_section(tr_zp_ids, tr_section_id):
    for i in tr_zp_ids:
        if tr_section_id in i:
            return i.get(tr_section_id)


if __name__ == "__main__":
    # Access TestRail Request
    client = APIClient("https://testrail.your-domain.com/")  # Put TR domain here
    client.user = config('EMAIL')
    client.password = config('PASSWORD')
    tr_folders = client.send_get('get_sections/1')

    # Access Zephyr
    url_f = "https://api.zephyrscale.smartbear.com/v2/folders?maxResults=3000&projectKey=XXXX"  # Jira project key
    headers_f = {
        "Accept": "application/json",
        "Authorization": config('BEARER')
    }

    # logging
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    created_folders = []
    logging.info("Checking created folders...")
    collect_zephyr_folders(url_f, headers_f)
    logging.info("Folders collected")

    Required = len(tr_folders)

    # Start creating folders
    logging.info("Start creating folders...")
    create_zephyr_folders(tr_folders, url_f, headers_f, created_folders)
