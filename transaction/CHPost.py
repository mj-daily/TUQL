#%%
from lib.gmail import MyGmailAPI
import json

#%%
class MobilePayment(object):
    def __init__(self, label_source):
        self.service = MyGmailAPI()
        with open(label_source, 'r') as f:
            labels = json.load(f)
            self.label_id = {}
            for label in labels:
                if 'MobilePayment' in label['name']:
                    name = label['name'].split('/')[-1]
                    self.label_id[name] = label['id']
        self.PXPay = self._PXPay()
    def _PXPay(self):
        msg_id = self.service.list_msg(labelIds=self.label_id['PXPay'])
        for mid in msg_id:
            mi = mid['id']
            msg = self.service.get_msg(mi)['snippet']
            print(msg)
        return msg_id