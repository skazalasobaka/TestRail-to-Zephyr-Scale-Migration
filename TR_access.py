import re
from datetime import datetime
from get_users_TR import find_user
from get_folders_TR import *
from TR_Client import *
from decouple import config
from pprint import pprint
from atlassian import Jira
import logging


def find_type(case_types, type_id):
    for i in case_types:
        if type_id == i['id']:
            return i['name']


def find_estimated_time(estimate, mseconds_per_unit):
    if estimate is not None:
        try:
            estimatedTime = int(estimate[:-1]) * int(mseconds_per_unit[estimate[-1]])
            return estimatedTime
        except:
            return None
    else:
        return None


def normal_url(url):
    return f"<a href={url}>{url}</a>"


def create_image_link(content):
    attachment = re.findall('get/[0-9]+', content)
    for attach in attachment:
        attach = attach.replace('get/', '')
        image = f'<img src="https://your-confl.atlassian.net/wiki/download/attachments/100000000095/{attach}" />'  # Confluence page ID and link
        content = content.replace(attach_indicator + attach + ')', image)
    return content


def find_preconditions(preconditions, href):
    if preconditions is not None:
        url = re.search(href, preconditions)
        if url:
            url = url.group("url")
            preconditions = preconditions.replace(url, normal_url(url))
        preconditions = preconditions.replace('\r', '<br>')
        if attach_indicator in preconditions:
            preconditions = create_image_link(preconditions)
        return preconditions
    else:
        return None


def tablesFormat(text):
    text = text.replace("<br>", "\r\n")
    tableflag = 0
    table = []
    tablestart_with_header = """<table border='1' style='border-collapse:collapse'><tr><th>"""
    tablestart_without_header = """<table border='1' style='border-collapse:collapse'><tr><td>"""
    header_start = """<tr><th>"""
    row_start = """<tr><td>"""
    row_end = """</td></tr>"""
    header_end = """</th></tr>"""
    tabletail = """</table>"""

    for row in text.splitlines():
        if row.startswith("|||") and tableflag == 0:
            tableflag = 1
            row = row.replace("|||", tablestart_with_header, 1).replace("|", "</th><th>") + header_end
        elif row.startswith("||") and tableflag == 0:
            tableflag = 1
            row = row.replace("||", tablestart_without_header, 1).replace("|", "</td><td>") + row_end
        elif row.startswith("|") and tableflag == 0:
            tableflag = 1
            row = row.replace("|", tablestart_without_header, 1).replace("|", "</td><td>") + row_end
        elif row.startswith("|||"):
            row = header_start + row.replace("|||", "", 1).replace("|", "</th><th>") + header_end
        elif row.startswith("||"):
            row = row_start + row.replace("||", "", 1).replace("|", "</td><td>") + row_end
        elif row.startswith("|"):
            row = row_start + row.replace("|", "", 1).replace("|", "</td><td>") + row_end
        else:
            if tableflag == 1:
                row = tabletail + row
            tableflag = 0
            row += "<br>"
        table.append(row)
    if not table[-1].replace('<br>', '').endswith(tabletail): table.append(tabletail + "<br>")

    return "".join(table)


