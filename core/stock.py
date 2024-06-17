import numpy as np
from matplotlib import pyplot as plt
from datetime import datetime
from typing import TypedDict

from tools import drawtable, setTimeTask, getnowtime, getnowdate,send
from model import User, Stock, Order, StockData
from globalConfig import mysql, groupIDs
import globalConfig

def issueStock(messageList: list[str], qid: str):
    """
    :param messageList: 发行 股票名称 缩写 发行量 价格 自我保留股数
    :param qid: 发行者的qq号
    :return: 发行提示信息
    """
    assert len(messageList) == 6, '发行失败:您的发行格式不正确！'

    stockName: str = messageList[1]
    stockID: str = messageList[2]
    assert 3 < len(stockName) <= 12, '发行失败:股票名称必须为4-12个字符！'
    assert not Stock.findAll(mysql, 'stockName=?', (stockName,)), "发行失败:该股票名称已经被占用！"

    assert len(stockID) == 3, '发行失败:股票缩写必须为3个字符！'
    assert not Stock.find(stockID, mysql), "发行失败:该股票缩写已经被占用！"

    issuer: User = User.find(qid, mysql)
    assert issuer.money >= 1000,'发行失败：要发行股票，您需要证明自己至少有1000元资产（不会扣除）！'

    stockNum: int = int(messageList[3])
    assert 10000 <= stockNum <= 100000, '发行失败:股票发行量必须在10000股到100000股之间！'

    price: float = float(messageList[4])
    assert price < 100, '发行失败：初始股价过高！'

    selfRetain: int = int(messageList[5])
    assert 0 <= selfRetain < 0.5 * stockNum, '发行失败:自我持有量过低或过高！'

    nowtime = getnowtime()
    primaryEndTime = nowtime + 86400
    stock = Stock(stockID=stockID,
                  stockName=stockName,
                  stockNum=stockNum,
                  openStockNum=stockNum - selfRetain,
                  provisionalFunds=0,
                  issuer=qid,
                  price=price,
                  selfRetain=selfRetain,
                  primaryEndTime=primaryEndTime,
                  bidders=[],
                  askers=[],
                  histprice={'designatedIssuePrice': price},
                  shareholders={qid: selfRetain},
                  primaryClosed=False,
                  secondaryOpen=False,
                  isIndex=False,
                  avgDividend=0.0)
    stock.add(mysql)
    issuer.stocks[stockID] = selfRetain
    issuer.save(mysql)
    setTimeTask(primaryClosing, primaryEndTime, stock)  # 一级市场认购结束事件
    ans = '发行成功！您的股票将在一级市场开放认购24小时，随后开始在二级市场流通。'
    return ans


