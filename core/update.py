import numpy as np

from staticFunctions import send,getnowtime,setTimeTask
from model import User,Mine,Sale,Purchase,Auction,Debt,Plan,Stock,Statistics
from globalConfig import mysql,deposit,effisItemCount,effisDailyDecreaseRate,vatRate
from staticFunctions import sqrtmoid, tech_validator,mineralSample,mineExpectation

def init():
    """
    防止由于程序中止而未能成功进行事务更新
    """
    nowtime=getnowtime()

    for user in User.findAll(mysql):
        updateForbidTime(user)

    for sale in Sale.findAll(mysql):
        if sale.endtime<=nowtime:
            updateSale(sale)
        else:
            setTimeTask(updateSale,sale.endtime,sale)
    for purchase in Purchase.findAll(mysql):
        if purchase.endtime<=nowtime:
            updatePurchase(purchase)
        else:
            setTimeTask(updatePurchase,purchase.endtime,purchase)
    for auction in Auction.findAll(mysql):
        if auction.endtime<=nowtime:
            updateAuction(auction)
        else:
            setTimeTask(updateAuction,auction.endtime,auction)
    for debt in Debt.findAll(mysql):
        if debt.endtime<=nowtime:
            updateDebt(debt)
        else:
            setTimeTask(updateDebt,debt.endtime,debt)
    for stock in Stock.findAll(mysql):
        if stock.primaryEndTime<=nowtime:
            updateStock(stock)
        else:
            setTimeTask(updateStock,stock.primaryEndTime,stock)
    for plan in Plan.findAll(mysql):
        if plan.enacted and (plan.timeEnacted+plan.timeRequired<=nowtime):
            updatePlan(plan)
        elif plan.enacted:
            setTimeTask(updatePlan,plan.timeEnacted+plan.timeRequired,plan)

def assetCalculation(user:User):
    assets = user.money
    for i in user.stocks.items():
        stock = Stock.find(i[0],mysql)
        assets += i[1] * stock.price
    for debt in Debt.findAll(mysql, 'creditor=?', (user.qid,)):
        assets += debt.money
    for debt in Debt.findAll(mysql, 'debitor=?', (user.qid,)):
        assets -= debt.money

    return assets

def updateForbidTime(user:User):
    user.forbidtime=[0]*len(user.forbidtime)
    user.save(mysql)

def updateAbundance():
    for mine in Mine.findAll(mysql):
        if mine.abundance==0.0:
            continue
        mine.abundance=round((1.25+mine.abundance)/2,2)
        if mine.abundance>1:
            mine.abundance=0.0
        mine.save(mysql)

def updateSale(sale:Sale):
    """
    :param sale: 到达截止时间的预售
    """
    qid:str=sale.qid
    tradeID:int=sale.tradeID
    user:User=User.find(qid,mysql)
    if Sale.find(tradeID,mysql) is None:#预售已成功进行
        return None
    if Sale.find(tradeID,mysql).starttime!=sale.starttime:
        return None

    mineralID:int=sale.mineralID
    mineralNum:int=sale.mineralNum
    mineral:dict[int,int]=user.mineral
    mineral.setdefault(mineralID,0)
    mineral[mineralID]+=mineralNum#将矿石返还给预售者
    user.mineral=mineral

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
    if Purchase.find(tradeID,mysql).starttime!=purchase.starttime:
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
    offersList:list=auction.offers

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
            tmineral:dict[int,int]=tuser.mineral
            tmineral.setdefault(mineralID,0)
            tmineral[mineralID]+=mineralNum#给予矿石
            tuser.mineral=tmineral
            tuser.inputTax += bids[0][1] * vatRate
            tuser.save(mysql)
            send(tqid,'您在拍卖:%s中竞拍成功，矿石已发送到您的账户'%tradeID,False)

            user.money+=bids[0][1]
            user.outputTax += bids[0][1]*vatRate
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
        mineral:dict[int,int]=user.mineral
        mineral.setdefault(mineralID,0)
        mineral[mineralID]+=mineralNum  #将矿石返还给拍卖者
        user.mineral=mineral

        user.save(mysql)
        auction.remove(mysql)

        send(qid,'您的拍卖:%s未能进行,矿石已返还到您的账户'%tradeID,False)

