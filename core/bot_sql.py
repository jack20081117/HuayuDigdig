import sqlite3

createUserTable = 'create table users (' \
           'qid varchar(10),' \
           'schoolID varchar(5),' \
           'money int,' \
           'mineral varchar(1000),' \
           'process_tech double,' \
           'extract_tech double,' \
           'digable boolean' \
           ') default charset utf8'  # 建表users

createUser = "insert into users " \
           "(qid,schoolID,money,mineral,process_tech,extract_tech,digable) " \
           "values ('%s','%s',%s,'%s',%f,%f,%s)" # 创建用户
           # 拥有的矿石 加工科技 开采科技 是否能继续挖矿 (最后四个)

selectUserBySchoolID="select * from users where schoolID='%s'" # 获取用户信息
selectUserByQQ="select * from users where qid='%s'" # 获取用户信息
selectUserByUserID = "select * from users where userid=%d"

updateMoneyByqq="update users set money=%d where qid='%s'"
updateMineByQQ ="update users set mineral='%s' where qid='%s'"
updateDigableByQQ ="update users set digable=%s where qid='%s'"
updateDigableAll="update users set digable=%s"

createMine='create table mines (' \
           'mineid int primary key,' \
           'abundance float' \
           ')'

insertMine="insert into mine " \
           "(mineID,abundance) " \
           "values (%d,%f)"

selectAbundanceByID="select abundance from mine where mineID=%d"

updateAbundanceByID="update mine set abundance=%f where mineID=%d"
updateAbundance="update mine set abundance=%f"

def select(database,sql):
    with sqlite3.connect(database) as conn:
        cursor=conn.cursor()
        cursor.execute(sql)
        conn.commit()
        res=cursor.fetchall()
        cursor.close()
    return res

def execute(database,sql):
    with sqlite3.connect(database) as conn:
        cursor=conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()

if __name__ == '__main__':
    execute('data.db',createUser)
    execute('data.db',createMine)
    execute('data.db',insertMine%(1,0))
    execute('data.db',insertMine%(2,0))
    execute('data.db',insertMine%(3,0))
    execute('data.db',insertMine%(4,0))
    execute('data.db',insertMine%(5,0))
    execute('data.db',insertMine%(6,0))