def find_steps(steps, expected, steps_separated, items, steps_expected, inline, href):
    if steps is not None or expected is not None:
        if steps is not None:
            url = re.search(href, steps)
            if url:
                url = url.group("url")
                steps = steps.replace(url, normal_url(url))
            steps = steps.replace('\r', '<br>')
            if attach_indicator in steps:
                steps = create_image_link(steps)
            inline['description'] = steps
        if expected is not None:
            url = re.search(href, expected)
            if url:
                url = url.group("url")
                expected = expected.replace(url, normal_url(url))
            expected = expected.replace('\r', '<br>')
            if attach_indicator in expected:
                expected = create_image_link(expected)
            inline['expectedResult'] = expected

        steps_expected['inline'] = inline
        items.append(steps_expected)

    if steps_separated is not None:
        for j in steps_separated:
            steps_expected = {}
            inline = {}

            url = re.search(href, j['content'])
            if "|" in j['content']:
                j['content'] = tablesFormat(j['content'])
            if url:
                url = url.group("url")
                j['content'] = j['content'].replace(url, normal_url(url))
            j['content'] = j['content'].replace('\n', '<br>\n')
            if attach_indicator in j['content']:
                j['content'] = create_image_link(j['content'])
            inline['description'] = j['content']

            url = re.search(href, j['expected'])
            if "|" in j['expected']:
                j['expected'] = tablesFormat(j['expected'])
            if url:
                url = url.group("url")
                j['expected'] = j['expected'].replace(url, normal_url(url))
            j['expected'] = j['expected'].replace('\n', '<br>\n')
            if attach_indicator in j['expected']:
                j['expected'] = create_image_link(j['expected'])
            inline['expectedResult'] = j['expected']
            steps_expected['inline'] = inline
            items.append(steps_expected)

    return items


def find_yes_or_no(yes_no):
    if yes_no is True:
        return 'Yes'
    else:
        return 'No'


def find_objective(objective):
    if objective is not None:
        objective = objective.replace('\r', '<br>')
        return objective


def find_comments(comment, href):
    if comment is not None:
        url = re.search(href, comment)
        if url:
            url = url.group("url")
            comment = comment.replace(url, normal_url(url))
        comment = comment.replace('\r', '<br>')
        if attach_indicator in comment:
            comment = create_image_link(comment)
        return comment


def find_country(country, countries):
    custom_country = []
    for j in country:
        custom_country.append(countries[j])
    return custom_country


def has_attachment(preconds, steps, expected, steps_separated):
    attach = ''
    if preconds is not None:
        if attach_indicator in preconds:
            attach = 'Yes'
    if steps is not None:
        if attach_indicator in steps:
            attach = 'Yes'
    if expected is not None:
        if attach_indicator in expected:
            attach = 'Yes'
    if steps_separated is not None:
        for i in steps_separated:
            if attach_indicator in i['content'] or attach_indicator in i['expected']:
                attach = 'Yes'
    if attach != 'Yes':
        return 'No'
    else:
        return 'Yes'


def get_folder_name(tr_folders, section_id):
    for i in tr_folders:
        if section_id == i['id']:
            return i['name']


def get_refs(refs):
    if refs:
        ticket_ids = []
        jira = Jira(
            url='https://jira-domain.atlassian.net/',  # Your Jira domain
            username=config('EMAIL'),
            password=config('JIRA_TOKEN'),
            cloud=True)

        refs = list(refs.split(","))
        for i in refs:
            i = i.replace(" ", "")  # Some values consist spaces some not
            try:
                ticket = jira.issue(i)
                ticket_ids.append(ticket['id'])
            except:
                continue

        return ticket_ids


