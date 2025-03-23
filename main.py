#%%
from transaction.CHPost import MobilePayment

#%%

#%%
if __name__ == '__main__':
    mp = MobilePayment('labels.json')
    for key, value in mp.label_id.items():
        print(key, value)
    print(mp.PXPay)