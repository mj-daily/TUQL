#%%
from base64 import urlsafe_b64decode
import os
from Google import create_service
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from lib import extract_numbers_from_string as getnum

#%% 
def get_monthly_statement(service, query, target_dir):
    page_token, messages = (None, [])
    while True:
        results = service.users().messages().list(
            userId='me', q=query, pageToken=page_token
        ).execute()
        messages.extend(results.get('messages', []))
        page_token = results.get('nextPageToken')
        if not page_token: break
    file_data = []
    for message in messages:
        msg = service.users().messages().get(
            userId='me', id=message['id']
        ).execute()
        # print(msg)
        parts = msg['payload'].get('parts', [])
        for part in parts:
            if part['filename'] == "銀行對帳單.PDF":
                if 'data' in part['body']:
                    data = part['body']['data']
                else:
                    att_id = part['body']['attachmentId']
                    att = service.users().messages().attachments().get(
                        userId='me', messageId=message['id'], id=att_id
                    ).execute()
                    data = att['data']
                file_data.append(urlsafe_b64decode(data.encode('UTF-8')))

                # if not os.path.exists(target_dir):
                #     os.makedirs(target_dir)

                # path = os.path.join(target_dir, part['filename'])
                # with open(path, 'wb') as f:
                #     f.write(file_data)
                # print(f'Attachment {part["filename"]} downloaded.')
    return file_data

class PXPay(object):
    def __init__(self, snippet:list):
        self.id = snippet[5].split(')')[0]
        self.date = self._get_date(snippet)
        self.trade_number = getnum(snippet[-3])[0]
        self.income = int(getnum(snippet[-1].split()[0])[0])
    def _get_date(self, item:list):
        date_list = getnum(snippet[-4])
        self.yyyy = date_list[0]
        self.mm = date_list[1]
        self.dd = date_list[2]
        return f"{self.yyyy}-{self.mm}-{self.dd}"
        
#%%
CLINET_FILE = 'token.json'
API_NAME = 'gmail'
API_VERSION = 'v1'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

creds = None
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

#%%
# service = create_service(CLINET_FILE, API_NAME, API_VERSION, SCOPES)
service = build("gmail", "v1", credentials=creds)
results = service.users().getProfile(userId='me').execute()
# service.users().labels().list(userId='me').execute()
service.users().messages().list(userId='me', labelIds=['Label_1359550306618142105']).execute()
msg = service.users().messages().get(userId='me', id='195bb7a4190f98f5').execute()
snippet = msg['snippet'].split('*')
#%% PXPay
px = PXPay(snippet)
# %%
# query = 'from:(post.gov.tw) subject:(對帳單) has:attachment filename:pdf'
# target_dir = 'attachments/post'
# get_monthly_statement(service, query, target_dir)

# date = ['TFBN_2410.PDF', 'TFBN_2409.PDF']
# query = 'from:(taipeifubon.com.tw) subject:(對帳) has:attachment filename:pdf'
# target_dir = 'attachments/tfbn'
# file_data = get_monthly_statement(service, query, target_dir)
# for i, fd in enumerate(file_data):
#     # print(fd)
#     if not os.path.exists(target_dir):
#         os.makedirs(target_dir)

#     path = os.path.join(target_dir, date[i])
#     with open(path, 'wb') as f:
#         f.write(fd)
#     print(f'Attachment {date[i]} downloaded.')

# %%
