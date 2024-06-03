from tools import drawtable,setTimeTask,getnowtime
from model import Stock
from globalConfig import mysql

def issue(message_list:list[str],qid:str):
    """
    :param message_list: 发行 股票名称 缩写 发行量 价格 自我保留股数
    :param qid: 发行者的qq号
    :return: 发行提示信息
    """
    assert len(message_list)==6,'发行失败:您的发行格式不正确！'
    stockName:str=message_list[1]
    stockID:str=message_list[2]
    assert 3<len(stockName)<=12,'发行失败:股票名称必须为4-12个字符！'
    assert len(stockID)==3,'发行失败:股票缩写必须为3个字符！'
    stockNum:int=int(message_list[3])
    assert 10000<=stockNum<=100000,'发行失败:股票发行量必须在10000股到100000股之间！'
    price:float=float(message_list[4])
    assert price < 100,'发行失败：初始股价过高！'
    selfRetain:int=int(message_list[5])
    assert 0<=selfRetain<0.5*stockNum,'发行失败:自我持有量过低或过高！'
    nowtime = getnowtime()
    primaryEndTime = nowtime + 86400

    stock=Stock(stockID=stockID,stockName=stockName,stockNum=stockNum,issue_qid=qid,price=price,self_retain=selfRetain,
                primaryEndTime=primaryEndTime,histprice={},shareholders={},avg_dividend=0.0)
    stock.add(mysql)
    setTimeTask(primaryClosing,primaryEndTime)
    ans='发行成功！您的股票将在一级市场开放认购24小时，随后开始在二级市场流通。'
    return ans

def primaryClosing(stock:Stock):
    shareholders:dict = stock.shareholders
    #for holderID, amount in shareholders.items():

    return None

def acquireStock(message_list:list[str],qid:str):
    """
    :param message_list: 认购 股票名称/缩写 股数
    :param qid:
    :return: 提示信息
    """

    # TODO: assertions

    stockNum: int = int(message_list[2])
    assert stockNum >= 1000,'认购失败！在一级市场认购股票需购买至少1000股！'

    #Transfer of assets

    return ans


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