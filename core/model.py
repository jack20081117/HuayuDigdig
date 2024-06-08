from orm import Model,StringField,IntegerField,BooleanField,FloatField
from globalConfig import mysql

class User(Model):
    __table__='users'

    qid=StringField(columnType='varchar(20)',primaryKey=True)
    schoolID=StringField(columnType='varchar(5)')
    money=FloatField()
    mineral=StringField(columnType='varchar(2000)')
    #industrialTech=FloatField()
    #extractTech=FloatField()
    #refineTech=FloatField()
    tech=StringField(columnType='varchar(200)') #Dict str:float
    digable=BooleanField()
    factoryNum=IntegerField()
    effis=StringField(columnType='varchar(200)')
    mines=StringField(columnType='varchar(200)')
    stocks=StringField(columnType='varchar(2000)')
    enactedPlanTypes=StringField(columnType='varchar(200)') #dict for plan types
    busyFactoryNum=IntegerField()
    lastEffisUpdateTime = IntegerField()
    inputTax=FloatField() #进项税额（抵扣）
    outputTax=FloatField() #销项税额
    paidTaxes=BooleanField()
    techCards=StringField(columnType='varchar(2000)')


class Plan(Model):
    __table__='plans'

    planID=IntegerField(primaryKey=True)
    qid = StringField(columnType='varchar(20)')
    schoolID = StringField(columnType='varchar(5)')
    jobtype=IntegerField()
    factoryNum=IntegerField()
    ingredients=StringField(columnType='varchar(50)')
    techPath=StringField(columnType='varchar(200)')
    techName=StringField(columnType='varchar(20)')
    products=StringField(columnType='varchar(50)')
    workUnitsRequired=IntegerField()
    timeEnacted=IntegerField()
    timeRequired=IntegerField()
    enacted = BooleanField()


class Mine(Model):
    __table__='mines'

    mineID=IntegerField(primaryKey=True)
    abundance=FloatField()


class Sale(Model):
    __table__='sales'

    tradeID=IntegerField(primaryKey=True)
    qid=StringField(columnType='varchar(20)')
    mineralID=IntegerField()
    mineralNum=IntegerField()
    price=IntegerField()
    starttime=IntegerField()
    endtime=IntegerField()


class Purchase(Model):
    __table__='purchases'

    tradeID=IntegerField(primaryKey=True)
    qid=StringField(columnType='varchar(20)')
    mineralID=IntegerField()
    mineralNum=IntegerField()
    price=IntegerField()
    starttime=IntegerField()
    endtime=IntegerField()


class Auction(Model):
    __table__='auctions'

    tradeID=IntegerField(primaryKey=True)
    qid=StringField(columnType='varchar(20)')
    mineralID=IntegerField()
    mineralNum=IntegerField()
    price=IntegerField()
    starttime=IntegerField()
    endtime=IntegerField()
    secret=BooleanField()
    bestprice=IntegerField()
    offers=StringField(columnType='varchar(2000)')


class Stock(Model):
    __table__='stocks'

    stockID=StringField(columnType='varchar(3)',primaryKey=True)
    stockName=StringField(columnType='varchar(12)')
    stockNum=IntegerField()
    openStockNum=IntegerField() #一级市场认购时仍未被认购的股数
    provisionalFunds=FloatField() #一级市场认购进行时临时资金的存放处，如果成功上市将转移给发行人
    issuer=StringField(columnType='varchar(20)') #发行人
    price=FloatField()
    openingPrice=FloatField()
    volume=IntegerField()
    selfRetain=IntegerField() #一级市场发行时自留股数
    histprice=StringField(columnType='varchar(100)')
    shareholders=StringField(columnType='varchar(2000)')
    bidders=StringField(columnType='varchar(500)') # 本期买入者不能再进行卖出
    askers=StringField(columnType='varchar(500)') # 本期卖出者不能再进行买入
    primaryEndTime = IntegerField() #一级市场认购结束时间
    primaryClosed=BooleanField()
    secondaryOpen=BooleanField()
    avgDividend=FloatField()

class Order(Model): #股市委托
    __table__ = "orders"

    orderID = IntegerField(primaryKey=True)
    stockID = StringField(columnType='varchar(3)')
    requester = StringField(columnType='varchar(20)')
    buysell = BooleanField() #True = buy False = sell
    amount = IntegerField()
    completedAmount = IntegerField()
    priceLimit = FloatField()
    timestamp = IntegerField()
    funds = FloatField()

class StockData(Model): #持久化储存股市信息
    __table__ = "stockData"

    timestamp = StringField(columnType='varchar(20)',primaryKey=True)
    prices = StringField(columnType='varchar(500)') #字典，储存每个时间点股价
    volumes = StringField(columnType='varchar(500)') #字典，储存每个时间点成交量
    opening = BooleanField()
    closing = BooleanField()

class Debt(Model):
    __table__='debts'

    debtID=IntegerField(primaryKey=True)
    creditor=StringField(columnType='varchar(20)')  # 债权人
    debitor=StringField(columnType='varchar(20)')  # 债务人
    money=IntegerField()  # 贷款金额
    duration=IntegerField()
    starttime=IntegerField()
    endtime=IntegerField()
    interest=FloatField()

AllModels:list[Model]=[User,Mine,Sale,Purchase,Auction,Stock,Debt,Order,Plan]

if __name__=='__main__':  #创建新表
    for model in AllModels:
        model.create(mysql)
    for i in range(1,5):
        _mine=Mine(mineID=i,abundance=0.0)
        _mine.add(mysql)