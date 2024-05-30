from datetime import datetime

from tools import send
from model import User,Mine,Sale,Purchase,Auction,Debt
from globalConfig import mysql,deposit

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