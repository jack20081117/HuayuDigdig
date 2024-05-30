from datetime import datetime

from tools import setTimeTask,drawtable,send,generateTime
from model import User,Debt
from globalConfig import mysql
from update import updateDebt

def prelend(message_list:list[str],qid:str):
    """
    :param message_list: 放贷 金额 放贷时间 利率 起始时间 终止时间
    :param qid: 放贷者的qq号
    :return: 放贷提示信息
    """
    assert len(message_list)==6,'放贷失败:您的放贷格式不正确！'
    nowtime:int=round(datetime.timestamp(datetime.now()))
    try:
        money=int(message_list[1])
        duration=generateTime(message_list[2])
        interest=float(message_list[3])
        if message_list[4]=='现在' or message_list[4]=='now':
            starttime:int=nowtime
        else:
            starttime:int=int(datetime.strptime(message_list[4],'%Y-%m-%d,%H:%M:%S').timestamp())
        if generateTime(message_list[5]):
            endtime:int=starttime+generateTime(message_list[5])
        else:
            endtime:int=int(datetime.strptime(message_list[5],'%Y-%m-%d,%H:%M:%S').timestamp())
    except ValueError:
        return "放贷失败:您的放贷格式不正确！"

    creditor=User.find(qid,mysql)
    assert creditor.money>money,"放贷失败:您的余额不足！"
    assert endtime>nowtime,'放贷失败:已经超过截止期限！'
    starttime=max(nowtime,starttime)
    creditor.money-=money
    creditor.save(mysql)

    debtID:int=max([0]+[debt.debtID for debt in Debt.findAll(mysql)])+1
    debt=Debt(debtID=debtID,creditor_id=qid,debitor_id='nobody',money=money,
              duration=duration,starttime=starttime,endtime=endtime,interest=float(interest))
    debt.add(mysql)
    setTimeTask(updateDebt,endtime,debt)

    ans='放贷成功！'
    return ans

def borrow(message_list:list[str],qid:str):
    """
    :param message_list: 借贷 债券编号 金额
    :param qid: 借贷者的qq号
    :return: 借贷提示信息
    """
    assert len(message_list)==3,"借贷失败:您的借贷格式不正确！"
    nowtime:int=round(datetime.timestamp(datetime.now()))
    try:
        debtID:int=int(message_list[1])
        money:int=int(message_list[2])
    except ValueError:
        return "借贷失败:您的借贷格式不正确！"
    debt=Debt.find(debtID,mysql)
    assert debt is not None,"借贷失败:不存在此债券！"
    assert debt.debitor_id=='nobody',"借贷失败:此债券已被贷款！"
    assert debt.creditor_id!=qid,'借贷失败:您不能向自己贷款！'
    assert money>0,"借贷失败:借贷金额必须为正！"
    assert debt.money>=money,"借贷失败:贷款金额过大！"
    assert debt.starttime<nowtime,"借贷失败:此债券尚未开始放贷！"
    assert debt.endtime>nowtime,"借贷失败:此债券已结束放贷！"

    debt.money-=money
    debt.save(mysql)
    creditor_id=debt.creditor_id
    duration=debt.duration
    interest=debt.interest
    if debt.money<=0:
        debt.remove(mysql)

    newdebtID:int=max([0]+[debt.debtID for debt in Debt.findAll(mysql)])+1
    newdebt=Debt(debtID=newdebtID,creditor_id=creditor_id,debitor_id=qid,money=money,
                 duration=duration,starttime=nowtime,endtime=nowtime+duration,interest=interest)
    newdebt.add(mysql)
    setTimeTask(updateDebt,nowtime+duration,newdebt)

    debitor=User.find(qid,mysql)
    debitor.money+=money
    debitor.save(mysql)

    ans='借贷成功！请注意在借贷时限内还款！'
    return ans

def repay(message_list:list[str],qid:str):
    """
    :param message_list: 还款 债券编号 金额
    :param qid: 还款者的qq号
    :return: 还款提示信息
    """
    assert len(message_list)==3,'还款失败:您的还款格式不正确！'
    nowtime:int=round(datetime.timestamp(datetime.now()))
    try:
        debtID:int=int(message_list[1])
        money:int=int(message_list[2])
    except ValueError:
        return '还款失败:您的还款格式不正确！'
    debt=Debt.find(debtID,mysql)
    debitor=User.find(qid,mysql)
    assert debt is not None,"还款失败:不存在此债券！"
    assert debt.debitor_id==qid,'还款失败:您不是此债券的债务人！'
    assert money>0,'还款失败:还款金额必须为正！'
    assert debitor.money>money,'还款失败:您的余额不足！'
    assert debt.endtime>nowtime,'还款失败:此债券已结束还款！'

    if money>=debt.money:
        debitor.money-=(money-debt.money)#返还多余的还款
        debitor.save(mysql)
        debt.remove(mysql)
        ans='还款成功！您已还清此贷款！'
        send(debt.creditor_id,'您的债券:%s已还款完毕，贷款已送到您的账户'%debtID,False)
    else:
        debt.money-=money
        debitor.money-=money
        debt.save(mysql)
        debitor.save(mysql)
        ans='还款成功！剩余贷款金额:%d'%debt.money
    return ans

def debtMarket(message_list:list[str],qid:str):
    """
    :param message_list: 债市
    :param qid:
    :return: 提示信息
    """
    debts:list[Debt]=Debt.findAll(mysql,where='debitor_id=?',args=('nobody',))
    ans='欢迎来到债市！\n'
    if debts:
        ans+='以下是所有目前可借的贷款:\n'
        debtData=[['债券编号','金额','债权人','借出时间','利率','起始时间','终止时间']]
        for debt in debts:
            debttime:str=''
            if debt.duration//86400:
                debttime+='%d天'%(debt.duration//86400)
            if (debt.duration%86400)//3600:
                debttime+='%d小时'%((debt.duration%86400)//3600)
            if (debt.duration%3600)//60:
                debttime+='%d分钟'%((debt.duration%3600)//60)
            starttime:str=datetime.fromtimestamp(float(debt.starttime)).strftime('%Y-%m-%d %H:%M:%S')
            endtime:str=datetime.fromtimestamp(float(debt.endtime)).strftime('%Y-%m-%d %H:%M:%S')
            debtData.append([debt.debtID,debt.money,debt.creditor_id,debttime,debt.interest,starttime,endtime])
        drawtable(debtData,'debt.png')
        ans+='[CQ:image,file=debt.png]'
    else:
        ans+='目前没有可借的贷款！'
    return ans