import json
import requests
import re
import markdown
import imgkit
import numpy as np
from datetime import datetime

from bot_model import *
from bot_functions import *


headers:dict={
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58'
}

imgkit_config=imgkit.config(wkhtmltoimage=r'D:/Program Files/wkhtmltopdf/bin/wkhtmltoimage.exe')

with open("./config.json","r",encoding='utf-8') as config:
    config=json.load(config)
env:str=config["env"]
player_tax:float=config["tax"]["player"]
deposit:float=config["deposit"]
delay:dict=config['delay']
group_ids:list=config['group_ids']
mysql:bool=(env=='prod')

def sigmoid(x:float)->float:return 1/(1+np.exp(-x))

commands:dict={}
effisStr=['分解效率','合成效率','复制效率','修饰效率','炼油效率','建工效率']

info_msg="查询到QQ号为:%s的用户信息\n"\
         "学号:%s\n"\
         "当前余额:%s\n"\
         "加工科技点:%s\n"\
         "开采科技点:%s\n"\
         "炼油科技点:%s\n"\
         "当前是否可开采:%s\n"\
         "以下为该用户拥有的矿石:\n%s"\
         "工厂数: %s\n"\
         "以下为该玩家各工种生产效率:\n%s"\
         "以下为该玩家拥有的私人矿井编号:\n%s"\

def handler(funcStr:str):
    """
    该装饰器装饰的函数会自动加入handle函数
    :param funcStr: 功能
    """
    def real_handler(func:callable):
        commands[funcStr]=func
        return func

    return real_handler

def init():
    """
    在矿井刷新时进行初始化
    """
    for user in User.findAll(mysql):
        user.digable=1
        user.save(mysql)
    for mine in Mine.findAll(mysql):
        mine.abundance=0.0
        mine.save(mysql)
    for debt in Debt.findAll(mysql):
        debt.money=round(debt.money*(1+debt.interest))
        debt.save(mysql)
    update()

def update():
    """
    防止由于程序中止而未能成功进行事务更新
    """
    nowtime=round(datetime.timestamp(datetime.now()))
    endedSales:list[Sale]=Sale.findAll(mysql,'endtime<?',(nowtime,))  #已经结束的预售
    endedPurchases:list[Purchase]=Purchase.findAll(mysql,'endtime<?',(nowtime,))  #已经结束的预订
    endedAuctions:list[Auction]=Auction.findAll(mysql,'endtime<?',(nowtime,)) #已经结束的拍卖
    endedDebts:list[Debt]=Debt.findAll(mysql,'endtime<?',(nowtime,))  #已经结束的债券

    for sale in endedSales:
        updateSale(sale)
    for purchase in endedPurchases:
        updatePurchase(purchase)
    for auction in endedAuctions:
        updateAuction(auction)
    for debt in endedDebts:
        updateDebt(debt)

def updateSale(sale:Sale):
    """
    :param sale: 到达截止时间的预售
    """
    qid:str=sale.qid
    tradeID:int=sale.tradeID
    user:User=User.find(qid,mysql)
    if Sale.find(tradeID,mysql) is None:#预售已成功进行
        return None

    mineralID:int=sale.mineralID
    mineralNum:int=sale.mineralNum
    mineralDict:dict=dict(eval(user.mineral))
    if mineralID not in mineralDict:
        mineralDict[mineralID]=0
    mineralDict[mineralID]+=mineralNum#将矿石返还给预售者
    user.mineral=str(mineralDict)

    user.save(mysql)
    sale.remove(mysql)

    send(qid,'您的预售:%s未能进行,矿石已返还到您的账户'%tradeID,False)

def updatePurchase(purchase:Purchase):
    """
    :param purchase: 到达截止时间的预订
    """
    qid:str=purchase.qid
    tradeID:int=purchase.tradeID
    user:User=User.find(qid,mysql)
    if Purchase.find(tradeID,mysql) is None:#预订已成功进行
        return None

    price:int=purchase.price
    user.money+=price#将钱返还给预订者

    user.save(mysql)
    purchase.remove(mysql)

    send(qid,'您的预订:%s未能进行,钱已返还到您的账户'%tradeID,False)

