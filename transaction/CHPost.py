#%%
from lib.gmail import MyGmailAPI
from lib import extract_numbers_from_string as getnum
import json
#%%

#%%
class Deposit(object):
    def __init__(self, label_source):
        self.service = MyGmailAPI()
        with open(label_source, 'r') as f:
            labels = json.load(f)
        for label in labels:
            if 'Deposits' in label['name']:
                self.label_id = label['id']
                break
        else:
            raise ValueError("No label with 'Deposits' found in the provided labels.")
        msg_id = self.service.list_msg(labelIds=self.label_id)
        self.records = []
        for mid in msg_id:
            mi = mid['id']
            msg = self.service.get_msg(mi)['snippet']
            record = self._ExtractMessege(msg)
            self.records.append(record)
    def _to_datetime(self, date_msg:str, time_msg:str):
        date_list = getnum(date_msg)
        time_list = getnum(time_msg)
        yyyy = int(date_list[0]) + 1911
        mm, dd = date_list[1], date_list[2]
        HH, MN = time_list[0], time_list[1]
        return f'{yyyy:04}-{mm}-{dd}T{HH}:{MN}'
    def _ExtractMessege(self, msg:str):
        record = {}
        snippet = msg.split()
        record['TO'] = int(snippet[3][-5:])
        record['TP'] = snippet[7][-4:]
        record['FM'] = int(snippet[8][-5:])
        record['DT'] = self._to_datetime(snippet[5], snippet[6])
        record['AM'] = int(getnum(snippet[4])[0])
        return record

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
        self.EZPay = self._EZPay()
        self.iPass = self._iPass()
    def _PXPay(self):
        msg_id = self.service.list_msg(labelIds=self.label_id['PXPay'])
        records = []
        print("Reading records from PXPay...")
        for mid in msg_id:
            mi = mid['id']
            msg = self.service.get_msg(mi)['snippet']
            if "交易金額" in msg:
                records.append(self._ExtractSnippet(msg, 'CHPost'))
        return records
    def _EZPay(self):
        msg_id = self.service.list_msg(labelIds=self.label_id['EZPay'])
        records = []
        print("Reading records from EZPay...")
        for mid in msg_id:
            mi = mid['id']
            msg = self.service.get_msg(mi)['snippet']
            if "交易金額" in msg:
                records.append(self._ExtractSnippet(msg, 'CHPost'))
        return records
    def _iPass(self):
        msg_id = self.service.list_msg(labelIds=self.label_id['iPass'])
        records = []
        print("Reading records from iPass...")
        for mid in msg_id:
            mi = mid['id']
            msg = self.service.get_msg(mi)['snippet']
            if "交易金額" in msg:
                records.append(self._ExtractSnippet(msg, 'CHPost'))
        return records
    def to_date(self, date_list):
        yyyy = date_list[0]
        mm = date_list[1]
        dd = date_list[2]
        return f"{yyyy}-{mm}-{dd}"
    def _ExtractSnippet(self, snippet:str, source:str):
        record = {}
        if (source == "CHPost"):
            snippet = snippet.split('*')
            record['ID'] = int(snippet[5].split(')')[0])
            record['DT'] = self.to_date(getnum(snippet[-4]))
            record['NO'] = getnum(snippet[-3])[0]
            record['AM'] = int(getnum(snippet[-1].split()[0])[0])
            return record
        else:
            raise ValueError(f"Unrecognized source: {source}")
            