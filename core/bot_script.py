from datetime import datetime
from bot_sql import *
import sqlite3
import random,socket
import numpy as np
import os,json,requests,re

group_ids: list=[788951477]
headers={
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58'}

with open("./config.json","r") as config:
    config=json.load(config)
env:str=config["env"]
if env=="prod":
    mysql=True
else:
    mysql=False

help_msg='您好！欢迎使用森bot！\n'
help_msg+='您可以使用如下功能：\n'
help_msg+='1:查询时间：输入 time\n'
help_msg+='2:注册账号：输入 注册 `学号`\n'
help_msg+='3.1 矿井1号会生成从2-30000均匀分布的随机整数矿石\n'
help_msg+='3.2 矿井2号会生成从2-30000对数均匀分布的随机整数矿石\n'
help_msg+='3.3 矿井3号会生成从2-300均匀分布的随机整数矿石\n'
help_msg+='3.4 矿井4号会生成从2-300对数均匀分布的随机整数矿石\n'
help_msg+='3.5 矿井5号会生成从2-300000均匀分布的随机整数矿石\n'
help_msg+='3.6 矿井6号会生成从2-300000对数均匀分布的随机整数矿石\n'
help_msg+='4:兑换矿石：输入 兑换 `矿石编号` 只有在矿石编号为3、5、6位学号的因数或班级因数时才可兑换！'


def init():
    '''
    在矿井刷新时进行初始化
    '''
    execute(updateDigableAll,mysql,(True))
    execute(updateAbundance,mysql,(0.0,))


def extract(qid,mineralNum,mineID):
    # 
    '''获取矿石
    :param qid:开采者的qq号
    :param mineralNum:开采得矿石的编号
    :param mineID:矿井编号
    :return:开采信息
    '''
    abundance:float=select('data.db',selectAbundanceByID%(mineID))[0][0] # 矿井丰度
    user:tuple=select('data.db',selectUserByQQ%qid)[0] # 用户信息元组
    mineral:str=user[3] # 用户拥有的矿石（str of dict）
    extractTech:float=user[5] # 开采等级
    digable:bool=user[6] # 是否可以开采
    
    prob:float=0.0 # 初始化概率
    
    if not digable:
        # 不可开采
        ans='开采失败: 您必须等到下一个整点才能再次开采矿井！'
        return ans

    # 决定概率 
    if abundance==0.0:
        prob=1.0
    else:
        prob=abundance*extractTech

    if np.random.random()>prob:
        execute(updateDigableByQQ,mysql,(False,qid))
        ans='开采失败: 您的运气不佳，未能开采成功！'
    else:
        mineralDict:dict=dict(eval(mineral))
        # 加一个矿石
        if mineralNum not in mineralDict:
            mineralDict[mineralNum]=0
        mineralDict[mineralNum]+=1
        execute(updateMineByQQ,mysql,(mineralDict,qid))
        execute(updateAbundanceByID,mysql,(prob,mineID))
        ans='开采成功！您获得了编号为%d的矿石！'%mineralNum
    return ans


def signup(message_list,qid,tf,gid=0):
    ans=''
    if len(message_list)!=2 or not re.match(r'\d{5}',message_list[1]) or len(message_list[1])!=5:
        ans='注册失败:请注意您的输入格式！'
        return ans
    schoolID:str=message_list[1]
    if select('data.db',selectUserBySchoolID%schoolID) or select('data.db',selectUserByQQ%qid):
        ans='注册失败:您已经注册过，无法重复注册！'
        return ans
    execute(createUser,mysql,(qid,schoolID,0,{},0.0,0.0,True))
    ans="注册成功！"
    return ans

def getMineral(message_list,tf,qid,gid=0):
    if len(message_list)!=2:
        ans='开采失败:请指定要开采的矿井！'
        return ans
    mineralID:int=int(message_list[1])
    if mineralID==1:
        mineralNum=np.random.randint(2,30000)
        ans=extract(qid,mineralNum,1)
    elif mineralID==2:
        mineralNum=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(30000)*1000))/1000))
        ans=extract(qid,mineralNum,2)
    elif mineralID==3:
        mineralNum=np.random.randint(2,300)
        ans=extract(qid,mineralNum,3)
    elif mineralID==4:
        mineralNum=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(300)*1000))/1000))
        ans=extract(qid,mineralNum,4)
    elif mineralID==5:
        mineralNum=np.random.randint(2,300000)
        ans=extract(qid,mineralNum,5)
    elif mineralID==6:
        mineralNum=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(300000)*1000))/1000))
        ans=extract(qid,mineralNum,6)
    else:
        ans='开采失败:不存在此矿井！'
    return ans


