import logging,sqlite3,json,pymysql
#logging.basicConfig(level=logging.INFO)

createArgsString=lambda num:('?,'*num)[:-1]

with open("./config.json","r") as config:
    config=json.load(config)
env:str=config["env"]

if env=="prod":
    with open("./mysql.json","a") as config:
        pass
    with open("./mysql.json","r") as dbconfig:
        dbconfig=json.load(dbconfig)
    connection=pymysql.connect(host=dbconfig["host"],user=dbconfig["user"],password=dbconfig["password"],
                               db=dbconfig["db"],charset="utf8")
    mysqlcursor=connection.cursor()

def select(sql,mysql=False,args=()):
    if not mysql:
        with sqlite3.connect("data.db") as conn:
            cursor=conn.cursor()
            cursor.execute(sql,args)
            conn.commit()
            res=cursor.fetchall()
            cursor.close()
    else:
        mysqlcursor.execute(sql,args)
        res=mysqlcursor.fetchall()
    return res

def execute(sql,mysql=False,args=()):
    if not mysql:
        with sqlite3.connect("data.db") as conn:
            cursor=conn.cursor()
            cursor.execute(sql,args)
            conn.commit()
            cursor.close()
    else:
        mysqlcursor.execute(sql,args)
        connection.commit()

class Field(object):
    def __init__(self,name,columnType,primaryKey,default):
        self.name=name
        self.columnType=columnType
        self.primaryKey=primaryKey
        self.default=default

    def __str__(self):
        return '<%s,%s:%s>'%(self.__class__.__name__,self.columnType,self.name)

class StringField(Field):
    def __init__(self,name=None,columnType='varchar(100)',primaryKey=False,default=None):
        super(StringField,self).__init__(name,columnType,primaryKey,default)

class BooleanField(Field):
    def __init__(self,name=None,default=None):
        super(BooleanField,self).__init__(name,'boolean',False,default)

class IntegerField(Field):
    def __init__(self,name=None,primaryKey=False,default=None):
        super(IntegerField,self).__init__(name,'bigint',primaryKey,default)

class FloatField(Field):
    def __init__(self,name=None,default=None):
        super(FloatField,self).__init__(name,'double',False,default)

class ModelMetaclass(type):
    def __new__(mcs,name,bases,attrs):
        if name=='Model':
            return type.__new__(mcs,name,bases,attrs)
        tableName=attrs.get('__table__',None) or name
        logging.info('Found model:%s (table:%s)'%(name,tableName))
        mappings={}
        fields=[]
        primaryKey=None
        for k,v in attrs.items():
            if not isinstance(v,Field):
                continue
            logging.info('Found mapping:%s ==> %s'%(k,v))
            mappings[k]=v
            if v.primaryKey:
                if primaryKey:
                    raise RuntimeError('Duplicate primary key for field:%s'%k)
                primaryKey=k
            else:
                fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        for k in mappings.keys():
            attrs.pop(k)
        escapedFields=list(map(lambda f:'`%s`'%f,fields))
        attrs['__mappings__']=mappings
        attrs['__table__']=tableName
        attrs['__primaryKey__']=primaryKey
        attrs['__fields__']=fields
        attrs['__create__']='create table if not exists `%s` (`%s` %s primary key,%s)'\
                            %(tableName,primaryKey,mappings[primaryKey].columnType,','.join(list(map(lambda f:'`%s` %s'%(f,mappings[f].columnType),fields))))
        attrs['__select__']='select `%s`,%s from `%s`'\
                            %(primaryKey,','.join(escapedFields),tableName)
        attrs['__insert__']='insert into `%s` (`%s`,%s) values (%s)'\
                            %(tableName,primaryKey,','.join(escapedFields),createArgsString(len(escapedFields)+1))
        attrs['__update__']='update `%s` set %s where `%s`=?'\
                            %(tableName,','.join(map(lambda f:'`%s`=?'%(mappings.get(f).name or f),fields)),primaryKey)
        attrs['__delete__']='delete from `%s` where `%s`=?'\
                            %(tableName,primaryKey)
        return type.__new__(mcs,name,bases,attrs)

