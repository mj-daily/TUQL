# parsers/base.py
from abc import ABC, abstractmethod

class BankParser(ABC):
    """銀行解析器基礎介面"""
    
    @abstractmethod
    def parse_pdf(self, pdf_stream, password):
        """
        解析 PDF
        回傳: (account_number, transactions)
        """
        pass

    @abstractmethod
    def recognize_screenshot(self, image_bytes):
        """
        解析圖片
        回傳: 交易資料字典
        """
        pass