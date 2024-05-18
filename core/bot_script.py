from datetime import datetime
from bot_sql import *
import sqlite3
import random,socket
import numpy as np
import os,json,requests,re

group_ids=[788951477,780474840]
headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58'}

def handle(res,group):
    ans=''#回复给用户的内容
    if group:#是群发消息
        message=res.get("raw_message")
        uid=res.get('sender').get('user_id')#发消息者的qq号
        gid=res.get('group_id')#群的qq号
        if gid not in group_ids:
            return None
        if "[CQ:at,qq=2470751924]" not in message:#必须在自己被at的情况下才能作出回复
            return None
        message_list=message.split(' ')
        func_str=message_list[1]
        message_list.pop(0)#忽略at本身
        if func_str=='time':
            ans='当前时间为：%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif func_str=='注册':
            if len(message_list)!=2 or not re.match(r'\d{5}',message_list[1]) or len(message_list[1])!=5:
                ans='注册失败:请注意您的输入格式！'
                send(gid,ans,group=True)
                return None
            schoolID=message_list[1]
            if select('data.db',selectUserByID%schoolID) or select('data.db',selectUserByqq%uid):
                ans='注册失败:您已经注册过，无法重复注册！'
                send(gid,ans,group=True)
                return None
            execute('data.db',insertUser%(uid,schoolID,0,[],0,0,1))
            ans='注册成功！'
        elif func_str=='帮助':
            ans='您好！欢迎使用森bot！\n'
            ans+='您可以使用如下功能：\n'
            ans+='1:查询时间：输入 time\n'
            ans+='2:注册账号：输入 注册 `学号`\n'
        send(gid,ans,group=True)
    else:
        message=res.get("raw_message")
        uid=res.get('sender').get('user_id')
        message_list=message.split(' ')
        func_str=message_list[0]
        if func_str=='time':
            ans='当前时间为：%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif func_str=='注册':
            if len(message_list)!=2 or not re.match(r'\d{5}',message_list[1]) or len(message_list[1])!=5:
                ans='注册失败:请注意您的输入格式！'
                send(uid,ans,group=False)
                return None
            schoolID=message_list[1]
            if select('data.db',selectUserByID%schoolID) or select('data.db',selectUserByqq%uid):
                ans='注册失败:您已经注册过，无法重复注册！'
                send(uid,ans,group=False)
                return None
            execute('data.db',insertUser%(uid,schoolID,0,[],0,0,1))
            ans='注册成功！'
        elif func_str=='开采':
            if len(message_list)!=2:
                ans='开采失败:请指定要开采的矿井！'
                send(uid,ans,group=False)
                return None
            mineralID=message_list[1]
            if mineralID=='1':
                mineralNum=np.random.randint(2,28900)
                usedTimes=int(select('data.db',selectTimeByID%(1))[0][0])
                user=select('data.db',selectUserByqq%uid)[0]
                mineral,extractTech,digable=user[3],float(user[5]),user[6]
                if not int(digable):
                    ans='开采失败:您必须等到下一个整点才能再次开采矿井！'
                    send(uid,ans,group=False)
                    return None
                if usedTimes==0:prob=1
                else:prob=np.power(extractTech,usedTimes)
                if np.random.random()>prob:
                    ans='开采失败:您的运气不佳'
                    execute('data.db',updateDigableByqq%('0',uid))
                else:
                    ans='开采成功！您获得了编号为%d的矿石！'%mineralNum
                    new_mineral=list(eval(mineral))
                    new_mineral.append(mineralNum)
                    new_mineral=str(new_mineral)
                    execute('data.db',updateMineByqq%(new_mineral,uid))
                    execute('data.db',updateTimeByID%(str(usedTimes+1),'1'))
            else:
                ans='开采失败:不存在此矿井！'
                send(uid,ans,group=False)
                return None
        elif func_str=='帮助':
            ans='您好！欢迎使用森bot！\n'
            ans+='您可以使用如下功能：\n'
            ans+='1:查询时间：输入 time\n'
            ans+='2:注册账号：输入 注册 `学号`\n'
        send(uid,ans,group=False)

def send(id,message,group=False):
    """
    用于发送消息的函数
    :param uid: 用户id
    :param message: 发送的消息
    :param gid: 群id
    :return: none
    """

    if not group:
        # 如果发送的为私聊消息
        params={
            "user_id":id,
            "message":message,
        }
        resp=requests.get("http://127.0.0.1:5700/send_private_msg",params=params)
    else:
        params={
            'group_id':id,
            "message":message
        }
        resp=requests.get("http://127.0.0.1:5700/send_group_msg",params=params)