def updateAuction(auction:Auction):
    """
    :param auction: 到达截止时间的拍卖
    """
    qid:str=auction.qid
    tradeID:int=auction.tradeID
    user:User=User.find(qid,mysql)
    offersList:list=list(eval(auction.offers))

    bids:list[tuple[str,int,int]]=sorted(offersList,key=lambda t:(t[1],-t[2]),reverse=True)#先按出价从大到小排序再按时间从小到大排序
    mineralID:int=auction.mineralID
    mineralNum:int=auction.mineralNum
    while bids:
        success=False#投标是否成功
        tqid:str=bids[0][0]
        if len(bids)==1:
            bids.append(('nobody',auction.price,0))#默认最后一人
        if tqid=='nobody':#无人生还
            bids.pop()
            break
        tuser:User=User.find(tqid,mysql)
        if tuser.money+round(bids[0][1]*deposit)>=bids[1][1]:#第一人现金+第一人押金>=第二人出价
            success=True#投标成功
            tuser.money-=bids[0][1]-round(bids[0][1]*deposit)#扣除剩余金额
            tmineralDict:dict=dict(eval(tuser.mineral))
            if mineralID not in tmineralDict:
                tmineralDict[mineralID]=0
            tmineralDict[mineralID]+=mineralNum#给予矿石
            tuser.mineral=str(tmineralDict)
            tuser.save(mysql)
            send(tqid,'您在拍卖:%s中竞拍成功，矿石已发送到您的账户'%tradeID,False)

            user.money+=bids[0][1]
            user.save(mysql)

            for otherbid in bids[1:]:#返还剩余玩家押金
                if otherbid[0]=='nobody':
                    break
                otheruser=User.find(otherbid[0],mysql)
                otheruser.money+=round(otherbid[1]*deposit)
                otheruser.save(mysql)
                send(otheruser.qid,'您在拍卖:%s中竞拍失败，押金已返还到您的账户'%tradeID,False)

            auction.remove(mysql)

        else:#投标失败
            bids.pop(0)#去除第一人
            send(tqid,'您在拍卖:%s中竞拍失败，押金已扣除'%tradeID,False)
        if success:#结束投标
            break
    if not bids:
        mineralDict:dict=dict(eval(user.mineral))
        if mineralID not in mineralDict:
            mineralDict[mineralID]=0
        mineralDict[mineralID]+=mineralNum  #将矿石返还给拍卖者
        user.mineral=str(mineralDict)

        user.save(mysql)
        auction.remove(mysql)

        send(qid,'您的拍卖:%s未能进行,矿石已返还到您的账户'%tradeID,False)

def updateDebt(debt:Debt):
    """
    :param debt: 到达截止时间的债券
    """
    creditor_id:str=debt.creditor_id
    debitor_id:str=debt.debitor_id
    interest:float=debt.interest
    debtID:int=debt.debtID
    money:int=round(debt.money*(1+interest))

    if Debt.find(debtID,mysql) is None:#债务已还清
        return None

    creditor:User=User.find(creditor_id)
    if debitor_id=='nobody':#未被借贷的债券
        creditor.money+=debt.money
        creditor.save(mysql)
        debt.remove(mysql)

        send(creditor_id,'您的债券:%s未被借贷，金额已返还到您的账户'%debtID,False)
        return None

    debitor:User=User.find(debitor_id)

    if debitor.money>=money:#还清贷款
        creditor.money+=money
        debitor.money-=money

        debt.remove(mysql)#删除债券
        creditor.save(mysql)
        debitor.save(mysql)

        send(creditor_id,'您的债券:%s已还款完毕，金额已返还到您的账户！'%debtID,False)
        send(debitor_id,'您的债券%s已强制还款，金额已从您的账户中扣除！'%debtID,False)
    else:#贷款无法还清
        money-=debitor.money
        creditor.money+=debitor.money
        debitor.money=0
        schoolID:str=debitor.schoolID
        mineralDict=dict(eval(debitor.mineral))

        for mineralID in mineralDict.keys():
            if int(schoolID)%mineralID==0\
            or int(schoolID[:3])%mineralID==0\
            or int(schoolID[2:])%mineralID==0\
            or int(schoolID[:2]+'0'+schoolID[2:])%mineralID==0:
                while money>0 and mineralDict[mineralID]>0:
                    mineralDict[mineralID]-=1
                    money-=mineralID
                    creditor.money+=mineralID
                if money<0:
                    break
        debitor.mineral=str(mineralDict)
        if money<=0:#还清贷款
            creditor.money+=money#兑换矿石多余的钱
            debitor.money-=money#兑换矿石多余的钱

            debt.remove(mysql)#删除债券
            creditor.save(mysql)
            debitor.save(mysql)

            send(creditor_id,'您的债券:%s已还款完毕，金额已返还到您的账户！'%debtID,False)
            send(debitor_id,'您的债券%s已强制还款，金额已从您的账户中扣除！'%debtID,False)
        else:#TODO:破产清算
            debitor.money=-money
            creditor.save(mysql)
            debitor.save(mysql)