def updateDebt(debt:Debt):
    """
    :param debt: 到达截止时间的债券
    """
    creditorID:str=debt.creditor
    debitorID:str=debt.debitor
    interest:float=debt.interest
    debtID:int=debt.debtID
    money:int=round(debt.money*(1+interest))

    if Debt.find(debtID,mysql) is None:#债务已还清
        return None

    creditor:User=User.find(creditorID)
    if debitorID=='nobody':#未被借贷的债券
        creditor.money+=debt.money
        creditor.save(mysql)
        debt.remove(mysql)

        send(creditorID,'您的债券:%s未被借贷，金额已返还到您的账户'%debtID,False)
        return None

    debitor:User=User.find(debitorID)

    if debitor.money>=money:#还清贷款
        creditor.money+=money
        debitor.money-=money

        debt.remove(mysql)#删除债券
        creditor.save(mysql)
        debitor.save(mysql)

        send(creditorID,'您的债券:%s已还款完毕，金额已返还到您的账户！'%debtID,False)
        send(debitorID,'您的债券%s已强制还款，金额已从您的账户中扣除！'%debtID,False)
    else:#贷款无法还清
        money-=debitor.money
        creditor.money+=debitor.money
        debitor.money=0
        schoolID:str=debitor.schoolID
        mineral:dict[int,int]=debitor.mineral

        for mineralID in mineral.keys():
            if int(schoolID)%mineralID==0\
            or int(schoolID[:3])%mineralID==0\
            or int(schoolID[2:])%mineralID==0\
            or int(schoolID[:2]+'0'+schoolID[2:])%mineralID==0:
                while money>0 and mineral[mineralID]>0:
                    mineral[mineralID]-=1
                    money-=mineralID
                    creditor.money+=mineralID
                if money<0:
                    break
        debitor.mineral=mineral
        if money<=0:#还清贷款
            creditor.money+=money#兑换矿石多余的钱
            debitor.money-=money#兑换矿石多余的钱

            debt.remove(mysql)#删除债券
            creditor.save(mysql)
            debitor.save(mysql)

            send(creditorID,'您的债券:%s已还款完毕，金额已返还到您的账户！'%debtID,False)
            send(debitorID,'您的债券%s已强制还款，金额已从您的账户中扣除！'%debtID,False)
        else:#TODO:破产清算
            debitor.money=-money
            creditor.save(mysql)
            debitor.save(mysql)

def updateEfficiency(user:User,finishedPlan):
    """
    :param user : 涉及到的用户
    :param finishedPlan: 到达截止时间的生产计划，如无填0
    """
    nowtime = getnowtime()
    effis:dict = user.effis
    enactedPlansByType:dict = user.enactedPlanTypes
    lastUpdateTime = user.lastEffisUpdateTime
    elapsedTime = nowtime - lastUpdateTime
    for i in range(effisItemCount):
        enactedPlansByType.setdefault(i,0)
        effis.setdefault(i,0.0)
        if finishedPlan and i == finishedPlan.jobtype:
            if i == 4: # 特判炼油科技
                tech = user.tech['refine']
            else:
                tech = user.tech['industrial']
            effis[i] += 8 * finishedPlan.timeRequired * sqrtmoid(tech) * effisDailyDecreaseRate/86400
        elif enactedPlansByType[i] == 0:
            effis[i] -= elapsedTime * effisDailyDecreaseRate/86400
            effis[i] = max(0,effis[i])

    user.lastEffisUpdateTime = nowtime
    user.effis = effis
    user.save(mysql)
    
   
