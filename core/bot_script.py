from datetime import datetime
from bot_sql import *
import sqlite3
import random,socket
import numpy as np
import os,json,requests,re,hashlib

group_ids:list=[788951477]
headers={
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58'}

with open("./config.json","r") as config:
    config=json.load(config)
env:str=config["env"]
player_tax=config["player_tax"]

if env=="prod":
    mysql=True
else:
    mysql=False

def sigmoid(x:float)->float:return 1/(1+np.exp(-x))

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
         '5:兑换矿石：输入 兑换 `矿石编号` 只有在矿石编号为3、5、6位学号的因数或班级因数时才可兑换！\n'\
         '6:矿石市场：\n' \
         '本节所有时间格式必须为YYYY-MM-DD,hh:mm:ss格式，"是否"数值取值为0或1。\n'\
         '6.1 摆卖矿石 输入 摆卖 `矿石编号` `矿石数目` `是否拍卖` `价格` `起始时间` `终止时间` 即可将矿石放置到市场上准备售出'

info_msg="查询到QQ号为：%s的用户信息\n"\
         "学号：%s\n"\
         "当前余额：%s\n"\
         "加工科技点：%s\n"\
         "开采科技点：%s\n"\
         "当前是否可开采：%s\n"\
         "以下为该用户拥有的矿石：\n"\
         "%s"

commands:dict={}

def handler(funcStr):
    """
    该装饰器装饰的函数会自动加入handle函数
    :param funcStr: 功能
    """
    def real_handler(func):
        commands[funcStr]=func
        return func

    return real_handler

def init():
    """
    在矿井刷新时进行初始化
    """
    execute(updateDigableAll,mysql,(1,))
    execute(updateAbundanceAll,mysql,(0.0,))


def extract(qid,mineralID,mineID):
    """获取矿石
    :param qid:开采者的qq号
    :param mineralID:开采得矿石的编号
    :param mineID:矿井编号
    :return:开采信息
    """
    abundance:float=select(selectAbundanceByID,mysql,(mineID,))[0][0]  # 矿井丰度
    user:tuple=select(selectUserByQQ,mysql,(qid,))[0]  # 用户信息元组
    mineral:str=user[3]  # 用户拥有的矿石（str of dict）
    extractTech:float=user[5]  # 开采等级
    digable:bool=user[6]  # 是否可以开采

    prob:float=0.0  # 初始化概率

    assert digable,'开采失败:您必须等到下一个整点才能再次开采矿井！'

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
        execute(updateMineralByQQ,mysql,(mineralDict,qid))
        execute(updateAbundanceByID,mysql,(prob,mineID))
        ans='开采成功！您获得了编号为%d的矿石！'%mineralID
    return ans

@handler("time")
def returnTime(m,q):
    return '当前时间为：%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@handler("注册")
def signup(message_list,qid):
    ans=''
    assert len(message_list)==2 and re.match(r'\d{5}',message_list[1]) and len(message_list[1])==5,'注册失败:请注意您的输入格式！'
    schoolID:str=message_list[1]
    assert not select(selectUserBySchoolID,mysql,(schoolID,)) and not select(selectUserByQQ,mysql,(qid,)),'注册失败:您已经注册过，无法重复注册！'
    execute(createUser,mysql,(qid,schoolID,0,{},0.0,0.0,1))
    ans="注册成功！"
    return ans

@handler("开采")
def getMineral(message_list,qid):
    assert len(message_list)==2,'开采失败:请指定要开采的矿井！'
    mineralID:int=int(message_list[1])
    if mineralID==1:
        mineralID=np.random.randint(2,30000)
        ans=extract(qid,mineralID,1)
    elif mineralID==2:
        mineralID=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(30000)*1000))/1000))
        ans=extract(qid,mineralID,2)
    elif mineralID==3:
        mineralID=np.random.randint(2,999)
        ans=extract(qid,mineralID,3)
    elif mineralID==4:
        mineralID=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(999)*1000))/1000))
        ans=extract(qid,mineralID,4)
    else:
        ans='开采失败:不存在此矿井！'
    return ans

@handler("兑换")
def exchange(message_list,qid):
    assert len(message_list)==2,'兑换失败:请指定要兑换的矿石！'
    mineralID:int=int(message_list[1])
    user:tuple=select(selectUserByQQ,mysql,(qid,))[0]
    schoolID:str=user[1]
    money:int=user[2]
    mineralDict:dict=dict(eval(user[3]))
    assert mineralID in mineralDict,'兑换失败:您不具备此矿石！'
    assert not int(schoolID)%mineralID\
        or not int(schoolID[:3])%mineralID\
        or not int(schoolID[2:])%mineralID\
        or not int(schoolID[:2]+'0'+schoolID[2:])%mineralID,'兑换失败:您不能够兑换此矿石！'
    mineralDict[mineralID]-=1
    if mineralDict[mineralID]<=0:
        mineralDict.pop(mineralID)
    execute(updateMineralByQQ,mysql,(str(mineralDict),qid))
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

