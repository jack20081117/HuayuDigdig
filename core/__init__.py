from model import *
from orm import execute
from globalConfig import dbconfig
from tools import setCrontab
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
        last_effis_update_time=nowtime,
        input_tax=0.0,  # 进项税额（抵扣）
        output_tax=0.0,  # 销项税额
        paid_taxes=True
    )  # 注册新用户
    user.add(mysql)
    ans = "注册成功！"
    return ans

if_delete_and_create = input("Do you want to DELETE the database and remake them again? This will DELETE ALL YOUR DATA NOW! (yes/no): ")
if if_delete_and_create == "yes":
    execute("drop database if exists %s", mysql, (dbconfig["db"], ))
    User.create(mysql)
    create_treasury()
    Mine.create(mysql)
    Sale.create(mysql)
    Purchase.create(mysql)
    Auction.create(mysql)
    Stock.create(mysql)
    Debt.create(mysql)
    for i in range(1,5):
        _mine=Mine(mineID=i,abundance=0.0)
        _mine.save(mysql)
    setCrontab(tax_update,hour='23')
else:
    print("Initialized Failed.")