def primaryClosing(stock: Stock):
    stockNum = stock.stockNum
    openStockNum = stock.openStockNum
    selfRetain = stock.selfRetain
    price = stock.price
    soldNum = stockNum - openStockNum - selfRetain
    # if stock.primaryClosed:
    #     return None
    if soldNum / (stockNum - selfRetain) * price < 1:  # 调整价格小于每股1元
        send(stock.issuer, "您的股票%s在一级市场按%.2f认购了%s，调整后股价过低，上市失败！募集的资本将被退还给投资者。" % (stock.stockName, soldNum, price))
        shareholders: dict = stock.shareholders
        for holderID, amount in shareholders.items():
            holder = User.find(holderID, mysql)
            holder.stock.pop(stock.stockID)
            if holderID != stock.issuer:
                send(holderID, "股票%s发行失败！您的%.2f元资本已被退还给您。" % (stock.stockName, amount * price))
                holder.money += amount * price
            holder.save(mysql)
        stock.remove(mysql)
    else:
        if openStockNum == 0:
            newprice = price
            send(stock.issuer, "您的股票%s在一级市场已按%.2f一股全部认购完毕，上市成功！%.2f元资本已转移给您，股票将在下一次开盘进入二级市场交易！"
                 % (stock.stockName, price, stock.provisionalFunds))
        else:
            newprice = soldNum / (stockNum - selfRetain) * price
            send(stock.issuer, "您的股票%s在一级市场按%.2f认购了%s，调整后股价为%.2f，上市成功！%.2f元资本已转移给您，股票将在下一次开盘进入二级市场交易！"
                 % (stock.stockName, price, soldNum, newprice, stock.provisionalFunds))
            roundedSum = 0
            for holderID, amount in stock.shareholders.items():
                holder = User.find(holderID, mysql)
                if holderID != stock.issuer:
                    newAmount = round(amount * (stockNum - selfRetain) / soldNum)
                    roundedSum += newAmount
                    send(holderID,
                         "股票%s未认购完，您的%s股将等比扩增为%s，发行价调整为%.2f。" % (stock.stockName, amount, newAmount, newprice))
                    holder.stock[stock.stockID] = newAmount
                    stock.shareholders[holderID] = newAmount
                holder.save(mysql)
            selfRetain -= roundedSum - (stockNum - selfRetain)  # 四舍五入后的误差从自留股份中找补
            stock.selfRetain = selfRetain
            stock.shareholders[stock.issuer] = selfRetain
            holder = User.find(stock.issuer, mysql)
            holder.stock[stock.stockID] = selfRetain

        stock.primaryClosed=True
        stock.secondaryOpen=True
        stock.histprice['adjustedIssuePrice'] = newprice
        issuer: User = User.find(stock.issuer, mysql)
        issuer.money += stock.provisionalFunds
        stock.provisionalFunds = 0
        stock.save(mysql)
        issuer.save(mysql)

def acquireStock(messageList: list[str], qid: str):
    """
    :param messageList: 认购 股票名称/缩写 股数
    :param qid:
    :return: 提示信息
    """

    assert len(messageList) == 3, '认购失败:您的认购格式不正确！'
    try:
        stockNum: int = int(messageList[2])
    except ValueError:
        return "认购失败:您的认购格式不正确！"
    assert stockNum >= 1000, '认购失败！在一级市场认购股票需购买至少1000股！'

    stockIdentifier = str(messageList[1])

    if len(stockIdentifier) == 3:
        # 通过股票缩写查找
        stock: Stock = Stock.find(stockIdentifier, mysql)
        assert stock, "认购失败:不存在代码为%s的股票！" % stockIdentifier
    else:
        # 通过股票名称查找
        assert Stock.findAll(mysql, 'stockName=?', (stockIdentifier,)), "认购失败:不存在代码为%s的股票！" % stockIdentifier
        stock: Stock = Stock.findAll(mysql, 'stockName=?', (stockIdentifier,))[0]

    assert not stock.primaryClosed, "认购失败！该股票已结束一级市场认购阶段！"
    assert stockNum <= stock.openStockNum, '认购失败！您想要认购的股数超过了目前开放认购的该股票总股数！'
    assert qid != stock.issuer, '认购失败！您不能认购自己发行的股票！'

    acquirer: User = User.find(qid, mysql)
    price = stockNum * stock.price
    assert acquirer.money >= price, '认购失败！您的余额不足，认购%s股%s需要至少%.2f元！' % (stockNum, stock.stockName, price)

    acquirer.money -= price
    stock.provisionalFunds += price  # 扣款进入临时资金池
    acquirer.stocks.setdefault(stock.stockID, 0)
    acquirer.stocks[stock.stockID] += stockNum
    acquirer.save(mysql)

    stock.shareholders.setdefault(acquirer.qid, 0)
    stock.shareholders[acquirer.qid] += stockNum
    stock.openStockNum -= stockNum
    if stock.openStockNum<=0:
        primaryClosing(stock)
    stock.save(mysql)

    ans = '认购成功！'
    return ans

def toPaperFuel(messageList: list[str], qid: str):
    """
    :param messageList: 兑换纸燃油 数量
    :param qid:
    :return: 提示信息
    """
    assert len(messageList) == 2, '兑换失败:您的兑换格式不正确！'
    try:
        stockNum: int = int(messageList[1])
    except ValueError:
        return "兑换失败:您的兑换格式不正确！"
    user = User.find(qid, mysql)
    assert 0 in user.mineral, '兑换失败：您没有燃油！'
    assert user.mineral[0] >= stockNum,'兑换失败：您现在只有%s单位燃油！' % user.mineral[0]

    pfu = Stock.find('pfu', mysql)
    user = User.find(qid, mysql)
    pfu.stockNum += stockNum
    pfu.shareholders.setdefault(qid, 0)
    pfu.shareholders[qid] += stockNum
    user.mineral[0] -= stockNum
    if user.mineral[0] == 0:
        user.mineral.pop(0)
    user.stocks.setdefault('pfu',0)
    user.stocks['pfu'] += stockNum

    pfu.save(mysql)
    user.save(mysql)

    ans = '您已成功兑换%s单位纸燃油！' % stockNum

    return ans


def fromPaperFuel(messageList: list[str], qid: str):
    """
    :param messageList: 兑换燃油 数量
    :param qid:
    :return: 提示信息
    """
    assert len(messageList) == 2, '兑换失败:您的兑换格式不正确！'
    try:
        stockNum: int = int(messageList[1])
    except ValueError:
        return "兑换失败:您的兑换格式不正确！"
    user = User.find(qid, mysql)
    assert 'pfu' in user.stocks, '兑换失败：您没有纸燃油！'
    assert user.stocks['pfu'] >= stockNum, '兑换失败：您现在只有%s单位纸燃油！' % user.stocks['pfu']

    pfu = Stock.find('pfu', mysql)
    user = User.find(qid, mysql)
    pfu.stockNum -= stockNum
    pfu.shareholders[qid] -= stockNum
    if pfu.shareholders[qid] == 0:
        pfu.shareholders.pop(qid)
    user.mineral.setdefault(0, 0)
    user.mineral[0] += stockNum
    user.stocks['pfu'] -= stockNum
    if user.stocks['pfu'] == 0:
        user.stocks.pop('pfu')

    pfu.save(mysql)
    user.save(mysql)

    ans = '您已成功兑换%s单位燃油！' % stockNum

    return ans

def stockMarket(messageList: list[str], qid: str):
    """
    :param messageList: 股市
    :param qid:
    :return: 提示信息
    """
    stocks: list[Stock] = Stock.findAll(mysql)
    ans = '欢迎来到股市！\n'
    if not stocks:
        ans+='目前没有发行的股票！'
        return ans
    ans += '以下是所有目前发行的股票:\n'
    stockTable = [['股票名称', '股票缩写', '发行量', '可购量','当前股价','股票状态']]
    for stock in stocks:
        status:str='证券指数' if stock.isIndex else (('开放交易' if stock.secondaryOpen else '认购结束') if stock.primaryClosed else '开放认购')
        stockTable.append([stock.stockName, stock.stockID, stock.stockNum,stock.openStockNum,stock.price,status])
    drawtable(stockTable, 'stock.png')
    ans += '[CQ:image,file=stock.png]\n'

    date=getnowdate()
    AllStockData:list[StockData]=StockData.findAll(mysql,where='timestamp>=? and timestamp<=?',args=[date-6*86400,date+86400])
    if not AllStockData:
        return ans
    ans+='以下是所有发行股票的股价变动:\n'
    stockPrices:dict[str,list]={'loi':[],'lyi':[]}
    for stockData in AllStockData:
        timestamp=stockData.timestamp
        prices=stockData.prices
        stockPrices['loi'].append([timestamp,stockData.index])
        stockPrices['lyi'].append([timestamp,stockData.index2])
        for stockID,price in prices.items():
            stockPrices.setdefault(stockID,[])
            stockPrices[stockID].append([timestamp,price])

    plt.figure(figsize=(10,5))
    for stockID in stockPrices.keys():
        xs,ys=[],[]
        for datum in stockPrices[stockID]:
            xs.append(datetime.fromtimestamp(datum[0]-8*3600))
            ys.append(datum[1])
        plt.plot(xs,ys,linestyle='-',marker=',',label=stockID,alpha=0.5)
    plt.legend(loc='upper right')

    plt.savefig('../go-cqhttp/data/images/stockprices.png')
    ans+='[CQ:image,file=stockprices.png]\n'
    return ans

