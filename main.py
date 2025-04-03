#%%
from transaction.CHPost import MobilePayment, Deposit

#%%

#%%
if __name__ == '__main__':
    mp = MobilePayment('labels.json')
    target1 = mp.PXPay
    target2 = mp.EZPay
    target3 = mp.iPass
#%%
    Month = '2025-03'
    ##### PXPay amounts
    amounts1 = 0
    for t in target1:
        if Month in t['DT']:
            amounts1 += t['AM']

    ##### EZPay amounts
    amounts2 = 0
    for t in target2:
        if Month in t['DT']:
            amounts2 += t['AM']

    ##### iPass amounts
    amounts3 = 0
    for t in target3:
        if Month in t['DT']:
            amounts3 += t['AM']

    print(f"MobilePay in {Month}:")
    print(f"    PXPay: {amounts1:8} (NT$)")
    print(f"    EZPay: {amounts2:8} (NT$)")
    print(f"    iPass: {amounts3:8} (NT$)")
#%%
    dp = Deposit('labels.json').records
    #%%
    Month = "2025-03"
    amount = {}
    for r in dp:
        if Month in r['DT']:
            print(r)
            if r['TP'] not in amount:
                amount[r['TP']] = 0
            amount[r['TP']] += r['AM']
    print()
    print(f"Deposits in {Month}:")
    for k, v in amount.items():
        print(f"    {k}: {v:8} (NT$)")
