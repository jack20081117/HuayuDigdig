from staticFunctions import setTimeTask,drawtable,send,generateTime,getnowtime,generateTimeStr,generateTimeStamp
from model import User,Debt
from globalConfig import mysql
from update import updateDebt

class DebtService(object):
    def __init__(self):
        pass

    @staticmethod
    def prelendDebt(messageList:list[str],qid:str):
        """
        :param messageList: 放贷 金额 放贷时间 利率 起始时间 终止时间
        :param qid: 放贷者的qq号
        :return: 放贷提示信息
        """
        assert len(messageList)==6,'放贷失败:您的放贷格式不正确！'
        nowtime:int=getnowtime()#现在的时间
        try:
            money=int(messageList[1])
            duration=generateTime(messageList[2])
            interest=float(messageList[3])
            if messageList[4]=='现在' or messageList[4]=='now':
                starttime:int=nowtime
            else:
                starttime:int=generateTimeStamp(messageList[4])
            if generateTime(messageList[5]):
                endtime:int=starttime+generateTime(messageList[5])
            else:
                endtime:int=generateTimeStamp(messageList[5])
        except ValueError:
            return "放贷失败:您的放贷格式不正确！"

        creditor=User.find(qid,mysql)
        assert creditor.money>money,"放贷失败:您的余额不足！"
        assert endtime>nowtime,'放贷失败:已经超过截止期限！'
        starttime=max(nowtime,starttime)
        creditor.money-=money
        creditor.save(mysql)

        debtID:int=max([0]+[debt.debtID for debt in Debt.findAll(mysql)])+1
        debt=Debt(debtID=debtID,creditor=qid,debitor='nobody',money=money,
                duration=duration,starttime=starttime,endtime=endtime,interest=float(interest))
        debt.add(mysql)
        setTimeTask(updateDebt,endtime,debt)

        ans='放贷成功！'
        return ans

    @staticmethod
    def borrowDebt(messageList:list[str],qid:str):
        """
        :param messageList: 借贷 债券编号 金额
        :param qid: 借贷者的qq号
        :return: 借贷提示信息
        """
        assert len(messageList)==3,"借贷失败:您的借贷格式不正确！"
        nowtime:int=getnowtime()#现在的时间
        try:
            debtID:int=int(messageList[1])
            money:int=int(messageList[2])
        except ValueError:
            return "借贷失败:您的借贷格式不正确！"
        debt=Debt.find(debtID,mysql)
        assert debt is not None,"借贷失败:不存在此债券！"
        assert debt.debitor=='nobody',"借贷失败:此债券已被贷款！"
        assert debt.creditor!=qid,'借贷失败:您不能向自己贷款！'
        assert money>0,"借贷失败:借贷金额必须为正！"
        assert debt.money>=money,"借贷失败:贷款金额过大！"
        assert debt.starttime<nowtime,"借贷失败:此债券尚未开始放贷！"
        assert debt.endtime>nowtime,"借贷失败:此债券已结束放贷！"

        debt.money-=money
        debt.save(mysql)
        creditorID=debt.creditor
        duration=debt.duration
        interest=debt.interest
        if debt.money<=0:
            debt.remove(mysql)

        newdebtID:int=max([0]+[debt.debtID for debt in Debt.findAll(mysql)])+1
        newdebt=Debt(debtID=newdebtID,creditor=creditorID,debitor=qid,money=money,
                    duration=duration,starttime=nowtime,endtime=nowtime+duration,interest=interest)
        newdebt.add(mysql)
        setTimeTask(updateDebt,nowtime+duration,newdebt)

        debitor=User.find(qid,mysql)
        debitor.money+=money
        debitor.save(mysql)

        ans='借贷成功！该债务编号为%s，请注意在借贷时限内还款！' % newdebtID
        return ans

    @staticmethod
    def repayDebt(messageList:list[str],qid:str):
        """
        :param messageList: 还款 债券编号 金额
        :param qid: 还款者的qq号
        :return: 还款提示信息
        """
        assert len(messageList)==3,'还款失败:您的还款格式不正确！'
        nowtime:int=getnowtime()#现在的时间
        try:
            debtID:int=int(messageList[1])
            money:int=int(messageList[2])
        except ValueError:
            return '还款失败:您的还款格式不正确！'
        debt=Debt.find(debtID,mysql)
        debitor=User.find(qid,mysql)
        assert debt is not None,"还款失败:不存在此债券！"
        assert debt.debitor==qid,'还款失败:您不是此债券的债务人！'
        assert money>0,'还款失败:还款金额必须为正！'
        assert debitor.money>money,'还款失败:您的余额不足！'
        assert debt.endtime>nowtime,'还款失败:此债券已结束还款！'

        if money>=debt.money:
            debitor.money-=(money-debt.money)#返还多余的还款
            debitor.save(mysql)
            debt.remove(mysql)
            ans='还款成功！您已还清此贷款！'
            send(debt.creditor,'您的债券:%s已还款完毕，贷款已送到您的账户'%debtID,False)
        else:
            debt.money-=money
            debitor.money-=money
            debt.save(mysql)
            debitor.save(mysql)
            ans='还款成功！剩余贷款金额:%d'%debt.money
        return ans

    @staticmethod
    def transferDebt(messageList:list[str],qid:str):
        """
        :param messageList: 转让债务 债券编号 转让对象(学号/q+QQ号）
        :param qid: 还款者的qq号
        :return: 还款提示信息
        """
        assert len(messageList) == 3, '转让债权失败:您的转让格式不正确！'
        nowtime=getnowtime()
        try:
            debtID:int=int(messageList[1])
            newCreditorID:str=str(messageList[2])
        except ValueError:
            return '转让债权失败:您的债券编号不正确！'

        debt=Debt.find(debtID,mysql)
        assert debt is not None,"转让债权失败:不存在此债券！"
        assert debt.creditor==qid,'转让债权失败:您不是此债券的债权人！'
        assert debt.endtime > nowtime, '转让债权失败:此债券已结束还款！'

        if newCreditorID.startswith("q"):
            # 通过QQ号查找对方
            tqid: str = newCreditorID[1:]
            newCreditor: User = User.find(tqid, mysql)
            assert newCreditor, "转让债权失败:QQ号为%s的用户未注册！" % tqid
        else:
            tschoolID: str = newCreditorID
            # 通过学号查找
            assert User.findAll(mysql, 'schoolID=?', (tschoolID,)), "转让债权失败:学号为%s的用户未注册！" % tschoolID
            newCreditor: User = User.findAll(mysql, 'schoolID=?', (tschoolID,))[0]

        assert newCreditor.qid != debt.debitor, "转让债权失败:不能转让给债务人！"

        debt.creditor = newCreditor.qid
        debt.save(mysql)
        ans = '转让债权成功！编号%s的债券已成功转让给%s，该债券还有%.2f待偿还！' % (debt.debtID, newCreditorID, debt.money)

        return ans

    @staticmethod
    def forgiveDebt(messageList:list[str],qid:str):
        """
        :param messageList: 免除 债券编号
        :param qid:
        :return: 提示信息
        """
        assert len(messageList) == 2, '免除债务失败:您的转让格式不正确！'
        nowtime=getnowtime()
        try:
            debtID:int=int(messageList[1])
        except ValueError:
            return '免除债务失败:您的债券编号不正确！'

        debt = Debt.find(debtID, mysql)
        assert debt is not None,"免除债务失败:不存在此债券！"
        assert debt.creditor==qid,'免除债务失败:您不是此债券的债权人！'
        assert debt.endtime > nowtime, '免除债务失败:此债券已结束还款！'


        ans="免除债务成功！债券编号%s已被销毁，债务人%s现在无需偿还剩余的%.2f元！" % (debtID, debt.debitor, debt.money)
        send(debt.debitor,"债权人%s已经免除了您编号%s的债务，您现在无需偿还剩下的%.2f元！" % (debt.creditor, debtID, debt.money))
        debt.remove(mysql)

        return ans

    @staticmethod
    def debtMarket(messageList:list[str],qid:str):
        """
        :param messageList: 债市
        :param qid:
        :return: 提示信息
        """
        debts:list[Debt]=Debt.findAll(mysql,where='debitor=?',args=('nobody',))
        ans='欢迎来到债市！\n'
        if debts:
            ans+='以下是所有目前可借的贷款:\n'
            debtData=[['债券编号','金额','债权人','借出时间','利率','时化利率','起始时间','终止时间']]
            for debt in debts:
                debttime:str=''
                if debt.duration//86400:
                    debttime+='%d天'%(debt.duration//86400)
                if (debt.duration%86400)//3600:
                    debttime+='%d小时'%((debt.duration%86400)//3600)
                if (debt.duration%3600)//60:
                    debttime+='%d分钟'%((debt.duration%3600)//60)
                starttime:str=generateTimeStr(debt.starttime)
                endtime:str=generateTimeStr(debt.endtime)
                hourly_interest = ('%.2f' % (100*debt.interest/((debt.endtime - debt.starttime)/3600))) + "%"
                debtData.append([debt.debtID,debt.money,debt.creditor,debttime,debt.interest,hourly_interest,starttime,endtime])
            drawtable(debtData,'debt.png')
            ans+='[CQ:image,file=debt.png]'
        else:
            ans+='目前没有可借的贷款！'
        return ans