def buyStock(messageList: list[str], qid: str):
    """
    :param messageList: 买入 股票名称/缩写 买入量 价格上限
    :param qid:
    :return: 提示信息
    """
    assert len(messageList) == 4, '买入失败:您的买入格式不正确！'
    assert globalConfig.stockMarketOpenFlag, "股市正在休市，请稍后再来！"
    try:
        stockNum: int = int(messageList[2])
        price:float = float(messageList[3])
    except ValueError:
        return "买入失败:您的买入格式不正确！"

    stockIdentifier = str(messageList[1])

    if len(stockIdentifier) == 3:
        # 通过股票缩写查找
        stock: Stock = Stock.find(stockIdentifier, mysql)
        assert stock, "买入失败:不存在代码为%s的股票！" % stockIdentifier
    else:
        # 通过股票名称查找
        assert Stock.findAll(mysql, 'stockName=?', (stockIdentifier,)), "买入失败:不存在代码为%s的股票！" % stockIdentifier
        stock: Stock = Stock.findAll(mysql, 'stockName=?', (stockIdentifier,))[0]

    assert not stock.isIndex, "您输入的股票是指数，不能直接购买！"
    assert stock.secondaryOpen, "买入失败！该股票还未开始二级市场交易阶段！"
    assert stockNum <= stock.stockNum, '买入失败！您想要买入的股数超过了该股票总股数！'
    assert not qid in stock.askers, '您不能在同一期开盘中既买又卖同一只股票！'
    assert 0.75*stock.price < price < 1.25*stock.price, '买入失败！您的报价超出了合理区间，建议重新考虑！'

    bidder: User = User.find(qid, mysql)
    totalPrice = stockNum * price
    assert bidder.money >= totalPrice, '买入失败！您的余额不足，买入%s股%s需要至少%.2f元！' % (stockNum, stock.stockName, totalPrice)

    if qid not in stock.bidders:
        stock.bidders.append(qid)

    bidder.money -= totalPrice
    bidder.save(mysql)
    stock.save(mysql)
    ans = makeOrder(qid, stock.stockID, 'buy', stockNum, price)
    return ans

def sellStock(messageList: list[str], qid: str):
    """
    :param messageList: 卖出 股票名称/缩写 卖出量 价格下限
    :param qid:
    :return: 提示信息
    """
    assert len(messageList) == 4, '卖出失败:您的卖出格式不正确！'
    assert globalConfig.stockMarketOpenFlag, "股市正在休市，请稍后再来！"
    try:
        stockNum: int = int(messageList[2])
        price: float = float(messageList[3])
    except ValueError:
        return "卖出失败:您的卖出格式不正确！"

    stockIdentifier = str(messageList[1])

    if len(stockIdentifier) == 3:
        # 通过股票缩写查找
        stock: Stock = Stock.find(stockIdentifier, mysql)
        assert stock, "卖出失败:不存在代码为%s的股票！" % stockIdentifier
    else:
        # 通过股票名称查找
        assert Stock.findAll(mysql, 'stockName=?', (stockIdentifier,)), "卖出失败:不存在代码为%s的股票！" % stockIdentifier
        stock: Stock = Stock.findAll(mysql, 'stockName=?', (stockIdentifier,))[0]

    assert stock.secondaryOpen, "卖出失败！该股票还未开始二级市场交易阶段！"
    assert stockNum <= stock.StockNum, '卖出失败！您想要卖出的股数超过了该股票总股数！'
    assert not qid in stock.bidders, '您不能在同一期开盘中既买又卖同一只股票！'
    assert 0.75 * stock.price < price < 1.25 * stock.price, '卖出失败！您的报价超出了合理区间，建议重新考虑！'

    asker: User = User.find(qid, mysql)
    asker.stocks.setdefault(stock.stockID, 0)
    assert asker.stocks[stock.stockID] >= stockNum, '卖出失败！您只有%s股%s！' % (asker.stocks[stock.stockID], stock.stockName)

    if qid not in stock.askers:
        stock.askers.append(qid)

    asker.stocks[stock.stockID] -= stockNum
    asker.save(mysql)
    stock.save(mysql)
    ans = makeOrder(qid, stock.stockID, 'sell', stockNum, price)
    return ans