def get_tr_cases(cases, tr_folders, TR_Cases, project_key, tr_zp_ids, case_types, priorities, mseconds_per_unit,
                 statuses, ex_types,
                 fun_domain, countries, href):
    counter = 0
    packed = len(cases)
    for i in cases:
        TR_Data = {}
        customFields = {}
        #print(i)

        # Project Key - default
        TR_Data['projectKey'] = project_key

        # TestRail ID
        customFields['TestRail ID'] = i['id']

        # Title
        TR_Data['name'] = i['title']

        # Create folders and map them
        TR_Data['folderId'] = get_section(tr_zp_ids, i['section_id'])
        customFields['TestRail Folder'] = get_folder_name(tr_folders, i['section_id'])

        # Type
        customFields['Type'] = find_type(case_types, i['type_id'])

        # Priority
        TR_Data["priorityName"] = priorities[i['priority_id']]

        # Coverage - issues id's should be get from Atlassian
        TR_Data['refs'] = get_refs(i['refs'])

        # Owner
        customFields['Owner'] = find_user(i['created_by'])

        # Created On
        customFields['Created On'] = datetime.utcfromtimestamp(i['created_on']).strftime('%Y-%m-%d')

        # Updated On
        customFields['Updated On'] = datetime.utcfromtimestamp(i['updated_on']).strftime('%Y-%m-%d')

        # Estimate
        TR_Data['estimatedTime'] = find_estimated_time(i['estimate'], mseconds_per_unit)

        # Status
        TR_Data["statusName"] = statuses[i['custom_status']]

        # Execution Type
        customFields['Execution Type'] = ex_types[i['custom_type']]

        # Functional Domain
        if i['custom_domain']:
            customFields['Functional Domain'] = fun_domain[i['custom_domain']]

        # Reviewer
        customFields['Reviewer'] = find_user(i['custom_reviewer'])

        # Approver
        customFields['Approver'] = find_user(i['custom_approver'])

        # Planned Release
        customFields['Planned Release'] = i['custom_planned_release']

        # Update Required
        customFields['Update Required'] = find_yes_or_no(i['custom_update_required'])

        # One Time Execution
        customFields['One Time Execution'] = find_yes_or_no(i['custom_one_time_execution'])

        # Rotatable
        customFields['Rotatable'] = find_yes_or_no(i['custom_rotatable'])

        # Preconditions (consist attachments)
        TR_Data['precondition'] = find_preconditions(i['custom_preconds'], href)

        # Has Attachment
        customFields['Has Attachment'] = has_attachment(i['custom_preconds'], i['custom_steps'], i['custom_expected'], i['custom_steps_separated'])

        # Steps: content and expected
        items = []
        steps_expected = {}
        inline = {}

        TR_Data['items'] = find_steps(i['custom_steps'], i['custom_expected'], i['custom_steps_separated'], items,
                                      steps_expected, inline, href)

        # Objective
        TR_Data['objective'] = find_objective(i['custom_goals'])

        # Comments
        customFields['Comments'] = find_comments(i['custom_comment'], href)
        if i['custom_comment'] is not None:
            customFields['Has Comment'] = 'Yes'
        else:
            customFields['Has Comment'] = 'No'


        # Country
        customFields['Country'] = find_country(i['custom_country'], countries)

        TR_Data['customFields'] = customFields
        TR_Cases.append(TR_Data)

        counter += 1
        logging.info(f'{counter} / {packed} Case {i["id"]} - "{i["title"]}" - PACKED')

    logging.info(f'Collected {counter} cases')
    with open("Packed_Cases.json", "w") as outfile:
        json.dump(TR_Cases, outfile)
    return TR_Cases


def create_cases(url_cases, headers):
    with open("Packed_Cases.json") as cases:
        cases = json.load(cases)
        to_create = len(cases)
        counter = 0
        for i in cases:
            logging.info(f'Start creating "{i["name"]}" case')
            # Test Case creation
            response = requests.request(
                "POST",
                url_cases,
                headers=headers,
                json=i
            )
            case = response.json()
            print(case)
            counter += 1
            logging.info(f'{counter} / {to_create} {case["key"]} - "{i["name"]}" - CREATED')

            # Links -  ZP Coverage field
            if i['refs']:
                logging.info(f'Found {len(i["refs"])} links. Uploading: ')
                url_links = f"https://api.zephyrscale.smartbear.com/v2/testcases/{case['key']}/links/issues"

                uploaded = len(i["refs"])
                count = 0
                for j in i['refs']:
                    link = {
                        "issueId": j,
                    }

                    response = requests.request(
                        "POST",
                        url_links,
                        headers=headers,
                        json=link
                    )

                    response.json()
                    # print(links)
                    count += 1
                    logging.info(f'Uploaded {count} / {len(i["refs"])} links')
                logging.info("Links uploaded")

            # Post Test Steps
            if i['items']:
                logging.info("Test Steps found. Uploading.")
                url_steps = f"https://api.zephyrscale.smartbear.com/v2/testcases/{case['key']}/teststeps"
                data = {
                    "mode": "OVERWRITE",
                    "items": i['items']
                }
                response = requests.request(
                    "POST",
                    url_steps,
                    headers=headers,
                    json=data
                )
                try:
                    response.json()
                except:
                    print(response.json())
                logging.info("Test Steps uploaded")

            # Post Non Image Attachments
            with open("TR_Attachments.json") as attaches:
                attaches = json.load(attaches)
                if str(i['customFields']['TestRail ID']) in attaches:
                    logging.info("Attachments found. Uploading")
                    url_attaches = f"https://api.zephyrscale.smartbear.com/v2/testcases/{case['key']}/links/weblinks"
                    for j in attaches[str(i['customFields']['TestRail ID'])]:
                        data = {
                            "description": j.removeprefix('https://confluence-domain.atlassian.net/wiki/download/attachments/100000000009/'),  # Confluence page ID and domain
                            "url": j
                        }
                        response = requests.request(
                            "POST",
                            url_attaches,
                            headers=headers,
                            json=data
                        )
                        response.json()
                    logging.info("Attachments uploaded.")


        logging.info("All test cases created")


