import string
import time
import pyupbit
import datetime
import pandas as pd
import requests
import numpy as np
import os
import pyupbit
from IPython.display import display
from ticker import Tickers

access_key = os.environ['UPBIT_ACCESS_KEY']
secret_key = os.environ['UPBIT_SECRET_KEY']
slack_url = os.environ['UPBIT_SLACK_URL']

tickers = Tickers()


def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=20)

    yesterday_open_price = df.iloc[-1]['open']
    yesterday_close_price = df.iloc[-1]['close']
    yesterday_high_price = df.iloc[-1]['high']
    yesterday_low_price = df.iloc[-1]['low']
    yesterday_diff_high_low = yesterday_high_price - yesterday_low_price

    k = 1 - abs(yesterday_open_price - yesterday_close_price) / \
        yesterday_diff_high_low

    target_price = yesterday_close_price + yesterday_diff_high_low * k
    print('목표 매수가: ', target_price)
    return target_price


def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="minute1", count=1)
    start_time = df.index[0]
    return start_time


def get_ma20(ticker):
    """20일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=20)
    ma20 = df['close'].rolling(window=20, min_periods=1).mean().iloc[-1]
    print('20일 이동 평균선: ', ma20)
    return ma20


def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0


def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]


def sendSlack(message):
    data = {'text': message}
    slackResponse = requests.post(slack_url, json=data)


# 로그인
upbit = pyupbit.Upbit(access_key, secret_key)


def goldencross(symbol):
    url = "https://api.upbit.com/v1/candles/minutes/240"
    querystring = {"market": symbol, "count": "100"}
    response = requests.request("GET", url, params=querystring)
    data = response.json()
    df = pd.DataFrame(data)
    df = df['trade_price'].iloc[::-1]
    ma20 = df.rolling(window=20, min_periods=1).mean()
    ma60 = df.rolling(window=60, min_periods=1).mean()
    test1 = ma20.iloc[-2]-ma60.iloc[-2]
    test2 = ma20.iloc[-1]-ma60.iloc[-1]

    call = '해당없음'

    if test1 > 0 and test2 < 0:
        call = '데드크로스'

    if test1 < 0 and test2 > 0:
        call = '골든크로스'
    print('')
    print(symbol)
    print('이동평균선 20: ', round(ma20.iloc[-1], 2))
    print('이동평균선 60: ', round(ma60.iloc[-1], 2))
    print('골든크로스/데드크로스: ', call)
    return call


for ticker in tickers.TARGETS:
    type = goldencross(ticker)
    try:
        now = datetime.datetime.now()
        start_time = get_start_time(ticker)
        end_time = start_time + datetime.timedelta(days=1)

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price(ticker, 0.5)
            ma20 = get_ma20(ticker)
            current_price = get_current_price(ticker)
            print("현재가: ", current_price)
            if target_price < current_price and ma20 < current_price:
                template_string = string.Template("""
`${ticker}`
- *골든크로스/데드크로스* : `${type}`
- *목표 매수가* : ${target_price}
- *20일 이평선* : ${ma20}
- *현재가* : ${current_price}
                """)
                template_value = {
                    "type": type,
                    "ticker": ticker,
                    "target_price": target_price,
                    "ma20": ma20,
                    "current_price": current_price
                }
                sendSlack(template_string.substitute(template_value))
        time.sleep(1)
    except Exception as e:
        print(e)
        time.sleep(1)
