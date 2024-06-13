import imgkit, markdown
from datetime import datetime
from matplotlib import pyplot as plt

from model import Statistics
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
            moneyData[-1][-1]+=stat.money
            fuelData[-1][-1]+=stat.fuel
    ans+='以下是所有兑换矿石数据：\n'
    xs,ys=[],[]
    for datum in moneyData:
        xs.append(datetime.fromtimestamp(datum[0]).date())
        ys.append(datum[1])
    plt.figure(figsize=(10,5))
    plt.plot_date(xs,ys,linestyle='-',marker='.')
    plt.savefig('../go-cqhttp/data/images/moneyData.png')
    ans+='[CQ:image,file=moneyData.png]\n'

    ans+='以下是所有开采燃油数据：\n'
    xs,ys=[],[]
    for datum in fuelData:
        xs.append(datetime.fromtimestamp(datum[0]).date())
        ys.append(datum[1])
    plt.figure(figsize=(10,5))
    plt.plot_date(xs,ys,linestyle='-',marker='.')
    plt.savefig('../go-cqhttp/data/images/fuelData.png')
    ans+='[CQ:image,file=fuelData.png]\n'
    return ans