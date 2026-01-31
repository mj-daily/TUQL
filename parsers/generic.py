import re
import pdfplumber
from .base import BankParser

class GenericParser(BankParser):
    def __init__(self, config):
        self.config = config
        
    def parse_pdf(self, pdf_stream, password):
        try:
            with pdfplumber.open(pdf_stream, password=password) as pdf:
                full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        except Exception as e:
            raise Exception(f"PDF 開啟失敗: {str(e)}")

        regex = self.config.get("regex_pattern")
        groups = self.config.get("groups", {})
        
        pattern = re.compile(regex)
        transactions = []
        
        for match in pattern.finditer(full_text):
            date = self._get_group_val(match, groups.get("date"))
            time = self._get_group_val(match, groups.get("time")) or "00:00:00"
            summary = self._get_group_val(match, groups.get("summary")) or "Generic Import"
            ref_no = self._get_group_val(match, groups.get("ref")) or ""
            amount_str = self._get_group_val(match, groups.get("amount"))

            if not date or not amount_str:
                continue

            try:
                amount = float(amount_str.replace(',', ''))
            except ValueError:
                continue

            # Handle positive/negative logic
            if "income_keywords" in self.config:
                # If income keywords defined: default to expense (negative), unless match found
                if not any(kw in summary for kw in self.config["income_keywords"]):
                    amount = -abs(amount)
                else:
                    amount = abs(amount)
            elif "expense_keywords" in self.config:
                # If expense keywords defined: default to income (positive), unless match found
                if any(kw in summary for kw in self.config["expense_keywords"]):
                    amount = -abs(amount)
                else:
                    amount = abs(amount)
            
            transactions.append({
                "date": date,
                "time": time,
                "summary": summary.strip(),
                "ref_no": ref_no.strip(),
                "amount": amount
            })
        
        # Try to find account number if configured
        account_no = "Generic"
        if "account_pattern" in self.config:
            acc_match = re.search(self.config["account_pattern"], full_text)
            if acc_match:
                 # If account_group is specified, use it, else group 1
                 grp = self.config.get("account_group", 1)
                 try:
                     raw_acc = acc_match.group(grp).strip()
                     # Optional: Logic to clean account number (keep last 5 digits etc) - keep simple for now
                     account_no = raw_acc
                 except IndexError:
                     pass

        return account_no, transactions

    def _get_group_val(self, match, group_idx):
        if group_idx is not None and isinstance(group_idx, int) and 1 <= group_idx <= len(match.groups()):
            val = match.group(group_idx)
            return val if val else ""
        return ""

    def recognize_screenshot(self, image_bytes):
        # Placeholder: Generic OCR not yet implemented
        return {}
