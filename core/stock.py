from tools import drawtable, setTimeTask, getnowtime, send
from model import User, Stock, Order
from globalConfig import mysql, stockMarketOpenFlag, group_ids
from typing import Dict, List


def issueStock(message_list: List[str], qid: str):
    """
    :param message_list: 发行 股票名称 缩写 发行量 价格 自我保留股数
    :param qid: 发行者的qq号
    :return: 发行提示信息
    """
    assert len(message_list) == 6, '发行失败:您的发行格式不正确！'

    stockName: str = message_list[1]
    stockID: str = message_list[2]
    assert 3 < len(stockName) <= 12, '发行失败:股票名称必须为4-12个字符！'
    assert not Stock.findAll(mysql, 'stockName=?', (stockName,)), "发行失败:该股票名称已经被占用！"

    assert len(stockID) == 3, '发行失败:股票缩写必须为3个字符！'
    assert not Stock.find(stockID, mysql), "发行失败:该股票缩写已经被占用！"

    stockNum: int = int(message_list[3])
    assert 10000 <= stockNum <= 100000, '发行失败:股票发行量必须在10000股到100000股之间！'

    price: float = float(message_list[4])
    assert price < 100, '发行失败：初始股价过高！'

    selfRetain: int = int(message_list[5])
    assert 0 <= selfRetain < 0.5 * stockNum, '发行失败:自我持有量过低或过高！'

    nowtime = getnowtime()
    primaryEndTime = nowtime + 86400
    stock = Stock(stockID=stockID,
                  stockName=stockName,
                  stockNum=stockNum,
                  openStockNum=stockNum - selfRetain,
                  provisionalFunds=0,
                  issue_qid=qid,
                  price=price,
                  selfRetain=selfRetain,
                  primaryEndTime=primaryEndTime,
                  bidders=[],
                  askers=[],
                  histprice={'designated_issue_price': price},
                  shareholders={qid: selfRetain},
                  primaryClosed=False,
                  secondaryOpen=False,
                  avg_dividend=0.0)
    stock.add(mysql)
    issuer: User = User.find(qid, mysql)
    issuer.stock[stockID] = selfRetain
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
    if soldNum / (stockNum - selfRetain) * price < 1:  # 调整价格小于每股1元
        send(stock.issue_qid, "您的股票%s在一级市场按%.2f认购了%s，调整后股价过低，上市失败！募集的资本将被退还给投资者。" % (stock.stockName, soldNum, price))
        shareholders: dict = stock.shareholders
        for holderID, amount in shareholders.items():
            holder = User.find(holderID, mysql)
            holder.stock.pop(stock.stockID)
            if holderID != stock.issue_qid:
                send(holderID, "股票%s发行失败！您的%.2f元资本已被退还给您。" % (stock.stockName, amount * price))
                holder.money += amount * price
            holder.save(mysql)
        stock.remove(mysql)
    else:
        if openStockNum == 0:
            newprice = price
            send(stock.issue_qid, "您的股票%s在一级市场已按%.2f一股全部认购完毕，上市成功！%.2f元资本已转移给您，股票将在下一次开盘进入二级市场交易！"
                 % (stock.stockName, stock.provisionalFunds, price))
        else:
            newprice = soldNum / (stockNum - selfRetain) * price
            send(stock.issue_qid, "您的股票%s在一级市场按%.2f认购了%s，调整后股价为%.2f，上市成功！%.2f元资本已转移给您，股票将在下一次开盘进入二级市场交易！"
                 % (stock.stockName, soldNum, price, newprice, stock.provisionalFunds))
            rounded_sum = 0
            for holderID, amount in stock.shareholders.items():
                holder = User.find(holderID, mysql)
                if holderID != stock.issue_qid:
                    new_amount = round(amount * (stockNum - selfRetain) / soldNum)
                    rounded_sum += new_amount
                    send(holderID,
                         "股票%s未认购完，您的%s股将等比扩增为%s，发行价调整为%.2f。" % (stock.stockName, amount, new_amount, newprice))
                    holder.stock[stock.stockID] = new_amount
                    stock.shareholders[holderID] = new_amount
                holder.save(mysql)
            selfRetain -= rounded_sum - (stockNum - selfRetain)  # 四舍五入后的误差从自留股份中找补
            stock.selfRetain = selfRetain
            stock.shareholders[stock.issue_qid] = selfRetain
            holder = User.find(stock.issue_qid, mysql)
            holder.stock[stock.stockID] = selfRetain

        stock.primaryClosed = True
        stock.histprice['adjusted_issue_price'] = newprice
        issuer: User = User.find(stock.issue_qid, mysql)
        stock.provisionalFunds = 0
        issuer.money += stock.provisionalFunds
        stock.save(mysql)
        issuer.save(mysql)

    return None