def extract(qid,mineralID,mineID):
    """获取矿石
    :param qid:开采者的qq号
    :param mineralID:开采得矿石的编号
    :param mineID:矿井编号
    :return:开采信息
    """
    mine:Mine=Mine.find(mineID,mysql)
    abundance:float=mine.abundance #矿井丰度
    user:User=User.find(qid,mysql)
    mineral=user.mineral # 用户拥有的矿石（str of dict）
    extractTech:float=user.extract_tech # 开采科技

    assert user.digable,'开采失败:您必须等到下一个整点才能再次开采矿井！'

    # 决定概率 
    if abundance==0.0:#若矿井未被开采过，则首次成功率为100%
        prob=1.0
    else:
        prob=round(abundance*sigmoid(extractTech),2)

    if np.random.random()>prob:#开采失败
        user.digable=0#在下一次刷新前不可开采
        user.save(mysql)
        ans='开采失败:您的运气不佳，未能开采成功！'
    else:
        mineralDict:dict[int,int]=dict(eval(mineral))
        if mineralID not in mineralDict:#用户不具备此矿石
            mineralDict[mineralID]=0
        mineralDict[mineralID]+=1 #加一个矿石
        user.mineral=str(mineralDict)
        user.save(mysql)
        mine.abundance=prob#若开采成功，则后一次的丰度是前一次的成功概率
        mine.save(mysql)
        ans='开采成功！您获得了编号为%d的矿石！'%mineralID
    return ans

  
@handler("time")
def returnTime(m,q):
    """
    返回当前时间
    """
    return '当前时间为:%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@handler("注册")
def signup(message_list:list[str],qid:str):
    """
    用户注册
    :param message_list: 注册 学号
    :param qid: 注册者的qq号
    :return: 注册提示信息
    """
    assert len(message_list)==2 and re.match(r'\d{5}',message_list[1]) and len(message_list[1])==5,'注册失败:请注意您的输入格式！'
    schoolID:str=message_list[1]
    assert not User.find(qid,mysql) and not User.findAll(mysql,'schoolID=?',(schoolID,)),'注册失败:您已经注册过，无法重复注册！'
    user=User(
        qid=qid,schoolID=schoolID,money=0,mineral='{}',
        process_tech=0.0,extract_tech=0.0,refine_tech=0.0,digable=1,
        factory_num=0,effis='[0.0,0.0,0.0,0.0,0.0,0.0]',mines='[]'
    )#注册新用户
    user.add(mysql)
    ans="注册成功！"
    return ans

@handler("开采")
def getMineral(message_list:list[str],qid:str):
    """
    根据传入的信息开采矿井
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
def exchange(message_list:list[str],qid:str):
    """
    兑换矿石
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
    user.save(mysql)

    ans='兑换成功！'
    return ans


@handler("查询")
def getUserInfo(message_list:list[str],qid:str):
    """
    查询用户个人信息
    :param message_list: 查询
    :param qid: 查询者的qq号
    :return: 查询提示信息
    """
    user:User=User.find(qid,mysql)
    schoolID:str=user.schoolID
    money:int=user.money
    mineral:str=user.mineral
    processTech:float=user.process_tech
    extractTech:float=user.extract_tech
    refineTech:float=user.refine_tech
    digable:bool=user.digable
    mineralDict:dict=dict(eval(mineral))
    factory_num:int=user.factory_num
    effisList:list=list(eval(user.effis))
    mineList:list=list(eval(user.mines))
    sortedMineralDict:dict={key:mineralDict[key] for key in sorted(mineralDict.keys())}

    mres:str=""
    for mid,mnum in sortedMineralDict.items():
        if mid==0:
            mres+="燃油%s个单位；\n"%mnum
        else:
            mres+="编号%s的矿石%s个；\n"%(mid,mnum)

    eres:str=''    #生产效率信息
    for index in range(6):
        eres+=effisStr[index]+":%s\n" % effisList[index]

    mineres:str='' #私有矿井信息
    for mine in mineList:
        mineres+='%s,' % mine

    ans:str=info_msg%(qid,schoolID,money,processTech,extractTech,refineTech,digable,
                  mres,factory_num,eres,mineres)
    return ans