if __name__ == "__main__":
    # Access TestRail Request
    client = APIClient("https://testrail.domain.com/")  # Your TR domain
    client.user = config('EMAIL')
    client.password = config('PASSWORD')

    cases = client.send_get('get_cases/1')  # Project ID - 1
    case_types = client.send_get('get_case_types')
    tr_folders = client.send_get('get_sections/1')

    TR_Cases = []  # List with dicts

    # Access Zephyr
    url_f = "https://api.zephyrscale.smartbear.com/v2/folders?maxResults=3000&projectKey=XXXX"  # Jira project key
    headers_f = {
        "Accept": "application/json",
        "Authorization": config('BEARER')
    }

    url_cases = "https://api.zephyrscale.smartbear.com/v2/testcases"

    # For Calculation and Mapping; Update the field values as you need!
    # -----------------------------------------------------------------------------------------------------------------------

    # project key
    project_key = 'XXXX'

    # section id
    tr_zp_ids = []
    tr_zp_ids = tr_zp_mapping(tr_folders, tr_zp_ids, url_f, headers_f)

    # estimated
    mseconds_per_unit = {"ms": 1, "s": 1000, "m": 60000, "h": 3600000, "d": 86400000, "w": 604800000}

    # priority
    types = ['Low', 'Normal', 'High']
    ids = [1, 2, 3]
    priorities = dict(zip(ids, types))

    # status
    types = ['Design', 'To be Updated', 'Ready for Review', 'Reviewed', 'Approved', 'Closed']
    ids = [1, 2, 3, 4, 5, 6]
    statuses = dict(zip(ids, types))

    # execution type
    types = ['Manual', 'Automatable', 'Automated', 'Not Automatable', 'Automated for Android', 'Automated for iOS',
             'Automation update required', 'Automatable as-is', 'Automatable partially', 'Dev Testing']
    ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    ex_types = dict(zip(ids, types))

    # functional domain
    types = ['Domain - X', 'Domain - Y', 'Example', 'Example-2', 'Example-3', 'Example-4', 'Operation',
             'Customer', 'Service', 'Report', 'Product', 'Marketing', 'Mobile',
             'API', 'Integration', 'Test', 'Chat', 'Technics',
             'Transformation', 'Function', 'Store',
             'Office', 'Analytics']
    ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
    fun_domain = dict(zip(ids, types))

    # country
    types = ['USA', 'Germany', 'France', 'Spain', 'Italy', 'China']
    ids = [1, 2, 3, 4, 5, 6]
    countries = dict(zip(ids, types))

    # links in text, replace to upload
    href = '(?P<url>https?://[^\s]+)'

    # find attachments in content
    attach_indicator = '![](index.php?/attachments/get/'

    # logging
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    logging.info("Packing all test cases...")
    TR_Cases = get_tr_cases(cases, tr_folders, TR_Cases, project_key, tr_zp_ids, case_types, priorities,
                            mseconds_per_unit, statuses,
                            ex_types, fun_domain, countries, href)

    #pprint(TR_Cases)

    logging.info("Start creating test cases...")
    create_cases(url_cases, headers_f)
