import re
def extract_numbers_from_string(s):
    return re.findall(r'\d+', s)