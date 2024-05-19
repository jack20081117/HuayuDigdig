from datetime import datetime
from bot_sql import *
import sqlite3
import random,socket
import numpy as np
import os,json,requests,re

group_ids:list=[788951477]
headers={
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58'}

with open("./config.json","r") as config:
    config=json.load(config)
env:str=config["env"]
if env=="prod":
    mysql=True
else:
    mysql=False


sigmoid = lambda x: 1/(1+np.exp(-x))

help_msg='您好！欢迎使用森bot！\n'\
         '您可以使用如下功能：\n'\
         '1:查询时间：输入 time\n'\
         '2:注册账号：输入 注册 `学号`\n'\
         '3:查询信息：输入 查询  即可获取用户个人信息\n'\
         '4:开采矿石：输入 开采 `矿井编号`\n'\
         '4.1 矿井1号会生成从2-30000均匀分布的随机整数矿石\n'\
         '4.2 矿井2号会生成从2-30000对数均匀分布的随机整数矿石\n'\
         '4.3 矿井3号会生成从2-999均匀分布的随机整数矿石\n'\
         '4.4 矿井4号会生成从2-999对数均匀分布的随机整数矿石\n'\
         '5:兑换矿石：输入 兑换 `矿石编号` 只有在矿石编号为3、5、6位学号的因数或班级因数时才可兑换！'

info_msg="查询到QQ号为：%s的用户信息\n"\
         "学号：%s\n"\
         "当前余额：%s\n"\
         "加工科技点：%s\n"\
         "开采科技点：%s\n"\
         "当前是否可开采：%s\n"\
         "以下为该用户拥有的矿石：\n"\
         "%s"

commands2functions:dict={}
commands = []


algorithms = [
    lambda start,end: np.random.randint(start, end),
    lambda start,end: int(np.exp(np.random.randint(int(np.log(start)*1000),int(np.log(end)*1000))/1000)),
]

def handler(funcStr):
    """
    该装饰器装饰的函数会自动加入handle函数
    :param funcStr: 功能
    """
    def real_handler(func):
        commands2functions[funcStr]=func
        commands.append(funcStr)
        return func

    return real_handler

def init():
    """
    在矿井刷新时进行初始化
    """
    execute(updateDigableAll,mysql,(1,))
    execute(updateAbundanceAll,mysql,(0.0,))


#algorithm: 
# 1: np.random.randint(start, end)
# 2: int(np.exp(np.random.randint(int(np.log(start)*1000),int(np.log(end)*1000))/1000))
def getMineralID(mineID:int)->int:
    alg, start, end = select(selectMineInfoByID, mysql, (mineID,))[0]
    return algorithms[alg-1](start,end)
    

def extract(qid,mineID):
    """获取矿石
    :param qid:开采者的qq号
    :param mineralID:开采得矿石的编号
    :param mineID:矿井编号
    :return:开采信息
    """
    mineralID = getMineralID(mineID)
    abundance:float=select(selectAbundanceByID,mysql,(mineID,))[0][0]  # 矿井丰度
    user:tuple=select(selectUserByQQ,mysql,(qid,))[0]  # 用户信息元组
    mineral:str=user[3]  # 用户拥有的矿石（str of dict）
    extractTech:float=user[5]  # 开采等级
    digable:bool=user[6]  # 是否可以开采

    prob:float=0.0  # 初始化概率

    if not digable:
        # 不可开采
        ans='开采失败:您必须等到下一个整点才能再次开采矿井！'
        return ans

    # 决定概率 
    if abundance==0.0:
        prob=1.0
    else:
        prob=round(abundance*sigmoid(extractTech),2)

    if np.random.random()>prob:
        execute(updateDigableByQQ,mysql,(0,qid))
        ans='开采失败:您的运气不佳，未能开采成功！'
    else:
        mineralDict:dict=dict(eval(mineral))
        # 加一个矿石
        if mineralID not in mineralDict:
            mineralDict[mineralID]=0
        mineralDict[mineralID]+=1
        execute(updateMineByQQ,mysql,(mineralDict,qid))
        execute(updateAbundanceByID,mysql,(prob,mineID))
        ans='开采成功！您获得了编号为%d的矿石！'%mineralID
    return ans

@handler("time")
def returnTime(m,q):
    return '当前时间为：%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@handler("注册")
def signup(message_list,qid):
    ans=''
    if len(message_list)!=2 or not re.match(r'\d{5}',message_list[1]) or len(message_list[1])!=5:
        ans='注册失败:请注意您的输入格式！'
        return ans
    schoolID:str=message_list[1]
    if select(selectUserBySchoolID,mysql,(schoolID,)) or select(selectUserByQQ,mysql,(qid,)):
        ans='注册失败:您已经注册过，无法重复注册！'
        return ans
    execute(createUser,mysql,(qid,schoolID,0,{},0.0,0.0,1))
    ans="注册成功！"
    return ans

@handler("开采")
def getMineral(message_list,qid):
    if len(message_list)!=2:
        ans='开采失败:请指定要开采的矿井！'
        return ans
    if not isinstance(message_list[1],int):
        return '开采失败：矿井号必须为正整数！'
    mineralID:int=int(message_list[1])
    if mineralID==1:
        ans=extract(qid,1)
    elif mineralID==2:
        ans=extract(qid,2)
    elif mineralID==3:
        ans=extract(qid,3)
    elif mineralID==4:
        ans=extract(qid,4)
    else:
        ans='开采失败:不存在此矿井！'
    return ans

@handler("兑换")
def exchange(message_list,qid):
    if len(message_list)!=2:
        ans='兑换失败:请指定要兑换的矿石！'
        return ans
    mineralID:int=int(message_list[1])
    user:tuple=select(selectUserByQQ,mysql,(qid,))[0]
    schoolID:str=user[1]
    money:int=user[2]
    mineralDict:dict=dict(eval(user[3]))
    if mineralID not in mineralDict:
        ans='兑换失败:您不具备此矿石！'
        return ans
    if int(schoolID)%mineralID\
            and int(schoolID[:3])%mineralID\
            and int(schoolID[2:])%mineralID\
            and int(schoolID[:2]+'0'+schoolID[2:])%mineralID:
        ans='兑换失败:您不能够兑换此矿石！'
        return ans
    mineralDict[mineralID]-=1
    if mineralDict[mineralID]<=0:
        mineralDict.pop(mineralID)
    execute(updateMineByQQ,mysql,(str(mineralDict),qid))
    money+=mineralID
    execute(updateMoneyByQQ,mysql,(money,qid))
    ans='兑换成功！'
    return ans

@handler("查询")
def getUserInfo(message_list,qid):
    user:tuple=select(selectUserByQQ,mysql,(qid,))[0]
    _,schoolID,money,mineral,process_tech,extract_tech,digable=user
    mres=""
    for mid,mnum in dict(eval(mineral)).items():
        mres+="编号%s的矿石%s个；\n"%(mid,mnum)
    ans=info_msg%(qid,schoolID,money,process_tech,extract_tech,digable,mres)
    return ans

@handler("帮助")
def getHelp(message_list,qid):
    return help_msg


def dealWithRequest(funcStr,message_list,qid):
    if funcStr in commands:
        ans=commands2functions[funcStr](message_list,qid)
    else:
        ans="未知命令：请输入'帮助'以获取帮助信息！"
    return ans

def handle(res,group):
    ans:str=''  #回复给用户的内容
    if group:#是群发消息
        message:str=res.get("raw_message")
        qid:str=res.get('sender').get('user_id')  #发消息者的qq号
        gid:str=res.get('group_id')  #群的qq号
        if gid not in group_ids:
            return None
        if "[CQ:at,qq=2470751924]" not in message:#必须在自己被at的情况下才能作出回复
            return None

        message_list:list=message.split(' ')
        funcStr:str=message_list[1]
        message_list.pop(0)  #忽略at本身

        ans=dealWithRequest(funcStr,message_list,qid)

        send(gid,ans,group=True)

    else:
        message:str=res.get("raw_message")
        qid:str=res.get('sender').get('user_id')
        message_list:list=message.split(' ')
        funcStr:str=message_list[0]

        ans=dealWithRequest(funcStr,message_list,qid)

        send(qid,ans,group=False)

def send(qid,message,group=False):
    """
    用于发送消息的函数
    :param qid:用户id
    :param message:发送的消息
    :param gid:群id
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
