from model import User
from globalConfig import vat_rate, mysql,group_ids
from tools import setCrontab,getnowtime,send

def pay_tax(message_list:list[str],qid:str):
    """
    缴税
    :param message_list: 纳税/缴税/交税 税金
    :param qid: 纳税人的qq号
    :return: 纳税提示信息
    """
    assert len(message_list)==2,'缴税失败:您的缴税格式不正确！'
    nowtime:int=getnowtime()#现在的时间
    try:
        money:int=int(message_list[1])
    except ValueError:
        return '缴税失败:您的缴税格式不正确！'

    taxpayer = User.find(qid,mysql)
    treasury = User.find('treasury',mysql)

    assert money>0,'缴税失败:缴税金额必须为正！'
    assert taxpayer.money>money,'缴税失败:您的余额不足！'
    assert not taxpayer.paid_taxes,'您本期已缴税，不必重复缴纳！'

    tax_amount = taxpayer.output_tax - taxpayer.input_tax
    output_tax = taxpayer.output_tax
    input_tax = taxpayer.input_tax

    if tax_amount <= 0:
        taxpayer.input_tax -= output_tax
        taxpayer.output_tax = 0
        taxpayer.paid_taxes = True
        taxpayer.save(mysql)
        return '您本期进项税额%.2f大于销项税额%.2f，无需纳税，进项税额余额转结到下一周期继续抵扣！' % (input_tax, output_tax)

    if money>=tax_amount:
        taxpayer.money-=money
        treasury.money+=money
        taxpayer.input_tax += money
        taxpayer.input_tax -= output_tax
        taxpayer.output_tax = 0 #销项税额归零
        taxpayer.paid_taxes = True
        taxpayer.save(mysql)
        treasury.save(mysql)
        return '您本期应纳税%.2f元，缴税%s大于等于应纳金额，税已结清，余额转结到下一期可抵扣！' % (tax_amount, money)
    else:
        taxpayer.money -= money
        treasury.money += money
        taxpayer.output_tax -= (taxpayer.input_tax + money)
        taxpayer.input_tax = 0 #进项税额抵扣完毕
        taxpayer.save(mysql)
        treasury.save(mysql)
        return '您本期应纳税%.2f元，缴税%s小于应纳金额，税尚未结清，请务必在本期缴完税务！' % (tax_amount, money)

def tax_update():
    treasury:User=User.find('treasury',mysql)
    pre_tax_amount = treasury.money
    for user in User.findAll(mysql):
        if user.qid not in ['treasury']:
            if user.paid_taxes:
                user.paid_taxes = False
                user.save(mysql)
                send(user.qid, '您本期已结清税款，进项税额余额%.2f元转结至下一期继续抵扣，感谢您对我游税务工作的支持。' % user.input_tax)
            elif user.output_tax - user.input_tax <= 10:
                send(user.qid,'提醒：本期您无需缴税或欠缴税额较小，但并未主动缴清，以后切勿忘记缴税。')
            elif 0.8*user.money > (user.output_tax - user.input_tax)*1.005:
                user.money -= (user.output_tax - user.input_tax)*1.005
                treasury.money += (user.output_tax - user.input_tax)*1.005
                user.save(mysql)
                send(user.qid, '提醒：本期您未缴清税款，但检测到您流动资金较充裕，已帮您自动扣税，加征5‰的手续费，以后建议您主动缴清！')
            else:
                user.output_tax += 0.1*(user.output_tax - user.input_tax)
                user.save(mysql)
                send(user.qid, '提醒：本期您未报税，且流动资金不充裕，请于下一期内主动结清拖欠的税款，以及加征的10%滞纳金！如果继续逾期您可能面临强制措施！')
    taxed_amount = treasury.money - pre_tax_amount
    for group_id in group_ids:
        send(group_id,'本期总共征税%.2f元,感谢各位对我游税务工作的支持。' % taxed_amount,group=True)
    treasury.save(mysql)


# 强制征税（需与破产清算机制合并考虑）
#def forced_tax(taxpayer:User):
#    if not taxpayer.paid_taxes:
#        if taxpayer.output_tax - taxpayer.input_tax <= taxpayer.money:


