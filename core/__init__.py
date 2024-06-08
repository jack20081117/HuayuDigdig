from model import AllModels,User,Mine
from orm import execute
from globalConfig import config,mysql
from tools import setCrontab,getnowtime

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

    print('Initialized Successed.')

else:
    print("Initialized Failed.")