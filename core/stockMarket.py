from tools import handler,drawtable
from model import Stock
from config import mysql

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