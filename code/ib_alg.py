#   ____   ____   _____              _ _                _    _
#   |  _ \ | __ ) |_   __ __ __ _  __| (_)_ __   __ _   / \  | | __ _  ___
#   | | | ||  _ \   | || '__/ _` |/ _` | | '_ \ / _`   / _ \ | |/ _` |/ _ \
#   | |_| _| |_) _  | || | | (_| | (_| | | | | | (_|  / ___ \| | (_| | (_) |
#   |____(_|____(_  |_||_|  \__,_|\__,_|_|_| |_|\__, /_/   \_|_|\__, |\___/
#                                               |___/           |___/

# Links
# https://www.alphavantage.co/support/#
# https://github.com/RomelTorres/alpha_vantage
# http://interactivebrokers.github.io/tws-api/index.html#gsc.tab=0

# Load Modules
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.common import *
from ibapi.contract import *
from ibapi.order import *
from alpha_vantage.timeseries import TimeSeries
import pandas as pd
import numpy as np
import datetime
import os as os

# Directory structure
home_dir = "/home/justin/projects/ib/IBJts/source/pythonclient/tests/"
code_dir = home_dir + "code/"
datain_dir = home_dir + "data/clean_in/"
dataout_dir = home_dir + "data/out/"

# Define classes & funcs
class my_test(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)

    def error(self, reqId:TickerId, errorCode:int, errorString:str):
        print("Error: ", reqId, " " , errorCode, " " , errorString)

def incr_OrderId(curr_OrderId):
    return curr_OrderId + 1

def clean_alpha_data(symb, avapi_key):
    ts = TimeSeries(avapi_key, output_format='pandas')
    df = ts.get_daily(symbol=symb, outputsize="full")[0]
    df["symb"] = symb
    df["date"] = df.index
    df["date"][df.shape[0] - 1] = df["date"][df.shape[0] - 1][0:10]
    df.index = range(df.shape[0])
    return df

def compute_coint(mtx):
    mu_mtx = np.zeros((mtx.shape[1], mtx.shape[1]))
    sigma_mtx = np.zeros((mtx.shape[1], mtx.shape[1]))
    for jc in range(mtx.shape[1]):
        for jc_prime in range(mtx.shape[1]):
            coint_vec = mtx[:, jc] - mtx[:, jc_prime]
            mu_mtx[jc, jc_prime] = np.nanmean(coint_vec)
            sigma_mtx[jc, jc_prime] = np.nanstd(coint_vec)
    return list((mu_mtx, sigma_mtx))

def det_signals(t, coint_mu_arr, coint_sig_arr, stk_prices_col, pos_bound, neg_bound, zero_bound=0):
    # if j,i = 1 buy j, if j,i = -1 short j
    buysell_mtx = np.zeros(coint_mu_arr[:, :, 1].shape)
    strngth_mtx = np.zeros(coint_mu_arr[:, :, 1].shape)
    curr_spread = compute_coint(stk_prices_col[t:t + 1].as_matrix())[0]
    for jr in range(coint_mu_arr.shape[0]):
        for jc in range(jr, coint_mu_arr.shape[1]):
            mu = coint_mu_arr[jr, jc, t]
            sigma = coint_sig_arr[jr, jc, t]
            uppr = sigma*pos_bound
            loww = -sigma*neg_bound
            if curr_spread[jr, jc] - mu > uppr:
                buysell_mtx[jr, jc] = -1
                buysell_mtx[jc, jr] = 1
                strngth_mtx[jr, jc] = (curr_spread[jr, jc] - mu) / sigma
                strngth_mtx[jc, jr] = -strngth_mtx[jr, jc]
            elif curr_spread[jr, jc] - mu < loww:
                buysell_mtx[jr, jc] = 1
                buysell_mtx[jc, jr] = -1
                strngth_mtx[jr, jc] = (curr_spread[jr, jc] - mu) / sigma
                strngth_mtx[jc, jr] = -strngth_mtx[jr, jc]
    return list((buysell_mtx, strngth_mtx))

