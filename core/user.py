import re
from globalConfig import mysql,effisStr,infoMsg,playerTax,effisItemCount,effisNameDict
from tools import getnowtime,sigmoid, indicators, factors, send
from model import User
from update import updateEfficiency

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
    assert not User.find(qid,mysql) and not User.findAll(mysql,'schoolID=?',(schoolID,)),'注册失败:您已经注册过，无法重复注册！'
    effis={key:0.0 for key in range(0,5)}
    user=User(
        qid=qid,
        schoolID=schoolID,
        money=0,
        mineral={},
        tech={'extract':0.0,'industrial':0.0,'refine':0.0},
        techCards={'extract':[],'industrial':[],'refine':[]},
        digable=1,
        forbidtime=nowtime,
        factoryNum=1,
        effis=effis,
        mines=[],
        stocks={},
        misc={},
        enactedPlanTypes={},
        busyFactoryNum=0,
        lastEffisUpdateTime=nowtime,
        inputTax=0.0, #进项税额（抵扣）
        outputTax=0.0, #销项税额
        effisFee=0.0,
        allowLearning=False,
    )#注册新用户
    user.add(mysql)
    ans="注册成功！"
    return ans

def getUserInfo(messageList:list[str],qid:str):
    """
    查询用户个人信息
    :param messageList: 查询
    :param qid: 查询者的qq号
    :return: 查询提示信息
    """
    user:User=User.find(qid,mysql)
    schoolID:str=user.schoolID
    money:int=user.money
    mineral:str=user.mineral
    industrialTech:float=user.tech['industrial']
    extractTech:float=user.tech['extract']
    refineTech:float=user.tech['refine']
    digable:bool=user.digable
    mineral:dict[int,int]=user.mineral
    factoryNum:int=user.factoryNum
    effis=user.effis
    mines=user.mines
    sortedMineral:dict[int,int]={key:mineral[key] for key in sorted(mineral.keys())}

    mres:str=""
    for mid,mnum in sortedMineral.items():
        if mid==0:
            mres+="燃油%s个单位；\n"%mnum
        else:
            mres+="编号%s的矿石%s个；\n"%(mid,mnum)

    eres:str=''    #生产效率信息
    for index in range(effisItemCount):
        effis.setdefault(index,0.0)
        eres+=effisStr[index]+":%.4f%%\n" % (sigmoid(effis[index])*100)

    mineres:str='' #私有矿井信息
    for mine in mines:
        mineres+='%s,' % mine

    ans:str=infoMsg%(qid,schoolID,money,industrialTech,extractTech,refineTech,digable,
                  mres,factoryNum,eres,mineres)

    return ans

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

def factorsLookup(messageList:list[str],qid:str):
    """
    :param messageList: 因子查询
    :param qid: 支付者的qq号
    :return: 支付提示信息
    """
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

    return ans

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