@handler("预售")
def presell(message_list:list[str],qid:str):
    """
    在市场上预售矿石
    :param message_list: 预售 矿石编号 矿石数量 价格 起始时间 终止时间
    :param qid: 预售者的qq号
    :return: 预售提示信息
    """
    assert len(message_list)==6,'预售失败:请按照规定格式进行预售！'
    nowtime:int=round(datetime.timestamp(datetime.now()))
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        price:int=int(message_list[3])
        if message_list[4]=='now':
            starttime:int=nowtime
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if message_list[5] in delay:
            endtime:int=starttime+delay[message_list[5]]
        else:
            endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except ValueError:
        return '预售失败:请按照规定格式进行预售！'

    user:User=User.find(qid,mysql)
    mineralDict:dict=dict(eval(user.mineral))
    assert mineralNum>=1,'预售失败:您必须至少预售1个矿石！'
    assert mineralID in mineralDict,'预售失败:您不具备此矿石！'
    assert mineralDict[mineralID]>=mineralNum,'预售失败:您的矿石数量不足！'
    assert price>0,'预售失败:预售价格必须为正数！'
    assert endtime>nowtime,'预售失败:已经超过截止期限！'
    starttime=max(nowtime,starttime)

    mineralDict[mineralID]-=mineralNum
    if mineralDict[mineralID]<=0:mineralDict.pop(mineralID)

    user.mineral=str(mineralDict)
    user.save(mysql)

    tradeID:int=max([0]+[sale.tradeID for sale in Sale.findAll(mysql)])+1

    sale:Sale=Sale(tradeID=tradeID,qid=qid,mineralID=mineralID,mineralNum=mineralNum,price=price,starttime=starttime,endtime=endtime)
    sale.add(mysql)
    setTimeTask(updateSale,endtime,sale)
    ans='预售成功！编号:%d'%tradeID
    return ans

@handler("购买")
def buy(message_list:list[str],qid:str):
    """
    在市场上购买矿石
    :param message_list: 购买 预售编号
    :param qid: 购买者的qq号
    :return: 购买提示信息
    """
    assert len(message_list)==2,'购买失败:请按照规定格式进行购买！'
    try:
        tradeID:int=int(message_list[1])
    except ValueError:
        return '购买失败:请按照规定格式进行购买！'
    sale:Sale=Sale.find(tradeID,mysql)
    assert sale,'购买失败:不存在此卖品！'
    user:User=User.find(qid,mysql)

    tqid=sale.qid
    mineralID:int=sale.mineralID
    mineralNum:int=sale.mineralNum
    price:int=sale.price
    starttime:int=sale.starttime
    endtime:int=sale.endtime

    nowtime:int=round(datetime.timestamp(datetime.now()))#现在的时间
    assert qid!=tqid,'购买失败:您不能购买自己的商品！'
    assert nowtime>=starttime,'购买失败:尚未到开始购买时间！'
    assert nowtime<=endtime,'购买失败:此商品预售已结束！'
    assert user.money>=price,'购买失败:您的余额不足！'

    user.money-=price#付钱
    tuser:User=User.find(tqid,mysql)
    tuser.money+=price#得钱

    mineralDict:dict=dict(eval(user.mineral))
    if mineralID not in mineralDict:
        mineralDict[mineralID]=0
    mineralDict[mineralID]+=mineralNum#增加矿石
    user.mineral=str(mineralDict)

    sale.remove(mysql)#删除市场上的此条记录
    user.save(mysql)
    tuser.save(mysql)

    ans='购买成功！'
    send(tqid,'您预售的商品(编号:%d)已被卖出！'%tradeID,False)
    return ans

@handler('预订')
def prebuy(message_list:list[str],qid:str):
    """
    在市场上预订矿石
    :param message_list: 预订 矿石编号 矿石数量 价格 起始时间 终止时间
    :param qid: 预订者的qq号
    :return: 预订提示信息
    """
    assert len(message_list)==6,'预订失败:请按照规定格式进行预订！'
    nowtime:int=round(datetime.timestamp(datetime.now()))
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        price:int=int(message_list[3])
        if message_list[4]=='现在' or message_list[4]=='now':
            starttime:int=nowtime
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if message_list[5] in delay:
            endtime:int=starttime+delay[message_list[5]]
        else:
            endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except ValueError:
        return '预订失败:请按照规定格式进行预订！'
    user:User=User.find(qid,mysql)

    assert user.money>=price,'预订失败:您的余额不足！'
    assert price>0,'预订失败:预订价格必须为正数！'
    assert endtime>nowtime,'预订失败:已经超过截止期限！'
    starttime=max(nowtime,starttime)
    user.money-=price

    tradeID:int=max([0]+[purchase.tradeID for purchase in Purchase.findAll(mysql)])+1

    purchase:Purchase=Purchase(tradeID=tradeID,qid=qid,mineralID=mineralID,mineralNum=mineralNum,price=price,starttime=starttime,endtime=endtime)
    purchase.add(mysql)
    setTimeTask(updatePurchase,endtime,purchase)
    user.save(mysql)

    ans='预订成功！编号:%d'%tradeID
    return ans