def updatePlan(plan:Plan):
    """
    :param plan: 到达截止时间的生产计划
    """
    qid: str = plan.qid
    planID: int = plan.planID
    user: User = User.find(qid, mysql)
    if Plan.find(planID, mysql) is None:  # 计划已取消
        return None

    products:dict=plan.products

    updateEfficiency(user, plan)  # 效率修正
    user.enactedPlanTypes[plan.jobtype] -= 1  # 取消当前门类的生产状态
    user.busyFactoryNum -= plan.factoryNum  # 释放被占用的工厂

    ans = ''
    if 0<=plan.jobtype<=4:
        mineral: dict[int,int]=user.mineral
        for mineralID,mineralNum in products.items():
            mineral.setdefault(mineralID,0)
            mineral[mineralID]+=mineralNum  # 将矿石增加给生产者
            if mineralID!=0:
                user.expr.setdefault(mineralID,0)
                user.expr[mineralID]+=mineralNum

        for mineralID,mineralNum in plan.ingredients.items():
            if mineralID!=0:
                user.expr.setdefault(mineralID,0)
                user.expr[mineralID]+=mineralNum

        if plan.jobtype==4:
            Statistics(timestamp=getnowtime(),money=0,fuel=products[0]).add(mysql)

        user.mineral=mineral  #更新矿石字典
        ans='您的生产:%s成功完成,矿石已增加到您的账户！'%planID
    elif plan.jobtype == 5:
        if 'factory' in products:
            ans = '您的工厂建设计划%s已完成！您的工厂数量已增加1'%planID
            user.misc[2] -= 1
            if user.misc[2] == 0:
                user.misc.pop(2)
            user.factoryNum += 1
        elif 'robot' in products:
            ans = '您的机器人建设计划%s已完成！您的采矿机器人数量已增加1'%planID
            user.robotNum += 1
            user.forbidtime.append(getnowtime())
    elif plan.jobtype == 6:
        validated_levels = tech_validator(plan.techName, plan.techPath, user.schoolID) #验证机返回给定技术路径前几级取得了成功
        if validated_levels == 0:  #第一级就验证失败
            ans='您的科研计划:%s已经失败！未能提高科研等级' % planID
        else: #有成功的部分
            valid_path = plan.techPath[:validated_levels]
            if not user.techCards[plan.techName]:  #第一次成功科研，对应科技门类还没有techcard记载
                user.techCards[plan.techName].append(valid_path) #直接设为主线
            elif valid_path in user.techCards[plan.techName]: # 没找到新东西
                ans='您的科研计划:%s成功，但是成功的部分技术路径（%s级）已经为您所知，未能提高科研等级！' % (planID, validated_levels)
            else: #有新成功的部分且不是第一次成功科研
                if validated_levels < len(plan.techPath): #部分成功
                    ans='您的科研计划:%s部分成功，前%s级技术路径可用！' % (planID, validated_levels)
                elif validated_levels == len(plan.techPath): #完全成功
                    ans='您的科研计划:%s完全成功，前%s级技术路径可用！' % (planID, validated_levels)

                if validated_levels > len(user.techCards[plan.techName][0]): # 新发现的科技路径比主线更强
                    user.techCards[plan.techName].insert(0, valid_path) #替换主线
                    user.tech[plan.techName] = 0.25*validated_levels #更新科技读数
                else:
                    user.techCards[plan.techName].append(valid_path) #增加一条后备线以供研究
    elif plan.jobtype == 7:
        scale = ((plan.workUnitsRequired - 10000)/300)**2
        indicator = np.random.random()
        if indicator > user.tech['extract']:
            ans='您的勘探:%s失败！' % planID
        elif indicator < user.tech['extract']*0.75: # 对数型矿井
            upper = mineralSample(int(0.9*scale),int(1.25*scale),logUniform=False)
            lower = mineralSample(2,int(0.5*upper),logUniform=True)
            mineID: int = max([0] + [mine.mineID for mine in Mine.findAll(mysql)]) + 1
            Mine(
                mineID=mineID,
                abundance=0.0,
                lower=lower,
                upper=upper,
                logUniform=True,
                expectation=mineExpectation(lower, upper, logUniform=True),
                private=True,
                open=False,
                owner=user.qid,
                entranceFee=0.0,
            ).add(mysql)
            user.mines.append(mineID)
            ans = '您的勘探:%s成功！矿井%s号已建立，为对数均匀分布类型，最小值%s，最大值%s。' % planID, mineID, lower, upper
        else:
            upper = mineralSample(int(0.75*scale),int(1.1*scale),logUniform=False)
            lower = mineralSample(2, int(0.5 * upper), logUniform=True)
            mineID: int = max([0] + [mine.mineID for mine in Mine.findAll(mysql)]) + 1
            Mine(
                mineID=mineID,
                abundance=0.0,
                lower=lower,
                upper=upper,
                logUniform=False,
                expectation=mineExpectation(lower, upper, logUniform=False),
                private=True,
                open=False,
                owner=user.qid,
                entranceFee=0.0,
            ).add(mysql)
            user.mines.append(mineID)
            ans = '您的勘探:%s成功！矿井%s号已建立，为均匀分布类型，最小值%s，最大值%s。' % planID, mineID, lower, upper

    send(qid, ans, False)
    
    user.save(mysql)
    plan.remove(mysql)