def acquireStock(message_list: List[str], qid: str):
    """
    :param message_list: 认购 股票名称/缩写 股数
    :param qid:
    :return: 提示信息
    """

    assert len(message_list) == 3, '认购失败:您的认购格式不正确！'
    try:
        stockNum: int = int(message_list[2])
    except ValueError:
        return "认购失败:您的认购格式不正确！"
    assert stockNum >= 1000, '认购失败！在一级市场认购股票需购买至少1000股！'

    stockIdentifier = str(message_list[1])

    if len(stockIdentifier) == 3:
        # 通过股票缩写查找对方
        stock: Stock = Stock.find(stockIdentifier, mysql)
        assert stock, "认购失败:不存在代码为%s的股票！" % stockIdentifier
    else:
        # 通过学号查找
        assert Stock.findAll(mysql, 'stockName=?', (stockIdentifier,)), "认购失败:不存在代码为%s的股票！" % stockIdentifier
        stock: Stock = Stock.findAll(mysql, 'stockName=?', (stockIdentifier,))[0]

    assert not stock.primaryClosed, "认购失败！该股票已结束一级市场认购阶段！"
    assert stockNum <= stock.openStockNum, '认购失败！您想要认购的股数超过了目前开放认购的该股票总股数！'
    assert qid != stock.issue_qid, '认购失败！您不能认购自己发行的股票！'

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
    stock.save(mysql)

    ans = '认购成功！'
    return ans


def stockMarket(message_list: List[str], qid: str):
    """
    :param message_list: 股市
    :param qid:
    :return: 提示信息
    """
    stocks: List[Stock] = Stock.findAll(mysql)
    ans = '欢迎来到股市！\n'
    if stocks:
        ans += '以下是所有目前发行的股票:\n'
        stockData = [['股票名称', '股票缩写', '发行量', '当前股价']]
        for stock in stocks:
            stockData.append([stock.stockName, stock.stockID, stock.stockNum, stock.price])
        drawtable(stockData, 'stock.png')
        ans += '[CQ:image,file=stock.png]'
    else:
        ans += '目前没有发行的股票！'
    return ans

def buyStock(message_list: List[str], qid: str):
    """
    :param message_list: 买入 股票名称/缩写 买入量 价格上限
    :param qid:
    :return: 提示信息
    """
    assert len(message_list) == 4, '买入失败:您的买入格式不正确！'
    assert stockMarketOpenFlag, "股市正在休市，请稍后再来！"
    try:
        stockNum: int = int(message_list[2])
        price:float = float(message_list[3])
    except ValueError:
        return "买入失败:您的买入格式不正确！"

    stockIdentifier = str(message_list[1])

    if len(stockIdentifier) == 3:
        # 通过股票缩写查找对方
        stock: Stock = Stock.find(stockIdentifier, mysql)
        assert stock, "买入失败:不存在代码为%s的股票！" % stockIdentifier
    else:
        # 通过学号查找
        assert Stock.findAll(mysql, 'stockName=?', (stockIdentifier,)), "买入失败:不存在代码为%s的股票！" % stockIdentifier
        stock: Stock = Stock.findAll(mysql, 'stockName=?', (stockIdentifier,))[0]

    assert stock.secondaryOpen, "买入失败！该股票还未开始二级市场交易阶段！"
    assert stockNum <= stock.StockNum, '买入失败！您想要买入的股数超过了该股票总股数！'
    assert not qid in stock.askers, '您不能在同一期开盘中既买又卖同一只股票！'
    assert 0.75*stock.price < price < 1.25*stock.price, '买入失败！您的报价超出了合理区间，建议重新考虑！'

    acquirer: User = User.find(qid, mysql)
    total_price = stockNum * price
    assert acquirer.money >= total_price, '买入失败！您的余额不足，买入%s股%s需要至少%.2f元！' % (stockNum, stock.stockName, total_price)

    if not qid in stock.bidders :
        stock.bidders.append(qid)

    acquirer.money -= total_price
    acquirer.save(mysql)
    ans = makeOrder(qid, stock.stockID, 'buy', StockNum, price)
    return ans