@handler('售卖')
def sell(message_list:list[str],qid:str):
    """
    在市场上售卖矿石
    :param message_list: 售卖 预订编号
    :param qid: 售卖者的qq号
    :return: 售卖提示信息
    """
    assert len(message_list)==2,'售卖失败:请按照规定进行售卖！'
    try:
        tradeID:int=int(message_list[1])
    except ValueError:
        return '购买失败:请按照规定格式进行购买！'
    purchase:Purchase=Purchase.find(tradeID,mysql)
    assert purchase,'购买失败:不存在此卖品！'
    user:User=User.find(qid,mysql)

    tqid:str=purchase.qid
    mineralID:int=purchase.mineralID
    mineralNum:int=purchase.mineralNum
    price:int=purchase.price
    starttime:int=purchase.starttime
    endtime:int=purchase.endtime

    nowtime:int=round(datetime.timestamp(datetime.now()))  #现在的时间
    assert qid!=tqid,'售卖失败:您不能向自己售卖商品！'
    assert nowtime>=starttime,'售卖失败:尚未到开始售卖时间！'
    assert nowtime<=endtime,'售卖失败:此商品预订已结束！'

    mineralDict:dict=dict(eval(user.mineral))
    assert mineralID in mineralDict,'售卖失败:您不具备此矿石！'
    assert mineralDict[mineralID]>=mineralNum,'售卖失败:您的矿石数量不足！'
    mineralDict[mineralID]-=mineralNum
    if mineralDict[mineralID]<=0:mineralDict.pop(mineralID)

    user.money+=price  #得钱
    user.mineral=str(mineralDict)
    user.save(mysql)

    tuser:User=User.find(tqid,mysql)

    tmineralDict:dict=dict(eval(tuser.mineral))
    if mineralID not in tmineralDict:
        tmineralDict[mineralID]=0
    tmineralDict[mineralID]+=mineralNum  #增加矿石
    tuser.mineral=str(tmineralDict)

    purchase.remove(mysql)#删除市场上的此条记录

    tuser.save(mysql)

    ans='售卖成功！'
    send(tqid,'您预订的商品(编号:%d)已被买入！'%tradeID,False)
    return ans

@handler("拍卖")
def preauction(message_list:list[str],qid:str):
    """
    在市场上拍卖矿石
    :param message_list: 拍卖 矿石编号 矿石数量 底价 起始时间 终止时间 是否保密
    :param qid: 拍卖者的qq号
    :return: 拍卖提示信息
    """
    assert len(message_list)==7,'拍卖失败:请按照规定格式进行拍卖！'
    nowtime:int=round(datetime.timestamp(datetime.now()))
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        price:int=int(message_list[3])
        secret:bool=bool(int(message_list[6]))
        if message_list[4]=='现在' or message_list[4]=='now':
            starttime:int=nowtime
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if message_list[5] in delay:
            endtime:int=starttime+delay[message_list[5]]
        else:
            endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except ValueError:
        return '拍卖失败:请按照规定格式进行拍卖！'

    user:User=User.find(qid,mysql)
    mineralDict:dict=dict(eval(user.mineral))
    assert mineralNum>=1,'拍卖失败:您必须至少拍卖1个矿石！'
    assert mineralID in mineralDict,'拍卖失败:您不具备此矿石！'
    assert mineralDict[mineralID]>=mineralNum,'拍卖失败:您的矿石数量不足！'
    assert price>0,'拍卖失败:底价必须为正数！'
    assert endtime>nowtime,'拍卖失败:已经超过截止期限！'
    starttime=max(nowtime,starttime)

    mineralDict[mineralID]-=mineralNum
    if mineralDict[mineralID]<=0:mineralDict.pop(mineralID)

    user.mineral=str(mineralDict)
    user.save(mysql)

    tradeID:int=max([0]+[auction.tradeID for auction in Auction.findAll(mysql)])+1

    auction:Auction=Auction(tradeID=tradeID,qid=qid,mineralID=mineralID,mineralNum=mineralNum,price=price,
                            starttime=starttime,endtime=endtime,secret=secret,bestprice=0,offers='[]')
    auction.add(mysql)
    setTimeTask(updateAuction,endtime,auction)
    ans='拍卖成功！编号:%d'%tradeID
    return ans

