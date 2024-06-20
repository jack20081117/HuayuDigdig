import random,requests
from datetime import datetime
import numpy as np
import imgkit
import math

import model
import globalConfig

from apscheduler.schedulers.background import BackgroundScheduler as bgsc
from hashlib import md5

def sigmoid(x:float)->float:return 1/(1+np.exp(-x))

digest = lambda s: md5(s.encode('ascii')).hexdigest()

def prime_sieve(n):
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    for p in range(2, math.isqrt(n) + 1):
        if is_prime[p]:
            for k in range(p * p, n + 1, p):
                is_prime[k] = False
    return [p for p in range(2, n + 1) if is_prime[p]]

def factors(n):
    prime_factors = []
    for p in prime_sieve(math.isqrt(n)):
        while n % p == 0:
            prime_factors.append(p)
            n //= p
        if n == 1:
            break
    if n > 1:
        prime_factors.append(n)
    factors = [1]
    for p in prime_factors:
        factors += [f * p for f in factors]
    return set(prime_factors),factors

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

def sqrtmoid(x:float)->float:
    return 0.25*np.sqrt(x)+0.5

def generate_random_digits(wei:int):
    return "".join(random.choice(globalConfig.chars) for i in wei)

def smartInterval(seconds:float):
    if seconds < 60:
        return "%.2fs" % seconds
    if seconds < 3600:
        return "%.2fmin" % (seconds / 60)
    if seconds < 86400:
        return "%.2fh" % (seconds / 3600)
    return "%.2fd" % (seconds / 86400)

def isPrime(n)->bool:
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

def indicators(schoolID:str)->list[int]:
    if len(schoolID) == 5:
        return [int(schoolID), int(schoolID[:3]),int(schoolID[2:]),
                int(schoolID[:2]+'0'+schoolID[2:])]
    elif len(schoolID) == 6:
        return [int(schoolID), int(schoolID[:4]), int(schoolID[2:])]
    elif len(schoolID) == 8:
        return [int(schoolID[2:]), int(schoolID[:2]), int(schoolID[4:])]
    return []

def exchangeable(qid:str,ore:int)->bool:
    indicator = indicators(qid)
    flag = False
    for i in indicator:
        flag = flag or not i%ore
    return flag

def tech_validator(tech_type:str, path:list[int], sid:str):
    method_string = tech_type
    determinant = 0
    validated_levels = 0
    for i in range(len(path)):
        tech_level = i + 1

        class_buff = '%s+%s' % (indicators(sid)[1], path[i])
        specific_buff = '%s+%s' % (sid, path[i])
        modifier = (int(digest(specific_buff)[-2:], 16) + int(digest(class_buff)[-2:], 16) - 256) / 2048

        determinant = round(determinant * 0.5 + path[i] * 0.5)

        prob = max(min(0.25 * np.log(determinant) / (4+np.log(tech_level)),
                       determinant / (256 * tech_level)) + modifier, 0)
        method_string = '%s+%s' % (method_string, path[i])
        indicator = int(digest(method_string)[-3:], 16)

        if not indicator + modifier <= round(4096 * prob):
            break
        else:
            validated_levels += 1

    return validated_levels

def mineExpectation(lower:int,upper:int,logUniform=False)->float:
    """
    矿井开采出矿石的期望值
    :param lower: 矿井矿石取值范围下界
    :param upper: 矿井矿石取值范围上界
    :param logUniform: 是否采用对数平均
    :return: 开采出矿石的期望值
    """
    if logUniform:
        return (upper-lower)/np.log(upper/lower)
    else:
        return (lower+upper)/2

def mineralSample(lower,upper,logUniform=False)->int:
    """
    开采矿井
    :param lower: 矿井矿石取值范围下界
    :param upper: 矿井矿石取值范围上界
    :param logUniform: 是否采用对数平均
    :return: 开采出的矿石
    """
    if logUniform:
        return int(np.exp(np.random.randint(int(np.log(lower)*1000),int(np.log(upper)*1000))/1000))
    else:
        return np.random.randint(lower,upper)

def getnowtime()->int:
    """
    生成当前时间timestamp
    """
    return round(datetime.timestamp(datetime.now()))

def getnowdate()->int:
    """
    生成当前日期timestamp
    """
    return getnowtime()//86400*86400

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
    imgkit.from_string(html,'../go-cqhttp/data/images/%s'%filename,config=globalConfig.imgkit_config,css='./style.css')

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

def setCrontab(func:callable,day_of_week='mon-sun',hour='0-23',minute='0',second='0',*args,**kwargs):
    """
    定时触发任务
    :param func: 要触发的任务（函数）
    :param day_of_week:
    :param hour:
    :param minute:
    :param second:
    :param args: 任务参数
    """
    scheduler=bgsc()
    scheduler.add_job(func,'cron',day_of_week=day_of_week,hour=hour,minute=minute,second=second,args=args,kwargs=kwargs)
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

def assetCalculation(user: model.User):
    assets = user.money
    for i in user.stocks.items():
        stock = model.Stock.find(i[0], globalConfig.mysql)
        assets += i[1] * stock.price
    for debt in model.Debt.findAll(globalConfig.mysql, 'creditor=?', (user.qid,)):
        assets += debt.money
    for debt in model.Debt.findAll(globalConfig.mysql, 'debitor=?', (user.qid,)):
        assets -= debt.money

    return assets

def transferStr(src:str,replacement:dict[str,str]):
    target:str=src
    for key,value in replacement.items():
        target=target.replace(key,value)
    return target

def send(qid:str,message:str,group=False):
    """
    用于发送消息的函数
    :param qid: 用户id 或 群id
    :param message: 发送的消息
    :param group: 是否为群消息
    :return:none
    """
    if qid == 'treasury':
        qid = '2313473487'

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