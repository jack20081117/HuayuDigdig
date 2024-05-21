from bot_model import *

with open("./config.json","r") as config:
    config=json.load(config)
env:str=config["env"]

createUserTable='create table users ('\
                'qid varchar(20),'\
                'schoolID varchar(5),'\
                'money int,'\
                'mineral varchar(1000),'\
                'process_tech double,'\
                'extract_tech double,'\
                'digable boolean'\
                ')'  # 建表users

createUserTableForMySQL='create table if not exists users ('\
                        'qid varchar(20),'\
                        'schoolID varchar(5),'\
                        'money int,'\
                        'mineral varchar(1000),'\
                        'process_tech double,'\
                        'extract_tech double,'\
                        'digable boolean'\
                        ') default charset utf8'  # 建表users

createMineTable='create table mine ('\
                'mineID int primary key,'\
                'abundance float'\
                ')'

createMineTableForMySQL='create table if not exists mine ('\
                        'mineID int primary key,'\
                        'abundance float'\
                        ')'

createSaleTable='create table sale ('\
                'saleID varchar(6),'\
                'qid varchar(20),'\
                'mineralID int,'\
                'mineralNum int,'\
                'auction boolean,'\
                'price int,'\
                'starttime int,'\
                'endtime int'\
                ')'

createPurchaseTable='create table purchase ('\
                'purchaseID varchar(6),'\
                'qid varchar(20),'\
                'mineralID int,'\
                'mineralNum int,'\
                'price int,'\
                'starttime int,'\
                'endtime int'\
                ')'

if __name__=='__main__':
    if env=="dev":
        execute(createUserTable,False)
        execute(createMineTable,False)
        execute(createSaleTable,False)
        execute(createPurchaseTable,False)
        for i in range(1,5):
            _mine=Mine(mineID=i,abundance=0.0)
            _mine.save(False)
    elif env=="prod":
        execute(createUserTableForMySQL,True)
        execute(createMineTableForMySQL,True)
        for i in range(1,5):
            _mine=Mine(mineID=i,abundance=0.0)
            _mine.save(True)