def sellStock(message_list: List[str], qid: str):
    """
    :param message_list: 卖出 股票名称/缩写 卖出量 价格下限
    :param qid:
    :return: 提示信息
    """
    assert len(message_list) == 4, '卖出失败:您的卖出格式不正确！'
    assert stockMarketOpenFlag, "股市正在休市，请稍后再来！"
    try:
        stockNum: int = int(message_list[2])
        price: float = float(message_list[3])
    except ValueError:
        return "卖出失败:您的卖出格式不正确！"

    stockIdentifier = str(message_list[1])

    if len(stockIdentifier) == 3:
        # 通过股票缩写查找对方
        stock: Stock = Stock.find(stockIdentifier, mysql)
        assert stock, "卖出失败:不存在代码为%s的股票！" % stockIdentifier
    else:
        # 通过学号查找
        assert Stock.findAll(mysql, 'stockName=?', (stockIdentifier,)), "卖出失败:不存在代码为%s的股票！" % stockIdentifier
        stock: Stock = Stock.findAll(mysql, 'stockName=?', (stockIdentifier,))[0]

    assert stock.secondaryOpen, "卖出失败！该股票还未开始二级市场交易阶段！"
    assert stockNum <= stock.StockNum, '卖出失败！您想要卖出的股数超过了该股票总股数！'
    assert not qid in stock.bidders, '您不能在同一期开盘中既买又卖同一只股票！'
    assert 0.75 * stock.price < price < 1.25 * stock.price, '卖出失败！您的报价超出了合理区间，建议重新考虑！'

    acquirer: User = User.find(qid, mysql)
    acquirer.stocks.setdefault(stock.stockID, 0)
    assert acquirer.stocks[stock.stockID] >= stockNum, '卖出失败！您只有%s股%s！' % (acquirer.stocks[stock.stockID], stock.stockName)

    if not qid in stock.askers:
        stock.askers.append(qid)

    acquirer.stocks[stock.stockID] -= stockNum
    ans = makeOrder(qid, stock.stockID, 'sell', StockNum, price)
    acquirer.save(mysql)
    return ans


def makeOrder(qid: str, stockID: int, direction: str, amount: int, price_limit: float):
    nowtime = getnowtime()
    newOrderID: int = max([0] + [order.debtID for order in Order.findAll(mysql)]) + 1
    order: Order = Order(
        orderID=newOrderID,
        stockID=stockID,
        requester=qid,
        buysell=direction == 'buy',  # True = buy False = sell
        amount=amount,
        completed_amount = 0,
        priceLimit=price_limit,
        timestamp=nowtime,
        funds=0,
    )
    if direction == 'buy':
        order.funds += amount*price
    order.save(mysql)

    ans = "您的申报创建成功！"
    return ans


def Pairing(bid: Order,ask:Order, amount: int, price: float): #配对撮合，更新已成交的股数
    bid.amount -= amount
    bid.completed_amount += amount
    bid.funds -= amount*price

    ask.amount -= amount
    ask.completed_amount += amount

    return None

def ResolveOrder(stock:Stock, order: Order, price:float): #成交写入User
    requester:user = User.find(order.requester)
    order.completed_amount = 0
    if order.buy:
        requester.stocks.setdefault(order.stockID, 0)
        requester.stocks[order.stockID] += order.completed_amount
        stock.shareholders.setdefault(requester.qid, 0)
        stock.shareholders[requester.qid] += order.completed_amount
        message = "您的股市购入申请%s成功以%.2f一股的价格成交%s股！" %(order.orderID,price,order.completed_amount)
        if order.amount == 0:
            message += "您的股市购入申请%s已经完全完成！未用的%.2f元资金已经返还到您的账户！" %(order.orderID,order.funds)
            requester.money += order.funds
            order.delete(mysql)
        else:
            order.save(mysql)
        send(requester, message)
    else:
        requester.money += order.completed_amount*price
        #shareholders更新具有滞后性，在提出申请时，User里的股数已经扣除（失败返还），但是在卖出成功之前，Stock中的字典不会改变
        stock.shareholders[requester.qid] -= order.completed_amount
        message = "您的股市卖出申请%s成功以%.2f一股的价格成交%s股！" % (order.orderID, price, order.completed_amount)
        if order.amount == 0:
            message += "您的股市卖出申请%s已经完全完成！" % (order.orderID)
            order.delete(mysql)
        else:
            order.save(mysql)
        send(requester, message)
    requester.save(mysql)

    return stock # 为了避免瞬时频繁更新stock，它将被传递直到Brokerage完成


