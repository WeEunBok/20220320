import time
import pyupbit
import datetime
import sys
import numpy
import pandas as pd
import schedule
from fbprophet import Prophet
import statsmodels.api as sm
import copy

access = "DxApnPFxyA4R81YbyIBMj2nY0NSw097xlFTxY57A"          # 본인 값으로 변경
secret = "cES7idWo8RWkcR1wbAyoS7Pfdcn7H8sspnMphDsK"          # 본인 값으로 변경

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    #2일치 데이터 조회
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    #df.iloc[0]['close'] : 다음날 싯가
    #(df.iloc[0]['high'] - df.iloc[0]['low']) * k : 변동폭
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0

#def get_current_price(ticker):
#    """현재가 조회"""
#    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]

def get_macd(price, slow, fast, smooth):
    exp1 = price.ewm(span = fast, adjust = False).mean()
    exp2 = price.ewm(span = slow, adjust = False).mean()
    macd = pd.DataFrame(exp1 - exp2).rename(columns = {'close':'macd'})
    signal = pd.DataFrame(macd.ewm(span = smooth, adjust = False).mean()).rename(columns = {'macd':'signal'})
    macd_osc = pd.DataFrame(macd['macd'] - signal['signal']).rename(columns = {0:'macd_osc'})
    frames =  [macd, signal, macd_osc]
    df = pd.concat(frames, join = 'inner', axis = 1)
    return df


#로그인
upbit = pyupbit.Upbit(access, secret)
#INPUT 값 받기
#coin = sys.argv[1]
#coin = "ETC"
coin = input('무슨코인?')
#file_name = "REAL_RSI_AI-"+coin+".txt"
#file = open(file_name, 'w')
#file.write("autotrade start \n")
#file.flush()

#my_money = 0
#my_money = get_balance("KRW")
buy_money = 0
krw = 0
rsi_gubun = 0
buy_cnt = 0
#data = "coin : %s \n" % coin
#file.write(data)
#file.flush()

KRW_coin = "KRW-"+coin
#data = "KRW_coin : %s \n" % KRW_coin
#file.write(data)
#file.flush()


#2차원 배열 선얼 [14][30]
#당일 - 전일 상승분 배열
up_arr   = numpy.zeros((187, 14))
#당일 - 전일 하락분 배열
down_arr = numpy.zeros((187, 14))
#1차 배열
#상승분 평균
avg_up   = numpy.zeros((187))
#하락분 평균
avg_down = numpy.zeros((187))
#rsi 상승분 기초데이터
rsi_base_up   = numpy.zeros((187))
#rsi 하락분 기초데이터
rsi_base_down = numpy.zeros((187))
#rsi 계산 최종 데이터
rsi_arr = numpy.zeros(187)


