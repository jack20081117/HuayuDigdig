from model import AllModels,User,Mine
from orm import execute
from globalConfig import config,mysql
from tools import setCrontab,getnowtime,mineExpectation

def createTreasury():
    """
    注册国库
    """
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
    )
    user.add(mysql)

def createInitialMines():
    """
    注册公共矿井
    """
    Mine(
        mineID=1,
        abundance=0.0,
        lower=2,
        upper=30000,
        logUniform=False,
        expectation = mineExpectation(2,30000),
        private=False,
        owner='treasury',
        entranceFee=0.0,
    ).add(mysql)
    Mine(
        mineID=2,
        abundance=0.0,
        lower=2,
        upper=30000,
        logUniform=True,
        expectation=mineExpectation(2, 30000, logUniform=True),
        private=False,
        owner='treasury',
        entranceFee=0.0,
    ).add(mysql)
    Mine(
        mineID=3,
        abundance=0.0,
        lower=2,
        upper=999,
        logUniform=False,
        expectation=mineExpectation(2, 999),
        private=False,
        owner='treasury',
        entranceFee=0.0,
    ).add(mysql)
    Mine(
        mineID=4,
        abundance=0.0,
        lower=2,
        upper=999,
        logUniform=True,
        expectation=mineExpectation(2, 999,logUniform=True),
        private=False,
        owner='treasury',
        entranceFee=0.0,
    ).add(mysql)

if_delete_and_create = input("Do you want to DELETE the database and remake them? This will DELETE ALL YOUR DATA NOW! (y/n): ")
if if_delete_and_create == "y":
    if mysql:
        execute("drop database if exists %s", mysql, (config["db"], ))
    for model in AllModels:
        model.delete(mysql)
        model.create(mysql)
    createTreasury()
    createInitialMines()

    print('Successfully initialized.')

else:
    print("Failed to initialize.")