# parser.py
# (init_db 已移至 database.py)
from parsers.post import PostOfficeParser
from parsers.tbb import TBBParser

def get_parser(bank_code):
    """解析器工廠：根據銀行代碼回傳對應的解析器實例"""
    if bank_code == '050':
        return TBBParser()
    elif bank_code == '700':
        return PostOfficeParser()
    else:
        # 預設使用郵局 (兼容舊版)，或可拋出錯誤
        return PostOfficeParser()
