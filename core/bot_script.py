from datetime import datetime
from bot_model import *
import numpy as np
import json,requests,re,hashlib
from matplotlib import pyplot as plt
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler as bgsc
plt.rcParams['font.family']=['Microsoft YaHei']

headers={
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58'
}

with open("./config.json","r",encoding='utf-8') as config:
    config=json.load(config)
env:str=config["env"]
player_tax:float=config["tax"]["player"]
deposit:float=config["deposit"]
delay:dict=config['delay']
group_ids:list=config['group_ids']
mysql:bool=(env=='prod')

def sigmoid(x:float)->float:return 1/(1+np.exp(-x))

help_msg='您好！欢迎使用森bot！\n'\
         '您可以使用如下功能:\n'\
         '1:查询时间:输入 time\n'\
         '2:注册账号:输入 注册 `学号`\n'\
         '3:查询信息:输入 查询  即可获取用户个人信息\n'\
         '4:开采矿石:输入 开采 `矿井编号`\n'\
         '    4.1 矿井1号会生成从2-30000均匀分布的随机整数矿石\n'\
         '    4.2 矿井2号会生成从2-30000对数均匀分布的随机整数矿石\n'\
         '    4.3 矿井3号会生成从2-999均匀分布的随机整数矿石\n'\
         '    4.4 矿井4号会生成从2-999对数均匀分布的随机整数矿石\n'\
         '5:兑换矿石:输入 兑换 `矿石编号` 只有在矿石编号为3、5、6位学号的因数或班级因数时才可兑换！\n'\
         '6:矿石市场:\n' \
         '注:除快捷键外，本节所有时间格式必须为YYYY-MM-DD,hh:mm:ss格式，"是否"数值取值为0或1\n' \
         '    6.1 市场 输入 市场 即可查看目前市场上存在的交易\n'\
         '    6.2 预售矿石 输入 预售 `矿石编号` `矿石数目` `价格` `起始时间` `终止时间` 即可在市场上预售矿石\n'\
         '    6.3 购买矿石 输入 购买 `交易编号`\n'\
         '    6.4 预订矿石 输入 预订 `矿石编号` `矿石数目` `价格` `起始时间` `终止时间` 即可在市场上预订矿石\n'\
         '    6.5 售卖矿石 输入 售卖 `交易编号`\n' \
         '    6.6 拍卖矿石 输入 拍卖 `矿石编号` `矿石数目` `底价` `起始时间` `终止时间` `是否对出价保密` 即可在市场上拍卖矿石\n' \
         '    6.7 投标矿石 输入 投标 `交易编号` `出价` 要求支付数额为出价%d%%的押金，在拍卖终止时结算，最终出价为出价第二高者的出价\n'\
         '快捷键:now:当前时间 10min:十分钟后 30min:半小时后 1h:一小时后 3h:三小时后\n' \
         '7:支付金钱:输入 支付 `编号` $`金额` (金额前应带有美元符号$)即可向对方支付指定金额\n'\
         '    7.1 向QQ用户支付，编号以q开头，后加QQ号\n'\
         '    7.2 向指定学号用户支付，直接输入学号即可\n' \
         ''%(round(deposit*100))

commands:dict={}

def handler(funcStr):
    """
    该装饰器装饰的函数会自动加入handle函数
    :param funcStr: 功能
    """
    def real_handler(func):
        commands[funcStr]=func
        return func

    return real_handler

def init():
    """
    在矿井刷新时进行初始化
    """
    execute('update users set digable=?',mysql,(1,))
    execute('update mines set abundance=?',mysql,(0.0,))
    update()

def update():
    """
    防止由于程序中止而未能成功进行事务更新
    """
    nowtime=round(datetime.timestamp(datetime.now()))
    endedSales:list[Sale]=Sale.findAll(mysql,'endtime<?',(nowtime,))  #已经结束的预售
    endedPurchases:list[Purchase]=Purchase.findAll(mysql,'endtime<?',(nowtime,))  #已经结束的预订
    endedAuctions:list[Auction]=Purchase.findAll(mysql,'endtime<?',(nowtime,))

    for sale in endedSales:
        updateSale(sale)
    for purchase in endedPurchases:
        updatePurchase(purchase)
    for auction in endedAuctions:
        updateAuction(auction)

