import re
import markdown
import imgkit
from datetime import datetime
from matplotlib import pyplot as plt
plt.rcParams['font.family']='Microsoft Yahei'

from staticFunctions import getnowtime,getnowdate,sigmoid,indicators,factors,send,drawtable,generateTimeStr
from globalConfig import mysql,imgkit_config,effisItemCount,effisNameDict,effisStr,playerTax
from model import User,Statistics,Debt
from update import updateEfficiency,assetCalculation

class StaticService(object):
    def __init__(self):
        pass

    @staticmethod
    def returnTime(m, q):
        """
        返回当前时间
        """
        return '当前时间为:%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def getHelp(messageList:list[str],qid:str):
        filename='help_msg.md' if len(messageList)==1 else '%s.md'%messageList[1]
        try:
            with open('help_msg/%s'%filename,'r',encoding='utf-8') as help_msg:
                html=markdown.markdown(help_msg.read())
        except FileNotFoundError:
            return '您的指令错误！'
        imgkit.from_string(html,'../go-cqhttp/data/images/help.png',config=imgkit_config,css='./style.css')
        ans='[CQ:image,file=help.png]'
        return ans

    @staticmethod
    def getStats(messageList:list[str],qid:str):
        ans='欢迎查看国家统计局！\n'
        moneyData=[]
        fuelData=[]
        nowdate=getnowdate()
        for i in range(6,-1,-1):
            date=nowdate-86400*i
            stats = Statistics.findAll(mysql, where='timestamp>=? and timestamp<=?', args=[date,date+86400])
            moneyData.append([date,0])
            fuelData.append([date,0])
            for stat in stats:
                if stat.money:
                    moneyData.append([stat.timestamp,0])
                    moneyData[-1][-1]+=stat.money+moneyData[-2][-1]
                if stat.fuel:
                    fuelData.append([stat.timestamp,0])
                    fuelData[-1][-1]+=stat.fuel+fuelData[-2][-1]
        ans+='以下是所有兑换矿石与开采燃油数据：\n'
        xs,ys=[],[]
        for datum in moneyData:
            xs.append(datetime.fromtimestamp(datum[0]-8*3600))
            ys.append(datum[1])
        plt.figure(figsize=(10,5))
        plt.plot(xs,ys,linestyle='-',marker=',',label='矿石',alpha=0.5)

        xs,ys=[],[]
        for datum in fuelData:
            xs.append(datetime.fromtimestamp(datum[0]-8*3600))
            ys.append(datum[1])
        plt.plot(xs,ys,linestyle='-',marker=',',label='燃油',alpha=0.5)

        plt.legend()
        plt.savefig('../go-cqhttp/data/images/statistics.png')
        ans+='[CQ:image,file=statistics.png]\n'

        return ans

    @staticmethod
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


