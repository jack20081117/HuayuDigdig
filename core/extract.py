import numpy as np

from tools import sigmoid
from model import User,Mine
from globalConfig import mysql,vatRate

def extractMineral(qid,mineralID,mineID):
    """获取矿石
    :param qid:开采者的qq号
    :param mineralID:开采得矿石的编号
    :param mineID:矿井编号
    :return:开采信息
    """
    mine:Mine=Mine.find(mineID,mysql)
    abundance:float=mine.abundance #矿井丰度
    user:User=User.find(qid,mysql)
    mineral:dict[int,int]=user.mineral # 用户拥有的矿石
    extractTech:float=user.tech['extract'] # 开采科技

    assert user.digable,'开采失败:您必须等到下一个整点才能再次开采矿井！'

    # 决定概率
    if abundance==0.0:#若矿井未被开采过，则首次成功率为100%
        prob=1.0
    else:
        prob=round(abundance*sigmoid(extractTech),2)

    if np.random.random()>prob:#开采失败
        user.digable=0#在下一次刷新前不可开采
        user.save(mysql)
        ans='开采失败:您的运气不佳，未能开采成功！'
    else:
        mineral.setdefault(mineralID,0)#防止用户不具备此矿石报错
        mineral[mineralID]+=1 #加一个矿石
        user.mineral=mineral
        user.save(mysql)
        mine.abundance=prob#若开采成功，则后一次的丰度是前一次的成功概率
        mine.save(mysql)
        ans='开采成功！您获得了编号为%d的矿石！'%mineralID
    return ans

def getMineral(messageList:list[str],qid:str):
    """
    根据传入的信息开采矿井
    :param messageList: 开采 矿井编号
    :param qid: 开采者的qq号
    :return: 开采提示信息
    """
    assert len(messageList)==2,'开采失败:请指定要开采的矿井！'
    mineralID:int=int(messageList[1])
    if mineralID==1:
        mineralID=np.random.randint(2,30000)
        ans=extractMineral(qid,mineralID,1)
    elif mineralID==2:
        mineralID=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(30000)*1000))/1000))
        ans=extractMineral(qid,mineralID,2)
    elif mineralID==3:
        mineralID=np.random.randint(2,999)
        ans=extractMineral(qid,mineralID,3)
    elif mineralID==4:
        mineralID=int(np.exp(np.random.randint(int(np.log(2)*1000),int(np.log(999)*1000))/1000))
        ans=extractMineral(qid,mineralID,4)
    else:
        ans='开采失败:不存在此矿井！'
    return ans

def exchangeMineral(messageList:list[str],qid:str):
    """
    兑换矿石
    :param messageList: 兑换 矿石编号
    :param qid: 兑换者的qq号
    :return: 兑换提示信息
    """
    assert len(messageList)==2,'兑换失败:请指定要兑换的矿石！'
    mineralID:int=int(messageList[1])
    user:User=User.find(qid,mysql)
    schoolID:str=user.schoolID
    money:int=user.money
    mineral=user.mineral
    assert mineralID in mineral,'兑换失败:您不具备此矿石！'
    assert not int(schoolID)%mineralID\
        or not int(schoolID[:3])%mineralID\
        or not int(schoolID[2:])%mineralID\
        or not int(schoolID[:2]+'0'+schoolID[2:])%mineralID,'兑换失败:您不能够兑换此矿石！'

    mineral[mineralID]-=1
    if mineral[mineralID]<=0:
        mineral.pop(mineralID)

    user.mineral=mineral
    user.money+=mineralID
    user.outputTax += mineralID * vatRate #增值税
    user.save(mysql)

    ans='兑换成功！'
    return ans