def updateSale(sale:Sale):
    """
    :param sale: 到达截止时间的预售
    """
    qid:str=sale.qid
    tradeID:str=sale.tradeID
    user:User=User.find(qid,mysql)
    if Sale.find(tradeID) is None:#预售已成功进行
        return None

    mineralID:int=sale.mineralID
    mineralNum:int=sale.mineralNum
    mineralDict:dict=dict(eval(user.mineral))
    if mineralID not in mineralDict:
        mineralDict[mineralID]=0
    mineralDict[mineralID]+=mineralNum#将矿石返还给预售者
    user.mineral=str(mineralDict)

    user.update(mysql)
    sale.remove(mysql)

    send(qid,'您的预售:%s未能进行,矿石已返还到您的账户'%tradeID,False)

def updatePurchase(purchase:Purchase):
    """
    :param purchase: 到达截止时间的预订
    """
    qid:str=purchase.qid
    tradeID:str=purchase.tradeID
    user:User=User.find(qid,mysql)
    if Purchase.find(tradeID) is None:#预订已成功进行
        return None

    price:int=purchase.price
    user.money+=price#将钱返还给预订者

    user.update(mysql)
    purchase.remove(mysql)

    send(qid,'您的预订:%s未能进行,钱已返还到您的账户'%tradeID,False)

def updateAuction(auction:Auction):
    """
    :param auction: 到达截止时间的拍卖
    """
    qid:str=auction.qid
    tradeID:str=auction.tradeID
    user:User=User.find(qid,mysql)
    offersList:list=list(eval(auction.offers))

    bids:list[tuple[str,int,int]]=sorted(offersList,key=lambda t:(t[1],-t[2]),reverse=True)#先按出价从大到小排序再按时间从小到大排序
    mineralID:int=auction.mineralID
    mineralNum:int=auction.mineralNum
    while bids:
        success=False#投标是否成功
        tqid:str=bids[0][0]
        if len(bids)==1:
            bids.append(('nobody',auction.price,0))#默认最后一人
        if tqid=='nobody':#无人生还
            bids.pop()
            break
        tuser:User=User.find(tqid)
        if tuser.money+round(bids[0][1]*deposit)>=bids[1][1]:#第一人现金+第一人押金>=第二人出价
            success=True#投标成功
            tuser.money-=bids[0][1]-round(bids[0][1]*deposit)#扣除剩余金额
            tmineralDict:dict=dict(eval(tuser.mineral))
            if mineralID not in tmineralDict:
                tmineralDict[mineralID]=0
            tmineralDict[mineralID]+=mineralNum#给予矿石
            tuser.mineral=str(tmineralDict)
            tuser.update(mysql)
            send(tqid,'您在拍卖:%s中竞拍成功，矿石已发送到您的账户'%tradeID,False)

            user.money+=bids[0][1]
            user.update(mysql)

            for otherbid in bids[1:]:#返还剩余玩家押金
                otheruser=User.find(otherbid[0])
                otheruser.money+=round(otherbid[1]*deposit)
                otheruser.update(mysql)
                send(otheruser.qid,'您在拍卖:%s中竞拍失败，押金已返还到您的账户'%tradeID,False)
        else:#投标失败
            bids.pop(0)#去除第一人
            send(tqid,'您在拍卖:%s中竞拍失败，押金已扣除'%tradeID,False)
        if success:#结束投标
            break
    if not bids:
        mineralDict:dict=dict(eval(user.mineral))
        if mineralID not in mineralDict:
            mineralDict[mineralID]=0
        mineralDict[mineralID]+=mineralNum  #将矿石返还给拍卖者
        user.mineral=str(mineralDict)

        user.update(mysql)
        auction.remove(mysql)

        send(qid,'您的拍卖:%s未能进行,矿石已返还到您的账户'%tradeID,False)

