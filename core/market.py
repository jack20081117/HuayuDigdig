from datetime import datetime

from tools import drawtable,setTimeTask,send,generateTime,getnowtime
from model import User,Sale,Purchase,Auction
from globalConfig import mysql,deposit
from update import updateSale,updatePurchase,updateAuction

def presell(message_list:list[str],qid:str):
    """
    在市场上预售矿石
    :param message_list: 预售 矿石编号 矿石数量 价格 起始时间 终止时间
    :param qid: 预售者的qq号
    :return: 预售提示信息
    """
    assert len(message_list)==6,'预售失败:请按照规定格式进行预售！'
    nowtime:int=getnowtime()#现在的时间
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        price:int=int(message_list[3])
        if message_list[4]=='now':
            starttime:int=nowtime
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if generateTime(message_list[5]):
            endtime:int=starttime+generateTime(message_list[5])
        else:
            endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except ValueError:
        return '预售失败:请按照规定格式进行预售！'

    user:User=User.find(qid,mysql)
    mineral=user.mineral
    assert mineralNum>=1,'预售失败:您必须至少预售1个矿石！'
    assert mineralID in mineral,'预售失败:您不具备此矿石！'
    assert mineral[mineralID]>=mineralNum,'预售失败:您的矿石数量不足！'
    assert price>0,'预售失败:预售价格必须为正数！'
    assert endtime>nowtime,'预售失败:已经超过截止期限！'
    starttime=max(nowtime,starttime)

    mineral[mineralID]-=mineralNum
    if mineral[mineralID]<=0:
        mineral.pop(mineralID)

    user.mineral=mineral
    user.save(mysql)

    tradeID:int=max([0]+[sale.tradeID for sale in Sale.findAll(mysql)])+1

    sale:Sale=Sale(tradeID=tradeID,qid=qid,mineralID=mineralID,mineralNum=mineralNum,price=price,starttime=starttime,endtime=endtime)
    sale.add(mysql)
    setTimeTask(updateSale,endtime,sale)
    ans='预售成功！编号:%d'%tradeID
    return ans

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

    nowtime:int=getnowtime()#现在的时间
    assert qid!=tqid,'购买失败:您不能购买自己的商品！'
    assert nowtime>=starttime,'购买失败:尚未到开始购买时间！'
    assert nowtime<=endtime,'购买失败:此商品预售已结束！'
    assert user.money>=price,'购买失败:您的余额不足！'

    user.money-=price#付钱
    tuser:User=User.find(tqid,mysql)
    tuser.money+=price#得钱

    mineral=user.mineral
    if mineralID not in mineral:
        mineral[mineralID]=0
    mineral[mineralID]+=mineralNum#增加矿石
    user.mineral=mineral

    sale.remove(mysql)#删除市场上的此条记录
    user.save(mysql)
    tuser.save(mysql)

    ans='购买成功！'
    send(tqid,'您预售的商品(编号:%d)已被卖出！'%tradeID,False)
    return ans

def prebuy(message_list:list[str],qid:str):
    """
    在市场上预订矿石
    :param message_list: 预订 矿石编号 矿石数量 价格 起始时间 终止时间
    :param qid: 预订者的qq号
    :return: 预订提示信息
    """
    assert len(message_list)==6,'预订失败:请按照规定格式进行预订！'
    nowtime:int=getnowtime()#现在的时间
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        price:int=int(message_list[3])
        if message_list[4]=='现在' or message_list[4]=='now':
            starttime:int=nowtime
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if generateTime(message_list[5]):
            endtime:int=starttime+generateTime(message_list[5])
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
    assert isinstance(purchase.endtime, object)
    endtime:int=purchase.endtime

    nowtime:int=getnowtime()#现在的时间
    assert qid!=tqid,'售卖失败:您不能向自己售卖商品！'
    assert nowtime>=starttime,'售卖失败:尚未到开始售卖时间！'
    assert nowtime<=endtime,'售卖失败:此商品预订已结束！'

    mineral=user.mineral
    assert mineralID in mineral,'售卖失败:您不具备此矿石！'
    assert mineral[mineralID]>=mineralNum,'售卖失败:您的矿石数量不足！'
    mineral[mineralID]-=mineralNum
    if mineral[mineralID]<=0:
        mineral.pop(mineralID)

    user.money+=price  #得钱
    user.mineral=mineral
    user.save(mysql)

    tuser:User=User.find(tqid,mysql)

    tmineral=tuser.mineral
    if mineralID not in tmineral:
        tmineral[mineralID]=0
    tmineral[mineralID]+=mineralNum  #增加矿石
    tuser.mineral=tmineral

    purchase.remove(mysql)#删除市场上的此条记录

    tuser.save(mysql)

    ans='售卖成功！'
    send(tqid,'您预订的商品(编号:%d)已被买入！'%tradeID,False)
    return ans

def preauction(message_list:list[str],qid:str):
    """
    在市场上拍卖矿石
    :param message_list: 拍卖 矿石编号 矿石数量 底价 起始时间 终止时间 是否保密
    :param qid: 拍卖者的qq号
    :return: 拍卖提示信息
    """
    assert len(message_list)==7,'拍卖失败:请按照规定格式进行拍卖！'
    nowtime:int=getnowtime()#现在的时间
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        price:int=int(message_list[3])
        secret:bool=bool(int(message_list[6]))
        if message_list[4]=='现在' or message_list[4]=='now':
            starttime:int=nowtime
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if generateTime(message_list[5]):
            endtime:int=starttime+generateTime(message_list[5])
        else:
            endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except ValueError:
        return '拍卖失败:请按照规定格式进行拍卖！'

    user:User=User.find(qid,mysql)
    mineral=user.mineral
    assert mineralNum>=1,'拍卖失败:您必须至少拍卖1个矿石！'
    assert mineralID in mineral,'拍卖失败:您不具备此矿石！'
    assert mineral[mineralID]>=mineralNum,'拍卖失败:您的矿石数量不足！'
    assert price>0,'拍卖失败:底价必须为正数！'
    assert endtime>nowtime,'拍卖失败:已经超过截止期限！'
    starttime=max(nowtime,starttime)

    mineral[mineralID]-=mineralNum
    if mineral[mineralID]<=0:
        mineral.pop(mineralID)

    user.mineral=mineral
    user.save(mysql)

    tradeID:int=max([0]+[auction.tradeID for auction in Auction.findAll(mysql)])+1

    auction:Auction=Auction(tradeID=tradeID,qid=qid,mineralID=mineralID,mineralNum=mineralNum,price=price,
                            starttime=starttime,endtime=endtime,secret=secret,bestprice=0,offers='[]')
    auction.add(mysql)
    setTimeTask(updateAuction,endtime,auction)
    ans='拍卖成功！编号:%d'%tradeID
    return ans

def bid(message_list:list[str],qid:str):
    """
    在市场上对矿石进行投标
    :param message_list: 投标 拍卖编号 价格
    :param qid: 投标者的qq号
    :return: 投标提示信息
    """
    assert len(message_list)==3,'投标失败:请按照规定格式进行投标！'
    nowtime=getnowtime()#现在的时间
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