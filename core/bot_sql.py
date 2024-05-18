import sqlite3

createUser='create table users (' \
           'qq varchar(20),' \
           'schoolID varchar(10),' \
           'money varchar(20),' \
           'mineral varchar(1000),' \
           'process_tech varchar(10),' \
           'extract_tech varchar(10),' \
           'digable varchar(10)' \
           ')'

insertUser="insert into users " \
           "(qq,schoolID,money,mineral,process_tech,extract_tech,digable) " \
           "values ('%s','%s','%s','%s','%s','%s','%s')"

selectUserByID="select * from users where schoolID='%s'"
selectUserByqq="select * from users where qq='%s'"

updateMineByqq="update users set mineral='%s' where qq='%s'"
updateDigableByqq="update users set digable='%s' where qq='%s'"
updateDigable="update users set digable='%s'"

createMine='create table mine (' \
           'id varchar(10),' \
           'time varchar(10)' \
           ')'

insertMine="insert into mine " \
           "(id,time) " \
           "values ('%s','%s')"

selectTimeByID="select time from mine where id='%s'"

updateTimeByID="update mine set time='%s' where id='%s'"
updateTime="update mine set time='%s'"

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
    execute('data.db',insertMine%('1','0'))