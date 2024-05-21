from datetime import datetime
from bot_model import *
import numpy as np
import json,requests,re,hashlib

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
         '您可以使用如下功能:\n'\
         '1:查询时间:输入 time\n'\
         '2:注册账号:输入 注册 `学号`\n'\
         '3:查询信息:输入 查询  即可获取用户个人信息\n'\
         '4:开采矿石:输入 开采 `矿井编号`\n'\
         '    4.1 矿井1号会生成从2-30000均匀分布的随机整数矿石\n'\
         '    4.2 矿井2号会生成从2-30000对数均匀分布的随机整数矿石\n'\
         '    4.3 矿井3号会生成从2-999均匀分布的随机整数矿石\n'\
         '    4.4 矿井4号会生成从2-999对数均匀分布的随机整数矿石\n'\
         '5:兑换矿石:输入 兑换 `矿石编号` 只有在矿石编号为3、5、6位学号的因数或班级因数时才可兑换！\n'\
         '6:矿石市场:\n' \
         '本节所有时间格式必须为YYYY-MM-DD,hh:mm:ss格式，"是否"数值取值为0或1。\n'\
         '6.2 摆卖矿石 输入 摆卖 `矿石编号` `矿石数目` `是否拍卖` `价格` `起始时间` `终止时间` 即可将矿石放置到市场上准备售出\n'\
         '6.3 购买矿石 输入 购买 `交易编号`\n'\
         '6.4 预订矿石 输入 预订 `矿石编号` `矿石数目` `价格` `起始时间` `终止时间` 即可在市场上预订矿石\n'\
         '6.5 售卖矿石 输入 售卖 `交易编号`\n'\
         '7:支付金钱:输入 支付 `编号` $`金额` 【金额前应带有美元符号$】即可向对方支付指定金额\n'\
         '    7.1 向QQ用户支付，编号以q开头，后加QQ号\n'\
         '    7.2 向指定学号用户支付，直接输入学号即可\n'\

info_msg="查询到QQ号为:%s的用户信息\n"\
         "学号:%s\n"\
         "当前余额:%s\n"\
         "加工科技点:%s\n"\
         "开采科技点:%s\n"\
         "当前是否可开采:%s\n"\
         "以下为该用户拥有的矿石:\n"\
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
    execute('update users set digable=?',mysql,(1,))
    execute('update mine set abundance=?',mysql,(0.0,))


def extract(qid,mineralID,mineID):
    """获取矿石
    :param qid:开采者的qq号
    :param mineralID:开采得矿石的编号
    :param mineID:矿井编号
    :return:开采信息
    """
    mine:Mine=Mine.find(mineID,mysql)
    #abundance:float=select(selectAbundanceByID,mysql,(mineID,))[0][0]  # 矿井丰度
    abundance:float=mine.abundance #矿井丰度
    user:User=User.find(qid,mysql)
    mineral=user.mineral # 用户拥有的矿石（str of dict）
    extractTech=user.extract_tech # 开采科技

    assert user.digable,'开采失败:您必须等到下一个整点才能再次开采矿井！'

    # 决定概率 
    if abundance==0.0:
        prob=1.0
    else:
        prob=round(abundance*sigmoid(extractTech),2)

    if np.random.random()>prob:
        user.digable=0
        user.update(mysql)
        ans='开采失败:您的运气不佳，未能开采成功！'
    else:
        mineralDict:dict=dict(eval(mineral))
        # 加一个矿石
        if mineralID not in mineralDict:
            mineralDict[mineralID]=0
        mineralDict[mineralID]+=1
        user.mineral=str(mineralDict)
        user.update(mysql)
        mine.abundance=prob
        mine.update(mysql)
        ans='开采成功！您获得了编号为%d的矿石！'%mineralID
    return ans

@handler("time")
def returnTime(m,q):
    return '当前时间为:%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@handler("注册")
