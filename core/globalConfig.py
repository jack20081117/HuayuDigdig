import json
import imgkit
import pymysql

from matplotlib import pyplot as plt
plt.rcParams['font.family']='Microsoft Yahei'

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
botID:str=config["bot_id"][env]
mysql:bool=(env=='prod')
effisItemCount:int=config["effis_item_count"]
effisDailyDecreaseRate:float=config["effis_daily_decrease_rate"]
permitBase:float=config["permit_cost"]
permitGradient:float=config["permit_gradient"]
factoryWUR=config['factory_wur']
robotWUR=config['robot_wur']
mesLength:int=config["message_maxLength"]

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
fuelFactorDict={
    0: 3,
    1: 6,
    2: 1,
    3: 2,
    4: 8,
    5: 4,
    6: 4,
    7: 4
}

chars="0123456789abcdef"