@handler("投标")
def bid(message_list:list[str],qid:str):
    """
    在市场上对矿石进行投标
    :param message_list: 投标 拍卖编号 价格
    :param qid: 投标者的qq号
    :return: 投标提示信息
    """
    assert len(message_list)==3,'投标失败:请按照规定格式进行投标！'
    nowtime=datetime.timestamp(datetime.now())
    try:
        tradeID:int=int(message_list[1])
        userprice:int=int(message_list[2])
    except ValueError:
        return '投标失败:请按照规定格式进行投标！'
    auction:Auction=Auction.find(tradeID,mysql)
    assert auction,'投标失败:不存在此卖品！'
    user:User=User.find(qid,mysql)

    tqid:str=auction.qid
    mineralID:int=auction.mineralID
    mineralNum:int=auction.mineralNum
    price:int=auction.price
    starttime:int=auction.starttime
    endtime:int=auction.endtime
    secret:bool=auction.secret#是否对出价保密

    nowtime=round(datetime.timestamp(datetime.now()))#现在的时间
    assert qid!=tqid,'投标失败:您不能购买自己的商品！'
    assert nowtime>=starttime,'投标失败:尚未到开始拍卖时间！'
    assert nowtime<=endtime,'投标失败:此商品拍卖已结束！'
    assert userprice>0,'投标失败:您的出价必须为正数！'
    assert userprice>=price,'投标失败:您的出价低于底价！'
    assert user.money>=round(userprice*deposit),'投标失败:您的余额不足以支付押金！'

    if secret:#对出价保密
        user.money-=round(userprice*deposit)#支付押金
    else:#不对出价保密
        bestprice=auction.bestprice#当前最高价
        assert userprice>bestprice,'投标失败:您的出价低于当前最高价！'
        user.money-=round(userprice*deposit)#支付押金

    offersList:list[tuple[str,str,int]]=list(eval(auction.offers))
    offersList.append((qid,userprice,nowtime))
    auction.bestprice=max(userprice,auction.bestprice)
    auction.offers=str(offersList)

    auction.save(mysql)
    user.save(mysql)
    ans='投标成功！'
    return ans

@handler("市场")
def mineralMarket(message_list:list[str],qid:str):
    """
    查看市场
    :param message_list: 市场
    :param qid:
    :return: 提示信息
    """
    sales:list[Sale]=Sale.findAll(mysql)
    purchases:list[Purchase]=Purchase.findAll(mysql)
    auctions:list[Auction]=Auction.findAll(mysql)
    ans='欢迎来到矿石市场！\n'

    if sales:
        ans+='以下是所有处于预售中的商品:\n'
        saleData=[['交易编号','矿石编号','矿石数目','价格','起始时间','结束时间']]
        for sale in sales:
            starttime:str=datetime.fromtimestamp(float(sale.starttime)).strftime('%Y-%m-%d %H:%M:%S')
            endtime:str=datetime.fromtimestamp(float(sale.endtime)).strftime('%Y-%m-%d %H:%M:%S')
            saleData.append([sale.tradeID,sale.mineralID,sale.mineralNum,sale.price,starttime,endtime])
        drawtable(saleData,'sale.png')
        ans+='[CQ:image,file=sale.png]\n'
    else:
        ans+='目前没有处于预售中的商品！\n'

    if purchases:
        ans+='以下是所有处于预订中的商品:\n'
        purchaseData=[['交易编号','矿石编号','矿石数目','价格','起始时间','结束时间']]
        for purchase in purchases:
            starttime:str=datetime.fromtimestamp(float(purchase.starttime)).strftime('%Y-%m-%d %H:%M:%S')
            endtime:str=datetime.fromtimestamp(float(purchase.endtime)).strftime('%Y-%m-%d %H:%M:%S')
            purchaseData.append([purchase.tradeID,purchase.mineralID,purchase.mineralNum,purchase.price,starttime,endtime])
        drawtable(purchaseData,'purchase.png')
        ans+='[CQ:image,file=purchase.png]\n'
    else:
        ans+='目前没有处于预订中的商品！\n'

    if auctions:
        ans+='以下是所有处于拍卖中的商品:\n'
        auctionData=[['交易编号','矿石编号','矿石数目','底价','起始时间','结束时间','当前最高价']]
        for auction in auctions:
            starttime:str=datetime.fromtimestamp(float(auction.starttime)).strftime('%Y-%m-%d %H:%M:%S')
            endtime:str=datetime.fromtimestamp(float(auction.endtime)).strftime('%Y-%m-%d %H:%M:%S')
            auctionDatum=[auction.tradeID,auction.mineralID,auction.mineralNum,auction.price,starttime,endtime]
            if auction.secret:
                auctionDatum.append('-')
            else:
                auctionDatum.append(auction.bestprice)
            auctionData.append(auctionDatum)
        drawtable(auctionData,'auction.png')
        ans+='[CQ:image,file=auction.png]\n'
    else:
        ans+='目前没有处于拍卖中的商品！\n'

    return ans

@handler("发行")
def issue(message_list:list[str],qid:str):
    """
    :param message_list: 发行 股票名称 缩写 发行量 价格 自我保留比例
    :param qid: 发行者的qq号
    :return: 发行提示信息
    """
    assert len(message_list)==6,'发行失败:您的发行格式不正确！'
    stockName:str=message_list[1]
    stockID:str=message_list[2]
    assert len(stockName)<=8,'发行失败:股票名称必须在8个字符以内！'
    assert len(stockID)==3,'发行失败:股票缩写必须为3个字符！'
    stockNum:int=int(message_list[3])
    assert 10000<=stockNum<=100000,'发行失败:股票发行量必须在10000股到100000股之间！'
    price:int=int(message_list[4])
    selfRetain:float=float(message_list[5])

    stock=Stock(stockID=stockID,stockName=stockName,stockNum=stockNum,issue_qid=qid,price=price,self_retain=selfRetain,
                histprice='{}',shareholders='{}',avg_dividend=0.0)
    stock.add(mysql)
    ans='发行成功！'