def signup(message_list,qid):
    """
    :param message_list: 注册 学号
    :param qid: 注册者的qq号
    :return: 注册提示信息
    """
    ans=''
    assert len(message_list)==2 and re.match(r'\d{5}',message_list[1]) and len(message_list[1])==5,'注册失败:请注意您的输入格式！'
    schoolID:str=message_list[1]
    assert not User.find(qid,mysql) and not User.findAll(mysql,'schoolID=?',(schoolID,)),'注册失败:您已经注册过，无法重复注册！'
    user=User(qid=qid,schoolID=schoolID,money=0,mineral='{}',process_tech=0.0,extract_tech=0.0,digable=1)
    user.save(mysql)
    ans="注册成功！"
    return ans

@handler("开采")
def getMineral(message_list,qid):
    """
    :param message_list: 开采 矿井编号
    :param qid: 开采者的qq号
    :return: 开采提示信息
    """
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
    """
    :param message_list: 兑换 矿石编号
    :param qid: 兑换者的qq号
    :return: 兑换提示信息
    """
    assert len(message_list)==2,'兑换失败:请指定要兑换的矿石！'
    mineralID:int=int(message_list[1])
    user:User=User.find(qid,mysql)
    schoolID:str=user.schoolID
    money:int=user.money
    mineralDict:dict=dict(eval(user.mineral))
    assert mineralID in mineralDict,'兑换失败:您不具备此矿石！'
    assert not int(schoolID)%mineralID\
        or not int(schoolID[:3])%mineralID\
        or not int(schoolID[2:])%mineralID\
        or not int(schoolID[:2]+'0'+schoolID[2:])%mineralID,'兑换失败:您不能够兑换此矿石！'

    mineralDict[mineralID]-=1
    if mineralDict[mineralID]<=0:
        mineralDict.pop(mineralID)

    user.mineral=str(mineralDict)
    user.money+=mineralID
    user.update(mysql)

    ans='兑换成功！'
    return ans

@handler("查询")
def getUserInfo(message_list,qid):
    user:User=User.find(qid,mysql)
    schoolID=user.schoolID
    money=user.money
    mineral=user.mineral
    processTech=user.process_tech
    extractTech=user.extract_tech
    digable=user.digable
    mres=""
    mineralDict:dict=dict(eval(mineral))
    sortedMineralDict={key:mineralDict[key] for key in sorted(mineralDict.keys())}
    for mid,mnum in sortedMineralDict.items():
        mres+="编号%s的矿石%s个；\n"%(mid,mnum)
    ans=info_msg%(qid,schoolID,money,processTech,extractTech,digable,mres)
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
        auction:bool=bool(int(message_list[3]))
        price:int=int(message_list[4])
        starttime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
        endtime:int=int(datetime.strptime(message_list[6],'%Y-%m-%d,%H:%M:%S').timestamp())
    except Exception as err:
        raise AssertionError('摆卖失败:请按照规定格式进行摆卖！')

    user:User=User.find(qid,mysql)
    mineralDict:dict=dict(eval(user.mineral))
    assert mineralNum>=1,'摆卖失败:您必须至少摆卖1个矿石！'
    assert mineralID in mineralDict,'摆卖失败:您不具备此矿石！'
    assert mineralDict[mineralID]>=mineralNum,'摆卖失败:您的矿石数量不足！'
    nowtime=datetime.timestamp(datetime.now())
    assert endtime>nowtime,'摆卖失败:已经超过截止期限！'
    starttime=max(round(nowtime),starttime)

    mineralDict[mineralID]-=mineralNum
    if mineralDict[mineralID]<=0:mineralDict.pop(mineralID)

    user.mineral=str(mineralDict)
    user.update(mysql)

    if not auction:#非拍卖
        pass
    else:#拍卖
        pass

    md5=hashlib.md5()
    md5.update(('%.2f'%nowtime).encode('utf-8'))
    saleID=md5.hexdigest()[:6]

    sale:Sale=Sale(saleID=saleID,qid=qid,mineralID=mineralID,mineralNum=mineralNum,auction=auction,price=price,starttime=starttime,endtime=endtime)
    sale.save(mysql)
    ans='摆卖成功！编号:%s'%saleID
    return ans

