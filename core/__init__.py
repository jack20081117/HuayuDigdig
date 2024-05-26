from model import *
from orm import execute
from globalConfig import dbconfig

if_delete_and_create = input("Do you want to DELETE the database and remake them again? This will DELETE ALL YOUR DATA NOW! (yes/no): ")
if if_delete_and_create == "yes":
    execute("drop database if exists %s", mysql, (dbconfig["db"], ))
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
else:
    print("Initialized Failed.")