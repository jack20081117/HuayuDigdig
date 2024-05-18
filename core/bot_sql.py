import sqlite3

createUser='create table users (' \
           'userid int primary key auto_increment not null,' \
           'qq varchar(10),' \
           'schoolID varchar(5),' \
           'money int,' \
           'mineral varchar(1000),' \
           'process_tech double,' \
           'extract_tech double,' \
           'digable boolean' \
           ')'

insertUser="insert into users " \
           "(qq,schoolID,money,mineral,process_tech,extract_tech,digable) " \
           "values ('%s','%s',%s,'%s',%f,%f,%s)"

selectUserByID="select * from users where schoolID='%s'"
selectUserByqq="select * from users where qq='%s'"

updateMineByqq="update users set mineral='%s' where qq='%s'"
updateDigableByqq="update users set digable=%s where qq='%s'"
updateDigable="update users set digable=%s"

createMine='create table mine (' \
           'id int,' \
           'time int' \
           ')'

insertMine="insert into mine " \
           "(id,time) " \
           "values (%d,%d)"

selectTimeByID="select time from mine where id=%d"

updateTimeByID="update mine set time=%d where id=%d"
updateTime="update mine set time=%d"

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