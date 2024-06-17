from model import AllModels,User,Mine,Misc,Stock
from orm import execute
from globalConfig import config,mysql,adminIDs
from tools import getnowtime,mineExpectation

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
        stocks={},
        misc={},
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
        open=True,
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
        open=True,
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
        open=True,
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
        open=True,
        owner='treasury',
        entranceFee=0.0,
    ).add(mysql)

    return None

def createSystemMisc():
    Misc(
        miscID=1,
        name='Factory Building Permit',
        description='Entitles the owner to build a new facility.'
    ).add(mysql)
    Misc(
        miscID=2,
        name='Factory Building Permit Under Use',
        description='Entitles the owner to build a new facility. Is already attributed.'
    ).add(mysql)

def createPaperFuel():
    stock = Stock(stockID='pfu',
                  stockName='PaperFuel',
                  stockNum=0,
                  openStockNum=0,
                  provisionalFunds=0,
                  issuer='treasury',
                  price=3,
                  selfRetain=0,
                  primaryEndTime=0,
                  bidders=[],
                  askers=[],
                  histprice={'designatedIssuePrice': 3},
                  shareholders={},
                  primaryClosed=True,
                  secondaryOpen=False,
                  avgDividend=0.0)
    stock.add(mysql)

def createInitialStocks():
    Stock(stockID='lyi',
          stockName='Longyin Index',
          stockNum=0,
          openStockNum=0,
          provisionalFunds=0,
          issuer='treasury',
          price=100,
          selfRetain=0,
          primaryEndTime=0,
          bidders=[],
          askers=[],
          histprice={},
          shareholders={},
          primaryClosed=True,
          secondaryOpen=True,
          isIndex=True,
          avgDividend=0.0).add(mysql)

    Stock(stockID='loi',
          stockName='Longyin Oil Index',
          stockNum=0,
          openStockNum=0,
          provisionalFunds=0,
          issuer='treasury',
          price=100,
          selfRetain=0,
          primaryEndTime=0,
          bidders=[],
          askers=[],
          histprice={},
          shareholders={},
          primaryClosed=True,
          secondaryOpen=True,
          isIndex=True,
          avgDividend=0.0).add(mysql)

    Stock(stockID='adm',
          stockName='Administrative stock',
          stockNum=10000,
          openStockNum=0,
          provisionalFunds=0,
          issuer='treasury',
          price=100,
          selfRetain=4000,
          primaryEndTime=0,
          bidders=[],
          askers=[],
          histprice={},
          shareholders={adminID:2000 for adminID in adminIDs},
          primaryClosed=True,
          secondaryOpen=False,
          isIndex=False,
          avgDividend=0.0).add(mysql)

if_delete_and_create = input("Do you want to DELETE the database and remake them? This will DELETE ALL YOUR DATA NOW! (y/n): ")
if if_delete_and_create == "y":
    if mysql:
        execute("drop database if exists %s", mysql, (config["db"], ))
    for model in AllModels:
        model.delete(mysql)
        model.create(mysql)
    createTreasury()
    createInitialMines()
    createSystemMisc()
    createPaperFuel()
    createInitialStocks()

    print('Successfully initialized.')

else:
    print("Failed to initialize.")