def giveDividend(messageList: list[str], qid: str):
    """
    :param messageList: 分红 股票名称/缩写 钱数
    :param qid:
    :return: 提示信息
    """
    assert len(messageList) == 3, '分红失败:您的分红格式不正确！'
    try:
        dividend: float = float(messageList[2])
    except ValueError:
        return "分红失败:您的分红格式不正确！"

    stockIdentifier = str(messageList[1])

    if len(stockIdentifier) == 3:
        # 通过股票缩写查找
        stock: Stock = Stock.find(stockIdentifier, mysql)
        assert stock, "分红失败:不存在代码为%s的股票！" % stockIdentifier
    else:
        # 通过股票名称查找
        assert Stock.findAll(mysql, 'stockName=?', (stockIdentifier,)), "分红失败:不存在代码为%s的股票！" % stockIdentifier
        stock: Stock = Stock.findAll(mysql, 'stockName=?', (stockIdentifier,))[0]

    #assert dividend, '买入失败！您的报价超出了合理区间，建议重新考虑！'
    assert stock.issuer == qid, "分红失败，您不是该股票的发行者！"

    issuer: User = User.find(qid, mysql)
    assert issuer.money >= dividend, '分红失败！您的余额不足！'

    issuer.money -= dividend
    issuer.save(mysql)

    divisor = stock.stockNum
    if qid in stock.shareholders:
        divisor -= stock.shareholders[qid]

    for share in stock.shareholders.items():
        recipient = User.find(share[0],mysql)
        recipient.money += dividend*share[1]/divisor
        send(recipient.qid,'股票%s的发行者%s分红了%.2f元，您凭持有的%s股获得了其中的%.2f元！'
             % (stock.stockID, qid, dividend, share[1], dividend*share[1]/divisor))
        recipient.save(mysql)

    stock.avg_dividend += dividend/divisor

    ans = '分红成功！该股票平均每股分红已达到%.2f元！' % stock.avg_dividend

    return ans

def makeOrder(qid: str, stockID: int, direction: str, amount: int, priceLimit: float):
    nowtime = getnowtime()
    newOrderID: int = max([0] + [order.orderID for order in Order.findAll(mysql)]) + 1
    order: Order = Order(
        orderID=newOrderID,
        stockID=stockID,
        requester=qid,
        buysell=direction == 'buy',  # True = buy False = sell
        amount=amount,
        completedAmount = 0,
        priceLimit=priceLimit,
        timestamp=nowtime,
        funds=0,
    )
    if direction == 'buy':
        order.funds += amount*priceLimit
    order.add(mysql)

    ans = "您的申报创建成功！"
    return ans

def pairing(bid: Order,ask:Order, amount: int, price: float): #配对撮合，更新已成交的股数
    bid.amount -= amount
    bid.completedAmount += amount
    bid.funds -= amount*price

    ask.amount -= amount
    ask.completedAmount += amount

def resolveOrder(stock:Stock, order: Order, price:float)->tuple[Stock,float]: #成交写入User
    requester:User = User.find(order.requester)
    order.completedAmount = 0
    stockTax = 0
    if order.buysell:
        requester.stocks.setdefault(order.stockID, 0)
        requester.stocks[order.stockID] += order.completedAmount
        stock.shareholders.setdefault(requester.qid, 0)
        stock.shareholders[requester.qid] += order.completedAmount
        message = "您的股市购入申请%s成功以%.2f一股的价格成交%s股！\n" %(order.orderID,price,order.completedAmount)
        if order.amount == 0:
            message += "您的股市购入申请%s已经完全完成！未用的%.2f元资金已经返还到您的账户！" %(order.orderID,order.funds)
            requester.money += order.funds
            order.remove(mysql)
        else:
            order.save(mysql)
    else:
        money = order.completedAmount*price
        stockTax = 0.005 * money
        requester.money += money - stockTax
        #shareholders更新具有滞后性，在提出申请时，User里的股数已经扣除（失败返还），但是在卖出成功之前，Stock中的字典不会改变
        #treasury.save(mysql)
        stock.shareholders[requester.qid] -= order.completedAmount
        message = "您的股市卖出申请%s成功以%.2f一股的价格成交%s股！征收了您%.2f元股票交易税！\n" % (order.orderID, price, order.completedAmount, stockTax)
        if order.amount == 0:
            message += "您的股市卖出申请%s已经完全完成！" % order.orderID
            order.remove(mysql)
        else:
            order.save(mysql)

    send(order.requester, message)
    requester.save(mysql)

    return stock, stockTax # 为了避免瞬时频繁更新stock，它将被传递直到Brokerage完成


