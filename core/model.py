from orm import Model,StringField,IntegerField,BooleanField,FloatField
from globalConfig import mysql

class User(Model):
    __table__='users'

    qid=StringField(columnType='varchar(20)',primaryKey=True)
    schoolID=StringField(columnType='varchar(5)')
    money=IntegerField()
    mineral=StringField(columnType='varchar(2000)')
    process_tech=FloatField()
    extract_tech=FloatField()
    refine_tech=FloatField()
    digable=BooleanField()
    factory_num=IntegerField()
    effis=StringField(columnType='varchar(200)')
    mines=StringField(columnType='varchar(200)')
    stocks=StringField(columnType='varchar(2000)')


class Plan(Model):
    __table__='plans'

    planID=IntegerField(primaryKey=True)
    jobtype=IntegerField()
    ingredients=StringField(columnType='varchar(50)')
    product=StringField(columnType='varchar(50)')
    accumulated=FloatField()
    requirement=FloatField()


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
    stockName=StringField(columnType='varchar(8)')
    stockNum=IntegerField()
    issue_qid=StringField(columnType='varchar(20)')
    price=IntegerField()
    self_retain=FloatField()
    histprice=StringField(columnType='varchar(2000)')
    shareholders=StringField(columnType='varchar(2000)')
    avg_dividend=FloatField()


class Debt(Model):
    __table__='debts'

    debtID=IntegerField(primaryKey=True)
    creditor_id=StringField(columnType='varchar(20)')  # 债权人
    debitor_id=StringField(columnType='varchar(20)')  # 债务人
    money=IntegerField()  # 贷款金额
    duration=IntegerField()
    starttime=IntegerField()
    endtime=IntegerField()
    interest=FloatField()


if __name__=='__main__':  #创建新表
    User.create(mysql)
    Mine.create(mysql)
    Sale.create(mysql)
    Purchase.create(mysql)
    Auction.create(mysql)
    Stock.create(mysql)
    Debt.create(mysql)
    for i in range(1,5):
        _mine=Mine(mineID=i,abundance=0.0)
        _mine.save(mysql)