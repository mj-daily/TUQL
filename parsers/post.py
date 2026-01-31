import re
import pdfplumber
from .base import BankParser
from .utils import reader, preprocess_image
from .registry import register_parser

@register_parser('700')
class PostOfficeParser(BankParser):
    def parse_pdf(self, pdf_stream, password, **kwargs):
        try:
            with pdfplumber.open(pdf_stream, password=password) as pdf:
                full_text = "\n".join([page.extract_text() for page in pdf.pages])
        except Exception as e:
            raise Exception(f"PDF 開啟失敗: {str(e)}")

        acc_match = re.search(r"帳\s+號[:：\s]*([\d\*\-]+)", full_text)
        raw_acc = acc_match.group(1).strip() if acc_match else "Unknown"
        last_5_acc = raw_acc[-5:] if len(raw_acc) >= 5 else raw_acc
        account_no_parsed = last_5_acc.replace('*', '').replace('-', '')
        
        INCOME_KEYWORDS = ["薪資", "利息", "轉入", "存入", "退款"]
        item_pattern = re.compile(r"(\d{3}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\S+)\s+(.*?)\s+([\d,]+)(?=\n|$)")
        
        transactions = []
        for match in item_pattern.finditer(full_text):
            date, time, summary, ref_no, amount = match.groups()
            amount_val = float(amount.replace(',', ''))
            if not any(kw in summary for kw in INCOME_KEYWORDS):
                amount_val = -abs(amount_val)
            transactions.append({
                "date": date, "time": time, "summary": summary,
                "ref_no": ref_no.strip(), "amount": amount_val
            })
        return account_no_parsed, transactions

    def recognize_screenshot(self, image_bytes):
        processed_img = preprocess_image(image_bytes)
        result = reader.readtext(processed_img, detail=0, paragraph=True)
        full_text = " ".join(result).split("交易") # 郵局特徵分割點
        
        # 預設值
        data = {"date":"", "time":"", "summary":"", "amount":0, "ref_no":"", "account_number":""}
        
        if len(full_text) > 0:
            # 帳號
            acc_match = re.search(r"帳\s*號\s*[\*\d\-]*?(\d{5})", full_text[0])
            if acc_match: data["account_number"] = acc_match.group(1)
            
            # 金額 (抓第一段最後的數字)
            try:
                amt_str = full_text[0].split()[-1]
                data["amount"] = float(amt_str.replace(',', ''))
            except: pass
            
            # 摘要
            data["summary"] = "".join(re.findall(r"[\u4e00-\u9fff]", full_text[0].replace("帳號", "")))

            # 日期時間 (通常在第二段)
            if len(full_text) > 1:
                d_match = re.search(r"(\d{3}/\d{2}/\d{2})", full_text[1])
                t_match = re.search(r"(\d{2}:\d{2}:\d{2})", full_text[1])
                if d_match: data["date"] = d_match.group(1)
                if t_match: data["time"] = t_match.group(1)
            
            # 序號 (通常在第三段)
            if len(full_text) > 2:
                try: data["ref_no"] = full_text[2].split()[1]
                except: pass

        return data