def stockMarketOpen():
    globalConfig.stockMarketOpenFlag = True
    groupMessage = ""
    for stock in Stock.findAll(mysql):
        stockID = stock.stockID
        if stock.primaryClosed and not stock.secondaryOpen:
            stock.secondaryOpen = True
            if groupMessage:
                groupMessage += '\n'
            groupMessage += '股票%s（代号：%s）本期开放二级市场交易，参考价为%.2f元一股！' % (stock.stockName, stock.stockID, stock.price)
        stock.save(mysql)
    for groupID in groupIDs:
        send(groupID,groupMessage or "休市结束，股市开始接受申报！",group=True)


def stockMarketClose():
    """
    关闭股市
    :return:
    """
    globalConfig.stockMarketOpenFlag = False#股市休市
    for stock in Stock.findAll(mysql):
        stockID = stock.stockID
        stock.askers = []  #清空买卖记录
        stock.bidders = []
        stock.save(mysql)
    for order in Order.findAll(mysql):  #清理剩余订单
        qid = order.requester
        requester:User = User.find(qid,mysql)
        if order.buy:
            requester.money+=order.funds
            send(qid,"您编号为%s的买入申报有%s股未能成交，%.2f元余额已经退还给您。" % (order.orderID, order.amount, order.funds))
        else:
            requester.stocks.setdefault(order.stockID, 0)
            requester.stocks[order.stockID] += order.amount
            send(qid, "您编号为%s的卖出申报有%s股未能成交，已经退还给您。" % (order.orderID, order.amount))
        requester.save(mysql)
        order.remove(mysql)


def resolveAuction(aggregate=True, closing=False):
    nowtime = getnowtime()
    dataEntry = StockData(
        timestamp=nowtime,
        prices={},
        volumes={},
        opening=aggregate,
        closing=closing,
        index=100,
        index2=100,
    )
    dataEntry.add(mysql)
    capitalSum = 0
    capitalSumNoOil = 0
    indexSum = 0
    indexSumNoOil = 0
    for stock in Stock.findAll(mysql):
        if stock.isIndex:
            continue
        stockID = stock.stockID
        oldPrice = stock.price
        oldCapital = stock.price*stock.stockNum
        capitalSum += oldCapital
        if not stockID=='pfu':
            capitalSumNoOil += oldCapital
        if not stock.secondaryOpen:
            continue
        orders = Order.findAll(mysql, 'stockID=?', (stockID,), OrderBy='timestamp')
        if not orders:
            stock.volume = 0
            dataEntry.prices[stock.stockID] = stock.price
            dataEntry.volumes[stock.stockID] = stock.volume
            if aggregate:
                stock.openingPrice = stock.price
            stock.save(mysql)
            dataEntry.save(mysql)
            continue
        if aggregate:
            stock = brokerage(stockID, orders, stock.price, stock.price, aggregate)
        else:
            stock = brokerage(stockID, orders, stock.price, stock.openingPrice, aggregate)

        difference = stock.price/oldPrice
        indexSum += difference*oldCapital
        if not stockID=='pfu':
            indexSumNoOil += difference*oldCapital
        dataEntry.prices[stock.stockID] = stock.price
        dataEntry.volumes[stock.stockID] = stock.volume
        stock.save(mysql)

    index = Stock.find('loi',mysql)
    index2 = Stock.find('lyi',mysql)
    indexDifference = indexSum/capitalSum
    indexDifferenceNoOil = indexSumNoOil/capitalSumNoOil
    dataEntry.index = indexDifference*index.price
    dataEntry.index2 = indexDifferenceNoOil*index2.price
    index.price = dataEntry.index
    index2.price = dataEntry.index2
    dataEntry.save(mysql)
    index.save(mysql)
    index2.save(mysql)

    return None

