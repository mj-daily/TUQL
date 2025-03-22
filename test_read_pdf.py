#%%
from pypdf import *

#%% Functions
def read(diri:str):
    reader = PdfReader(diri)
    if reader.is_encrypted:
        pwd = input(f"Enter the password for {diri.split('/')[-1]}")
        reader.decrypt(pwd)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text
#%%
if __name__ == "__main__":
    text = read(
        diri="PO05_11310.pdf"
    )
    print(text)