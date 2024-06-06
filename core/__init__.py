from model import AllModels,User,Mine
from orm import execute
from globalConfig import config,mysql
from tools import setCrontab,getnowtime
from taxes import taxUpdate
from stock import resolveAuction,stockMarketOpen,stockMarketClose

def create_treasury():
    user = User(
        qid='treasury',
        schoolID='gov01',
        money=0,
        mineral={},
        industrialTech=0.0,
        extractTech=0.0,
        refineTech=0.0,
        digable=1,
        factoryNum=1,
        effis={},
        mines=[],
        stocks=[],
        enactedPlanTypes={},
        busyFactoryNum=0,
        lastEffisUpdateTime=getnowtime(),
        inputTax=0.0,  # 进项税额（抵扣）
        outputTax=0.0,  # 销项税额
        paidTaxes=True
    )  # 注册国库
    user.add(mysql)

if_delete_and_create = input("Do you want to DELETE the database and remake them again? This will DELETE ALL YOUR DATA NOW! (yes/no): ")
if if_delete_and_create == "yes":
    if mysql:
        execute("drop database if exists %s", mysql, (config["db"], ))
    for model in AllModels:
        model.delete(mysql)
        model.create(mysql)
    create_treasury()
    for i in range(1,5):
        _mine=Mine(mineID=i,abundance=0.0)
        _mine.add(mysql)
    setCrontab(taxUpdate,hour='23')

    setCrontab(stockMarketOpen, hour='8,13,18', minute='30') #股市开盘
    setCrontab(resolveAuction, hour='9,14,19', minute='0', second='0',aggregate=True) #集合竞价结算
    setCrontab(resolveAuction, hour='9,14,19', minute='4-56/4', second='0', aggregate=False)
    setCrontab(resolveAuction, hour='10-12,15-17,20-22', minute='0-56/4', second='0',aggregate=False)
    setCrontab(resolveAuction, hour='13,18,23', minute='0', second='0', aggregate=False,closing=True) # 股市收盘交易
    setCrontab(stockMarketClose, hour='13,18,23', minute='0', second='1')  # 股市收盘后勤

    print('Initialized Successed.')

else:
    print("Initialized Failed.")