@handler("购买")
def buy(message_list,qid):
    """
    :param message_list: 购买 摆卖编号
    :param qid: 购买者的qq号
    :return: 购买提示信息
    """
    assert len(message_list)==2,'购买失败:请按照规定格式进行购买！'
    saleID:str=message_list[1]
    sale:Sale=Sale.find(saleID,mysql)
    assert sale,'购买失败:不存在此卖品！'
    user:User=User.find(qid)

    tqid=sale.qid
    mineralID=sale.mineralID
    mineralNum=sale.mineralNum
    price=sale.price
    starttime=sale.starttime

    nowtime=datetime.timestamp(datetime.now())#现在的时间
    assert qid!=tqid,'购买失败:您不能购买自己的商品！'
    assert nowtime>=starttime,'购买失败:尚未到开始售卖时间！'
    assert user.money>=price,'购买失败:您的余额不足！'

    user.money-=price#付钱
    tuser:User=User.find(tqid)
    tuser.money+=price#得钱

    mineralDict:dict=dict(eval(user.mineral))
    if mineralID not in mineralDict:
        mineralDict[mineralID]=0
    mineralDict[mineralID]+=mineralNum#增加矿石
    user.mineral=str(mineralDict)

    sale.remove(mysql)#删除市场上的此条记录
    user.update(mysql)
    tuser.update(mysql)

    ans='购买成功！'
    send(tqid,'您摆卖的商品(编号:%s)已被卖出！'%saleID,False)
    return ans

@handler('预订')
def prebuy(message_list,qid):
    """
    :param message_list: 预订 矿石编号 矿石数量 价格 起始时间 终止时间
    :param qid: 预订者的qq号
    :return: 预订提示信息
    """
    assert len(message_list)==6,'预订失败:请按照规定格式进行预订！'
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        price:int=int(message_list[3])
        starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except Exception as err:
        raise AssertionError('预订失败:请按照规定格式进行预订！')
    user:User=User.find(qid)

    assert user.money>=price,'预订失败:您的余额不足！'
    nowtime=datetime.timestamp(datetime.now())
    assert endtime>nowtime,'摆卖失败:已经超过截止期限！'
    starttime=max(round(nowtime),starttime)
    user.money-=price

    md5=hashlib.md5()
    md5.update(('%.2f'%nowtime).encode('utf-8'))
    purchaseID=md5.hexdigest()[:6]
    purchase:Purchase=Purchase(purchaseID=purchaseID,qid=qid,mineralID=mineralID,mineralNum=mineralNum,price=price,starttime=starttime,endtime=endtime)
    purchase.save(mysql)
    user.update(mysql)

    ans='预订成功！编号:%s'%purchaseID
    return ans

@handler('售卖')
def sell(message_list,qid):
    """
    :param message_list: 售卖 预订编号
    :param qid: 售卖者的qq号
    :return: 售卖提示信息
    """
    assert len(message_list)==2,'售卖失败:请按照规定进行售卖！'
    purchaseID:str=message_list[1]
    purchase:Purchase=Purchase.find(purchaseID)
    assert purchase,'购买失败:不存在此卖品！'
    user:User=User.find(qid)

    tqid=purchase.qid
    mineralID=purchase.mineralID
    mineralNum=purchase.mineralNum
    price=purchase.price
    starttime=purchase.starttime

    nowtime=datetime.timestamp(datetime.now())  #现在的时间
    assert qid!=tqid,'售卖失败:您不能向自己售卖商品！'
    assert nowtime>=starttime,'售卖失败:尚未到开始售卖时间！'
    mineralDict:dict=dict(eval(user.mineral))
    assert mineralID in mineralDict,'售卖失败:您不具备此矿石！'
    assert mineralDict[mineralID]>=mineralNum,'售卖失败:您的矿石数量不足！'
    mineralDict[mineralID]-=mineralNum
    if mineralDict[mineralID]<=0:mineralDict.pop(mineralID)

    user.money+=price  #得钱
    user.mineral=str(mineralDict)
    user.update(mysql)

    tuser:User=User.find(tqid)

    tmineralDict:dict=dict(eval(tuser.mineral))
    if mineralID not in tmineralDict:
        tmineralDict[mineralID]=0
    tmineralDict[mineralID]+=mineralNum  #增加矿石
    tuser.mineral=str(tmineralDict)

    purchase.remove(mysql)#删除市场上的此条记录

    tuser.update(mysql)

    ans='售卖成功！'
    send(tqid,'您预订的商品(编号:%s)已被买入！'%purchaseID,False)
    return ans