class UserService(object):
    def __init__(self):
        pass

    @staticmethod
    def signup(messageList:list[str],qid:str):
        """
        用户注册
        :param messageList: 注册 学号
        :param qid: 注册者的qq号
        :return: 注册提示信息
        """
        assert len(messageList)==2 \
            and re.match(r'((1[0-9]|2[0-9]|30)\d{3,4}|(19|20)\d{2}(0[1-9]|1[0-2])\d{2})',messageList[1]) \
            and len(messageList[1]) in [5,6,8],'注册失败:请注意您的输入格式！'
        schoolID:str=messageList[1]
        nowtime = getnowtime()
        assert not User.find(qid, mysql) and not User.findAll(mysql, 'schoolID=?', (schoolID,)),'注册失败:您已经注册过，无法重复注册！'
        effis = {key:0.0 for key in range(0,8)}
        user = User(
            qid=qid,
            schoolID=schoolID,
            money=0,
            mineral={},
            tech={'extract':0.0,'industrial':0.0,'refine':0.0},
            techCards={'extract':[],'industrial':[],'refine':[]},
            forbidtime=[nowtime],
            factoryNum=1,
            effis=effis,
            mines=[],
            expr={},
            stocks={},
            misc={},
            enactedPlanTypes={},
            busyFactoryNum=0,
            lastEffisUpdateTime=nowtime,
            inputTax=0.0, #进项税额（抵扣）
            outputTax=0.0, #销项税额
            effisFee=0.0,
            allowLearning=False,
            robotNum=0,
        )#注册新用户
        user.add(mysql)
        ans="注册成功！"
        return ans

    @staticmethod
    def getUserInfo(messageList:list[str],qid:str):
        """
        查询用户个人信息
        :param messageList: 查询
        :param qid: 查询者的qq号
        :return: 查询提示信息
        """
        user:User = User.find(qid, mysql)
        if not user:
            return "[错误] 您尚未注册!"
        ans='查询到QQ号为%s的用户信息:\n'%qid
        schoolID:str=user.schoolID
        money:int=user.money
        industrialTech:float=user.tech['industrial']
        extractTech:float=user.tech['extract']
        refineTech:float=user.tech['refine']
        digable:str='是' if user.forbidtime[0] < getnowtime() else '否'
        mineral:dict[int,int]=user.mineral
        sortedMineral:dict[int,int]={key:mineral[key] for key in sorted(mineral.keys())}
        factoryNum:int=user.factoryNum

        infoTable=[
            ['学号','余额','加工科技点','开采科技点','炼油科技点','当前是否可开采','工厂数'],
            [schoolID,money,industrialTech,extractTech,refineTech,digable,factoryNum]
        ]
        drawtable(infoTable,'infoTable.png')
        ans+='[CQ:image,file=infoTable.png]\n'

        ans+="以下为该玩家拥有的矿石:\n"
        mineralTable=[['编号','数目']*2]
        rawMineralTable=[['矿石%s'%key if key else '燃油',value] for key,value in sortedMineral.items()]
        for i in range(0,len(rawMineralTable),2):
            if i+1<len(rawMineralTable):
                mineralTable.append(rawMineralTable[i])
                mineralTable[-1].extend(rawMineralTable[i+1])
            else:
                mineralTable.append(rawMineralTable[i])
                mineralTable[-1].extend(['',''])

        drawtable(mineralTable,'mineralTable.png')
        ans+='[CQ:image,file=mineralTable.png]\n'

        ans+="以下为该玩家各工种生产效率:\n"

        effis=user.effis
        effisTable=[['工种','生产效率']]
        effisTable.extend([[effisStr[index],"%.4f%%\n"%(sigmoid(effis[index])*100)] for index in range(effisItemCount)])
        drawtable(effisTable,'effisTable.png')
        ans+='[CQ:image,file=effisTable.png]\n'

        debts: list[Debt]=Debt.findAll(mysql,where='creditor=?',args=(qid,))

        if debts:
            ans+='以下为该玩家借出的贷款:\n'
            debtData=[['债券编号','金额','债务人','借出时间','利率','时化利率','起始时间','终止时间']]
            for debt in debts:
                debttime: str=''
                if debt.duration//86400:
                    debttime+='%d天'%(debt.duration//86400)
                if (debt.duration%86400)//3600:
                    debttime+='%d小时'%((debt.duration%86400)//3600)
                if (debt.duration%3600)//60:
                    debttime+='%d分钟'%((debt.duration%3600)//60)
                starttime: str=generateTimeStr(debt.starttime)
                endtime: str=generateTimeStr(debt.endtime)
                hourly_interest=('%.2f'%(100*debt.interest/((debt.endtime-debt.starttime)/3600)))+"%"
                debitor='空' if debt.debitor=='nobody' else debt.debitor
                debtData.append([debt.debtID,debt.money,debitor,debttime,debt.interest,hourly_interest,starttime,endtime])
            drawtable(debtData,'lend.png')
            ans+='[CQ:image,file=lend.png]\n'
        else:
            ans+='目前该玩家未借出贷款。\n'

        debts:list[Debt]=Debt.findAll(mysql,where='debitor=?',args=(qid,))
        if debts:
            ans+='以下为该玩家借入的贷款:\n'
            debtData=[['债券编号','金额','债权人','借出时间','利率','时化利率','起始时间','终止时间']]
            for debt in debts:
                debttime: str=''
                if debt.duration//86400:
                    debttime+='%d天'%(debt.duration//86400)
                if (debt.duration%86400)//3600:
                    debttime+='%d小时'%((debt.duration%86400)//3600)
                if (debt.duration%3600)//60:
                    debttime+='%d分钟'%((debt.duration%3600)//60)
                starttime: str=generateTimeStr(debt.starttime)
                endtime: str=generateTimeStr(debt.endtime)
                hourly_interest=('%.2f'%(100*debt.interest/((debt.endtime-debt.starttime)/3600)))+"%"
                debtData.append([debt.debtID,debt.money,debt.creditor,debttime,debt.interest,hourly_interest,starttime,endtime])
            drawtable(debtData,'borrow.png')
            ans+='[CQ:image,file=borrow.png]\n'
        else:
            ans+='目前该玩家未借入贷款。\n'

        stocks:dict[str,int]=user.stocks
        if stocks:
            ans+='以下是该玩家持有的股票:\n'
            stockTable=[['股票名称','持有股数']]
            stockTable.extend([[stockID,stockNum] for stockID,stockNum in stocks.items()])
            drawtable(stockTable,'stockTable.png')
            ans+='[CQ:image,file=stockTable.png]'
        else:
            ans+='目前该玩家未持有股票。'

        ans+="以下为该玩家拥有的私人矿井编号:\n"
        ans+=','.join('%s' for mine in user.mines)

        return ans

    @staticmethod
    def pay(messageList:list[str],qid:str):
        """
        :param messageList: 支付 q`QQ号`/`学号` `金额`
        :param qid: 支付者的qq号
        :return: 支付提示信息
        """
        assert len(messageList)==3,'支付失败:您的支付格式不正确！'
        target=str(messageList[1])
        #assert messageList[2].startswith("$"),'支付失败:您的金额格式不正确！'
        try:
            money:float=float(str(messageList[2]))
        except ValueError:
            return "支付失败:您的金额格式不正确！应当为:`金额`"

        user:User=User.find(qid,mysql)

        assert user.money>=money,"支付失败:您的余额不足！"
        if target.startswith("q"):
            # 通过QQ号查找对方
            tqid:str=target[1:]
            tuser:User=User.find(tqid,mysql)
            assert tuser,"支付失败:QQ号为%s的用户未注册！"%tqid
        else:
            tschoolID:str=target
            # 通过学号查找
            assert User.findAll(mysql,'schoolID=?',(tschoolID,)),"支付失败:学号为%s的用户未注册！"%tschoolID
            tuser:User=User.findAll(mysql,'schoolID=?',(tschoolID,))[0]

        user.money-=money
        tuser.money+=round(money*(1-playerTax))

        user.save(mysql)
        tuser.save(mysql)

        return "支付成功！"

    @staticmethod
    def factorsLookup(messageList:list[str],qid:str):
        """
        :param messageList: 因子查询 （目标矿石）
        :param qid: 支付者的qq号
        :return: 支付提示信息
        """
        if len(messageList) == 1:
            user: User = User.find(qid, mysql)
            indicatorList = indicators(user.schoolID)
            ans = '您的天赋代码的%s个判定段和其质因子如下：\n' % len(indicatorList)
            allFactorList = []
            for i in indicatorList:
                primeFactors, Factors = factors(i)
                ans += '%s:' % i
                ans+=' '.join('%s'%p for p in sorted(primeFactors))
                ans += '\n'
                allFactorList += Factors
            ans+= '所有可供您兑换的矿石编号如下：\n'
            ans+=','.join(['%s'%factor for factor in sorted(set(allFactorList)) if factor!=1])
        else:
            try:
                mineral: int = int(messageList[1])
            except ValueError:
                return "查询失败:您的查询格式不正确！"
            primeFactors, Factors = factors(mineral)
            ans = '质因子:'+' '.join('%s' % p for p in sorted(primeFactors))+'\n'+'所有因子:'
            ans += ','.join(['%s' % factor for factor in sorted(Factors) if factor != 1])

        return ans

    @staticmethod
    def forbidLearning(messageList:list[str],qid:str):
        """
        :param messageList: 禁止学习
        :param qid: 允许者的qq号
        :return: 允许提示信息
        """
        user = User.find(qid,mysql)
        user.allowLearning = False
        user.save(mysql)

        return "已经禁止他人向您学习生产效率！"

    @staticmethod
    def allowLearning(messageList:list[str],qid:str):
        """
        :param messageList: 允许学习 学费价格
        :param qid: 允许者的qq号
        :return: 允许提示信息
        """
        assert len(messageList)==2,'允许失败:您的指令格式不正确！'
        try:
            money:float=float(str(messageList[1]))
        except ValueError:
            return "允许失败:您的学费格式不正确！"
        user = User.find(qid, mysql)
        user.allowLearning = True
        user.effisFee = money
        user.save(mysql)

        return "已经允许他人以%.2f一项一次的学费向您学习生产效率！" % money

    @staticmethod
    def learnEffis(messageList:list[str],qid:str):
        """
        :param messageList: 学习 效率名 学习对象
        :param qid: 允许者的qq号
        :return: 允许提示信息
        """
        assert len(messageList) == 3, '学习失败:您的指令格式不正确！'
        assert messageList[1] in effisNameDict, '学习失败：未知效率类别！'
        effisID = effisNameDict[messageList[1]]
        target = messageList[2]
        if target.startswith("q"):
            # 通过QQ号查找对方
            tqid:str=target[1:]
            tuser:User=User.find(tqid,mysql)
            assert tuser,"学习失败:QQ号为%s的用户未注册！"%tqid
        else:
            tschoolID:str=target
            # 通过学号查找
            assert User.findAll(mysql,'schoolID=?',(tschoolID,)),"学习失败:学号为%s的用户未注册！"%tschoolID
            tuser:User=User.findAll(mysql,'schoolID=?',(tschoolID,))[0]

        assert tuser.allowLearning, "学习失败：对方禁止了他人学习效率！"
        user = User.find(qid,mysql)
        assert user.money >= tuser.effisFee, "学习失败：您的余额不够缴纳学费！"

        updateEfficiency(tuser, 0)
        assert user.effis[effisID] < tuser.effis[effisID], "您的该项效率目前比学习对象还要高，不需要进行学习！"

        user.effis[effisID] = user.effis[effisID]*0.25+tuser.effis[effisID]*0.75
        tuser.effis[effisID] = user.effis[effisID]*0.1+tuser.effis[effisID]*0.9
        user.money -= tuser.effisFee
        tuser.money += tuser.effisFee
        send(tuser.qid,"%s(%s)向你学习了%s效率，您得到了%.2f元报酬，当前该项效率为%.2f点" %
            (user.schoolID,user.qid,messageList[1],tuser.effisFee,tuser.effis[effisID]))

        user.save(mysql)
        tuser.save(mysql)

        return "学习成功！您的%s效率已经提高到了%.2f点" % (messageList[1], user.effis[effisID])


