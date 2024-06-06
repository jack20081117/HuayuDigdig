from model import User
from globalConfig import vatRate, mysql,groupIDs
from tools import setCrontab,getnowtime,send

def payTax(messageList:list[str],qid:str):
    """
    缴税
    :param messageList: 纳税/缴税/交税 税金
    :param qid: 纳税人的qq号
    :return: 纳税提示信息
    """
    assert len(messageList)==2,'缴税失败:您的缴税格式不正确！'
    nowtime:int=getnowtime()#现在的时间
    try:
        money:int=int(messageList[1])
    except ValueError:
        return '缴税失败:您的缴税格式不正确！'

    taxpayer = User.find(qid,mysql)
    treasury = User.find('treasury',mysql)

    assert money>0,'缴税失败:缴税金额必须为正！'
    assert taxpayer.money>money,'缴税失败:您的余额不足！'
    assert not taxpayer.paidTaxes,'您本期已缴税，不必重复缴纳！'

    taxAmount = taxpayer.outputTax - taxpayer.inputTax
    outputTax = taxpayer.outputTax
    inputTax = taxpayer.inputTax

    if taxAmount <= 0:
        taxpayer.inputTax -= outputTax
        taxpayer.outputTax = 0
        taxpayer.paidTaxes = True
        taxpayer.save(mysql)
        return '您本期进项税额%.2f大于销项税额%.2f，无需纳税，进项税额余额转结到下一周期继续抵扣！' % (inputTax, outputTax)

    if money>=taxAmount:
        taxpayer.money-=money
        treasury.money+=money
        taxpayer.inputTax += money
        taxpayer.inputTax -= outputTax
        taxpayer.outputTax = 0 #销项税额归零
        taxpayer.paidTaxes = True
        taxpayer.save(mysql)
        treasury.save(mysql)
        return '您本期应纳税%.2f元，缴税%s大于等于应纳金额，税已结清，余额转结到下一期可抵扣！' % (taxAmount, money)
    else:
        taxpayer.money -= money
        treasury.money += money
        taxpayer.outputTax -= (taxpayer.inputTax + money)
        taxpayer.inputTax = 0 #进项税额抵扣完毕
        taxpayer.save(mysql)
        treasury.save(mysql)
        return '您本期应纳税%.2f元，缴税%s小于应纳金额，税尚未结清，请务必在本期缴完税务！' % (taxAmount, money)

def taxUpdate():
    treasury:User=User.find('treasury',mysql)
    preTaxAmount = treasury.money
    for user in User.findAll(mysql):
        if user.qid not in ['treasury']:
            if user.paidTaxes:
                user.paidTaxes = False
                user.save(mysql)
                send(user.qid, '您本期已结清税款，进项税额余额%.2f元转结至下一期继续抵扣，感谢您对我游税务工作的支持。' % user.inputTax)
            elif user.outputTax - user.inputTax <= 10:
                send(user.qid,'提醒：本期您无需缴税或欠缴税额较小，但并未主动缴清，以后切勿忘记缴税。')
            elif 0.8*user.money > (user.outputTax - user.inputTax)*1.005:
                user.money -= (user.outputTax - user.inputTax)*1.005
                treasury.money += (user.outputTax - user.inputTax)*1.005
                user.save(mysql)
                send(user.qid, '提醒：本期您未缴清税款，但检测到您流动资金较充裕，已帮您自动扣税，加征5‰的手续费，以后建议您主动缴清！')
            else:
                user.outputTax += 0.1*(user.outputTax - user.inputTax)
                user.save(mysql)
                send(user.qid, '提醒：本期您未报税，且流动资金不充裕，请于下一期内主动结清拖欠的税款，以及加征的10%滞纳金！如果继续逾期您可能面临强制措施！')
    taxedAmount = treasury.money - preTaxAmount
    for group_id in group_ids:
        send(group_id,'本期总共征税%.2f元,感谢各位对我游税务工作的支持。' % taxedAmount,group=True)
    treasury.save(mysql)


# 强制征税（需与破产清算机制合并考虑）
#def forcedTax(taxpayer:User):
#    if not taxpayer.paidTaxes:
#        if taxpayer.outputTax - taxpayer.inputTax <= taxpayer.money:


