import numpy as np

from tools import sigmoid,sqrtmoid,getnowtime,generateTimeStr,setTimeTask, mineralSample
from update import updateDigable
from model import User,Mine
from globalConfig import mysql,vatRate

def extractMineral(qid:str,mineralID:int,mine:Mine):
    """获取矿石
    :param qid:开采者的qq号
    :param mineralID:开采得矿石的编号
    :param mine:矿井
    :return:开采信息
    """
    abundance:float=mine.abundance #矿井丰度
    user:User=User.find(qid,mysql)
    mineral:dict[int,int]=user.mineral # 用户拥有的矿石
    extractTech:float=user.tech['extract'] # 开采科技

    assert user.digable,'开采失败:您必须等到%s才能再次开采矿井！'%generateTimeStr(user.forbidtime)

    if mine.private and qid != mine.owner:
        owner = User.find(mine.owner, mysql)
        assert mine.fee <= user.money, '开采失败！您没有足够的钱支付该私有矿井的%s元入场费。' % mine.fee
        user.money -= mine.fee
        owner.money += mine.fee
        owner.save(mysql)

    # 决定概率
    if abundance==0.0:#若矿井未被开采过，则首次成功率为100%
        prob=1.0
    else:
        prob=round(abundance*sqrtmoid(extractTech),2)

    user.digable = 0  # 在下一次刷新前不可开采

    if np.random.random()>prob:#开采失败
        forbidInterval = 90 * np.log(mineralID) / sqrtmoid(extractTech)
        ans='开采失败:您的运气不佳，未能开采成功！'
    else:
        forbidInterval = 60 * np.log(mineralID) / sqrtmoid(extractTech)

        mineral.setdefault(mineralID,0)#防止用户不具备此矿石报错
        mineral[mineralID]+=1 #加一个矿石
        mine.abundance=prob#若开采成功，则后一次的丰度是前一次的成功概率
        ans='开采成功！您获得了编号为%d的矿石！'%mineralID
        if np.random.random()<= sigmoid(extractTech)/4:
            percentage = np.random.random()/5+0.2
            oil = round(mineralID/np.log(mineralID) * percentage+1)
            ans+='此次开采连带发现%d单位天然燃油！' % oil
            mineral.setdefault(0, 0)
            mineral[0] += oil
        user.mineral = mineral
        mine.save(mysql)
    if mine.private:
        forbidInterval /= 1.5

    forbidtime = round(getnowtime() + forbidInterval)
    user.forbidtime=forbidtime
    user.save(mysql)

    setTimeTask(updateDigable, user.forbidtime, user)
    return ans

def getMineral(messageList:list[str],qid:str):
    """
    根据传入的信息开采矿井
    :param messageList: 开采 矿井编号
    :param qid: 开采者的qq号
    :return: 开采提示信息
    """
    assert len(messageList)==2,'开采失败:请指定要开采的矿井！'
    mineID:int=int(messageList[1])
    mine: Mine = Mine.find(mineID, mysql)
    assert mine, '开采失败:不存在此矿井！'
    assert mine.open or qid==mine.owner, '该矿井目前并未开放！'
    mineralID = mineralSample(mine.lower,mine.upper,logUniform=mine.logUniform)
    ans = extractMineral(qid,mineralID,mine)
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

def openMine(messageList:list[str],qid:str):
    """
    根据传入的信息开放私有矿井
    :param messageList: 开放 矿井编号 收费
    :param qid: qq号
    :return: 提示信息
    """
    assert len(messageList) == 3, '开放失败:请按照格式输入！'
    try:
        mineID: int = int(messageList[1])
        fee: float = float(messageList[2])
    except ValueError:
        return '开放失败:请按照规定格式进行开放！'

    user = User.find(qid, mysql)
    assert mineID in user.mines, '您不拥有该矿井！'

    mine=Mine.find(mineID,mysql)

    mine.open = True
    mine.fee = fee

    mine.save(mysql)

    return '开放成功！'
