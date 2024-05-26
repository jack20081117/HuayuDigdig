import random,requests
from datetime import datetime
import numpy as np
from matplotlib import pyplot as plt
plt.rcParams['font.family']=['Microsoft YaHei']

from apscheduler.schedulers.background import BackgroundScheduler as bgsc

from config import *

def sigmoid(x:float)->float:return 1/(1+np.exp(-x))

def handler(funcStr:str):
    """
    该装饰器装饰的函数会自动加入handle函数
    :param funcStr: 功能
    """
    def real_handler(func:callable):
        commands[funcStr]=func
        return func

    return real_handler

def generate_random_digits(wei:int):
    return "".join(random.choice(chars) for i in wei)


def drawtable(data:list,filename:str):
    """
    将市场信息绘制成表格
    :param data: 要绘制的表格数据
    :param filename: 存储图片地址
    :return:
    """
    fig,ax=plt.subplots()
    table=ax.table(cellText=data,loc='center')
    table.auto_set_font_size(False)
    #table.set_fontsize(10)

    for key,cell in table.get_celld().items():
        cell.set_text_props(fontsize=8,ha='center',va='center')

    table.auto_set_column_width(col=list(range(len(data[0]))))

    ax.axis('off')
    plt.savefig('../go-cqhttp/data/images/%s'%filename)

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