@handler("市场")
def market(message_list,qid):
    """
    :param message_list: 市场
    :param qid:
    :return: 提示信息
    """
    sales:list[Sale]=Sale.findAll(mysql)
    purchases:list[Purchase]=Purchase.findAll(mysql)
    ans='欢迎来到矿石市场！\n'
    if sales:
        ans+='以下是所有处于摆卖中的商品:\n'
        for sale in sales:
            auction='是' if sale.auction else '否'
            starttime=datetime.fromtimestamp(float(sale.starttime)).strftime('%Y-%m-%d %H:%M:%S')
            endtime=datetime.fromtimestamp(float(sale.endtime)).strftime('%Y-%m-%d %H:%M:%S')
            ans+='交易编号:%s,矿石编号:%s,矿石数目:%s,拍卖:%s,起始时间:%s,结束时间:%s\n'\
                 %(sale.saleID,sale.mineralID,sale.mineralNum,auction,starttime,endtime)
    else:
        ans+='目前没有处于摆卖中的商品！\n'
    if purchases:
        ans+='以下是所有处于预订中的商品:\n'
        for purchase in purchases:
            starttime=datetime.fromtimestamp(float(purchase.starttime)).strftime('%Y-%m-%d %H:%M:%S')
            endtime=datetime.fromtimestamp(float(purchase.endtime)).strftime('%Y-%m-%d %H:%M:%S')
            ans+='交易编号:%s,矿石编号:%s,矿石数目:%s,起始时间:%s,结束时间:%s\n'\
                 %(purchase.purchaseID,purchase.mineralID,purchase.mineralNum,starttime,endtime)
    else:
        ans+='目前没有处于预订中的商品！\n'
    return ans

@handler("支付")
def pay(message_list,qid):
    # 格式1
    # 支付 q4867850 $20
    # 格式2
    # 支付 25778 $20
    assert len(message_list)==3,'支付失败:您的支付格式不正确！'
    target=str(message_list[1])
    assert message_list[2].startswith("$"),'支付失败:您的金额格式不正确！'
    try:
        money=int(str(message_list[2])[1:])
    except Exception:
        raise AssertionError("支付失败:金额格式不正确！应当为:$20")

    user:User=User.find(qid)

    assert user.money>=money,"支付失败:您的余额不足！"
    if target.startswith("q"):
        # 通过QQ号查找对方
        tqid:str=target[1:]
        tuser:User=User.find(tqid)
        assert tuser,"支付失败:QQ号为%s的用户未注册！"%tqid
    else:
        tschoolID:str=target
        # 通过学号查找
        assert User.findAll(mysql,'schoolID=?',(tschoolID,)),"支付失败:学号为%s的用户未注册！"%tschoolID
        tuser:User=User.findAll(mysql,'schoolID=?',(tschoolID,))[0]

    user.money-=money
    tuser.money+=round(money*(1-player_tax))

    user.update(mysql)
    tuser.update(mysql)

    return "支付成功！"

@handler("帮助")
def getHelp(message_list,qid):
    return help_msg


def dealWithRequest(funcStr,message_list,qid):
    if funcStr in commands:
        ans=commands[funcStr](message_list,qid)
    else:
        ans="未知命令:请输入'帮助'以获取帮助信息！"
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
