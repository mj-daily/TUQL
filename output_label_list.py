#%%
from lib.gmail import get_gmail_service
import json


def list_labels():
    service = get_gmail_service()
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    if not labels:
        print('No labels found.')
    else:
        with open('labels.json', 'w') as f:
            json.dump(labels, f, indent=4)
        print('Labels saved to labels.json')

#%%
if __name__ == '__main__':
    list_labels()