def main(clear_book_yn=0, execute_book_yn=0):
    # Parameters
    print("BEGIN...")
    window = 1000 # coint moving average window
    pos_bound = 1.5 # upper signal bound for coint ts (num std devs)
    neg_bound = 1.5 # lower signal bound for coint ts (num std devs)
    zero_bound = 0.05 # middle near zero bound for coint ts (nums td devs)
    strngth_multi = 5 # Strength multiplier number of contracts
    avapi_key = "E97HKU5JHFSNU7O9"  # Alpha Vantage API Key
    orderID = incr_OrderId(0) # Start order ID count
    portfolio_val = 900000 # Needs to be changed manually
    num_stks = 50

    # Create connection
    app = my_test()
    app.connect("127.0.0.1", 7497, 0)

    # Load and removes all positions from book
    if clear_book_yn & os.path.isfile(dataout_dir + "book.csv"):
        book = pd.read_csv(dataout_dir + "book.csv")
        for js in range(book.shape[0]):
            if book.buysell[js]>0:
                contract = Contract()
                contract.symbol = book.symb[js]
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.currency = "USD"
                contract.primaryExchange = "NASDAQ"
                order = Order()
                order.action = "SELL"
                order.orderType = "MKT"
                order.totalQuantity = book.quantity[js]
                orderID = incr_OrderId(orderID)
                app.placeOrder(orderID, contract, order)
            if book.buysell[js]<0:
                contract = Contract()
                contract.symbol = book.symb[js]
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.currency = "USD"
                contract.primaryExchange = "NASDAQ"
                order = Order()
                order.action = "BUY"
                order.orderType = "MKT"
                order.totalQuantity = book.quantity[js]
                orderID = incr_OrderId(orderID)
                app.placeOrder(orderID, contract, order)
        del book
        print("CLEARED ORDER BOOK...")

    # Pull data from AlphaVantage API
    stk_symbs = pd.read_csv(datain_dir + "nasdaq_symbols.csv", header=None)
    stk_symbs = stk_symbs.sample(num_stks)
    stk_symbs = stk_symbs.values.T.tolist()
    stk_df = pd.concat([clean_alpha_data(i, avapi_key) for i in stk_symbs[0]])
    #stk_df = pd.concat([clean_alpha_data(i, avapi_key) for i in ["HMC", "TM", "F"]]) # FOR TESTING
    stk_prices_col = stk_df.pivot(index='date', columns='symb')['close']
    stk_symbs = list(stk_prices_col.columns.values)
    print("HAS READ DATA IN...")

    # Create moving cointegration matrix (3d array firm_n, firm_n, time_t)
    coint_mu_arr = np.zeros((stk_prices_col.shape[1], stk_prices_col.shape[1], stk_prices_col.shape[0] - window))
    coint_sig_arr = np.zeros((stk_prices_col.shape[1], stk_prices_col.shape[1], stk_prices_col.shape[0] - window))
    for jw in range(stk_prices_col.shape[0] - window):
        beg_idx = jw
        end_idx = jw + window
        coint_mu_arr[:, :, jw], coint_sig_arr[:, :, jw] = compute_coint(stk_prices_col[beg_idx:end_idx].as_matrix())
    print("CREATED COINTEGATION MTX...")

    # Compute signal matrix
    end_t = stk_prices_col.shape[0]-1-window
    buysell_mtx, strngth_mtx = det_signals(end_t, coint_mu_arr, coint_sig_arr, stk_prices_col,
                                           pos_bound, neg_bound, zero_bound)
    print("CREATED SIGNAL MTX...")

    # Create new order book
    cum_buysell = buysell_mtx.sum(1)
    cum_strngth = np.absolute(strngth_mtx.sum(1))
    table = [[i for i in cum_buysell if i!=0], [i for i in cum_strngth if i!=0],
             [stk_symbs[i] for i in range(len(cum_buysell)) if cum_buysell[i] != 0],
             [i/cum_strngth.sum() for i in cum_strngth if i != 0],
             [datetime.datetime.now().strftime("%Y-%m-%d %H:%M") for i in range(len(cum_buysell))
                        if cum_buysell[i]!= 0]]
    book = pd.DataFrame(table).transpose()
    book.columns = ["buysell", "strngth", "symb", "perc_strngth", "date"]
    book = book[book.buysell.notnull()] # removes times when buysell cancel to get 0 but still !=0 in sigma
    book["total_val"] = (book.perc_strngth * portfolio_val).tolist()
    prices = [stk_prices_col[i][end_t] for i in book.symb]
    book["quantity"] = np.floor([book.total_val[i]/prices[i] for i in range(book.shape[0])])

    # Save book
    book.to_csv(dataout_dir + "book.csv", index=False)
    book.to_csv(dataout_dir + datetime.datetime.now().strftime("%Y-%m-%d_") + "book.csv", index=False)
    print("CREATED & SAVED ORDER BOOK...")

    # Execute longs and shorts
    if execute_book_yn:
        for js in range(book.shape[0]):
            if book.buysell[js]>0:
                contract = Contract()
                contract.symbol = book.symb[js]
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.currency = "USD"
                contract.primaryExchange = "NASDAQ"
                order = Order()
                order.action = "BUY"
                order.orderType = "MKT"
                order.totalQuantity = book.quantity[js]
                orderID = incr_OrderId(orderID)
                app.placeOrder(orderID, contract, order)
            if book.buysell[js]<0:
                contract = Contract()
                contract.symbol = book.symb[js]
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.currency = "USD"
                contract.primaryExchange = "NASDAQ"
                order = Order()
                order.action = "SELL"
                order.orderType = "MKT"
                order.totalQuantity = book.quantity[js]
                orderID = incr_OrderId(orderID)
                app.placeOrder(orderID, contract, order)
        app.run()
        print("EXECUTED ORDERS...")
    print("DONE.")

# Main run
if __name__ == "__main__":
    main()
