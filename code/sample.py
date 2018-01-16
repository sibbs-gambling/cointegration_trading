## TEST CODE FOR IB API

## IB API HELPFUL LINK: http://interactivebrokers.github.io/tws-api/index.html#gsc.tab=0

## NOTES
# host --> api address of pc you are using (or remote client)
# TWS must be logged in on machine to work (could not ssh without logging in  on that machine)
# Socket port must be the same as shown in TWS or IBG
# IBG more barebones than TWS
# clientID --> 0 (unsure why)
# 127.0.0.1 00> always self IP Address
# Connect call creates reader thread to send messages back and forth between TWS and API
# app.connect is in client.py file
# ALPHA VANTAGE API KEY: 61780LY8Z8II7LTY
#

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.common import *
from ibapi.utils import iswrapper #just for decorator
from ibapi.contract import *
from ibapi.order import *
#from yahoo_finance import Share
from alpha_vantage.timeseries import TimeSeries
import pandas as pd
import numpy as np

class my_test(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)

    def error(self, reqId:TickerId, errorCode:int, errorString:str):
        print("Error: ", reqId, " " , errorCode, " " , errorString)


def incr_OrderId(curr_OrderId): # NEED TO MAKE PROGRAMMATIC LOOKUP OF IB Order Id last /\/\/\/\/\/\/\/\/
    return curr_OrderId + 1

def main():
    # Create connection
    app = my_test()
    # app.connect(self, host, port, clientId)
    app.connect("127.0.0.1", 7497, 0)

    # Start order ID count
    orderID = incr_OrderId(0)

    # Example function calls
    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.primaryExchange = "NASDAQ"

    order = Order()
    order.action = "BUY"
    order.orderType = "MKT"
    order.totalQuantity = "10"


    app.placeOrder(incr_OrderId(orderID), contract, order)
    app.run()
    # Pull data from AlphaVantage API
    #ts = TimeSeries(key='61780LY8Z8II7LTY', output_format='pandas')
    #symbs = pd.read_csv("../data/clean_in/nyse_symbols.csv")
    #data = ts.get_daily(symbol="AAPL", outputsize="full")
    #print(data)

    #yahoo = Share('YHOO')
    #print(yahoo.get_historical('2014-04-25', '2014-04-29'))



if __name__ == "__main__":
    main()





