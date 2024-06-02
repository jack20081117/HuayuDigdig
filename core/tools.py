import random,requests
from datetime import datetime
import numpy as np
import imgkit

from apscheduler.schedulers.background import BackgroundScheduler as bgsc

from globalConfig import chars,imgkit_config

def sigmoid(x:float)->float:return 1/(1+np.exp(-x))

def fromstr(data):
    if isinstance(data,str):
        try:
            realData=eval(data)
            if isinstance(realData,dict) or isinstance(realData,list) or isinstance(realData,tuple):
                data=realData
        except Exception:
            pass
    elif isinstance(data,list) or isinstance(data,tuple):
        data=[fromstr(datum) for datum in data]
    elif isinstance(data,dict):
        for key,value in data:
            data[key]=fromstr(value)
    return data

def tostr(data):
    if isinstance(data,int) or isinstance(data,float):
        return data
    return str(data)

def sqrtmoid(x:float)->float:return 0.25*np.sqrt(x)+0.5

def generate_random_digits(wei:int):
    return "".join(random.choice(chars) for i in wei)

def smart_interval(seconds:float):
    if seconds < 60:
        return "%.2fs" % seconds
    if seconds < 3600:
        return "%.2fmin" % (seconds / 60)
    if seconds < 86400:
        return "%.2fh" % (seconds / 3600)
    return "%.2fd" % (seconds / 86400)

def is_prime(n)->bool:
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

def getnowtime():
    return round(datetime.timestamp(datetime.now()))

def generateTime(timestr:str)->int:
    """
    根据字符串生成秒数
    :param timestr:格式:3min/2h/5d
    :return:对应的秒数
    """
    try:
        if timestr.endswith('min'):
            return int(timestr[:-3])*60
        elif timestr.endswith('h'):
            return int(timestr[:-1])*3600
        elif timestr.endswith('d'):
            return int(timestr[:-1])*86400
        else:
            return 0
    except ValueError:
        return 0

def generateTimeStamp(timestr:str)->int:
    """
    根据字符串生成timestamp
    :param timestr: %Y-%m-%d,%H:%M:%S格式的字符串，如2024-01-01,12:00:00
    :return: 字符串对应的timestamp
    """
    return int(datetime.strptime(timestr,'%Y-%m-%d,%H:%M:%S').timestamp())

def generateTimeStr(timestamp:int)->str:
    """
    根据timestamp生成字符串
    :param timestamp: 一个整数，如1704081600
    :return: timestamp对应的字符串
    """
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d,%H:%M:%S')

def drawtable(data:list,filename:str):
    """
    将市场信息绘制成表格
    :param data: 要绘制的表格数据
    :param filename: 存储图片地址
    :return:
    """

    html='<table>'
    title=data[0]
    markdownStr=0
    html+='<tr>'
    for element in title:
        html+='<th>%s</th>'%element
    html+='</tr>'
    for datum in data[1:]:
        html+='<tr>'
        for element in datum:
            html+='<td>%s</td>'%element
        html+='</tr>'
    html+='</table>'
    imgkit.from_string(html,'../go-cqhttp/data/images/%s'%filename,config=imgkit_config,css='./style.css')

def setInterval(func:callable,interval:int,*args,**kwargs):
    """
    定时触发任务
    :param func: 要触发的任务（函数）
    :param interval: 触发间隔（s）
    :param args: 任务参数
    """
    scheduler=bgsc()
    scheduler.add_job(func,"interval",args=args,kwargs=kwargs,seconds=interval)
    scheduler.start()

def setCrontab(func:callable,*args,**kwargs):
    """
    定时触发任务
    :param func: 要触发的任务（函数）
    :param args: 任务参数
    """
    scheduler=bgsc()
    scheduler.add_job(func,'cron',day_of_week='mon-sun',hour='0-23',minute=0,args=args,kwargs=kwargs)
    scheduler.start()

def setTimeTask(func:callable,runtime:int,*args,**kwargs):
    """
    定时触发任务
    :param func: 要触发的任务（函数）
    :param runtime: 触发时间timestamps
    :param args: 任务参数
    """
    scheduler=bgsc()
    scheduler.add_job(func,"date",args=args,kwargs=kwargs,run_date=datetime.fromtimestamp(float(runtime)))
    scheduler.start()

def send(qid:str,message:str,group=False):
    """
    用于发送消息的函数
    :param qid: 用户id 或 群id
    :param message: 发送的消息
    :param group: 是否为群消息
    :return:none
    """

    if not group:
        # 如果发送的为私聊消息
        params={
            "user_id":qid,
            "message":message,
        }
        _=requests.get("http://127.0.0.1:5700/send_private_msg",params=params)
    else:
        params={
            'group_id':qid,
            "message":message
        }
        _=requests.get("http://127.0.0.1:5700/send_group_msg",params=params)