def updateStock(stock: Stock):
    stockNum=stock.stockNum
    openStockNum=stock.openStockNum
    selfRetain=stock.selfRetain
    price=stock.price
    soldNum=stockNum-openStockNum-selfRetain
    if stock.primaryClosed:
        return None
    if soldNum/(stockNum-selfRetain)*price<1:  # 调整价格小于每股1元
        send(stock.issuer,"您的股票%s在一级市场按%.2f认购了%s，调整后股价过低，上市失败！募集的资本将被退还给投资者。"%(stock.stockName,soldNum,price))
        shareholders: dict=stock.shareholders
        for holderID,amount in shareholders.items():
            holder=User.find(holderID,mysql)
            holder.stocks.pop(stock.stockID)
            if holderID!=stock.issuer:
                send(holderID,"股票%s发行失败！您的%.2f元资本已被退还给您。"%(stock.stockName,amount*price))
                holder.money+=amount*price
            holder.save(mysql)
        stock.remove(mysql)
    else:
        if openStockNum==0:
            newprice=price
            send(stock.issuer,"您的股票%s在一级市场已按%.2f一股全部认购完毕，上市成功！%.2f元资本已转移给您，股票将在下一次开盘进入二级市场交易！"
                 %(stock.stockName,price,stock.provisionalFunds))
        else:
            newprice=soldNum/(stockNum-selfRetain)*price
            send(stock.issuer,"您的股票%s在一级市场按%.2f认购了%s，调整后股价为%.2f，上市成功！%.2f元资本已转移给您，股票将在下一次开盘进入二级市场交易！"
                 %(stock.stockName,price,soldNum,newprice,stock.provisionalFunds))
            roundedSum=0
            for holderID,amount in stock.shareholders.items():
                holder=User.find(holderID,mysql)
                if holderID!=stock.issuer:
                    newAmount=round(amount*(stockNum-selfRetain)/soldNum)
                    roundedSum+=newAmount
                    send(holderID,
                         "股票%s未认购完，您的%s股将等比扩增为%s，发行价调整为%.2f。"%(stock.stockName,amount,newAmount,newprice))
                    holder.stocks[stock.stockID]=newAmount
                    stock.shareholders[holderID]=newAmount
                holder.save(mysql)
            selfRetain-=roundedSum-(stockNum-selfRetain)  # 四舍五入后的误差从自留股份中找补
            stock.selfRetain=selfRetain
            stock.shareholders[stock.issuer]=selfRetain
            holder=User.find(stock.issuer,mysql)
            holder.stocks[stock.stockID]=selfRetain

        stock.primaryClosed=True
        stock.secondaryOpen=True
        stock.histprice['adjustedIssuePrice']=newprice
        stock.price=newprice
        stock.openStockNum=0
        issuer: User=User.find(stock.issuer,mysql)
        issuer.money+=stock.provisionalFunds
        stock.provisionalFunds=0
        stock.save(mysql)
        issuer.save(mysql)