# 자동매매 시작
while True:
    try:
        

        #2차원 배열 선얼 [14][30]
        #당일 - 전일 상승분 배열
        up_arr   = numpy.zeros((187, 14))
        #당일 - 전일 하락분 배열
        down_arr = numpy.zeros((187, 14))
        #1차 배열
        #상승분 평균
        avg_up   = numpy.zeros((187))
        #하락분 평균
        avg_down = numpy.zeros((187))
        #rsi 상승분 기초데이터
        rsi_base_up   = numpy.zeros((187))
        #rsi 하락분 기초데이터
        rsi_base_down = numpy.zeros((187))
        #rsi 계산 최종 데이터
        rsi_arr = numpy.zeros(187)

            
        #1분봉 43개 가지고오기
        minute_ohlcv = pyupbit.get_ohlcv(KRW_coin, interval="minute1", count=200)
        bitcoin_df = copy.deepcopy(minute_ohlcv)

        i = 0
        j = 0
        ##########################################################################
        #rsi start                                                               #
        ##########################################################################
        for i in range(0,187):
            sum_up = 0
            sum_down = 0

            for j in range(0,14):

                if i == 0 and j == 0:
                    up_arr[0][0]   = 0
                    down_arr[0][0] = 0
                else:
                    #등락 계산(T분 종가- T-1분 종가) 배열에 저장
                    if (minute_ohlcv.close[i+j] - minute_ohlcv.close[i+j-1]) >= 0:
                        up_arr[i][j]   =  (minute_ohlcv.close[i+j] - minute_ohlcv.close[i+j-1])
                        down_arr[i][j] = 0
                    else:
                        up_arr[i][j]   = 0
                        down_arr[i][j] = ((minute_ohlcv.close[i+j] - minute_ohlcv.close[i+j-1]) * -1)


                sum_up   += up_arr[i][j]
                sum_down += down_arr[i][j]
            
            #등락 평균
            avg_up[i]    = (sum_up / 14)
            avg_down[i]  = (sum_down / 14)

        for i in range(0,187):
            if i == 0:
                rsi_base_up[i]   = avg_up[i]
                rsi_base_down[i] = avg_down[i]
            else:
                rsi_base_up[i]   = (((rsi_base_up[i-1] * 13  ) + up_arr[i][13]  ) / 14)
                rsi_base_down[i] = (((rsi_base_down[i-1] * 13) + down_arr[i][13]) / 14)

            #RSI = 상승폭 총합 / (상승폭 총합 + 하락폭 총합)
            rsi_arr[i] = (100 * rsi_base_up[i]) /(rsi_base_up[i] + rsi_base_down[i])
        ##########################################################################
        #rsi end                                                                 #
        ##########################################################################

        ##########################################################################
        #prophet start                                                              #
        ##########################################################################


        bitcoin_df = bitcoin_df.reset_index()
        bitcoin_df['day'] = bitcoin_df['index']

        data = bitcoin_df[['day','close']]

        # to_datetime으로 day 피처를 시계열 피처로 변환합니다. 
        data['day'] = pd.to_datetime(data['day'])

        # day 데이터프레임의 index로 설정합니다.
        data.index = data['day']
        data.set_index('day', inplace=True)
        data.head()

        
        prophet = Prophet(seasonality_mode='multiplicative', 
                        yearly_seasonality=True,
                        weekly_seasonality=True, daily_seasonality=True,
                        changepoint_prior_scale=0.5)

        bodyset = list(zip(data.index,data['close']))

        prophet_data = pd.DataFrame(data = bodyset, columns=['ds', 'y'])

        #print(prophet_data)

        prophet.fit(prophet_data)

        future_data = prophet.make_future_dataframe(periods=30, freq='min')

        forecast_data = prophet.predict(future_data)


        ##########################################################################
        #prophet end                                                                #
        ##########################################################################



        # 현재가
        current_price = pyupbit.get_current_price(KRW_coin)
        # 평균단가
        avg_price = upbit.get_avg_buy_price(KRW_coin)
        # 원화잔고
        current_krw = get_balance("KRW")
        
        yhat_avg = (((forecast_data.yhat.values[229] / forecast_data.yhat.values[200]) - 1) * 100)
        
        #data = "now_date : %s %s %s \n" % (datetime.datetime.now(), buy_money, buy_cnt)
        #file.write(data)
        #file.flush()
        #data = "avg : %s prohyat: %s %s \n" % (yhat_avg, forecast_data.yhat.values[200], forecast_data.yhat.values[209])
        #file.write(data)
        #file.flush()
        #data = "rsi : %s / %s / %s \n" % (rsi_arr[186], rsi_arr[185], rsi_arr[184])
        
        #file.write(data)
        #file.flush()


        
        if avg_price == 0:
            krw = 0
            rsi_gubun = 0
        elif avg_price != 0 and rsi_gubun == 0:
            krw = 20000
            rsi_gubun = -1
        
        if krw == 0:
            if ((rsi_arr[185] <= 40 or rsi_arr[186] <= 40)) and (yhat_avg >= 1):
                krw = current_krw / 100
                #krw = 10000
                if krw > 5000:
                #if current_krw >= krw:
                    upbit.buy_market_order(KRW_coin, krw*0.9995) # 비트코인 매수
                #data = "now_date : %s --- BUY_COIN!! : %s \n" % (datetime.datetime.now(), current_price)
                #file.write(data)
                #file.flush()
                rsi_gubun = -1

        if krw != 0:
            if ((((current_price / avg_price) - 1) * 100) >= 1):
                coin_price = get_balance(coin)
                upbit.sell_market_order(KRW_coin, coin_price) # 비트코인 전량 매도
                #data = "now_date : %s --- SELL_COIN! : %s BUY_MONEY : %s\n" % (datetime.datetime.now(), current_price, buy_money)
                #file.write(data)
                #file.flush()
                krw = 0
                rsi_gubun = 0
        
        
        if krw != 0 and rsi_arr[186] < 40 and (rsi_arr[184] - rsi_arr[185]) < 0 and (rsi_arr[185] - rsi_arr[186]) >= 0 and (yhat_avg >= 1):
            #로그인찍기위함
            if krw > 5000:
                upbit.buy_market_order(KRW_coin, krw*0.9995) # 비트코인 매수
            #data = "now_date : %s --- BUY_COIN2! : %s BUY_MONEY : %s rsi : %s \n" % (datetime.datetime.now(), current_price, buy_money, rsi_arr[186])
            #file.write(data)
            #file.flush()
            rsi_gubun = -1
                

        time.sleep(5)
    except Exception as e:
        print(e)
        #file.close()
        time.sleep(30)