def StockMarketOpen():
    global stockMarketOpenFlag
    stockMarketOpenFlag = True
    group_message = ""
    for stock in Stock.findAll(mysql):
        stockID = stock.stockID
        if stock.primaryClosed and not stock.secondaryOpen:
            stock.secondaryOpen = True
            if group_message:
                group_message += '\n'
            group_message += '股票%s（代号：%s）本期开放二级市场交易，参考价为%.2f元一股！' % (stock.stockName, stock.stockID, stock.price)
        stock.save(mysql)
    if group_message:
        send(group_ids[0], group_message)
    else:
        send(group_ids[0], "休市结束，股市开始接受申报！")
    return None


def StockMarketClose():
    global stockMarketOpenFlag
    stockMarketOpenFlag = False
    for stock in Stock.findAll(mysql):
        stockID = stock.stockID
        stock.askers = []  #清空买卖记录
        stock.bidders = []
        stock.save(mysql)
    for order in Order.findAll(mysql):  #清理剩余订单
        user_id = order.requester
        user:User = User.find(user_id,mysql)
        if order.buy:
            user.money+=order.funds
            send(user_id,"您编号为%s的买入申报有%s股未能成交，%.2f元余额已经退还给您。" % (order.orderID, order.amount, order.funds))
        else:
            user.stocks.setdefault(order.stockID, 0)
            user.stocks[order.stockID] += order.amount
            send(user_id, "您编号为%s的卖出申报有%s股未能成交，已经退还给您。" % (order.orderID, order.amount))
        user.save(mysql)
        order.delete(mysql)
    return None


def ResolveAuction(aggregate=True, closing=False):
    nowtime = getnowtime()
    dataEntry = StockData(
        timestamp=generateTimeStr(nowtime),
        prices={},
        volumes={},
        opening=aggregate,
        closing=closing
    )
    for stock in Stock.findAll(mysql):
        stockID = stock.stockID
        if not stock.secondaryOpen:
            continue
        orders = Order.findAll(mysql, 'stockID=?', (stockID,), OrderBy='timestamp')
        if len(orders) == 0:
            stock.volume = 0
            dataEntry.prices[stock.stockID] = stock.price
            dataEntry.volumes[stock.stockID] = stock.volume
            if aggregate:
                stock.openingPrice = stock.price
            stock.save(mysql)
            dataEntry.save(mysql)
            continue
        if aggregate:
            stock = brokerage(stockID, orders, stock.price, stock.price)
        else:
            stock = brokerage(stockID, orders, stock.price, stock.openingPrice)

        dataEntry.prices[stock.stockID] = stock.price
        dataEntry.volumes[stock.stockID] = stock.volume
        stock.save(mysql)
        dataEntry.save(mysql)

    return None



def exchange(orders: List[Order], current_price:float, opening_price:float, threshold=0.1, threshold2=0.2):
    orders.sort(key=lambda order: order.price, reverse=True)
    aligned: Dict[str, Union(int,float,List[Order])] = {'buy': [], 'sell': [], 'price': [], 'cumulative_bids': [],
               'cumulative_asks': [], 'exchanged': [], 'tiebreaker': []}
    last_tier = 0
    tier_num = 0
    for order in orders:
        adjusted_price = order.price
        if order.price > current_price * (1 + threshold) or order.price > opening_price * (1 + threshold2) \
                and order.buy:
            adjusted_price = min(current_price * (1 + threshold), opening_price * (1 + threshold2))
        if order.price < current_price * (1 - threshold) or order.price < opening_price * (1 - threshold2) \
                and not order.buy:
            adjusted_price = max(current_price* (1 - threshold), opening_price * (1 - threshold2))  #涨跌幅限制
        if adjusted_price != last_tier:
            aligned['buy'][-1].sort(key=lambda order: order.orderID)
            aligned['sell'][-1].sort(key=lambda order: order.orderID)

            aligned['price'].append(adjusted_price)
            last_tier = adjusted_price
            tier_num += 1

            aligned['buy'].append([])
            aligned['sell'].append([])

        #将订单分配到成交价
        if order.buy:
            aligned['buy'][-1].append(order)
        else:
            aligned['sell'][-1].append(order)

    aligned['cumulative_bids'] = [0 for _ in range(tier_num)]
    aligned['cumulative_asks'] = [0 for _ in range(tier_num)]
    aligned['tiebreaker'] = [0 for _ in range(tier_num)]

    # print(aligned)
    # 计算每一成交价上的累积需求和累积供给
    for i in range(tier_num):
        for order in aligned['buy'][i]:
            aligned['cumulative_bids'][i] += order.amount
        aligned['cumulative_bids'][i] += aligned['cumulative_bids'][i - 1]
        for order in aligned['sell'][-i - 1]:
            aligned['cumulative_asks'][-i - 1] += order.amount
        aligned['cumulative_asks'][-i - 1] += aligned['cumulative_asks'][-i]

    # 计算在每一成交价上能实现的成交量
    max_exchanged = 0
    for i in range(tier_num):
        # print(aligned['cumulative_bids'][i], aligned['price'][i], aligned['cumulative_asks'][i], '\n')
        exchanged = min(aligned['cumulative_bids'][i], aligned['cumulative_asks'][i])
        max_exchanged = max(max_exchanged, exchanged)
        aligned['exchanged'].append(exchanged)

    return aligned, tier_num, max_exchanged