def extract(qid,mineralID,mineID):
    """获取矿石
    :param qid:开采者的qq号
    :param mineralID:开采得矿石的编号
    :param mineID:矿井编号
    :return:开采信息
    """
    mine:Mine=Mine.find(mineID,mysql)
    #abundance:float=select(selectAbundanceByID,mysql,(mineID,))[0][0]  # 矿井丰度
    abundance:float=mine.abundance #矿井丰度
    user:User=User.find(qid,mysql)
    mineral=user.mineral # 用户拥有的矿石（str of dict）
    extractTech=user.extract_tech # 开采科技

    assert user.digable,'开采失败:您必须等到下一个整点才能再次开采矿井！'

    # 决定概率 
    if abundance==0.0:#若矿井未被开采过，则首次成功率为100%
        prob=1.0
    else:
        prob=round(abundance*sigmoid(extractTech),2)

    if np.random.random()>prob:#开采失败
        user.digable=0#在下一次刷新前不可开采
        user.update(mysql)
        ans='开采失败:您的运气不佳，未能开采成功！'
    else:
        mineralDict:dict=dict(eval(mineral))
        if mineralID not in mineralDict:#用户不具备此矿石
            mineralDict[mineralID]=0
        mineralDict[mineralID]+=1 #加一个矿石
        user.mineral=str(mineralDict)
        user.update(mysql)
        mine.abundance=prob#若开采成功，则后一次的丰度是前一次的成功概率
        mine.update(mysql)
        ans='开采成功！您获得了编号为%d的矿石！'%mineralID
    return ans

def drawtable(data:list,filename:str):
    """
    将市场信息绘制成表格
    :param data: 要绘制的表格数据
    :param filename: 存储图片地址
    :return:
    """
    fig,ax=plt.subplots()
    table=ax.table(cellText=data,loc='center')
    table.auto_set_font_size(False)
    #table.set_fontsize(10)

    for key,cell in table.get_celld().items():
        cell.set_text_props(fontsize=8,ha='center',va='center')

    table.auto_set_column_width(col=list(range(len(data[0]))))

    ax.axis('off')
    plt.savefig('../go-cqhttp/data/images/%s'%filename)

def setInterval(func:callable,interval:int,*args,**kwargs):
    """
    定时触发任务
    :param func: 要触发的任务（函数）
    :param interval: 触发间隔（s）
    :param args: 任务参数
    """
    scheduler=bgsc()
    scheduler.add_job(func,"interval",args=args,kwargs=kwargs,seconds=interval)
    scheduler.start()

def setTimeTask(func:callable,runtime:int,*args,**kwargs):
    """
    定时触发任务
    :param func: 要触发的任务（函数）
    :param runtime: 触发时间timestamps
    :param args: 任务参数
    """
    scheduler=bgsc()
    scheduler.add_job(func,"date",args=args,kwargs=kwargs,run_date=datetime.fromtimestamp(float(runtime)))
    scheduler.start()
    
@handler("time")
def returnTime(m,q):
    """
    返回当前时间
    """
    return '当前时间为:%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@handler("注册")
def signup(message_list,qid):
    """
    用户注册
    :param message_list: 注册 学号
    :param qid: 注册者的qq号
    :return: 注册提示信息
    """
    assert len(message_list)==2 and re.match(r'\d{5}',message_list[1]) and len(message_list[1])==5,'注册失败:请注意您的输入格式！'
    schoolID:str=message_list[1]
    assert not User.find(qid,mysql) and not User.findAll(mysql,'schoolID=?',(schoolID,)),'注册失败:您已经注册过，无法重复注册！'
    user=User(
        qid=qid,schoolID=schoolID,money=0,mineral='{}',
        process_tech=0.0,extract_tech=0.0,refine_tech=0.0,digable=1,
        factory_num=0,effis='[0.0,0.0,0.0,0.0,0.0,0.0]',mines='[]'
    )#注册新用户
    user.save(mysql)
    ans="注册成功！"
    return ans

@handler("开采")
def getMineral(message_list,qid):
    """
    根据传入的信息开采矿井
    :param message_list: 开采 矿井编号
    :param qid: 开采者的qq号
    :return: 开采提示信息
    """
    assert len(message_list)==2,'开采失败:请指定要开采的矿井！'
    mineralID:int=int(message_list[1])
    if mineralID==1:
        mineralID=np.random.randint(2,30000)
        ans=extract(qid,mineralID,1)
    elif mineralID==2:
        mineralID=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(30000)*1000))/1000))
        ans=extract(qid,mineralID,2)
    elif mineralID==3:
        mineralID=np.random.randint(2,999)
        ans=extract(qid,mineralID,3)
    elif mineralID==4:
        mineralID=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(999)*1000))/1000))
        ans=extract(qid,mineralID,4)
    else:
        ans='开采失败:不存在此矿井！'
    return ans

@handler("兑换")
def exchange(message_list,qid):
    """
    兑换矿石
    :param message_list: 兑换 矿石编号
    :param qid: 兑换者的qq号
    :return: 兑换提示信息
    """
    assert len(message_list)==2,'兑换失败:请指定要兑换的矿石！'
    mineralID:int=int(message_list[1])
    user:User=User.find(qid,mysql)
    schoolID:str=user.schoolID
    money:int=user.money
    mineralDict:dict=dict(eval(user.mineral))
    assert mineralID in mineralDict,'兑换失败:您不具备此矿石！'
    assert not int(schoolID)%mineralID\
        or not int(schoolID[:3])%mineralID\
        or not int(schoolID[2:])%mineralID\
        or not int(schoolID[:2]+'0'+schoolID[2:])%mineralID,'兑换失败:您不能够兑换此矿石！'

    mineralDict[mineralID]-=1
    if mineralDict[mineralID]<=0:
        mineralDict.pop(mineralID)

    user.mineral=str(mineralDict)
    user.money+=mineralID
    user.update(mysql)

    ans='兑换成功！'
    return ans

effisStr=['分解效率','合成效率','复制效率','修饰效率','炼油效率','建工效率']

info_msg="查询到QQ号为：%s的用户信息\n"\
         "学号：%s\n"\
         "当前余额：%s\n"\
         "加工科技点：%s\n"\
         "开采科技点：%s\n"\
         "炼油科技点：%s\n"\
         "当前是否可开采：%s\n"\
         "以下为该用户拥有的矿石：\n%s"\
         "工厂数: %s\n"\
         "以下为该玩家各工种生产效率：\n%s"\
         "以下为该玩家拥有的私人矿井编号：\n%s"\

@handler("查询")
def getUserInfo(message_list,qid):
    """
    查询用户个人信息
    :param message_list: 查询
    :param qid: 查询者的qq号
    :return: 查询提示信息
    """
    user:User=User.find(qid,mysql)
    schoolID=user.schoolID
    money=user.money
    mineral=user.mineral
    processTech=user.process_tech
    extractTech=user.extract_tech
    refineTech=user.refine_tech
    digable=user.digable
    mres=""
    mineralDict:dict=dict(eval(mineral))
    factory_num=user.factory_num
    effisList:list=list(eval(user.effis))
    mineList:list=list(eval(user.mines))
    sortedMineralDict={key:mineralDict[key] for key in sorted(mineralDict.keys())}

    for mid,mnum in sortedMineralDict.items():
        if mid=='0':
            mres+="燃油%s个单位；\n" % mnum
        else:
            mres+="编号%s的矿石%s个；\n"%(mid,mnum)

    eres=''    #生产效率信息
    for index in range(6):
        eres+=effisStr[index]+":%s\n" % effisList[index]

    mineres='' #私有矿井信息
    for mine in mineList:
        mineres+='%s,' % mine

    ans=info_msg%(qid,schoolID,money,processTech,extractTech,refineTech,digable,
                  mres,factory_num,eres,mineres)
    return ans

