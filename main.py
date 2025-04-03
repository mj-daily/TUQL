#%%
from transaction.CHPost import MobilePayment

#%%

#%%
if __name__ == '__main__':
    mp = MobilePayment('labels.json')
    target = mp.PXPay

#%%