@handler("摆卖")
def presell(message_list,qid):#TODO
    """
    :param message_list: 摆卖 矿石编号 矿石数量 是否拍卖 价格 起始时间 终止时间
    :param qid: 摆卖者的qq号
    :return: 摆卖提示信息
    """
    assert len(message_list)==7,'摆卖失败:请按照规定格式进行摆卖！'
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        auction:bool=bool(message_list[3])
        price:int=int(message_list[4])
        starttime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
        endtime:int=int(datetime.strptime(message_list[6],'%Y-%m-%d,%H:%M:%S').timestamp())
    except Exception as err:
        raise AssertionError('摆卖失败:请按照规定格式进行摆卖！')

    user:tuple=select(selectUserByQQ,mysql,(qid,))[0]
    mineralDict:dict=dict(eval(user[3]))
    assert mineralID in mineralDict,'摆卖失败:您不具备此矿石！'
    assert mineralDict[mineralID]>=mineralNum,'摆卖失败:您的矿石数量不足！'
    mineralDict[mineralID]-=mineralNum
    execute(updateMineralByQQ,mysql,(mineralDict,qid))
    if not auction:#非拍卖
        pass
    else:#拍卖
        pass

    nowtime=datetime.timestamp(datetime.now())
    assert endtime>nowtime,'摆卖失败:已经超过截止期限！'
    starttime=max(round(nowtime),starttime)
    md5=hashlib.md5()
    md5.update(('%.2f'%nowtime).encode('utf-8'))
    saleID=md5.hexdigest()[:6]
    execute(createSale,mysql,(qid,saleID,mineralID,mineralNum,auction,price,starttime,endtime))
    ans='摆卖成功！编号:%s'%saleID
    return ans


@handler("支付")
def pay(message_list,qid):
    # 格式1
    # 支付 q4867850 $20
    # 格式2
    # 支付 25778 $20
    assert len(message_list)==3,'支付失败:您的支付格式不正确！'
    target=str(message_list[1])
    assert message_list[2].startswith("$"),'支付失败:您的金融格式不正确！'
    try:
        money=int(str(message_list[2])[1:])
    except Exception:
        raise AssertionError("支付失败：金额格式不正确！应当为：$20")

    a_money:int=select(selectUserByQQ,mysql,(qid,))[0][2]

    assert a_money>=money,"支付失败：余额不足！"
    if target.startswith("q"):
        # 通过QQ号查找对方
        tqid:str=target[1:]
        b_info:list=select(selectUserByQQ,mysql,(tqid,))
        assert b_info,"支付失败：QQ号为%s的用户未注册！"%tqid
        b_money:int=b_info[0][2]

        a_money-=money
        b_money+=round(money*(1-player_tax))

        execute(updateMoneyByQQ,mysql,(a_money,qid))
        execute(updateMoneyByQQ,mysql,(b_money,tqid))

        return "支付成功！"
    else:
        tschoolID:str=target
        # 通过学号查找
        b_info:list=select(selectUserBySchoolID,mysql,(tschoolID,))
        assert b_info,"支付失败：学号为%s的用户未注册！"%tschoolID
        tqid:str=b_info[0][0]
        b_money:int=b_info[0][2]

        a_money-=money
        b_money+=money*(1-player_tax)

        execute(updateMoneyByQQ,mysql,(b_money,tqid))
        execute(updateMoneyByQQ,mysql,(a_money,qid))

        return "支付成功！"

@handler("帮助")
def getHelp(message_list,qid):
    return help_msg


def dealWithRequest(funcStr,message_list,qid):
    if funcStr in commands:
        ans=commands[funcStr](message_list,qid)
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

        try:
            ans=dealWithRequest(funcStr,message_list,qid)
            send(gid,ans,group=True)
        except AssertionError as err:
            send(gid,err,group=True)

    else:
        message:str=res.get("raw_message")
        qid:str=res.get('sender').get('user_id')
        message_list:list=message.split(' ')
        funcStr:str=message_list[0]

        try:
            ans=dealWithRequest(funcStr,message_list,qid)
            send(qid,ans,group=False)
        except AssertionError as err:
            send(qid,err,group=False)

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
