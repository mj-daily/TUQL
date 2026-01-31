import re
import pdfplumber
from .base import BankParser
from .utils import reader, preprocess_image
from .registry import register_parser

@register_parser('050')
class TBBParser(BankParser):
    """台灣企銀 (050) 解析器"""
    
    def parse_pdf(self, pdf_stream, password, **kwargs):
        target_account = kwargs.get('target_account')

        # 簡易實作：假設台企銀 PDF 也是純文字流 (若為表格需改用 table extraction)
        try:
            with pdfplumber.open(pdf_stream, password=password) as pdf:
                full_text = "\n".join([page.extract_text() for page in pdf.pages])
                # print(full_text)
        except Exception as e:
            raise Exception(f"PDF 開啟失敗: {str(e)}")

        # 1. 決定回傳的帳號
        # 若有指定 target_account，則回傳該帳號 (假設過濾後都是該帳號的交易)
        # 若無，則嘗試從第一筆抓取或回傳 Unknown
        if target_account:
            account_no_parsed = target_account
        else:
            acc_match = re.search(r"轉出帳號\s*:\s*([^\s]+)", full_text)
            if acc_match:
                full_acc = acc_match.group(1)
                account_no_parsed = full_acc[-5:] if len(full_acc) >= 5 else full_acc
            else:
                account_no_parsed = "Unknown"

        # 2. 抓取交易
        transactions = []
        
        # 使用 Block Splitting 策略
        blocks = re.split(r"(?=轉出帳號\s*:)", full_text)
        blocks = [b for b in blocks if "轉出帳號" in b]
        
        for block in blocks:
            # [Filter Logic] 
            # 依據使用者所選的帳號(只有5碼 ex: 63701)比對每一筆交易紀錄的轉出帳號後五碼(ex: XXX01)
            # 若兩者的末2碼正確，才可被append (若不符則跳過整筆交易)
            should_process = True # 預設為處理 (若無 target_account 則全部轉入)

            if target_account:
                should_process = False # 若有指定目標帳號，則預設不處理，需比對成功才改為 True
                acc_match = re.search(r"轉出帳號\s*:\s*([^\s]+)", block)
                
                if acc_match:
                    block_acc = acc_match.group(1).strip()
                    # 比對末2碼
                    if len(target_account) >= 2 and len(block_acc) >= 2:
                        if target_account[-2:] == block_acc[-2:]:
                            should_process = True
                
            if not should_process:
                continue

            # 1. Date (用來定位 Category)
            date_match = re.search(r"(\d{3}/\d{2}/\d{2})", block)
            if not date_match: continue
            date_str = date_match.group(1)

            # Date Conversion (ROC to AD)
            try:
                y, m, d = date_str.split('/')
                formatted_date = f"{int(y)+1911}/{m}/{d}"
            except:
                formatted_date = date_str

            # 2. Category & Summary
            # 摘要統一使用交易類別的內容(如：跨行轉帳、自行轉帳、全國繳費等)
            # 類別通常位於日期行的下一行開頭
            summary = "TBB交易"
            category = "一般交易"
            
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            date_idx = -1
            for i, line in enumerate(lines):
                if date_str in line:
                    date_idx = i
                    break
            
            # 嘗試找尋已知類別
            found_cat = False
            if date_idx != -1 and date_idx + 1 < len(lines):
                cat_line = lines[date_idx + 1]
                for known_cat in ["跨行轉帳", "自行轉帳", "全國繳費"]:
                    if known_cat in cat_line:
                        category = known_cat
                        summary = known_cat
                        found_cat = True
                        break
            
            if not found_cat:
                 # Fallback, just pick first word of next line
                 if date_idx != -1 and date_idx + 1 < len(lines):
                     summary = lines[date_idx + 1].split()[0]
                     category = summary # treat as category

            # 3. Ref No
            # 跨行轉帳 -> 轉入帳號
            # 自行轉帳 -> 轉入
            # 全國繳費 -> 銷帳編號
            ref_no = ""
            if category == "跨行轉帳":
                m = re.search(r"轉入帳號\s*:\s*([^\s]+)", block)
                if m: ref_no = m.group(1)
            elif category == "自行轉帳":
                m = re.search(r"轉入\s*:\s*([^\s]+)", block)
                if m: ref_no = m.group(1)
            elif category == "全國繳費":
                m = re.search(r"銷帳編號\s*:\s*([^\s]+)", block)
                if m: ref_no = m.group(1)
            
            if not ref_no: 
                # 通用 fallback
                if "銷帳編號" in block:
                    m = re.search(r"銷帳編號\s*:\s*(\w+)", block)
                    if m: ref_no = m.group(1)
                else: 
                    ref_no = "PDF_IMPORT"

            # 4. Amount
            amt_match = re.search(r"(?:轉帳金額|繳費金額)\s*:\s*\$([\d,]+)", block)
            if not amt_match: continue
            amount = float(amt_match.group(1).replace(',', ''))
            amount = -abs(amount) # 視為支出

            # 5. Time
            time_match = re.search(r"(\d{2}:\d{2})", block)
            time_str = time_match.group(1) if time_match else "00:00"
            formatted_time = f"{time_str}:00"

            transactions.append({
                "date": formatted_date,
                "time": formatted_time,
                "summary": summary,
                "ref_no": ref_no,
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