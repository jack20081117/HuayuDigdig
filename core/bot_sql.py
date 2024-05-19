import json
import sqlite3
import pymysql

with open("./config.json","r") as config:
    config=json.load(config)
env: str=config["env"]

if env=="prod":
    with open("./mysql.json","a") as config:
        pass
    with open("./mysql.json","r") as dbconfig:
        dbconfig=json.load(dbconfig)
    connection=pymysql.connect(host=dbconfig["host"],user=dbconfig["user"],password=dbconfig["password"],
                               db=dbconfig["db"],charset="utf8")
    mysqlcursor=connection.cursor()

createUserTable='create table users ('\
                'qid varchar(10),'\
                'schoolID varchar(5),'\
                'money int,'\
                'mineral varchar(1000),'\
                'process_tech double,'\
                'extract_tech double,'\
                'digable boolean'\
                ')'  # 建表users

createUserTableForMySQL='create table if not exists users ('\
                        'qid varchar(10),'\
                        'schoolID varchar(5),'\
                        'money int,'\
                        'mineral varchar(1000),'\
                        'process_tech double,'\
                        'extract_tech double,'\
                        'digable boolean'\
                        ') default charset utf8'  # 建表users

createUser="insert into users "\
           "(qid,schoolID,money,mineral,process_tech,extract_tech,digable) "\
           "values ('%s','%s',%d,'%s',%f,%f,%d)"  # 创建用户
# 拥有的矿石 加工科技 开采科技 是否能继续挖矿 (最后四个)

selectUserBySchoolID="select * from users where schoolID=%s"  # 获取用户信息
selectUserByQQ="select * from users where qid=%s"  # 获取用户信息
selectUserByUserID="select * from users where userid=%d"

updateMoneyByQQ="update users set money=%d where qid=%s"
updateMineByQQ="update users set mineral='%s' where qid=%s"
updateDigableByQQ="update users set digable=%s where qid=%s"
updateDigableAll="update users set digable=%s"

createMineTable='create table mine ('\
                'mineid int primary key,'\
                'abundance float'\
                ')'

createMineTableForMySQL='create table if not exists mine ('\
                        'mineid int primary key,'\
                        'abundance float'\
                        ')'

insertMine="insert into mine "\
           "(mineID,abundance) "\
           "values (%s,%s)"

selectAbundanceByID="select abundance from mine where mineID=%d"

updateAbundanceByID="update mine set abundance=%f where mineID=%d"
updateAbundanceAll="update mine set abundance=%f"

def select(sql, mysql=False, args=()):
    if not mysql:
        with sqlite3.connect("data.db") as conn:
            cursor=conn.cursor()
            if args:
                sql=sql%args
            cursor.execute(sql)
            conn.commit()
            res=cursor.fetchall()
            cursor.close()
    else:
        mysqlcursor.execute(sql,args)
        res = mysqlcursor.fetchall()
    return res

def execute(sql,mysql=False,args=()):
    if not mysql:
        with sqlite3.connect("data.db") as conn:
            cursor=conn.cursor()
            if args:sql=sql%args
            cursor.execute(sql)
            conn.commit()
            cursor.close()
    else:
        mysqlcursor.execute(sql,args)
        connection.commit()

if __name__=='__main__':
    if env=="dev":
        execute(createUserTable,False)
        execute(createMineTable,False)
        execute(insertMine,False,(1,0))
        execute(insertMine,False,(2,0))
        execute(insertMine,False,(3,0))
        execute(insertMine,False,(4,0))
    elif env=="prod":
        execute(createUserTableForMySQL,True)
        execute(createMineTableForMySQL,True)
        execute(insertMine,True,(1,0))
        execute(insertMine,True,(2,0))
        execute(insertMine,True,(3,0))
        execute(insertMine,True,(4,0))