@handler("预售")
def presell(message_list,qid):
    """
    在市场上预售矿石
    :param message_list: 预售 矿石编号 矿石数量 价格 起始时间 终止时间
    :param qid: 预售者的qq号
    :return: 预售提示信息
    """
    assert len(message_list)==6,'预售失败:请按照规定格式进行预售！'
    nowtime=datetime.timestamp(datetime.now())
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        price:int=int(message_list[3])
        if message_list[4]=='现在' or message_list[4]=='now':
            starttime:int=round(nowtime)
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if message_list[5] in delay:
            endtime:int=starttime+delay[message_list[5]]
        else:
            endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except Exception as err:
        raise AssertionError('预售失败:请按照规定格式进行预售！')

    user:User=User.find(qid,mysql)
    mineralDict:dict=dict(eval(user.mineral))
    assert mineralNum>=1,'预售失败:您必须至少预售1个矿石！'
    assert mineralID in mineralDict,'预售失败:您不具备此矿石！'
    assert mineralDict[mineralID]>=mineralNum,'预售失败:您的矿石数量不足！'
    assert price>0,'预售失败:预售价格必须为正数！'
    assert endtime>nowtime,'预售失败:已经超过截止期限！'
    starttime=max(round(nowtime),starttime)

    mineralDict[mineralID]-=mineralNum
    if mineralDict[mineralID]<=0:mineralDict.pop(mineralID)

    user.mineral=str(mineralDict)
    user.update(mysql)

    md5=hashlib.md5()
    md5.update(('%.2f'%nowtime).encode('utf-8'))
    tradeID=md5.hexdigest()[:6]

    sale:Sale=Sale(tradeID=tradeID,qid=qid,mineralID=mineralID,mineralNum=mineralNum,price=price,starttime=starttime,endtime=endtime)
    sale.save(mysql)
    setTimeTask(updateSale,endtime,sale)
    ans='预售成功！编号:%s'%tradeID
    return ans

@handler("购买")
def buy(message_list,qid):
    """
    在市场上购买矿石
    :param message_list: 购买 预售编号
    :param qid: 购买者的qq号
    :return: 购买提示信息
    """
    assert len(message_list)==2,'购买失败:请按照规定格式进行购买！'
    tradeID:str=message_list[1]
    sale:Sale=Sale.find(tradeID,mysql)
    assert sale,'购买失败:不存在此卖品！'
    user:User=User.find(qid,mysql)

    tqid=sale.qid
    mineralID=sale.mineralID
    mineralNum=sale.mineralNum
    price=sale.price
    starttime=sale.starttime
    endtime=sale.endtime

    nowtime=datetime.timestamp(datetime.now())#现在的时间
    assert qid!=tqid,'购买失败:您不能购买自己的商品！'
    assert nowtime>=starttime,'购买失败:尚未到开始购买时间！'
    assert nowtime<=endtime,'购买失败:此商品预售已结束！'
    assert user.money>=price,'购买失败:您的余额不足！'

    user.money-=price#付钱
    tuser:User=User.find(tqid,mysql)
    tuser.money+=price#得钱

    mineralDict:dict=dict(eval(user.mineral))
    if mineralID not in mineralDict:
        mineralDict[mineralID]=0
    mineralDict[mineralID]+=mineralNum#增加矿石
    user.mineral=str(mineralDict)

    sale.remove(mysql)#删除市场上的此条记录
    user.update(mysql)
    tuser.update(mysql)

    ans='购买成功！'
    send(tqid,'您预售的商品(编号:%s)已被卖出！'%tradeID,False)
    return ans

@handler('预订')
def prebuy(message_list,qid):
    """
    在市场上预订矿石
    :param message_list: 预订 矿石编号 矿石数量 价格 起始时间 终止时间
    :param qid: 预订者的qq号
    :return: 预订提示信息
    """
    assert len(message_list)==6,'预订失败:请按照规定格式进行预订！'
    nowtime=datetime.timestamp(datetime.now())
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        price:int=int(message_list[3])
        if message_list[4]=='现在' or message_list[4]=='now':
            starttime:int=round(nowtime)
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if message_list[5] in delay:
            endtime:int=starttime+delay[message_list[5]]
        else:
            endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except Exception as err:
        raise AssertionError('预订失败:请按照规定格式进行预订！')
    user:User=User.find(qid,mysql)

    assert user.money>=price,'预订失败:您的余额不足！'
    assert price>0,'预订失败:预订价格必须为正数！'
    assert endtime>nowtime,'预订失败:已经超过截止期限！'
    starttime=max(round(nowtime),starttime)
    user.money-=price

    md5=hashlib.md5()
    md5.update(('%.2f'%nowtime).encode('utf-8'))
    tradeID=md5.hexdigest()[:6]
    purchase:Purchase=Purchase(tradeID=tradeID,qid=qid,mineralID=mineralID,mineralNum=mineralNum,price=price,starttime=starttime,endtime=endtime)
    purchase.save(mysql)
    setTimeTask(updatePurchase,endtime,purchase)
    user.update(mysql)

    ans='预订成功！编号:%s'%tradeID
    return ans

