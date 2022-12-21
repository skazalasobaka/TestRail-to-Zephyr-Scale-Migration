import re
from TR_Client import *
from decouple import config
import os
from requests.auth import HTTPBasicAuth
import itertools
from atlassian import Confluence
from pprint import pprint


def download_attachments(attachments, path, link, confluence, storage, file_ids=None):
    counter = 0
    for attach in attachments:
        if '.png' in attach:
            attachNum = attach.split('.', 1)[0]
            attachName = attach.split('.', 1)[0]
        else:
            attachNum = str(file_ids[attach])
            attachName = attach
        fullLink = link + attachNum

        response = requests.get(fullLink, auth=HTTPBasicAuth(config('EMAIL'), config('PASSWORD')))

        dataPath = os.path.join(path, attach)

        open(dataPath, "wb").write(response.content)
        confluence.attach_file(dataPath, name=f'{attachName}', content_type=None, page_id=f'{storage}', title=None, space="SPACE Name", comment=None)  # Put your space name

        os.remove(dataPath)
        counter += 1
        print(f"{counter} / {len(attachments)} uploaded to Confluence!")


def get_attach(content, regExp):
    if content is not None:
        getAttach = re.findall(regExp, content, re.DOTALL)
        return getAttach


def uploaded_attachments(storage):
    uploaded = []
    start = 0
    p = confluence.get_attachments_from_content(storage, start=f'{start}', limit=1000, expand=None, filename=None, media_type=None)
    while p['results'] != []:
        p = confluence.get_attachments_from_content(storage, start=f'{start}', limit=1000, expand=None, filename=None, media_type=None)
        for i in p['results']:
            uploaded.append(i['title'])
        start += 1000

    return uploaded


def find_file_attachments(cases, attachments, uploaded_files, file_ids):
    TR_Attachments = {}
    for i in cases:
        s = client.send_get(f'get_attachments_for_case/{i["id"]}')
        for j in s:
            if '.png' not in j['name'] and j['name'] not in attachments:
                file_ids[j['name']] = j['id']
                attachments.append(j['name'])
                j['name'] = j['name'].replace(' ', '%20')
                TR_Attachments.setdefault(i["id"], []).append(conf_link + str(file_storage) + '/' + j['name'])

    with open("TR_Attachments.json", "w") as outfile:
        json.dump(TR_Attachments, outfile)
    attachments = list(set(attachments) - set(uploaded_files))
    return attachments, file_ids


def find_image_attachments(cases, attachments, regExp, uploaded_images):
    for i in cases:

        content = [i['custom_preconds'], i['custom_steps'], i['custom_expected']]
        for j in content:
            attach = get_attach(j, regExp)
            if attach and attach not in attachments:
                attachments.append(attach)

        if i['custom_steps_separated'] is not None:
            for j in i['custom_steps_separated']:
                attach = get_attach(j['content'], regExp)
                if attach and attach not in attachments:
                    attachments.append(attach)

                attach = get_attach(j['expected'], regExp)
                if attach and attach not in attachments:
                    attachments.append(attach)

    attachments = list(itertools.chain.from_iterable(attachments))
    attachments = list(dict.fromkeys(attachments))
    attachments = [attach.replace('get/', '') for attach in attachments]
    attachments = list(set(attachments) - set(uploaded_images))
    attachments = [attach + '.png' for attach in attachments]
    return attachments


if __name__ == "__main__":
    client = APIClient("https://testrail.your-domain.com/")  # Put TR domain here
    client.user = config('EMAIL')
    client.password = config('PASSWORD')

    cases = client.send_get('get_cases/1')  # Project ID - 1

    path = '/Users/Dmitrii_Andreev/PycharmProjects/TestRail_Zephyr/tr-to-zp-migration/attachments'
    regExp = 'get/[0-9]+'
    link = 'https://your-jira.atlassian.com/index.php?/api/v2/get_attachment/'  # Update the link
    conf_link = 'https://your-confl.atlassian.net/wiki/download/attachments/'  # Update the link

    image_storage = 100000000095  # Confluence page ID
    file_storage = 100000000009  # Confluence page ID

    confluence = Confluence(
        url='https://your-confl.atlassian.net/',
        username=config('EMAIL'),
        password=config('JIRA_TOKEN'),
        cloud=True)

    uploaded_images = uploaded_attachments(image_storage)
    uploaded_files = uploaded_attachments(file_storage)

    Image_Attachments = []

    Image_Attachments = find_image_attachments(cases, Image_Attachments, regExp, uploaded_images)
    print(len(Image_Attachments))

    File_Attachments = []
    file_ids = {}

    File_Attachments, file_ids = find_file_attachments(cases, File_Attachments, uploaded_files, file_ids)
    #pprint(File_Attachments)
    #pprint(file_ids)

    download_attachments(Image_Attachments, path, link, confluence, image_storage)
    download_attachments(File_Attachments, path, link, confluence, file_storage, file_ids)
