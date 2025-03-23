#%%
from lib.gmail import get_gmail_service
from base64 import urlsafe_b64decode
from accounts import PXPay, PostBank

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
  
#%%
service = get_gmail_service()
print(type(service))
results = service.users().getProfile(userId='me').execute()
service.users().messages().list(userId='me', labelIds=['Label_example']).execute()
msg = service.users().messages().get(userId='me', id='example').execute()
snippet = msg['snippet'].split('*')

px = PXPay(snippet)
pt = PostBank(snippet)
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