@handler('售卖')
def sell(message_list,qid):
    """
    在市场上售卖矿石
    :param message_list: 售卖 预订编号
    :param qid: 售卖者的qq号
    :return: 售卖提示信息
    """
    assert len(message_list)==2,'售卖失败:请按照规定进行售卖！'
    tradeID:str=message_list[1]
    purchase:Purchase=Purchase.find(tradeID,mysql)
    assert purchase,'购买失败:不存在此卖品！'
    user:User=User.find(qid,mysql)

    tqid=purchase.qid
    mineralID=purchase.mineralID
    mineralNum=purchase.mineralNum
    price=purchase.price
    starttime=purchase.starttime
    endtime=purchase.endtime

    nowtime=datetime.timestamp(datetime.now())  #现在的时间
    assert qid!=tqid,'售卖失败:您不能向自己售卖商品！'
    assert nowtime>=starttime,'售卖失败:尚未到开始售卖时间！'
    assert nowtime<=endtime,'售卖失败:此商品预订已结束！'

    mineralDict:dict=dict(eval(user.mineral))
    assert mineralID in mineralDict,'售卖失败:您不具备此矿石！'
    assert mineralDict[mineralID]>=mineralNum,'售卖失败:您的矿石数量不足！'
    mineralDict[mineralID]-=mineralNum
    if mineralDict[mineralID]<=0:mineralDict.pop(mineralID)

    user.money+=price  #得钱
    user.mineral=str(mineralDict)
    user.update(mysql)

    tuser:User=User.find(tqid,mysql)

    tmineralDict:dict=dict(eval(tuser.mineral))
    if mineralID not in tmineralDict:
        tmineralDict[mineralID]=0
    tmineralDict[mineralID]+=mineralNum  #增加矿石
    tuser.mineral=str(tmineralDict)

    purchase.remove(mysql)#删除市场上的此条记录

    tuser.update(mysql)

    ans='售卖成功！'
    send(tqid,'您预订的商品(编号:%s)已被买入！'%tradeID,False)
    return ans

@handler("拍卖")
def preauction(message_list,qid):
    """
    在市场上拍卖矿石
    :param message_list: 拍卖 矿石编号 矿石数量 底价 起始时间 终止时间 是否保密
    :param qid: 拍卖者的qq号
    :return: 拍卖提示信息
    """
    assert len(message_list)==7,'拍卖失败:请按照规定格式进行拍卖！'
    nowtime=datetime.timestamp(datetime.now())
    try:
        mineralID:int=int(message_list[1])
        mineralNum:int=int(message_list[2])
        price:int=int(message_list[3])
        secret:bool=bool(int(message_list[6]))
        if message_list[4]=='现在' or message_list[4]=='now':
            starttime:int=round(nowtime)
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if message_list[5] in delay:
            endtime:int=starttime+delay[message_list[5]]
        else:
            endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except Exception as err:
        raise AssertionError('拍卖失败:请按照规定格式进行拍卖！')

    user:User=User.find(qid,mysql)
    mineralDict:dict=dict(eval(user.mineral))
    assert mineralNum>=1,'拍卖失败:您必须至少拍卖1个矿石！'
    assert mineralID in mineralDict,'拍卖失败:您不具备此矿石！'
    assert mineralDict[mineralID]>=mineralNum,'拍卖失败:您的矿石数量不足！'
    assert price>0,'拍卖失败:底价必须为正数！'
    assert endtime>nowtime,'拍卖失败:已经超过截止期限！'
    starttime=max(round(nowtime),starttime)

    mineralDict[mineralID]-=mineralNum
    if mineralDict[mineralID]<=0:mineralDict.pop(mineralID)

    user.mineral=str(mineralDict)
    user.update(mysql)

    md5=hashlib.md5()
    md5.update(('%.2f'%nowtime).encode('utf-8'))
    tradeID=md5.hexdigest()[:6]

    auction:Auction=Auction(tradeID=tradeID,qid=qid,mineralID=mineralID,mineralNum=mineralNum,price=price,
                            starttime=starttime,endtime=endtime,secret=secret,bestprice=0,offers='[]')
    auction.save(mysql)
    ans='拍卖成功！编号:%s'%tradeID
    return ans

