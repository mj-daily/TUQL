#%%
from lib.gmail import MyGmailAPI
from lib import extract_numbers_from_string as getnum
import json
#%%
def to_date(date_list):
    yyyy = date_list[0]
    mm = date_list[1]
    dd = date_list[2]
    return f"{yyyy}-{mm}-{dd}"
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
        records = []
        for mid in msg_id:
            mi = mid['id']
            msg = self.service.get_msg(mi)['snippet']
            if "交易金額" in msg:
                records.append(self._ExtractSnippet(msg, 'CHPost'))
        return records
    def _ExtractSnippet(self, snippet:str, source:str):
        record = {}
        if (source == "CHPost"):
            snippet = snippet.split('*')
            record['ID'] = int(snippet[5].split(')')[0])
            record['DT'] = to_date(getnum(snippet[-4]))
            record['NO'] = getnum(snippet[-3])[0]
            record['AM'] = int(getnum(snippet[-1].split()[0])[0])
            return record
        else:
            raise ValueError(f"Unrecognized source: {source}")
            