#%%
from transaction.CHPost import MobilePayment

#%%

#%%
if __name__ == '__main__':
    mp = MobilePayment('labels.json')
    target1 = mp.PXPay
    target2 = mp.EZPay
    target3 = mp.iPass

#%%