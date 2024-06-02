from orm import Model,StringField,IntegerField,BooleanField,FloatField
from globalConfig import mysql

class User(Model):
    __table__='users'

    qid=StringField(columnType='varchar(20)',primaryKey=True)
    schoolID=StringField(columnType='varchar(5)')
    money=FloatField()
    mineral=StringField(columnType='varchar(2000)')
    industrial_tech=FloatField()
    extract_tech=FloatField()
    refine_tech=FloatField()
    digable=BooleanField()
    factory_num=IntegerField()
    effis=StringField(columnType='varchar(200)')
    mines=StringField(columnType='varchar(200)')
    stocks=StringField(columnType='varchar(2000)')
    enacted_plan_types=StringField(columnType='varchar(200)') #dict for plan types
    busy_factory_num=IntegerField()
    last_effis_update_time = IntegerField()
    input_tax=FloatField() #进项税额（抵扣）
    output_tax=FloatField() #销项税额
    paid_taxes=BooleanField()


class Plan(Model):
    __table__='plans'

    planID=IntegerField(primaryKey=True)
    qid = StringField(columnType='varchar(20)')
    schoolID = StringField(columnType='varchar(5)')
    jobtype=IntegerField()
    factory_num=IntegerField()
    ingredients=StringField(columnType='varchar(50)')
    products=StringField(columnType='varchar(50)')
    work_units_required=IntegerField()
    time_enacted=IntegerField()
    time_required=IntegerField()
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
    primary_sold=IntegerField()
    issue_qid=StringField(columnType='varchar(20)')
    price=FloatField()
    self_retain=FloatField()
    histprice=StringField(columnType='varchar(2000)')
    shareholders=StringField(columnType='varchar(2000)')
    primaryEndTime = IntegerField()
    primary_ended=BooleanField()
    secondary_open=BooleanField()
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
    Plan.create(mysql)
    Mine.create(mysql)
    Sale.create(mysql)
    Purchase.create(mysql)
    Auction.create(mysql)
    Stock.create(mysql)
    Debt.create(mysql)
    for i in range(1,5):
        _mine=Mine(mineID=i,abundance=0.0)
        _mine.add(mysql)