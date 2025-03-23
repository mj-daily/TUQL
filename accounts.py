from lib import extract_numbers_from_string as getnum
def to_date(date_list):
    yyyy = date_list[0]
    mm = date_list[1]
    dd = date_list[2]
    return f"{yyyy}-{mm}-{dd}"

class PostBank(object):
    def __init__(self, snippet:list):
        self.account = snippet[-6].split(')')[0]
        self.target = snippet[5].split(')')[0]
        self.date = to_date(getnum(snippet[-4]))
        self.trade_number = getnum(snippet[-3])[0]
        self.trade_amount = int(getnum(snippet[-1].split()[0])[0])

class PXPay(object):
    def __init__(self, snippet:list):
        self.id = snippet[5].split(')')[0]
        self.date = to_date(getnum(snippet[-4]))
        self.trade_number = getnum(snippet[-3])[0]
        self.income = int(getnum(snippet[-1].split()[0])[0])