class Aligned(TypedDict):
    buy:list[list[Order]]
    sell:list[list[Order]]
    price:list[float]
    cumulativeBids:list[int]
    cumulativeAsks:list[int]
    exchanged:list
    tiebreaker:list

def exchangeStock(orders: list[Order], currentPrice:float, openingPrice:float, threshold=0.1, threshold2=0.2):
    """

    :param orders:
    :param currentPrice:当前股价
    :param openingPrice:开盘价
    :param threshold:
    :param threshold2:
    :return:
    """

    orders.sort(key=lambda order: order.price, reverse=True)#对所有申报按价格从高到低排序
    aligned: Aligned = {
        'buy': [],
        'sell': [],
        'price': [],
        'cumulativeBids': [],
        'cumulativeAsks': [],
        'exchanged': [],
        'tiebreaker': []
    }
    lastTier = 0#存储最后一次更新的报价
    tierNum = 0#报价的种数
    for order in orders:
        adjustedPrice = order.price
        #涨跌幅限制
        if (order.price > currentPrice * (1 + threshold) or order.price > openingPrice * (1 + threshold2)) and order.buy:#买入股票且给出的最高价过高
            adjustedPrice = min(currentPrice * (1 + threshold), openingPrice * (1 + threshold2))
        if (order.price < currentPrice * (1 - threshold) or order.price < openingPrice * (1 - threshold2)) and not order.buy:#抛出股票且给出的最低价过低
            adjustedPrice = max(currentPrice* (1 - threshold), openingPrice * (1 - threshold2))

        if adjustedPrice != lastTier:
            aligned['buy'][-1].sort(key=lambda order: order.orderID)#对当前的买入股票申报进行排序
            aligned['sell'][-1].sort(key=lambda order: order.orderID)#对当前的抛出股票申报进行排序

            aligned['price'].append(adjustedPrice)
            lastTier = adjustedPrice#更新报价
            tierNum += 1#增加报价种数

            aligned['buy'].append([])
            aligned['sell'].append([])

        #将订单分配到成交价
        if order.buy:
            aligned['buy'][-1].append(order)
        else:
            aligned['sell'][-1].append(order)

    aligned['cumulativeBids'] = [0 for _ in range(tierNum)]#每一成交价上的累积需求
    aligned['cumulativeAsks'] = [0 for _ in range(tierNum)]#每一成交价上的累积供给
    aligned['tiebreaker'] = [0 for _ in range(tierNum)]#tiebreaker的最小项代表成交价所在项

    # print(aligned)
    # 计算每一成交价上的累积需求和累积供给
    for i in range(tierNum):#tierNum从小到大，price从高到低
        for order in aligned['buy'][i]:
            aligned['cumulativeBids'][i] += order.amount#当前成交价上的需求
        aligned['cumulativeBids'][i] += aligned['cumulativeBids'][i - 1]#出价比成交价更高的买者也可以买入
        for order in aligned['sell'][-i - 1]:
            aligned['cumulativeAsks'][-i - 1] += order.amount#当前成交价上的供给
        aligned['cumulativeAsks'][-i - 1] += aligned['cumulativeAsks'][-i]#出价比成交价更低的抛者也可以抛出

    # 计算在每一成交价上能实现的成交量
    maxExchanged = 0#所有成交价上的最大成交量
    for i in range(tierNum):
        # print(aligned['cumulativeBids'][i], aligned['price'][i], aligned['cumulativeAsks'][i], '\n')
        exchanged = min(aligned['cumulativeBids'][i], aligned['cumulativeAsks'][i])
        maxExchanged = max(maxExchanged, exchanged)
        aligned['exchanged'].append(exchanged)

    return aligned, tierNum, maxExchanged

