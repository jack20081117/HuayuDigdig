﻿from flask import Flask,request
from datetime import datetime
from script import handle
from update import init,updateAbundance
from taxes import taxUpdate
from stock import resolveAuction,stockMarketOpen,stockMarketClose
from staticFunctions import setCrontab
from globalConfig import mysql
import globalConfig
import warnings
import signal
warnings.filterwarnings('ignore')

app=Flask(__name__)
level2name = {
    1: "DEBUG",
    2: "INFO",
    3: "WARN",
    4: "ERROR",
    5: "FATAL"
}
def log(mes, level=2):
    timre = datetime.now().strftime("%Y-%m-%d")
    time = datetime.now().strftime("%H:%M:%S")
    with open("./log/%s log.log"%timre, "a") as file:
        file.write("%s %s %s"%(time, level2name[level], mes)+"\r\n")

def shorten(s):
    l = globalConfig.mesLength
    if len(s) >= l:
        s = s.split("\n")[0]
        if s.__len__() >= l:
            s = s[:l]
    return s

init()
globalConfig.stockMarketOpenFlag=True

setCrontab(taxUpdate,hour='23')
setCrontab(updateAbundance,hour='0-23',minute='0,30')
setCrontab(stockMarketOpen, hour='8,13,18', minute='30') #股市开盘
setCrontab(resolveAuction, hour='9,14,19', minute='0', second='0',aggregate=True) #集合竞价结算
setCrontab(resolveAuction, hour='9,14,19', minute='4-56/4', second='0', aggregate=False)
setCrontab(resolveAuction, hour='10-12,15-17,20-22', minute='0-56/4', second='0',aggregate=False)
setCrontab(resolveAuction, hour='13,18,23', minute='0', second='0', aggregate=False,closing=True) # 股市收盘交易
setCrontab(stockMarketClose, hour='13,18,23', minute='0', second='0')  # 股市收盘后勤

@app.route('/',methods=['POST'])
def post():
    # 这里对消息进行分发，暂时先设置一个简单的分发
    res=request.get_json()
    try:
        try:
            message:str=res.get("raw_message")
            qid:str=str(res.get('sender').get('user_id'))  #发消息者的qq号
        except:
            return "KO"
        if res.get('message_type')=='private':  # 说明有好友发送信息过来
            result = handle(res,group=False, message=message,qid=qid)
        elif res.get('message_type')=='group':
            result = handle(res,group=True, message=message,qid=qid)
        else:
            return "KO"
        if message and result:
            log("收到来自%s的消息:%s.回复了:%s"%(qid, shorten(message), shorten(result)))
    except BaseException as err:
        log(str(err), level=4)

    return 'OK'

def shutdownApp(signum, frame):
    from globalConfig import connection
    print('HuayuDigDig 后端正在关闭……')
    connection.close()
    raise SystemExit(0)

if mysql:
    signal.signal(signal.SIGINT, shutdownApp)

if __name__=='__main__':
    app.run("127.0.0.1",port=5701,debug=True)  # 注意，这里的端口要和配置文件中的保持一致