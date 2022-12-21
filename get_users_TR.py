from decouple import config
from TR_Client import *
from pprint import pprint


client = APIClient("https://testrail.your-domain.com/")  # Put TR domain here
client.user = config('EMAIL')
client.password = config('PASSWORD')

users = client.send_get('get_users/')
#pprint(users)


def find_user(created_by):
    if created_by is not None:
        for i in users:
            if i['id'] == created_by:
                return i['name']
    else:
        return None