@handler("投标")
def bid(message_list,qid):
    """
    在市场上对矿石进行投标
    :param message_list: 投标 拍卖编号 价格
    :param qid: 投标者的qq号
    :return: 投标提示信息
    """
    assert len(message_list)==3,'投标失败:请按照规定格式进行投标！'
    nowtime=datetime.timestamp(datetime.now())
    try:
        tradeID:str=message_list[1]
        userprice:int=int(message_list[2])
    except Exception as err:
        raise AssertionError('投标失败:请按照规定格式进行投标！')
    auction:Auction=Auction.find(tradeID,mysql)
    assert auction,'投标失败:不存在此卖品！'
    user:User=User.find(qid,mysql)

    tqid:str=auction.qid
    mineralID:int=auction.mineralID
    mineralNum:int=auction.mineralNum
    price:int=auction.price
    starttime:int=auction.starttime
    endtime:int=auction.endtime
    secret:bool=auction.secret#是否对出价保密

    nowtime=round(datetime.timestamp(datetime.now()))#现在的时间
    assert qid!=tqid,'投标失败:您不能购买自己的商品！'
    assert nowtime>=starttime,'投标失败:尚未到开始拍卖时间！'
    assert nowtime<=endtime,'投标失败:此商品拍卖已结束！'
    assert userprice>0,'投标失败:您的出价必须为正数！'
    assert userprice>=price,'投标失败:您的出价低于底价！'
    assert user.money>=round(userprice*deposit),'投标失败:您的余额不足以支付押金！'

    if secret:#对出价保密
        user.money-=round(userprice*deposit)#支付押金
    else:#不对出价保密
        bestprice=auction.bestprice#当前最高价
        assert userprice>bestprice,'投标失败:您的出价低于当前最高价！'
        user.money-=round(userprice*deposit)#支付押金

    offersList:list[tuple[str,str,int]]=list(eval(auction.offers))
    offersList.append((qid,userprice,nowtime))
    auction.bestprice=max(userprice,auction.bestprice)
    auction.offers=str(offersList)

    auction.update(mysql)
    user.update(mysql)
    ans='投标成功！'
    return ans

@handler("市场")
def market(message_list,qid):
    """
    查看市场
    :param message_list: 市场
    :param qid:
    :return: 提示信息
    """
    sales:list[Sale]=Sale.findAll(mysql)
    purchases:list[Purchase]=Purchase.findAll(mysql)
    auctions:list[Auction]=Auction.findAll(mysql)
    ans='欢迎来到矿石市场！\n'
    if sales:
        ans+='以下是所有处于预售中的商品:\n'
        saleData=[['交易编号','矿石编号','矿石数目','价格','起始时间','结束时间']]
        for sale in sales:
            starttime=datetime.fromtimestamp(float(sale.starttime)).strftime('%Y-%m-%d %H:%M:%S')
            endtime=datetime.fromtimestamp(float(sale.endtime)).strftime('%Y-%m-%d %H:%M:%S')
            saleData.append([sale.tradeID,sale.mineralID,sale.mineralNum,sale.price,starttime,endtime])
            drawtable(saleData,'sale.png')
        ans+='[CQ:image,file=sale.png]'
    else:
        ans+='目前没有处于预售中的商品！\n'
    if purchases:
        ans+='以下是所有处于预订中的商品:\n'
        purchaseData=[['交易编号','矿石编号','矿石数目','价格','起始时间','结束时间']]
        for purchase in purchases:
            starttime=datetime.fromtimestamp(float(purchase.starttime)).strftime('%Y-%m-%d %H:%M:%S')
            endtime=datetime.fromtimestamp(float(purchase.endtime)).strftime('%Y-%m-%d %H:%M:%S')
            purchaseData.append([purchase.tradeID,purchase.mineralID,purchase.mineralNum,purchase.price,starttime,endtime])
            drawtable(purchaseData,'purchase.png')
        ans+='[CQ:image,file=purchase.png]'
    else:
        ans+='目前没有处于预订中的商品！\n'
    if auctions:
        ans+='以下是所有处于拍卖中的商品:\n'
        auctionData=[['交易编号','矿石编号','矿石数目','底价','起始时间','结束时间','当前最高价']]
        for auction in auctions:
            starttime=datetime.fromtimestamp(float(auction.starttime)).strftime('%Y-%m-%d %H:%M:%S')
            endtime=datetime.fromtimestamp(float(auction.endtime)).strftime('%Y-%m-%d %H:%M:%S')
            auctionDatum=[auction.tradeID,auction.mineralID,auction.mineralNum,auction.price,starttime,endtime]
            if auction.secret:
                auctionDatum.append('-')
            else:
                auctionDatum.append(auction.bestprice)
            auctionData.append(auctionDatum)
            drawtable(auctionData,'auction.png')
        ans+='[CQ:image,file=auction.png]'
    else:
        ans+='目前没有处于拍卖中的商品！\n'
    return ans