def handle(res,group):
    ans:str=''  #回复给用户的内容
    if group:  #是群发消息
        message:str=res.get("raw_message")
        qid:str=res.get('sender').get('user_id')  #发消息者的qq号
        gid:str=res.get('group_id')  #群的qq号
        if gid not in group_ids:
            return None
        if "[CQ:at,qq=2470751924]" not in message:  #必须在自己被at的情况下才能作出回复
            return None

        # 开始处理

        # 获取命令类型
        message_list: list=message.split(' ')
        funcStr:str=message_list[1]
        message_list.pop(0)  #忽略at本身

        # 遍历func_str
        if funcStr=='time':
            ans='当前时间为：%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif funcStr=='注册':
            ans=signup(message_list,qid,True,gid)

        elif funcStr=='开采':
            ans=getMineral(message_list,True,qid,gid)

        elif funcStr=='帮助':
            ans=help_msg

        elif funcStr=='兑换':
            if len(message_list)!=2:
                ans='兑换失败:请指定要兑换的矿石！'
                send(gid,ans,group=True)
                return None
            mineralNum:int=int(message_list[1])
            user:tuple=select('data.db',selectUserByQQ%qid)[0]
            schoolID:str=user[1]
            money:int=user[2]
            mineralDict:dict=dict(eval(user[3]))
            if mineralNum not in mineralDict:
                ans='兑换失败:您不具备此矿石！'
                send(gid,ans,group=True)
                return None
            if int(schoolID)%mineralNum\
                    and int(schoolID[:3])%mineralNum\
                    and int(schoolID[2:])%mineralNum\
                    and int(schoolID[:2]+'0'+schoolID[:3])%mineralNum:
                ans='兑换失败:您不能够兑换此矿石！'
                send(gid,ans,group=True)
                return None
            mineralDict[mineralNum]-=1
            if mineralDict[mineralNum]<=0:
                mineralDict.pop(mineralNum)
            execute(updateMineByQQ,mysql,(str(mineralDict),qid))
            money+=mineralNum
            execute(updateMoneyByQQ,mysql,(money,qid))
            ans='兑换成功！'

        else:
            ans="未知命令：请输入'帮助'以获取帮助信息！"

        send(gid,ans,group=True)

    else:
        message:str=res.get("raw_message")
        qid:str=res.get('sender').get('user_id')
        message_list:list=message.split(' ')
        funcStr:str=message_list[0]
        if funcStr=='time':
            ans='当前时间为：%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        elif funcStr=='注册':
            ans=signup(message_list,qid,False)

        elif funcStr=='开采':
            ans=getMineral(message_list,False,qid)

        elif funcStr=='帮助':
            ans=help_msg

        elif funcStr=='兑换':
            if len(message_list)!=2:
                ans='兑换失败:请指定要兑换的矿石！'
                send(qid,ans,group=False)
                return None
            mineralNum:int=int(message_list[1])
            user:tuple=select('data.db',selectUserByQQ%qid)[0]
            schoolID:str=user[1]
            money:int=user[2]
            mineralDict:dict=dict(eval(user[3]))
            if mineralNum not in mineralDict:
                ans='兑换失败:您不具备此矿石！'
                send(qid,ans,group=False)
                return None
            if int(schoolID)%mineralNum\
                    and int(schoolID[:3])%mineralNum\
                    and int(schoolID[2:])%mineralNum\
                    and int(schoolID[:2]+'0'+schoolID[:3])%mineralNum:
                ans='兑换失败:您不能够兑换此矿石！'
                send(qid,ans,group=False)
                return None
            mineralDict[mineralNum]-=1
            if mineralDict[mineralNum]<=0:
                mineralDict.pop(mineralNum)
            execute(updateMineByQQ,mysql,(mineralDict,qid))
            money+=mineralNum
            execute(updateMoneyByQQ,mysql,(money,qid))
            ans='兑换成功！'
        else:
            ans="未知命令：请输入'帮助'以获取帮助信息！"
        send(qid,ans,group=False)


def send(qid,message,group=False):
    """
    用于发送消息的函数
    :param qid: 用户id
    :param message: 发送的消息
    :param gid: 群id
    :return: none
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