class Model(dict,metaclass=ModelMetaclass):
    def __init__(self,*args,**kwargs):
        if kwargs:
            super(Model,self).__init__(**kwargs)
        else:
            try:
                _kwargs={}
                _args=list(args)
                for key in self.__mappings__.keys():
                    _kwargs[key]=_args[0]
                    _args.pop(0)
                super(Model,self).__init__(**_kwargs)
            except:
                raise RuntimeError('Lack of argument.')

    def __getattr__(self,item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'"%item)

    def __setattr__(self,key,value):
        self[key]=value

    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):
        value=getattr(self,key,None)
        if value is None:
            field=self.__mappings__[key]
            if field.default is not None:
                value=field.default() if callable(field.default) else field.default
                logging.debug('Using default value for %s:%s'%(key,str(value)))
                setattr(self,key,value)
        return value

    @classmethod
    def findAll(cls,mysql=False,where=None,args=None,**kwargs):
        sql=[cls.__select__]
        if where:
            sql.extend(['where',where])
        if args is None:
            args=[]
        orderBy=kwargs.get('orderBy',None)
        if orderBy:
            sql.extend(['order by',orderBy])
        limit=kwargs.get('limit',None)
        if limit:
            sql.append('limit')
            if isinstance(limit,int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit,tuple) and len(limit)==2:
                sql.append('?,?')
                args.append(limit)
            else:
                raise ValueError('Invalid limit value:%s'%str(limit))
        results=select(' '.join(sql),mysql,tuple(args))
        return [cls(*result) for result in results]

    @classmethod
    def find(cls,primaryKey,mysql=False):
        results=select('%s where `%s`=?'%(cls.__select__,cls.__primaryKey__),mysql,(primaryKey,))
        if not results:
            return None
        return cls(*results[0])

    @classmethod
    def create(cls,mysql=False):
        execute(cls.__create__,mysql)

    def save(self,mysql=False):
        args=[self.getValueOrDefault(self.__primaryKey__)]
        args.extend(list(map(self.getValueOrDefault,self.__fields__)))
        execute(self.__insert__,mysql,tuple(args))

    def update(self,mysql=False):
        args=list(map(self.getValue,self.__fields__))
        args.append(self.getValue(self.__primaryKey__))
        execute(self.__update__,mysql,tuple(args))

    def remove(self,mysql=False):
        args=[self.getValue(self.__primaryKey__)]
        execute(self.__delete__,mysql,tuple(args))

class User(Model):
    __table__='users'

    qid=StringField(columnType='varchar(20)',primaryKey=True)
    schoolID=StringField(columnType='varchar(5)')
    money=IntegerField()
    mineral=StringField(columnType='varchar(1000)')
    process_tech=FloatField()
    extract_tech=FloatField()
    refine_tech=FloatField()
    digable=BooleanField()
    factory_num=IntegerField()
    productivity=FloatField()
    efficiency=StringField(columnType='varchar(50)')
    mines=StringField(columnType='varchar(200)')

class Mine(Model):
    __table__='mines'

    mineID=IntegerField(primaryKey=True)
    abundance=FloatField()

class Sale(Model):
    __table__='sales'

    saleID=StringField(columnType='varchar(6)',primaryKey=True)
    qid=StringField(columnType='varchar(20)')
    mineralID=IntegerField()
    mineralNum=IntegerField()
    price=IntegerField()
    starttime=IntegerField()
    endtime=IntegerField()

class Purchase(Model):
    __table__='purchases'

    purchaseID=StringField(columnType='varchar(6)',primaryKey=True)
    qid=StringField(columnType='varchar(20)')
    mineralID=IntegerField()
    mineralNum=IntegerField()
    price=IntegerField()
    starttime=IntegerField()
    endtime=IntegerField()

class Auction(Model):
    __table__='auctions'

    auctionID=StringField(columnType='varchar(6)',primaryKey=True)
    qid=StringField(columnType='varchar(20)')
    mineralID=IntegerField()
    mineralNum=IntegerField()
    price=IntegerField()
    starttime=IntegerField()
    endtime=IntegerField()
    secret=BooleanField()
    bestprice=IntegerField()
    offers=StringField(columnType='varchar(250)')

if __name__ == '__main__':
    # user=User(qid='1329913830',schoolID='24885',money=0,mineral='{}',process_tech=0.0,extract_tech=0.0,digable=1)
    # user.save(False)
    # user=User.find('1329913830')
    # user.money=100
    # user.update(False)
    # purchase=Purchase.find('fc0e56')
    # print(purchase)
    User.create(False)
    Mine.create(False)
    Sale.create(False)
    Purchase.create(False)
    Auction.create(False)
    # for i in range(1,5):
    #     _mine=Mine(mineID=i,abundance=0.0)
    #     _mine.save(False)