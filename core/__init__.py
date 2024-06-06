from model import AllModels,User,Mine
from orm import execute
from globalConfig import config,mysql
from tools import setCrontab,getnowtime
from taxes import tax_update

def create_treasury():
    user = User(
        qid='treasury',
        schoolID='gov01',
        money=0,
        mineral={},
        industrial_tech=0.0,
        extract_tech=0.0,
        refine_tech=0.0,
        digable=1,
        factory_num=1,
        effis={},
        mines=[],
        stocks=[],
        enacted_plan_types={},
        busy_factory_num=0,
        last_effis_update_time=getnowtime(),
        input_tax=0.0,  # 进项税额（抵扣）
        output_tax=0.0,  # 销项税额
        paid_taxes=True
    )  # 注册新用户
    user.add(mysql)
    ans = "注册成功！"
    return ans

if_delete_and_create = input("Do you want to DELETE the database and remake them again? This will DELETE ALL YOUR DATA NOW! (yes/no): ")
if if_delete_and_create == "yes":
    if mysql:
        execute("drop database if exists %s", mysql, (config["db"], ))
    for model in AllModels:
        model.create(mysql)
    create_treasury()
    for i in range(1,5):
        _mine=Mine(mineID=i,abundance=0.0)
        _mine.save(mysql)
    setCrontab(tax_update,hour='23')

    setCrontab(StockMarketOpen, hour='8,13,18', minute='30') #股市开盘
    setCrontab(ResolveAuction, hour='9,14,19', minute='0', second='0',aggregate=True) #集合竞价结算
    setCrontab(ResolveAuction, hour='9,14,19', minute='4-56/4', second='0', aggregate=False)
    setCrontab(ResolveAuction, hour='10-12,15-17,20-22', minute='0-56/4', second='0',aggregate=False)
    setCrontab(ResolveAuction, hour='13,18,23', minute='0', second='0', aggregate=False,closing=True) # 股市收盘交易
    setCrontab(StockMarketClose, hour='13,18,23', minute='0', second='1')  # 股市收盘后勤

else:
    print("Initialized Failed.")