def brokerage(stockID:int, orders:list, current_price:float, opening_price:float):

    aligned, tier_num, max_exchanged = exchange(orders, current_price, opening_price)

    if max_exchanged == 0:    #没有新成交，新股价等于当前股价，成交量等于0
        return current_price, 0

    #nowtime = 100
    # 集合竞价中，如遇多个成交价可实现同样的最大成交量，以最接近上一期收盘价的成交价为成交价。
    # 连续竞价中，以具有较新申报的成交价为成交价。
    if aggregate:
        for i in range(tier_num):
            if aligned['exchanged'][i] == max_exchanged:
                aligned['tiebreaker'][i] = -1/(1+abs(self.current_price-aligned['price'][i]))
        deal_price = aligned['price'][np.argmin(np.array(aligned['tiebreaker']))]
    else:
        for i in range(tier_num):
            if aligned['exchanged'][i] == max_exchanged:
                if len(aligned['buy'][i]) == 0:
                    youngest_stamp = aligned['sell'][i][-1].timestamp
                elif len(aligned['sell'][i]) == 0:
                    youngest_stamp = aligned['buy'][i][-1].timestamp
                else:
                    youngest_stamp = max(aligned['buy'][i][-1].timestamp, aligned['sell'][i][-1].timestamp)
                aligned['tiebreaker'][i] = youngest_stamp

        deal_price:float = aligned['price'][np.argmax(np.array(aligned['tiebreaker']))]

    # print(aligned['exchanged'], np.argmin(np.array(aligned['tiebreaker'])), deal_price)

    completed_bids = []
    completed_asks = []
    for i in range(tier_num):
        if aligned['price'][i] >= deal_price:
            completed_bids += aligned['buy'][i]
        if aligned['price'][-i - 1] <= deal_price:
            completed_asks += aligned['sell'][-i - 1]

    # 成交规则：高于成交价的买入全部成交，低于成交价的卖出全部成交，等于成交价的申报中，至少一侧全部成交。
    stock:Stock = Stock.find(stockID,mysql)
    total_done_amount:int = 0
    while len(completed_bids) != 0 and len(completed_asks) != 0:
        done_amount = min(completed_bids[0].amount, completed_asks[0].amount)
        total_done_amount += done_amount
        #print(completed_bids[0], completed_asks[0], done_amount)

        Pairing(completed_bids[0],completed_asks[0],done_amount,deal_price)

        if completed_bids[0].amount == 0:
            stock = ResolveOrder(stock,completed_bids[0], deal_price)
            completed_bids = completed_bids[1:]
        if completed_asks[0].amount == 0:
            stock = ResolveOrder(stock,completed_asks[0], deal_price)
            completed_asks = completed_asks[1:]

    if completed_asks:
        for remaining in completed_asks:
            stock = ResolveOrder(stock,remaining,deal_price)
    if completed_bids:
        for remaining in completed_bids:
            stock = ResolveOrder(stock,remaining,deal_price)

    stock.price = deal_price
    stock.volume = total_done_amount
    if aggregate:
        stock.openingPrice = stock.price

    # print(total_done_amount)
    return stock