def brokerage(stockID:int, orders:list, currentPrice:float, openingPrice:float,aggregate:bool):
    """
    :param stockID:
    :param orders:
    :param currentPrice: 当前股价
    :param openingPrice: 开盘价
    :param aggregate: 是否采用集合竞价
    :return:
    """

    aligned, tierNum, maxExchanged = exchangeStock(orders, currentPrice, openingPrice)

    if maxExchanged == 0:    #没有新成交，新股价等于当前股价，成交量等于0
        return currentPrice, 0

    #nowtime = 100
    # 集合竞价中，如遇多个成交价可实现同样的最大成交量，以最接近上一期收盘价的成交价为成交价。
    # 连续竞价中，以具有较新申报的成交价为成交价。
    if aggregate:
        for i in range(tierNum):
            if aligned['exchanged'][i] == maxExchanged:#该成交价可实现最大成交量
                aligned['tiebreaker'][i] = -1/(1+abs(currentPrice-aligned['price'][i]))#价格越接近上一期收盘价，tiebreaker越小
    else:
        for i in range(tierNum):
            if aligned['exchanged'][i] == maxExchanged:#该成交价可实现最大成交量
                if not aligned['buy'][i]:
                    youngestStamp = aligned['sell'][i][-1].timestamp
                elif not aligned['sell'][i]:
                    youngestStamp = aligned['buy'][i][-1].timestamp
                else:
                    youngestStamp = max(aligned['buy'][i][-1].timestamp, aligned['sell'][i][-1].timestamp)
                aligned['tiebreaker'][i] = youngestStamp

    dealPrice:float = aligned['price'][np.argmax(np.array(aligned['tiebreaker']))]#最终成交价

    # print(aligned['exchanged'], np.argmin(np.array(aligned['tiebreaker'])), dealPrice)

    completedBids:list[Order] = []#所有能够成交的买入申报
    completedAsks:list[Order] = []#所有能够成交的抛出申报
    for i in range(tierNum):
        if aligned['price'][i] >= dealPrice:
            completedBids += aligned['buy'][i]
        if aligned['price'][-i - 1] <= dealPrice:
            completedAsks += aligned['sell'][-i - 1]

    # 成交规则：高于成交价的买入全部成交，低于成交价的卖出全部成交，等于成交价的申报中，至少一侧全部成交。
    stock:Stock = Stock.find(stockID,mysql)
    totalDoneAmount:int = 0#总成交量
    stockTaxCollected = 0.0 #征收的股票交易税
    treasury = User.find('treasury',mysql)
    while completedBids and completedAsks:
        stockTax = 0
        doneAmount = min(completedBids[0].amount, completedAsks[0].amount)#目前的最高价买入申报与目前的最低价卖出申报所能达到的最大成交量
        totalDoneAmount += doneAmount#更新总成交量
        #print(completedBids[0], completedAsks[0], doneAmount)

        pairing(completedBids[0],completedAsks[0],doneAmount,dealPrice)

        if completedBids[0].amount == 0:#该买入申报已全部成交
            stock, stockTax = resolveOrder(stock,completedBids[0], dealPrice)
            completedBids.pop(0)#清空该项
        if completedAsks[0].amount == 0:#该抛出申报已全部成交
            stock, stockTax = resolveOrder(stock,completedAsks[0], dealPrice)
            completedAsks.pop(0)#清空该项
        stockTaxCollected += stockTax

    if completedAsks:
        for remaining in completedAsks:
            stock, stockTax = resolveOrder(stock,remaining,dealPrice)
            stockTaxCollected += stockTax
    if completedBids:
        for remaining in completedBids:
            stock, stockTax = resolveOrder(stock,remaining,dealPrice)
            stockTaxCollected += stockTax

    treasury.money += stockTaxCollected
    treasury.save(mysql)

    stock.price = dealPrice#更新股价为成交价
    stock.volume = totalDoneAmount
    if aggregate:#若为集合竞价，下一次开盘价为前一次成交价
        stock.openingPrice = stock.price

    # print(totalDoneAmount)
    return stock

