from model import User
from globalConfig import mysql,groupIDs
from staticFunctions import getnowtime,send
from numpy import random

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
            elif 0.9*user.money > (user.outputTax - user.inputTax)*1.005:
                user.money -= (user.outputTax - user.inputTax)*1.005
                treasury.money += (user.outputTax - user.inputTax)*1.005
                user.save(mysql)
                send(user.qid, '提醒：本期您未缴清税款，但检测到您流动资金较充裕，已帮您自动扣税，加征5‰的手续费，以后建议您主动缴清！')
            else:
                user.outputTax += 0.1*(user.outputTax - user.inputTax)
                user.save(mysql)
                send(user.qid, '提醒：本期您未报税，且流动资金不充裕，请于下一期内主动结清拖欠的税款，以及加征的10%滞纳金！如果继续逾期您可能面临强制措施！')
    taxedAmount = treasury.money - preTaxAmount
    for groupID in groupIDs:
        send(groupID,'本期总共征税%.2f元,感谢各位对我游税务工作的支持。' % taxedAmount,group=True)
    treasury.save(mysql)

class taxesService():
    def payTax(self, messageList:list[str],qid:str):
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

    def lottery(self, messageList:list[str],qid:str):
        """
        抽奖(每次耗费10元）
        特等奖中奖概率0.00001 奖金50000元
        一等奖中奖概率0.0001 奖金10000元
        二等奖中奖概率0.005 奖金200元
        三等奖中奖概率0.05 奖金50元
        四等奖中奖概率0.2 奖金20元
        期望值：0.5+1+1+2.5+4=9元
        :param messageList: 抽奖 倍率(默认为1) 次数(默认为1)
        :param qid: 抽奖人的qq号
        :return: 抽奖提示信息
        """
        assert 1<=len(messageList)<=3, "您抽奖的格式不正确！"
        try:
            multiplier:int=1 if len(messageList)==1 else int(messageList[1])
            duplication:int=1 if len(messageList)<=2 else int(messageList[2])
        except ValueError:
            return '抽奖失败:您的抽奖次数不正确！'
        assert multiplier>0,"还在玩负数倍率的bug，真是不可饶恕！"
        assert multiplier <= 10, "大赌伤身，一次最多抽10倍！"
        assert duplication <= 20,"大赌伤身，一次最多抽20发！"
        user = User.find(qid, mysql)
        treasury = User.find('treasury', mysql)
        assert user.money >= 10, "您没有足够的钱抽奖一次！"
        ans = ''
        for i in range(duplication):
            if user.money <= 10*multiplier:
                ans += '您的余额不足继续抽奖！'
                break
            user.money -= 10*multiplier
            treasury.money += 10
            indicator = random.random()
            if indicator <= 0.00001:
                ans += '恭喜！中了特等奖，奖金50000！（概率0.00001）\n'
                user.money += 50000*multiplier
                treasury.money -= 50000*multiplier
            elif indicator <= 0.00011:
                ans += '恭喜！中了一等奖，奖金10000！（概率0.0001）\n'
                user.money += 10000*multiplier
                treasury.money -= 10000*multiplier
            elif indicator <= 0.00511:
                ans += '恭喜！中了二等奖，奖金200！（概率0.005）\n'
                user.money += 200*multiplier
                treasury.money -= 200*multiplier
            elif indicator <= 0.05511:
                ans += '恭喜！中了三等奖，奖金50！（概率0.05）\n'
                user.money += 50*multiplier
                treasury.money -= 50*multiplier
            elif indicator <= 0.25511:
                ans += '恭喜！中了四等奖，奖金20！（概率0.2）\n'
                user.money += 20*multiplier
                treasury.money -= 20*multiplier
            else:
                ans += '很遗憾，这次没有中奖！\n'

        user.save(mysql)
        treasury.save(mysql)

        return ans

    # 强制征税（需与破产清算机制合并考虑）
    #def forcedTax(taxpayer:User):
    #    if not taxpayer.paidTaxes:
    #        if taxpayer.outputTax - taxpayer.inputTax <= taxpayer.money:


