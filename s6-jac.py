#cnfg, tmp folders required
#runs on python3 32 bit. if switching to 64 use appropriate instantclient library

skip_kite=False

#false is for buy, change to true for sell
direction_switch=True



#[imports]
import logging
from kiteconnect import KiteTicker, KiteConnect
import pandas as pd
from datetime import datetime, date
from multiprocessing import Process, Queue
import time
import sqlalchemy as sa
from flask import Flask, request, jsonify, session
import random
import math
import requests
import os
from selenium import webdriver
from decimal import Decimal
import json
import configparser
from timeit import default_timer as timer


#[external paths]
loc_log_file='../tmp/s3.log'
config_file='../cnfg/db.ini'
chromedriver_file='../cnfg/chromedriver.exe'
access_token_A_file='../tmp/access_token_A.txt'
#access_token_B_file='../tmp/access_token_B.txt'
os.environ['PATH']='c:\\instantclient_19_5_x32'

#[logging config]
logging.getLogger('schedule').propagate = False
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(processName)-12.12s] [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    handlers=[
    logging.FileHandler(loc_log_file),
    logging.StreamHandler()
    ])

#logging.info('starting script s3.py')

config = configparser.ConfigParser()
config.read(config_file)

#[db config]

db_username=config['DB']['algoinvest_user']
db_password=config['DB']['algoinvest_pass']
db_host=config['DB']['algoinvest_host']
db_port=config['DB']['algoinvest_port']
db_database=config['DB']['algoinvest_service']
db_schema=db_username

#[dataframe config]
df=pd.DataFrame(columns=['instrument_token','zid','x','ltp','buy','sell','high','low','action','pBase','pExec','v','v2','qty','sl','id_a_buy','id_a_sell', 'profit', 'skip','rank','rank2'])
df=df.set_index('instrument_token')
df['instrument_token']=[5633,6401,3861249,4451329,25601,325121,40193,41729,54273,60417,1510401,4267265,4268801,81153,85761,1195009,94977,98049,103425,108033,2714625,112129,2911489,558337,134657,140033,2029825,2763265,320001,160001,160769,175361,177665,5215745,3876097,1215745,486657,197633,2800641,3771393,225537,232961,4314113,245249,173057,261889,1207553,1895937,2585345,315393,2513665,1850625,340481,341249,345089,2747905,348929,359937,356865,1270529,4774913,2863105,2883073,1346049,408065,415745,424961,1723649,3001089,4632577,492033,6386689,511233,2939649,2672641,519937,3400961,4879617,1041153,2815745,2674433,548353,4488705,3675137,1076225,582913,6054401,1629185,8042241,593665,4598529,2955009,3924993,2977281,4464129,633601,681985,3834113,3365633,523009,3930881,738561,758529,779521,794369,806401,837889,857857,3431425,871681,873217,884737,4343041,877057,895745,2953217,3465729,897537,900609,3529217,2170625,4278529,4369665,2952193,2889473,784129,951809,969473]
df['zid']=['ACC','ADANIENT','ADANIPORTS','ADANIPOWER','AMARAJABAT','AMBUJACEM','APOLLOHOSP','APOLLOTYRE','ASHOKLEY','ASIANPAINT','AXISBANK','BAJAJ-AUTO','BAJAJFINSV','BAJFINANCE','BALKRISIND','BANKBARODA','BATAINDIA','BEL','BERGEPAINT','BHARATFORG','BHARTIARTL','BHEL','BIOCON','BOSCHLTD','BPCL','BRITANNIA','CADILAHC','CANBK','CASTROLIND','CENTURYTEX','CESC','CHOLAFIN','CIPLA','COALINDIA','COLPAL','CONCOR','CUMMINSIND','DABUR','DIVISLAB','DLF','DRREDDY','EICHERMOT','EQUITAS','ESCORTS','EXIDEIND','FEDERALBNK','GAIL','GLENMARK','GODREJCP','GRASIM','HAVELLS','HCLTECH','HDFC','HDFCBANK','HEROMOTOCO','HEXAWARE','HINDALCO','HINDPETRO','HINDUNILVR','ICICIBANK','ICICIPRULI','IDFCFIRSTB','IGL','INDUSINDBK','INFY','IOC','ITC','JINDALSTEL','JSWSTEEL','JUBLFOOD','KOTAKBANK','L&TFH','LICHSGFIN','LT','LUPIN','M&M','M&MFIN','MANAPPURAM','MARICO','MARUTI','MCDOWELL-N','MFSL','MGL','MINDTREE','MOTHERSUMI','MRF','MUTHOOTFIN','NATIONALUM','NBCC','NCC','NESTLEIND','NIITTECH','NMDC','NTPC','OIL','ONGC','PIDILITIND','POWERGRID','PVR','RAMCOCEM','RECLTD','RELIANCE','SAIL','SBIN','SHREECEM','SIEMENS','SRF','SUNPHARMA','SUNTV','TATACHEM','TATAELXSI','TATAMOTORS','TATAMTRDVR','TATAPOWER','TATASTEEL','TCS','TECHM','TITAN','TORNTPHARM','TORNTPOWER','TVSMOTOR','UBL','UJJIVAN','ULTRACEMCO','UPL','VEDL','VOLTAS','WIPRO']
#[app config]
stockCount=20


#[flask config]
flask_port=8080
flask_host='localhost'
serializer=lambda obj: isinstance(obj, (date, datetime, Decimal)) and str(obj)  # noqa
#redirect_url='http://{host}:{port}/login'.format(host=flask_host, port=flask_port)
#login_url='https://api.kite.trade/connect/login?api_key={api_key}'.format(api_key=kite_api_key)
#console_url='https://developers.kite.trade/apps/{api_key}'.format(api_key=kite_api_key)
app=Flask(__name__)
app.secret_key=os.urandom(24)
login_template= """
                <!--<meta http-equiv="refresh" content="0; url=http://localhost:80/zloginsuccess.php?u={user_id}" />-->
                <p><a href="http://localhost:80/zloginsuccess.php?u={user_id}">Redirect</a></p>
                <h2 style="color: green">Success</h2>
                <div>Access token: <b>{access_token}</b></div>
                <h4>User login data</h4>
                <pre>{user_data}</pre>
                """

#login flask app

def getKiteClient(kite_api_key):
    kite=KiteConnect(api_key=kite_api_key)
    if "access_token" in session:
        kite.set_access_token(session["access_token"])
    return kite

@app.route("/login")
def loginKite():
    request_token=request.args.get("request_token")
    if not request_token:
        return  """
                Error while generating request token
                """

    if os.stat(access_token_A_file).st_size == 0 :
        kite=getKiteClient(api_key_A)
        data=kite.generate_session(request_token, api_secret=api_secret_A)
        session["access_token"]=data["access_token"]
        access_token = data["access_token"]
        with open(access_token_A_file, 'w') as the_file:
            the_file.write(access_token)
    elif os.stat(access_token_B_file).st_size == 0 :
        kite=getKiteClient(api_key_B)
        data=kite.generate_session(request_token, api_secret=api_secret_B)
        session["access_token"]=data["access_token"]
        access_token = data["access_token"]
        with open(access_token_B_file, 'w') as the_file:
            the_file.write(access_token)

    return login_template.format(
        access_token=data["access_token"],
        user_id = data["user_id"],
        user_data=json.dumps(
            data,
            indent=4,
            sort_keys=True,
            default=serializer
        )
    )


@app.route("/ticks")
def ticks():
    return f"""<meta http-equiv="refresh" content="2" >
                {df.to_json(orient='records')}
            """

#kite login multiprocessing workflow functions

def jobLoginListen(q=None):
    logging.info('starting login listener')
    while True:
        msg = q.get()
        if msg == 'DONE':
            break
        time.sleep(0.1)

def jobSpawnFlaskTicker1():
    logging.info('spawning flask ticker web server')
    app.run(host=flask_host, port=8081, debug=True, use_reloader=False)

def jobSpawnFlaskServer(q=None):
    logging.info('spawning flask login web server')
    app.run(host=flask_host, port=flask_port, debug=True, use_reloader=False)

def jobLoginSelenium(user,kite_api_key,kite_username,kite_password,kite_pin,q=None):
    logging.info('logging in to kite-investmento')
    driver = webdriver.Chrome(chromedriver_file)
    login_url = f'https://kite.trade/connect/login?v=3&api_key={kite_api_key}'
    driver.get(login_url)
    time.sleep(.5)
    username = driver.find_element_by_css_selector('#container > div > div > div.login-form > form > div.uppercase.su-input-group > input[type=text]')
    username.send_keys(kite_username)
    password = driver.find_element_by_css_selector('#container > div > div > div.login-form > form > div:nth-child(2) > input[type=password]')
    password.send_keys(kite_password)
    login_box = driver.find_element_by_css_selector('#container > div > div > div.login-form > form > div.actions > button')
    login_box.click()
    time.sleep(.5)
    q1 = driver.find_element_by_css_selector('#container > div > div > div.login-form > form > div:nth-child(2) > div > input[type=password]')
    q1.send_keys(kite_pin)
    login_box = driver.find_element_by_css_selector('#container > div > div > div.login-form > form > div.actions > button')
    login_box.click()
    time.sleep(2)
    driver.close()
    time.sleep(1)
    logging.info(f'sending flag for user {kite_username} to login listner queue')
    q.put(f'DONE')

def jobLoginMultiprocessing():
    logging.info('starting multiprocessing login workflow')
    open(access_token_A_file, 'w').close()
    #open(access_token_B_file, 'w').close()

    q1 = Queue()
    p1A = Process(target=jobLoginListen, args=(q1,))
    #p1B = Process(target=jobLoginListen, args=(q1,))
    p2 = Process(target=jobSpawnFlaskServer, args=(q1,))
    p3A = Process(target=jobLoginSelenium, args=('A',api_key_A,kite_username_A,kite_password_A,kite_pin_A,q1))
    #p3B = Process(target=jobLoginSelenium, args=('B',api_key_B,kite_username_B,kite_password_B,kite_pin_B,q1))
    p2.start()
    time.sleep(3)
#user A login
    p1A.start()
    p3A.start()
#waiting for listner to end
    p1A.join()
#loading access token for A to memory
    global access_token_A
    access_token_A=ReadAccessTokenFile(access_token_A_file)
    p1A.terminate()
    logging.info(f'access_token_A set as {access_token_A} ,closing login listner')
    p3A.terminate()
#user B login
    #p1B.start()
    #p3B.start()
#waiting for listner to end
    #p1B.join()
#loading access token for B to memory
    #global access_token_B
    #access_token_B=ReadAccessTokenFile(access_token_B_file)
    #p1B.terminate()
    #logging.info(f'access_token_B set as {access_token_B} ,closing login listner')
    #p3B.terminate()

    p2.terminate()
    logging.info('access keys acquired, closing flask login web server')
    logging.info('multiprocessing login workflow complete')

def ReadAccessTokenFile(file_name):
    for line in open(file_name, 'r'):
        access_token = line
        break
    return str(access_token)

#program

def getMarginX(df):

    response = requests.get('https://api.kite.trade/margins/equity')
    x = response.json()
    for i in x:
        df.loc[df['zid'] == i['tradingsymbol'], 'x'] = i['mis_multiplier']
    getMarginX=df


def jobReconnect(silent=0):
    if silent==0:
        logging.info('checking connection to database')
    global oracle_db
    oracle_db = sa.create_engine(f'oracle://{db_username}:{db_password}@{db_host}:{db_port}/{db_database}', max_identifier_length=128,pool_pre_ping=True)
    global con
    con = oracle_db.connect()


def jobUpdateDB(df,q=None,silent=0):
    if silent==0:
        logging.info('startng db table update')
    jobReconnect(1)
    df.to_sql('s3stockmaster', con, schema=db_schema, if_exists='replace',dtype={'instrument_token': sa.types.INTEGER(), 'zid': sa.types.NVARCHAR(50), 'x': sa.types.INTEGER(), 'ltp': sa.types.FLOAT(), 'action': sa.types.NVARCHAR(50), 'pBase': sa.types.FLOAT(), 'p0805': sa.types.FLOAT(), 'pExec': sa.types.FLOAT(), 'v': sa.types.FLOAT(), 'qty': sa.types.FLOAT(), 'ltp': sa.types.FLOAT(), 'id_a_buy': sa.types.INTEGER(), 'id_a_sell': sa.types.INTEGER(), 'profit': sa.types.FLOAT(), 'skip': sa.types.INTEGER(),}, index=False)
    if silent==0:
        logging.info('db table update complete')
    if q==None:
        pass
    else:
        q.put(1)


def jobImportDB():
    logging.info('startng db table import')
    jobReconnect()
    df=pd.read_sql_table('s3stockmaster', con, schema=db_schema)
    logging.info('db table import complete')
    return df


def checkExecutionStatus(api_key,access_token,order_id):
    headers={'X-Kite-Version': '3','Authorization': f'token {api_key}:{access_token}'}
    s=f'https://api.kite.trade/orders/{order_id}'
    response = requests.get(s, headers=headers)
    response = response.json()
    #sample --- {'placed_by': 'OO4828', 'order_id': '200309000328522', 'exchange_order_id': '1200000000454537', 'parent_order_id': None, 'status': 'COMPLETE', 'status_message': None, 'status_message_raw': None, 'order_timestamp': '2020-03-09 09:20:12', 'exchange_update_timestamp': '2020-03-09 09:20:12', 'exchange_timestamp': '2020-03-09 09:20:09', 'variety': 'regular', 'exchange': 'NSE', 'tradingsymbol': 'ONGC', 'instrument_token': 633601, 'order_type': 'LIMIT', 'transaction_type': 'SELL', 'validity': 'DAY', 'product': 'MIS', 'quantity': 1557, 'disclosed_quantity': 0, 'price': 80.5, 'trigger_price': 0, 'average_price': 80.5, 'filled_quantity': 1557, 'pending_quantity': 0, 'cancelled_quantity': 0, 'market_protection': 0, 'meta': {}, 'tag': None, 'guid': '15730XsGY1KigUhSSd'}
    x=response['data'][len(response['data'])-1]['status']
    #print(x)
    return x



def placeMarketOrder(api_key,access_token,ttype,symbol,qty):
    headers={'X-Kite-Version': '3','Authorization': f'token {api_key}:{access_token}'}
    data = {
      'tradingsymbol': f'{symbol}',
      'exchange': 'NSE',
      'transaction_type': f'{ttype}',
      'order_type': 'MARKET',
      'quantity': f'{qty}',
      'product': 'MIS',
      'validity': 'DAY'
    }
    response = requests.post('https://api.kite.trade/orders/regular', headers=headers, data=data)
    response = response.json()
    return int(response['data']['order_id']) if response['status']=='success' else -1



def placeLimitOrder(api_key,access_token,ttype,symbol,qty,price):
    headers={'X-Kite-Version': '3','Authorization': f'token {api_key}:{access_token}'}
    data = {
      'tradingsymbol': f'{symbol}',
      'exchange': 'NSE',
      'transaction_type': f'{ttype}',
      'order_type': 'LIMIT',
      'price': f'{price}',
      'quantity': f'{qty}',
      'product': 'MIS',
      'validity': 'DAY'
    }
    response = requests.post('https://api.kite.trade/orders/regular', headers=headers, data=data)
    response = response.json()
    return int(response['data']['order_id']) if response['status']=='success' else -1


def cancelLimitOrder(api_key,access_token,ttype,symbol,qty,price):
    headers={'X-Kite-Version': '3','Authorization': f'token {api_key}:{access_token}'}
    data = {
      'tradingsymbol': f'{symbol}',
      'exchange': 'NSE',
      'transaction_type': f'{ttype}',
      'order_type': 'LIMIT',
      'price': f'{price}',
      'quantity': f'{qty}',
      'product': 'MIS',
      'validity': 'DAY'
    }
    response = requests.post('https://api.kite.trade/orders/regular', headers=headers, data=data)
    response = response.json()
    return int(response['data']['order_id']) if response['status']=='success' else -1


def jobPositionWatcher(q,df):
    logging.info('watching df on RAM')

    #df['currProfit']=(df['ltp']-df['pExec'])*df['qty']
    #df['orderAmt'] = df['qty']*df['pExec']/df['x']
    #df['slR']=1.005*df['pExec']
    #df['slF']=0.995*df['pExec']

#A for first Buy and B for first sell
    for index, row in df.iterrows():
        if row['action']=='hitR':
            if skip_kite==False:
                row['id_b_buy']=placeLimitOrder(api_key_B,access_token_B,'BUY',row['zid'],row['qty'],row['ltp'])
                row['action']='runA'
            logging.info(f"kite order [ {row['zid']} - {row['qty']} - {row['ltp']} ]")
        elif row['action']=='hitF':
            if skip_kite==False:
                row['id_a_sell']=placeLimitOrder(api_key_A,access_token_A,'SELL',row['zid'],row['qty'],row['ltp'])
            logging.info(f"kite order [ {row['zid']} - {row['qty']} - {row['ltp']} ]")
        elif row['action']=='closeA':
            if skip_kite==False:
                row['id_a_sell']=placeLimitOrder(api_key_A,access_token_A,'SELL',row['zid'],row['qty'],row['ltp'])
            logging.info(f"kite order [ {row['zid']} - {row['qty']} - {row['ltp']} ]")
        elif row['action']=='closeB':
            if skip_kite==False:
                row['id_b_buy']=placeLimitOrder(api_key_B,access_token_B,'SELL',row['zid'],row['qty'],row['ltp'])
                row['action']='runA'
            logging.info(f"kite order [ {row['zid']} - {row['qty']} - {row['ltp']} ]")

    #df['curP'] = df['x']*(df['ltp']-df['pExec'])/df['pExec']



def on_ticks(ws, ticks):
    for tick in ticks:
         df.loc[df.instrument_token == tick['instrument_token'], ['ltp','buy','sell','high','low'],] = [tick['last_price'],tick['buy_quantity'],tick['sell_quantity'],tick['ohlc']['high'],tick['ohlc']['low']]
        #logic
        #df.loc[(df.ltp > 1.005*df['pExec']), ['action','sl']] = 'hitR',df['pExec']
        #df.loc[(df.ltp < 0.995*df['pExec']), ['action','sl']] = 'hitF',df['pExec']

    #os.system("cls")
    #pd.set_option('display.max_rows', len(df))
    #print(df)
    #all_ticks.extend(ticks)

def on_connect(ws, response):
    logging.info('kite websocket subscribe flag')
    ws.subscribe([5633,6401,3861249,4451329,25601,325121,40193,41729,54273,60417,1510401,4267265,4268801,81153,85761,1195009,94977,98049,103425,108033,2714625,112129,2911489,558337,134657,140033,2029825,2763265,320001,160001,160769,175361,177665,5215745,3876097,1215745,486657,197633,2800641,3771393,225537,232961,4314113,245249,173057,261889,1207553,1895937,2585345,315393,2513665,1850625,340481,341249,345089,2747905,348929,359937,356865,1270529,4774913,2863105,2883073,1346049,408065,415745,424961,1723649,3001089,4632577,492033,6386689,511233,2939649,2672641,519937,3400961,4879617,1041153,2815745,2674433,548353,4488705,3675137,1076225,582913,6054401,1629185,8042241,593665,4598529,2955009,3924993,2977281,4464129,633601,681985,3834113,3365633,523009,3930881,738561,758529,779521,794369,806401,837889,857857,3431425,871681,873217,884737,4343041,877057,895745,2953217,3465729,897537,900609,3529217,2170625,4278529,4369665,2952193,2889473,784129,951809,969473])

def on_close(ws, code, reason):
    logging.info('kite websocket connection closed, attempting reconnect')
    # doesnt work ws.reconnect()


def startTicker(q):

    logging.info('starting threaded websocket connection, loading initial state')
   
    # Initialise
    global access_token_A
    access_token_A=ReadAccessTokenFile(access_token_A_file)
    #global access_token_B
    #access_token_B=ReadAccessTokenFile(access_token_B_file)
    global kws
    kws = KiteTicker(api_key_A,access_token_A)

    #setting queue for DB update
    qDB = Queue()

    #put df in queue
    #jobReconnect()
    global df
    #if oracle_db.dialect.has_table(oracle_db, 's3stockmaster'):
    #    df=jobImportDB()
    #    logging.info('putting db imported dataframe in multiprocessing queue on RAM')
    #    q.put(df)
    #else:
    #    pass
    #    print('does not exist')

    qDB.put(1)

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close
    kws.connect(threaded=True)

    flagMargin=False
    flagStartOver=False

    counterStockTick=0

    df['profit'] = 0
    df['rank'] = 0
    df['rank2'] = 0
    df['loser'] = 0
    df['skip'] = 0
    df['buy'] = 0
    df['sell'] = 0
    df['high'] = 0
    df['low'] = 0
    #t = timer()

    global df_original
    df_original = df

    while True:

#index and make changes in a copy of df called df_calc
        df_calc=df
        df_calc = df_calc.set_index('instrument_token')

#traverse dataframe
        for index, row in df_calc.iterrows():

#set base buy and sell quantity
            if df_calc.loc[index,'action']=='BaseSet':
                pass

#identify the stock to be traded
            elif df_calc.loc[index,'action']=='StockSelect':

                if df_calc.loc[index,'rank']==1 and df_calc.loc[index,'v']>=2:
                    df_calc.at[index,'qty']= math.floor(344/df_calc.loc[index,'ltp']*df_calc.loc[index,'x'])
                    df_calc.at[index,'action']='Start'
                elif df_calc.loc[index,'rank']==1 and df_calc.loc[index,'v']<2:
                    flagStartOver=True

#place order on zerodha for the selected trade
            elif df_calc.loc[index,'action']=='Start':

                if skip_kite==False:
                    if direction_switch == True:
                        df_calc.at[index,'id_a_sell']=placeMarketOrder(api_key_A,access_token_A,'SELL',df_calc.loc[index,'zid'],df_calc.loc[index,'qty'])
                        df_calc.at[index,'sl']=1.003*df_calc.loc[index,'ltp']
                    else:
                        df_calc.at[index,'id_a_buy']=placeMarketOrder(api_key_A,access_token_A,'BUY',df_calc.loc[index,'zid'],df_calc.loc[index,'qty'])
                        df_calc.at[index,'sl']=0.997*df_calc.loc[index,'ltp']
                    
                    df_calc.at[index,'action']='VerifyStart'
                df_calc.at[index,'pExec']=df_calc.loc[index,'ltp']

#verify if the initial zerodha order is completed
            elif df_calc.loc[index,'action']=='VerifyStart':

                if skip_kite==False:
                    if direction_switch == True:
                        status=checkExecutionStatus(api_key_A,access_token_A,df_calc.loc[index,'id_a_sell'])
                        if status == "COMPLETE":
                            df_calc.at[index,'id_a_buy']=placeLimitOrder(api_key_A,access_token_A,'BUY',df_calc.loc[index,'zid'],df_calc.loc[index,'qty'],round(0.997*df_calc.loc[index,'ltp'],1))
                            df_calc.at[index,'action']='RunTrade'
                        elif status == "REJECTED":
                            df_calc.at[index,'action']='FatalError'
                    else:
                        status=checkExecutionStatus(api_key_A,access_token_A,df_calc.loc[index,'id_a_buy'])
                        if status == "COMPLETE":
                            df_calc.at[index,'id_a_sell']=placeLimitOrder(api_key_A,access_token_A,'SELL',df_calc.loc[index,'zid'],df_calc.loc[index,'qty'],round(1.003*df_calc.loc[index,'ltp'],1))
                            df_calc.at[index,'action']='RunTrade'
                        elif status == "REJECTED":
                            df_calc.at[index,'action']='FatalError'
                else:
                    df_calc.at[index,'action']='RunTrade'


            elif df_calc.loc[index,'action']=='ExitManual':
                pass

#verify if the closing zerodha order is completed
            elif df_calc.loc[index,'action']=='RunTrade':

                if skip_kite==False:
                    
                    slflag = 0

                    if direction_switch == True:
                        if df_calc.loc[index,'ltp']>df_calc.loc[index,'sl']:
                            #df_calc.at[index,'id_a_buy']=placeMarketOrder(api_key_A,access_token_A,'BUY',df_calc.loc[index,'zid'],df_calc.loc[index,'qty'])
                            #df_calc.at[index,'action']='TradeComplete'
                            df_calc.at[index,'action']='ExitManual'
                            slflag = 1
                    else:
                        if df_calc.loc[index,'ltp']<df_calc.loc[index,'sl']:
                            #df_calc.at[index,'id_a_sell']=placeMarketOrder(api_key_A,access_token_A,'SELL',df_calc.loc[index,'zid'],df_calc.loc[index,'qty'])
                            #df_calc.at[index,'action']='TradeComplete'
                            df_calc.at[index,'action']='ExitManual'
                            slflag = 1

                    if slflag == 0:

                        if direction_switch == True:
                            status=checkExecutionStatus(api_key_A,access_token_A,df_calc.loc[index,'id_a_buy'])
                        else:
                            status=checkExecutionStatus(api_key_A,access_token_A,df_calc.loc[index,'id_a_sell'])
                        if status == "COMPLETE":
                            df_calc.at[index,'action']='TradeComplete'
                        elif status == "REJECTED":
                            df_calc.at[index,'action']='FatalError'

                else:
                    df_calc.at[index,'action']='TradeComplete'

#trade completed on zerodha, start over
            elif df_calc.loc[index,'action']=='TradeComplete':
                df_calc.at[index,'skip']=0 #skip 1 to prevent repetition of stock
                flagStartOver=True

            elif df_calc.loc[index,'action']=='FatalError':
                df_calc.at[index,'skip']=1
                #df_calc.at[index,'action']='StockSelect'

            else:
                if df_calc.loc[index,'ltp'] > 0.1:
                    df_calc.at[index,'pBase']= df_calc.loc[index,'ltp']
                    df_calc.at[index,'action']='BaseSet'
                    counterStockTick+=1
                else:
                    if counterStockTick > 100:
                        df_calc.at[index,'action']='BaseSet'
                    else:
                        df_calc.at[index,'action']='Waiting'
        
        #if all action status is the same -- steps for global changes
        if df_calc.action.nunique() == 1:
            if 'StockSelect' in df_calc.values:

                #filter out stocks
                df_calc= df_calc[df_calc.skip == 0]
                df_calc= df_calc[df_calc.buy > 10]
                df_calc= df_calc[df_calc.sell > 10]
                df_calc= df_calc[df_calc.high > 10]
                df_calc= df_calc[df_calc.low > 10]
                df_calc= df_calc[df_calc.ltp < 1000]
                df_calc= df_calc[df_calc.x > 1]

                #calculate volatility and rank
                if direction_switch == True:
                    df_calc['v'] =  df_calc['sell']/df_calc['buy']
                    df_calc['v2'] = (df_calc['ltp']-df_calc['low'])/(df_calc['high']-df_calc['low'])
                else:
                    df_calc['v'] =  df_calc['buy']/df_calc['sell']
                    df_calc['v2'] = (df_calc['high']-df_calc['ltp'])/(df_calc['high']-df_calc['low'])
                
                df_calc= df_calc[df_calc.v2 > 0.5]
                
                df_calc['rank'] = df_calc['v'].rank(ascending=False)
                df_calc['rank2'] = df_calc['v2'].rank(ascending=False)
            
            elif 'BaseSet' in df_calc.values:
                #set values to prevent error
                df_calc.loc[df_calc['sell']==0, 'sell'] += 1
                df_calc.loc[df_calc['buy']==0, 'buy'] += 1

                #t = timer()
                if flagMargin == False:
                    if 12.5 in df_calc.values:
                        pass
                    else:
                        getMarginX(df_calc)
                        df_original = df_original.set_index('instrument_token')
                        df_original = df_calc
                        df_original = df_original.reset_index()
                        flagMargin = True
                df_calc['action'] = 'StockSelect'


        df_calc = df_calc.reset_index()

        df=df_calc

        if flagStartOver == True:
            counterStockTick=0
            df = df_original
            flagStartOver=False

        os.system("cls")
        #pd.set_option('display.max_rows', len(df_calc))
        if direction_switch == True:
            print('Direction: Sell -> Buy')
        else:
            print('Direction: Buy -> Sell')
        print(f'Stock count: {df.shape[0]}')
        print(df.nsmallest(5, 'rank'))

        if qDB.qsize()==1:
            qDB.get()
            #pDB = Process(target=jobUpdateDB, args=(df_calc,qDB,1))
            #pDB.start()
        #else:
            #logging.info('dataframe updated on RAM only, skipping DB write')

        #q.put(df_calc)

        time.sleep(.2)


if __name__ == "__main__":

#start the program by logging in to kite
    #jobLoginMultiprocessing()
    #time.sleep(2)

#to display ticks dataframe on localhost:8081/ticks
    #pTicker = Process(target=jobSpawnFlaskTicker1)
    #pTicker.start()

#start ticker
    q = Queue()
    p = Process(target=startTicker, args=(q,))
    p.start()