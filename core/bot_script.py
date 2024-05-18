from datetime import datetime
from bot_sql import *
import sqlite3
import random,socket
import numpy as np
import os,json,requests,re

group_ids:list=[788951477]
headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58'}

def init():
    '''
    在矿井刷新时进行初始化
    '''
    execute('data.db',updateDigable%(True))
    execute('data.db',updateTime%(0))

def extract(uid:str,mineralNum:int,mineID:int)->str:
    '''
    :param uid:开采者的qq号
    :param mineralNum:开采得矿石的编号
    :param mineID:矿井编号
    :return:开采信息
    '''
    abundance:float=select('data.db',selectAbundanceByID%(mineID))[0][0]
    user:tuple=select('data.db',selectUserByqq%uid)[0]
    mineral:str=user[3]
    extractTech:float=user[5]
    digable:bool=user[6]
    if not digable:
        ans='开采失败:您必须等到下一个整点才能再次开采矿井！'
        return ans
    prob:float=0#开采成功的概率
    if abundance==0:
        prob=1.0
        abundance=1
    else:
        prob=abundance*extractTech
    if np.random.random()>prob:
        ans='开采失败:您的运气不佳'
        execute('data.db',updateDigableByqq%(False,uid))
    else:
        ans='开采成功！您获得了编号为%d的矿石！'%mineralNum
        mineralDict:dict=dict(eval(mineral))
        if mineralNum not in mineralDict:mineralDict[mineralNum]=0
        mineralDict[mineralNum]+=1
        execute('data.db',updateMineByqq%(mineralDict,uid))
        execute('data.db',updateAbundanceByID%(prob,mineID))
    return ans

def handle(res,group):
    ans:str=''#回复给用户的内容
    if group:#是群发消息
        message:str=res.get("raw_message")
        uid:str=res.get('sender').get('user_id')#发消息者的qq号
        gid:str=res.get('group_id')#群的qq号
        if gid not in group_ids:
            return None
        if "[CQ:at,qq=2470751924]" not in message:#必须在自己被at的情况下才能作出回复
            return None
        message_list:list=message.split(' ')
        funcStr:str=message_list[1]
        message_list.pop(0)#忽略at本身
        if funcStr=='time':
            ans='当前时间为：%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif funcStr=='注册':
            if len(message_list)!=2 or not re.match(r'\d{5}',message_list[1]) or len(message_list[1])!=5:
                ans='注册失败:请注意您的输入格式！'
                send(gid,ans,group=True)
                return None
            schoolID:str=message_list[1]
            if select('data.db',selectUserByID%schoolID) or select('data.db',selectUserByqq%uid):
                ans='注册失败:您已经注册过，无法重复注册！'
                send(gid,ans,group=True)
                return None
            execute('data.db',insertUser%(uid,schoolID,0,{},0.0,0.0,True))
            ans='注册成功！'
        elif funcStr=='开采':
            if len(message_list)!=2:
                ans='开采失败:请指定要开采的矿井！'
                send(gid,ans,group=True)
                return None
            mineralID:int=int(message_list[1])
            if mineralID==1:
                mineralNum=np.random.randint(2,28900)
                ans=extract(uid,mineralNum,1)
            elif mineralID==2:
                mineralNum=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(28900)*1000))/1000))
                ans=extract(uid,mineralNum,2)
            else:
                ans='开采失败:不存在此矿井！'
                send(gid,ans,group=True)
                return None
        elif funcStr=='帮助':
            ans='您好！欢迎使用森bot！\n'
            ans+='您可以使用如下功能：\n'
            ans+='1:查询时间：输入 time\n'
            ans+='2:注册账号：输入 注册 `学号`\n'
            ans+='3:开采矿石：输入 开采 `编号`\n'
            ans+='3.1 矿井1号会生成从2-28900均匀分布的随机整数矿石\n'
            ans+='3.2 矿井2号会生成从2-28900对数均匀分布的随机整数矿石\n'
        send(gid,ans,group=True)
    else:
        message:str=res.get("raw_message")
        uid:str=res.get('sender').get('user_id')
        message_list:list=message.split(' ')
        funcStr:str=message_list[0]
        if funcStr=='time':
            ans='当前时间为：%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif funcStr=='注册':
            if len(message_list)!=2 or not re.match(r'\d{5}',message_list[1]) or len(message_list[1])!=5:
                ans='注册失败:请注意您的输入格式！'
                send(uid,ans,group=False)
                return None
            schoolID:str=message_list[1]
            if select('data.db',selectUserByID%schoolID) or select('data.db',selectUserByqq%uid):
                ans='注册失败:您已经注册过，无法重复注册！'
                send(uid,ans,group=False)
                return None
            execute('data.db',insertUser%(uid,schoolID,0,{},0.0,0.0,True))
            ans='注册成功！'
        elif funcStr=='开采':
            if len(message_list)!=2:
                ans='开采失败:请指定要开采的矿井！'
                send(uid,ans,group=False)
                return None
            mineralID:int=int(message_list[1])
            if mineralID==1:
                mineralNum=np.random.randint(2,28900)
                ans=extract(uid,mineralNum,1)
            elif mineralID==2:
                mineralNum=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(28900)*1000))/1000))
                ans=extract(uid,mineralNum,2)
            else:
                ans='开采失败:不存在此矿井！'
                send(uid,ans,group=False)
                return None
        elif funcStr=='兑换':
            if len(message_list)!=2:
                ans='兑换失败:请指定要兑换的矿石！'
                send(uid,ans,group=False)
                return None
            mineralNum:int=int(message_list[1])
            user:tuple=select('data.db',selectUserByqq%uid)[0]
            schoolID:str=user[1]
            money:int=user[2]
            mineralDict:dict=dict(eval(user[3]))
            if mineralNum not in mineralDict:
                ans='兑换失败:您不具备此矿石！'
                send(uid,ans,group=False)
                return None
            if int(schoolID)%mineralNum \
            and int(schoolID[:3])%mineralNum \
            and int(schoolID[2:])%mineralNum \
            and int(schoolID[:2]+'0'+schoolID[:3])%mineralNum:
                ans='兑换失败:您不能够兑换此矿石！'
                send(uid,ans,group=False)
                return None
            mineralDict[mineralNum]-=1
            if mineralDict[mineralNum]<=0:
                mineralDict.pop(mineralNum)
            execute('data.db',updateMineByqq%(mineralDict,uid))
            money+=mineralNum
            execute('data.db',updateMoneyByqq%(money,uid))
            ans='兑换成功！'
        elif funcStr=='帮助':
            ans='您好！欢迎使用森bot！\n'
            ans+='您可以使用如下功能：\n'
            ans+='1:查询时间：输入 time\n'
            ans+='2:注册账号：输入 注册 `学号`\n'
            ans+='3:开采矿石：输入 开采 `矿井编号`\n'
            ans+='3.1 矿井1号会生成从2-28900均匀分布的随机整数矿石\n'
            ans+='3.2 矿井2号会生成从2-28900对数均匀分布的随机整数矿石\n'
            ans+='4:兑换矿石：输入 兑换 `矿石编号` 只有在矿石编号为3、5、6位学号的因数或班级因数时才可兑换！'
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