@handler('股市')
def stockMarket(message_list:list[str],qid:str):
    """
    :param message_list: 股市
    :param qid:
    :return: 提示信息
    """
    stocks:list[Stock]=Stock.findAll(mysql)
    ans='欢迎来到股市！\n'
    if stocks:
        ans+='以下是所有目前发行的股票:\n'
        stockData=[['股票名称','股票缩写','发行量','当前股价']]
        for stock in stocks:
            stockData.append([stock.stockName,stock.stockID,stock.stockNum,stock.price])
        drawtable(stockData,'stock.png')
        ans+='[CQ:image,file=stock.png]'
    else:
        ans+='目前没有发行的股票！'
    return ans

@handler("支付")
def pay(message_list:list[str],qid:str):
    """
    :param message_list: 支付 q`QQ号`/`学号` $`金额`
    :param qid: 支付者的qq号
    :return: 支付提示信息
    """
    assert len(message_list)==3,'支付失败:您的支付格式不正确！'
    target=str(message_list[1])
    assert message_list[2].startswith("$"),'支付失败:您的金额格式不正确！'
    try:
        money:int=int(str(message_list[2])[1:])
    except ValueError:
        return "支付失败:您的金额格式不正确！应当为:$`金额`"

    user:User=User.find(qid,mysql)

    assert user.money>=money,"支付失败:您的余额不足！"
    if target.startswith("q"):
        # 通过QQ号查找对方
        tqid:str=target[1:]
        tuser:User=User.find(tqid,mysql)
        assert tuser,"支付失败:QQ号为%s的用户未注册！"%tqid
    else:
        tschoolID:str=target
        # 通过学号查找
        assert User.findAll(mysql,'schoolID=?',(tschoolID,)),"支付失败:学号为%s的用户未注册！"%tschoolID
        tuser:User=User.findAll(mysql,'schoolID=?',(tschoolID,))[0]

    user.money-=money
    tuser.money+=round(money*(1-player_tax))

    user.save(mysql)
    tuser.save(mysql)

    return "支付成功！"

@handler("帮助")
def getHelp(message_list:list[str],qid:str):
    with open('help_msg.md','r',encoding='utf-8') as help_msg:
        html=markdown.markdown(help_msg.read())
    imgkit.from_string(html,'../go-cqhttp/data/images/help.png',config=imgkit_config,css='./style.css')
    ans='[CQ:image,file=help.png]'
    return ans

@handler("放贷")
def prelend(message_list:list[str],qid:str):
    """
    :param message_list: 放贷 金额 放贷时间 利率 起始时间 终止时间
    :param qid: 放贷者的qq号
    :return: 放贷提示信息
    """
    assert len(message_list)==6,'放贷失败:您的放贷格式不正确！'
    nowtime:int=round(datetime.timestamp(datetime.now()))
    try:
        money=int(message_list[1])
        debttime=message_list[2]
        interest=float(message_list[3])
        if message_list[4]=='现在' or message_list[4]=='now':
            starttime:int=nowtime
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if message_list[5] in delay:
            endtime:int=starttime+delay[message_list[5]]
        else:
            endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except ValueError:
        return "放贷失败:您的金额格式不正确！"

    duration:int=0
    if debttime.endswith("m"):
        duration=int(debttime[:-1])*60
    elif debttime.endswith("h"):
        duration=int(debttime[:-1])*3600
    elif debttime.endswith("d"):
        duration=int(debttime[:-1])*86400
    else:
        return "放贷失败:您的时间格式不正确！应当为:`借出时间`(m/h/d)"

    creditor=User.find(qid,mysql)
    assert creditor.money>money,"放贷失败:您的余额不足！"
    assert endtime>nowtime,'放贷失败:已经超过截止期限！'
    starttime=max(nowtime,starttime)
    creditor.money-=money
    creditor.save(mysql)

    debtID:int=max([0]+[debt.debtID for debt in Debt.findAll(mysql)])+1
    debt=Debt(debtID=debtID,creditor_id=qid,debitor_id='nobody',money=money,
              duration=duration,starttime=starttime,endtime=endtime,interest=float(interest))
    debt.add(mysql)
    setTimeTask(updateDebt,endtime,debt)

    ans='放贷成功！'
    return ans