@handler("支付")
def pay(message_list,qid):
    """
    :param message_list: 支付 q`QQ号`/`学号` $`金额`
    :param qid: 支付者的qq号
    :return: 支付提示信息
    """
    assert len(message_list)==3,'支付失败:您的支付格式不正确！'
    target=str(message_list[1])
    assert message_list[2].startswith("$"),'支付失败:您的金额格式不正确！'
    try:
        money=int(str(message_list[2])[1:])
    except Exception:
        raise AssertionError("支付失败:您的金额格式不正确！应当为:$`金额`")

    user:User=User.find(qid)

    assert user.money>=money,"支付失败:您的余额不足！"
    if target.startswith("q"):
        # 通过QQ号查找对方
        tqid:str=target[1:]
        tuser:User=User.find(tqid)
        assert tuser,"支付失败:QQ号为%s的用户未注册！"%tqid
    else:
        tschoolID:str=target
        # 通过学号查找
        assert User.findAll(mysql,'schoolID=?',(tschoolID,)),"支付失败:学号为%s的用户未注册！"%tschoolID
        tuser:User=User.findAll(mysql,'schoolID=?',(tschoolID,))[0]

    user.money-=money
    tuser.money+=round(money*(1-player_tax))

    user.update(mysql)
    tuser.update(mysql)

    return "支付成功！"

@handler("帮助")
def getHelp(message_list,qid):
    return help_msg


def dealWithRequest(funcStr,message_list,qid):
    if funcStr in commands:
        ans=commands[funcStr](message_list,qid)
    else:
        ans="未知命令:请输入'帮助'以获取帮助信息！"
    return ans

def handle(res,group):
    ans:str=''  #回复给用户的内容
    if group:#是群发消息
        message:str=res.get("raw_message")
        qid:str=res.get('sender').get('user_id')  #发消息者的qq号
        gid:str=res.get('group_id')  #群的qq号
        if gid not in group_ids:
            return None
        if "[CQ:at,qq=2470751924]" not in message:#必须在自己被at的情况下才能作出回复
            return None

        message_list:list=message.split(' ')
        funcStr:str=message_list[1]
        message_list.pop(0)  #忽略at本身

        try:
            ans=dealWithRequest(funcStr,message_list,qid)
            send(gid,ans,group=True)
        except AssertionError as err:
            send(gid,err,group=True)

    else:
        message:str=res.get("raw_message")
        qid:str=res.get('sender').get('user_id')
        message_list:list=message.split(' ')
        funcStr:str=message_list[0]

        try:
            ans=dealWithRequest(funcStr,message_list,qid)
            send(qid,ans,group=False)
        except AssertionError as err:
            send(qid,err,group=False)

def send(qid,message,group=False):
    """
    用于发送消息的函数
    :param qid: 用户id 或 群id
    :param message: 发送的消息
    :param group: 是否为群消息
    :return:none
    """

    if not group:
        # 如果发送的为私聊消息
        params={
            "user_id":qid,
            "message":message,
        }
        _=requests.get("http://127.0.0.1:5700/send_private_msg",params=params)
    else:
        params={
            'group_id':qid,
            "message":message
        }
        _=requests.get("http://127.0.0.1:5700/send_group_msg",params=params)
