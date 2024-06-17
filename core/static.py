import imgkit, markdown
from datetime import datetime
from matplotlib import pyplot as plt
plt.rcParams['font.family']='Microsoft Yahei'

from model import Statistics,User,Stock,Debt
from globalConfig import imgkit_config,mysql
from tools import getnowdate

def returnTime(m,q):
    """
    返回当前时间
    """
    return '当前时间为:%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def getHelp(messageList:list[str],qid:str):
    with open('help_msg.md','r',encoding='utf-8') as help_msg:
        html=markdown.markdown(help_msg.read())
    imgkit.from_string(html,'../go-cqhttp/data/images/help.png',config=imgkit_config,css='./style.css')
    ans='[CQ:image,file=help.png]'
    return ans

def getStats(messageList:list[str],qid:str):
    ans='欢迎查看国家统计局！\n'
    moneyData=[]
    fuelData=[]
    nowdate=getnowdate()
    for i in range(6,-1,-1):
        date=nowdate-86400*i
        stats:list[Statistics]=Statistics.findAll(mysql,where='timestamp>=? and timestamp<=?',args=[date,date+86400])
        moneyData.append([date,0])
        fuelData.append([date,0])
        for stat in stats:
            moneyData.append([stat.timestamp,0])
            moneyData[-1][-1]+=stat.money+moneyData[-2][-1]
            fuelData.append([stat.timestamp,0])
            fuelData[-1][-1]+=stat.fuel+fuelData[-2][-1]
    ans+='以下是所有兑换矿石与开采燃油数据：\n'
    xs,ys=[],[]
    for datum in moneyData:
        xs.append(datetime.fromtimestamp(datum[0]-8*3600))
        ys.append(datum[1])
    plt.figure(figsize=(10,5))
    plt.plot(xs,ys,linestyle='-',marker='.',label='矿石')

    xs,ys=[],[]
    for datum in fuelData:
        xs.append(datetime.fromtimestamp(datum[0]-8*3600))
        ys.append(datum[1])
    plt.plot(xs,ys,linestyle='-',marker='.',label='燃油')

    plt.legend()
    plt.savefig('../go-cqhttp/data/images/statistics.png')
    ans+='[CQ:image,file=statistics.png]\n'

    return ans

def assetCalculation(user:User):
    assets = user.money
    for i in user.stocks.items():
        stock = Stock.find(i[0], mysql)
        assets += i[1] * stock.price
    for debt in Debt.findAll(mysql, 'creditor=?', (user.qid,)):
        assets += debt.money
    for debt in Debt.findAll(mysql, 'debitor=?', (user.qid,)):
        assets -= debt.money

    return assets

def showWealthiest(messageList: list[str], qid: str):
    """
    显示最富有的前10%
    :param messageList: 财富排行
    :param qid:
    :return: 提示信息
    """
    ans = ""
    allUserList = User.findAll(mysql)
    allUserList.sort(key=assetCalculation, reverse=True)
    showNum = round(0.1 * len(allUserList) + 1)
    for i in range(showNum):
        ans += "%s. %s拥有流动资产 %.2f 元\n" % (i+1, allUserList[i].qid, assetCalculation(allUserList[i]))

    return ans