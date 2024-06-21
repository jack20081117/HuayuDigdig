import numpy as np

from staticFunctions import sigmoid,sqrtmoid,getnowtime,generateTimeStr,setTimeTask, mineralSample,exchangeable
from model import User,Mine,Statistics
from globalConfig import mysql,vatRate


def extractMineral(qid:str,mineralID:int,mine:Mine,useRobot:bool=False, robotID:int=0):
    """获取矿石
    :param qid:开采者的qq号
    :param mineralID:开采得矿石的编号
    :param mine:矿井
    :param useRobot:是否使用机器人
    :param robotID:机器人编号
    :return:开采信息
    """
    nowtime:int=getnowtime()
    abundance:float=mine.abundance #矿井丰度
    user:User=User.find(qid,mysql)
    mineral:dict[int,int]=user.mineral # 用户拥有的矿石
    extractTech:float=user.tech['extract'] # 开采科技

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

    if useRobot:
        fuelUsage = 10 * np.log(mineralID) / sqrtmoid(extractTech)
        assert 0 in user.mineral, "您没有燃油，无法使用采矿机器人！"
        assert user.mineral[0] >= fuelUsage, "本次机器开采预计需要消耗%.2f单位燃油，您的燃油不充足！" % fuelUsage
        user.mineral[0] -= fuelUsage

    if np.random.random()>prob:#开采失败
        forbidInterval = 90 * np.log(mineralID) / sqrtmoid(extractTech)
        ans='开采失败:您的运气不佳，未能开采成功！'
    else:
        forbidInterval = 60 * np.log(mineralID) / sqrtmoid(extractTech)

        mineral.setdefault(mineralID,0)#防止用户不具备此矿石报错
        mineral[mineralID]+=1 #加一个矿石
        mine.abundance=prob#若开采成功，则后一次的丰度是前一次的成功概率
        ans='开采成功！您获得了编号为%d的矿石！'%mineralID
        if np.random.random() <= sigmoid(extractTech)/3.5:
            percentage = np.random.random()/4+0.25
            oil = round(mineralID/np.log(mineralID) * percentage+1)
            ans+='此次开采连带发现%d单位天然燃油！' % oil
            Statistics(timestamp=nowtime,money=0,fuel=oil).add(mysql)
            mineral.setdefault(0, 0)
            mineral[0] += oil
        user.mineral = mineral
        mine.save(mysql)
    if mine.private:
        forbidInterval /= 1.2

    forbidtime = round(getnowtime() + forbidInterval)
    user.forbidtime[robotID]=forbidtime
    user.save(mysql)

    return ans

