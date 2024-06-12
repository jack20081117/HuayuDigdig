import json
import imgkit
import pymysql

headers:dict={
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58'
}

imgkit_config=imgkit.config(wkhtmltoimage=r'D:/Program Files/wkhtmltopdf/bin/wkhtmltoimage.exe')

with open("./config.json","r",encoding='utf-8') as config:
    config=json.load(config)
env:str=config["env"]
vatRate:float=config["tax"]["vat"]
playerTax:float=config['tax']['player']
deposit:float=config["deposit"]
groupIDs:list=config['group_ids']
adminIDs:list=config['admin_ids']
botID:str=config['bot_id']
mysql:bool=(env=='prod')
effisItemCount:int=config["effis_item_count"]
effisDailyDecreaseRate:float=config["effis_daily_decrease_rate"]
permitBase:float=config["permit_cost"]
permitGradient:float=config["permit_gradient"]

stockMarketOpenFlag = False

if mysql:
    with open("./mysql.json","a") as config:
        pass
    with open("./mysql.json","r") as dbconfig:
        dbconfig=json.load(dbconfig)
    connection=pymysql.connect(host=dbconfig["host"],user=dbconfig["user"],password=dbconfig["password"],
                               db=dbconfig["db"],charset="utf8")
    mysqlcursor=connection.cursor()

effisStr=['分解效率','合成效率','复制效率','修饰效率','炼油效率','建工效率','科研效率','勘探效率']
effisNameDict={'分解':0,'合成':1,'复制':2,'修饰':3,'炼油':4,'建工':5,'科研':6,'勘探':7}
effisValueDict={0:'分解',1:'合成',2:'复制',3:'修饰',4:'炼油',5:'建工',6:'科研',7:'勘探'}
fuelFactorDict={0: 4, 1: 4, 2: 1, 3: 2, 4: 8, 5: 2, 6: 4, 7: 4}

infoMsg="查询到QQ号为:%s的用户信息\n"\
         "学号:%s\n"\
         "当前余额:%s\n"\
         "加工科技点:%s\n"\
         "开采科技点:%s\n"\
         "炼油科技点:%s\n"\
         "当前是否可开采:%s\n"\
         "以下为该用户拥有的矿石:\n%s"\
         "工厂数: %s\n"\
         "以下为该玩家各工种生产效率:\n%s"\
         "以下为该玩家拥有的私人矿井编号:\n%s"

chars="0123456789abcdef"