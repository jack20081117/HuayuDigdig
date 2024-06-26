﻿import logging,sqlite3
#logging.basicConfig(level=logging.INFO)
from globalConfig import *
from staticFunctions import fromstr,tostr

createArgsString=lambda num:('?,'*num)[:-1]#生成参数占位符字符串

def select(sql,mysql=False,args=()):
    if not mysql:
        with sqlite3.connect("data.db") as conn:
            cursor=conn.cursor()
            cursor.execute(sql,args)
            conn.commit()
            res=cursor.fetchall()
            cursor.close()
    else:
        #sql占位符是?,mysql占位符是%s,所以要对字符串进行replace操作
        connection.ping()
        mysqlcursor.execute(sql.replace('?','%s'),args)
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
        connection.ping()
        mysqlcursor.execute(sql.replace('?','%s'),args)
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
        attrs['__slots__']=tuple(mappings.keys())
        attrs['__mappings__']=mappings
        attrs['__table__']=tableName
        attrs['__primaryKey__']=primaryKey
        attrs['__fields__']=fields
        attrs['__create__']='create table if not exists `%s` (`%s` %s primary key,%s)'\
                            %(tableName,primaryKey,mappings[primaryKey].columnType,','.join(list(map(lambda f:'`%s` %s'%(f,mappings[f].columnType),fields))))
        attrs['__drop__']='drop table if exists %s'%tableName
        attrs['__select__']='select `%s`,%s from `%s`'\
                            %(primaryKey,','.join(escapedFields),tableName)
        attrs['__insert__']='replace into `%s` (`%s`,%s) values (%s)'\
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
            raise AttributeError(r"'%s' object has no attribute '%s'"%(self.__class__.__name__ or 'Model',item))

    def __setattr__(self,key,value):
        if key in self.keys():
            self[key]=value
        else:
            raise AttributeError(r"'%s' object has no attribute '%s'"%(self.__class__.__name__ or 'Model',key))

    def __eq__(self, other):
        if not isinstance(other,Model):
            return False
        if self[self.__primaryKey__]!=other[other.__primaryKey__]:
            return False
        if self.__fields__!=other.__fields__:
            return False
        for field in self.__fields__:
            if self[field]!=other[field]:
                return False
        return True

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
        """
        根据指定条件在表中查询对象
        :param mysql: 是否采用mysql
        :param where: 查询条件
        :param args: 查询条件参数
        :param kwargs: 其他附加参数
        :return: 查询结果 list[对象]
        """
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
        results=fromstr(results)
        return [cls(*result) for result in results]

    @classmethod
    def find(cls,primaryKey,mysql=False):
        """
        根据主键在表中查找对象
        :param primaryKey: 对象主键
        :param mysql: 是否采用mysql
        :return: 查找结果 对象 or None
        """
        results=select('%s where `%s`=?'%(cls.__select__,cls.__primaryKey__),mysql,(primaryKey,))
        if not results:
            return None
        result=fromstr(results[0])
        return cls(*result)

    @classmethod
    def create(cls,mysql=False):
        """
        在数据库中创建表
        :param mysql: 是否采用mysql
        """
        execute(cls.__create__,mysql)

    @classmethod
    def delete(cls,mysql=False):
        """
        在数据库中删除表
        :param mysql: 是否采用mysql
        """
        execute(cls.__drop__,mysql)

    def add(self,mysql=False):
        """
        在表中添加新对象
        :param mysql: 是否采用mysql
        """
        args=[self.getValueOrDefault(self.__primaryKey__)]
        args.extend(list(map(self.getValueOrDefault,self.__fields__)))
        args=list(map(tostr,args))
        execute(self.__insert__,mysql,tuple(args))

    def save(self,mysql=False):
        """
        在表中更新对象
        :param mysql: 是否采用mysql
        """
        args=list(map(self.getValue,self.__fields__))
        args.append(self.getValue(self.__primaryKey__))
        args=list(map(tostr,args))
        execute(self.__update__,mysql,tuple(args))

    def remove(self,mysql=False):
        """
        在表中删除对象
        :param mysql: 是否采用mysql
        """
        args=[self.getValue(self.__primaryKey__)]
        execute(self.__delete__,mysql,tuple(args))