class ExtractService():
    def __init__(self):
        pass

    @staticmethod
    def getFuel(messageList:list[str],qid:str):
        """
        手动收集燃料
        :param messageList: 收集燃料
        :param qid: 开采者的qq号
        :return: 开采提示信息
        """
        user = User.find(qid, mysql)
        nowtime = getnowtime()
        assert nowtime >= user.forbidtime[0], '收集失败:您必须等到%s才能再次收集燃料！' % generateTimeStr(user.forbidtime[0])
        user.forbidtime[0] = nowtime + 180
        user.mineral.setdefault(0, 0)
        collected = np.random.randint(4,16)
        user.mineral[0] += collected
        user.save(mysql)
        return "您收集到了%d单位燃料！" % collected
        
    @staticmethod
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
        nowtime = getnowtime()
        user = User.find(qid, mysql)
        assert nowtime >= user.forbidtime[0], '开采失败:您必须等到%s才能再次手动开采矿井！' % generateTimeStr(user.forbidtime[0])
        mineralID = mineralSample(mine.lower,mine.upper,logUniform=mine.logUniform)
        ans = extractMineral(qid,mineralID,mine)
        return ans

    @staticmethod
    def getMineralAuto(messageList:list[str],qid:str):
        """
        根据传入的信息使用采矿机器人开采矿井
        :param messageList: 机器开采 矿井编号
        :param qid: 开采者的qq号
        :return: 开采提示信息
        """
        assert len(messageList)==2,'开采失败:请指定要开采的矿井！'
        mineID:int=int(messageList[1])
        mine: Mine = Mine.find(mineID, mysql)
        assert mine, '开采失败:不存在此矿井！'
        assert mine.open or qid==mine.owner, '该矿井目前并未开放！'
        nowtime = getnowtime()
        user = User.find(qid, mysql)
        assert user.robotNum > 0,'您没有采矿机器人！'
        vacancy:bool = False
        vacantID:int = 0
        busymessage = ''
        for i in range(1,len(user.forbidtime)):
            if nowtime >= user.forbidtime[i]:
                vacancy = True
                vacantID = i
                break
            else:
                busymessage += '机器人%d需要等到%s才能再次开采！\n' % (i, generateTimeStr(user.forbidtime[i]))
        assert vacancy, "您没有当前空闲的采矿机器人！\n" + busymessage
        mineralID = mineralSample(mine.lower,mine.upper,logUniform=mine.logUniform)
        ans = extractMineral(qid,mineralID,mine,useRobot=True,robotID=vacantID)
        return ans

    @staticmethod
    def exchangeMineral(messageList:list[str],qid:str):
        """
        兑换矿石
        :param messageList: 兑换 矿石编号
        :param qid: 兑换者的qq号
        :return: 兑换提示信息
        """
        assert len(messageList)==2,'兑换失败:请指定要兑换的矿石！'
        nowtime:int=getnowtime()
        try:
            mineralID:int=int(messageList[1])
        except ValueError:
            return '兑换失败:您的兑换格式不正确！'
        user:User=User.find(qid,mysql)
        schoolID:str=user.schoolID
        mineral=user.mineral
        assert mineralID in mineral,'兑换失败:您不具备此矿石！'
        assert exchangeable(schoolID,mineralID),'兑换失败:您不能够兑换此矿石！'

        mineral[mineralID]-=1
        if mineral[mineralID]<=0:
            mineral.pop(mineralID)

        user.mineral=mineral
        user.money+=mineralID
        user.outputTax += mineralID * vatRate #增值税
        user.save(mysql)

        Statistics(timestamp=nowtime,money=mineralID,fuel=0).add(mysql)

        ans='兑换成功！'
        return ans

    @staticmethod
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

    @staticmethod
    def transferMine(messageList:list[str],qid:str):
        """
        :param messageList: 转让矿井 矿井编号 转让对象(学号/q+QQ号）
        :param qid: 转让者的qq号
        :return: 转让提示信息
        """
        assert len(messageList) == 3, '转让矿井失败:您的转让格式不正确！'
        try:
            transferID:int=int(messageList[1])
            newOwnerID:str=str(messageList[2])
        except ValueError:
            return '转让工厂失败:您的输入格式不正确！'

        user=User.find(qid,mysql)

        mine=Mine.find(transferID,mysql)
        assert mine is not None,"转让矿井失败:不存在此矿井！"
        assert mine.owner==qid,'转让矿井失败:您不是此矿井的主人！'

        if newOwnerID.startswith("q"):
            # 通过QQ号查找对方
            tqid: str = newOwnerID[1:]
            newOwner: User = User.find(tqid, mysql)
            assert newOwner, "转让矿井失败:QQ号为%s的用户未注册！" % tqid
        else:
            tschoolID: str = newOwnerID
            # 通过学号查找
            assert User.findAll(mysql, 'schoolID=?', (tschoolID,)), "转让矿井失败:学号为%s的用户未注册！" % tschoolID
            newOwner: User = User.findAll(mysql, 'schoolID=?', (tschoolID,))[0]

        if newOwner.qid == 'treasury':
            mine.private = False

        mine.owner = newOwner.qid
        user.mines.pop(user.mines.index(transferID))
        newOwner.mines.append(transferID)
        user.save(mysql)
        newOwner.save(mysql)
        ans = '转让矿井成功！矿井编号%s已成功转让给%s' % (transferID, newOwnerID)

        return ans

