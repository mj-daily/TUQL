import re
import pdfplumber
from .base import BankParser
from .utils import reader, preprocess_image

class TBBParser(BankParser):
    """台灣企銀 (050) 解析器"""
    
    def parse_pdf(self, pdf_stream, password):
        # 簡易實作：假設台企銀 PDF 也是純文字流 (若為表格需改用 table extraction)
        try:
            with pdfplumber.open(pdf_stream, password=password) as pdf:
                full_text = "\n".join([page.extract_text() for page in pdf.pages])
        except Exception as e:
            raise Exception(f"PDF 開啟失敗: {str(e)}")

        # 1. 抓取帳號 (尋找 050 開頭或 帳號 關鍵字)
        # 台企銀帳號通常較長，這裡假設抓取末5碼
        acc_match = re.search(r"(?:帳號|050)[:\-\s]*[\d]+(\d{5})", full_text)
        account_no_parsed = acc_match.group(1) if acc_match else "Unknown"

        # 2. 抓取交易 (假設格式：日期 摘要 金額 餘額)
        # Regex 需根據實際 PDF 調整，這裡提供通用版
        # 例如: 112/01/01 轉帳支出 1,000 ...
        item_pattern = re.compile(r"(\d{3,4}/\d{2}/\d{2})\s+([^\s\d]+)\s+([\d,]+)(?=\s|$)")
        
        transactions = []
        for match in item_pattern.finditer(full_text):
            date, summary, amount_str = match.groups()
            amount = float(amount_str.replace(',', ''))
            
            # 判斷收支：簡單關鍵字判斷
            if "支出" in summary or "提款" in summary or "扣款" in summary:
                amount = -abs(amount)
            
            transactions.append({
                "date": date,
                "time": "00:00:00", # PDF 通常無時間
                "summary": summary,
                "ref_no": "PDF_IMPORT",
                "amount": amount
            })
            
        return account_no_parsed, transactions

    def recognize_screenshot(self, image_bytes):
        processed_img = preprocess_image(image_bytes)
        # detail=0: 只回傳文字列表，不含座標
        result = reader.readtext(processed_img, detail=0) 
        full_text = " ".join(result)
        full_text = full_text.split("交易明細內容")[-1]
        
        data = {"date":"", "time":"", "summary":"台企銀轉帳", "amount":0, "ref_no":"", "account_number":""}
        
        # 1. 金額
        amt_match = full_text.split("摘要")[0].split()[-1]
        data["amount"] = float(amt_match.replace(',', ''))

        # 2. 日期 (支援 2023/05/20 或 112/05/20)
        date_match = full_text.split("摘要")[0].split()[0]
        date_match = re.search(r"(\d{3,4}[/\-]\d{2}[/\-]\d{2})", date_match)
        if date_match: data["date"] = date_match.group(1)

        # 3. 時間
        time_match = full_text.split("摘要")[0].split()[1] + ":00"
        time_match = re.search(r"(\d{2}:\d{2}:\d{2})", time_match)
        if time_match: data["time"] = time_match.group(1)

        # 4. 帳號 (尋找 "帳號" 後面的數字)
        # acc_match = re.search(r"帳號[:\s]*[\d\-]*(\d{5})", full_text)
        # if acc_match: data["account_number"] = acc_match.group(1)

        # 5. 備註/摘要
        note_match = full_text.split("摘要")[-1].split()[0]
        if note_match: data["summary"] = note_match

        # 6. 序號 (通常很長一段英文數字)
        ref_match = full_text.split("收付行")[-1].split()[0]
        if ref_match: data["ref_no"] = ref_match

        return data