@handler("借贷")
def borrow(message_list:list[str],qid:str):
    """
    :param message_list: 借贷 债券编号 金额
    :param qid: 借贷者的qq号
    :return: 借贷提示信息
    """
    assert len(message_list)==3,"借贷失败:您的借贷格式不正确！"
    nowtime:int=round(datetime.timestamp(datetime.now()))
    try:
        debtID:int=int(message_list[1])
        money:int=int(message_list[2])
    except ValueError:
        return "借贷失败:您的借贷格式不正确！"
    debt=Debt.find(debtID,mysql)
    assert debt is not None,"借贷失败:不存在此债券！"
    assert debt.debitor_id=='nobody',"借贷失败:此债券已被贷款！"
    assert debt.creditor_id!=qid,'借贷失败:您不能向自己贷款！'
    assert money>0,"借贷失败:借贷金额必须为正！"
    assert debt.money>=money,"借贷失败:贷款金额过大！"
    assert debt.starttime<nowtime,"借贷失败:此债券尚未开始放贷！"
    assert debt.endtime>nowtime,"借贷失败:此债券已结束放贷！"

    debt.money-=money
    debt.save(mysql)
    creditor_id=debt.creditor_id
    duration=debt.duration
    interest=debt.interest
    if debt.money<=0:
        debt.remove(mysql)

    newdebtID:int=max([0]+[debt.debtID for debt in Debt.findAll(mysql)])+1
    newdebt=Debt(debtID=newdebtID,creditor_id=creditor_id,debitor_id=qid,money=money,
                 duration=duration,starttime=nowtime,endtime=nowtime+duration,interest=interest)
    newdebt.add(mysql)
    setTimeTask(updateDebt,nowtime+duration,newdebt)

    debitor=User.find(qid,mysql)
    debitor.money+=money
    debitor.save(mysql)

    ans='借贷成功！请注意在借贷时限内还款！'
    return ans

@handler("还款")
def repay(message_list:list[str],qid:str):
    """
    :param message_list: 还款 债券编号 金额
    :param qid: 还款者的qq号
    :return: 还款提示信息
    """
    assert len(message_list)==3,'还款失败:您的还款格式不正确！'
    nowtime:int=round(datetime.timestamp(datetime.now()))
    try:
        debtID:int=int(message_list[1])
        money:int=int(message_list[2])
    except ValueError:
        return '还款失败:您的还款格式不正确！'
    debt=Debt.find(debtID,mysql)
    debitor=User.find(qid,mysql)
    assert debt is not None,"还款失败:不存在此债券！"
    assert debt.debitor_id==qid,'还款失败:您不是此债券的债务人！'
    assert money>0,'还款失败:还款金额必须为正！'
    assert debitor.money>money,'还款失败:您的余额不足！'
    assert debt.endtime>nowtime,'还款失败:此债券已结束还款！'

    if money>=debt.money:
        debitor.money-=(money-debt.money)#返还多余的还款
        debitor.save(mysql)
        debt.remove(mysql)
        ans='还款成功！您已还清此贷款！'
        send(debt.creditor_id,'您的债券:%s已还款完毕，贷款已送到您的账户'%debtID,False)
    else:
        debt.money-=money
        debitor.money-=money
        debt.save(mysql)
        debitor.save(mysql)
        ans='还款成功！剩余贷款金额:%d'%debt.money
    return ans

@handler("债市")
def debtMarket(message_list:list[str],qid:str):
    """
    :param message_list: 债市
    :param qid:
    :return: 提示信息
    """
    debts:list[Debt]=Debt.findAll(mysql,where='debitor_id=?',args=('nobody',))
    ans='欢迎来到债市！\n'
    if debts:
        ans+='以下是所有目前可借的贷款:\n'
        debtData=[['债券编号','金额','债权人','借出时间','利率','起始时间','终止时间']]
        for debt in debts:
            debttime:str=''
            if debt.duration//86400:
                debttime+='%d天'%(debt.duration//86400)
            if (debt.duration%86400)//3600:
                debttime+='%d小时'%((debt.duration%86400)//3600)
            if (debt.duration%3600)//60:
                debttime+='%d分钟'%((debt.duration%3600)//60)
            starttime:str=datetime.fromtimestamp(float(debt.starttime)).strftime('%Y-%m-%d %H:%M:%S')
            endtime:str=datetime.fromtimestamp(float(debt.endtime)).strftime('%Y-%m-%d %H:%M:%S')
            debtData.append([debt.debtID,debt.money,debt.creditor_id,debttime,debt.interest,starttime,endtime])
        drawtable(debtData,'debt.png')
        ans+='[CQ:image,file=debt.png]'
    else:
        ans+='目前没有可借的贷款！'
    return ans

def dealWithRequest(funcStr:str,message_list:list[str],qid:str):
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
