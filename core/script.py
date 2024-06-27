from globalConfig import groupIDs,botID,adminIDs,mysql
from model import User
from staticFunctions import send,transferStr

import service
commands:dict[str,callable]={}
replacement:dict[str,str]={
    "建设":"建造",
    "交税":"缴税",
    "纳税":"缴税"
}

from stock import StockService
from extract import ExtractService
from taxes import TaxesService
from debt import DebtService
from industrial import IndustrialService
from market import MarketService

def register(funcStr: str,func: callable):
    """
    向bot注册命令
    :param funcStr: 功能
    :param func: 功能函数
    """
    commands[funcStr]=func


def registerByDict(registers: dict[str,callable]):
    for funcStr,func in registers.items():
        register(funcStr,func)

def dealWithRequest(funcStr:str,messageList:list[str],qid:str):
    if transferStr(funcStr,replacement) in commands:
        ans=commands[funcStr](messageList,qid)
    else:
        ans="未知命令:请输入`帮助`以获取帮助信息，或通过`帮助 功能`获取该功能详细信息！"
    return ans

def handle(res,group, message, qid):
    ans:str=''  #回复给用户的内容
    if group:#是群发消息
        gid:str=str(res.get('group_id'))  #群的qq号
        if gid not in groupIDs:
            return None
        if "[CQ:at,qq=%s]"%botID not in message:#必须在自己被at的情况下才能作出回复
            return None

        messageList:list=message.split(' ')
        funcStr:str=messageList[1]
        messageList.pop(0)  #忽略at本身

        try:
            ans='[CQ:at,qq=%s]'%qid+dealWithRequest(funcStr,messageList,qid)
            send(gid,ans,group=True)
            return ans
        except AssertionError as err:
            send(gid,err,group=True)
            return err

    else:
        messageList:list=message.split(' ')
        funcStr:str=messageList[0]

        try:
            ans=dealWithRequest(funcStr,messageList,qid)
            send(qid,ans,group=False)
            return ans
        except AssertionError as err:
            send(qid,err,group=False)
            return str(err)

def distraint(messageList:list[str],qid:str):
    """
    强制执行
    :param messageList: 强制执行 被执行人学号/qid 被执行的命令名 *被执行的命令参数
    :param qid:
    :return: 提示信息
    """
    assert len(messageList) >= 3, '强制执行失败：输入格式不正确！'
    assert qid in adminIDs, '您无权进行强制执行！'
    identifier = messageList[1]
    if identifier.startswith("q"):
        # 通过QQ号查找对方
        tqid: str = identifier[1:]
        target: User = User.find(tqid, mysql)
        assert target, "强制执行失败:QQ号为%s的用户未注册！" % tqid
    else:
        tschoolID: str = identifier
        # 通过学号查找
        assert User.findAll(mysql, 'schoolID=?', (tschoolID,)), "强制执行失败:学号为%s的用户未注册！" % tschoolID
        target: User = User.findAll(mysql, 'schoolID=?', (tschoolID,))[0]
        tqid = target.qid

    funcStr = messageList[2]

    return commands[funcStr](messageList[2:],tqid)

def treasuryAction(messageList:list[str],qid:str):
    """
    国库财政行动
    :param messageList: 国库 被执行的命令名 *被执行的命令参数
    :param qid:
    :return: 提示信息
    """
    assert len(messageList) >= 2, '国库行动失败：输入格式不正确！'
    assert qid in adminIDs, '您无权调用国库经费！'

    funcStr = messageList[1]

    return commands[funcStr](messageList[1:],'treasury')
       

# SE => Service Executor
staticSE = service.StaticService()
userSE = service.UserService()
stockSE = StockService()
extractSE = ExtractService()
taxSE = TaxesService()
debtSE = DebtService()
industrialSE = IndustrialService()
marketSE = MarketService()

registerByDict({
    "time":     staticSE.returnTime,
    "帮助":     staticSE.getHelp,
    "财富排行": staticSE.showWealthiest,
    "统计局":   staticSE.getStats,
    
    "注册":     userSE.signup,
    "查询":     userSE.getUserInfo,
    "查询余额": userSE.getMoneyInfo,
    "支付":     userSE.pay,
    "因子查询": userSE.factorsLookup,
    "允许学习": userSE.allowLearning,
    "禁止学习": userSE.forbidLearning,
    "学习":     userSE.learnEffis,
    
    "发行":     stockSE.issueStock,
    "认购":     stockSE.acquireStock,
    "买入":     stockSE.buyStock,
    "抛出":     stockSE.sellStock,
    "股市":     stockSE.stockMarket,
    "股票走势":  stockSE.stockInfo,
    "分红":     stockSE.giveDividend,
    "兑换纸燃油":stockSE.toPaperFuel,
    "兑换燃油": stockSE.fromPaperFuel,
    
    "开采":     extractSE.getMineral,
    "开放":     extractSE.openMine,
    "关闭":     extractSE.closeMine,
    "兑换":     extractSE.exchangeMineral,
    "回购":     extractSE.buybackMineral,
    "转让矿井": extractSE.transferMine,
    "机器开采": extractSE.getMineralAuto,
    "收集燃料": extractSE.getFuel,
    
    "抽奖":     taxSE.lottery,
    "缴税":     taxSE.payTax,
    
    "放贷":     debtSE.prelendDebt,
    "借贷":     debtSE.borrowDebt,
    "还款":     debtSE.repayDebt,
    "转让债务": debtSE.transferDebt,
    "免除":     debtSE.forgiveDebt,
    "债市":     debtSE.debtMarket,
    
    "分解":     industrialSE.decompose,
    "合成":     industrialSE.synthesize,
    "修饰":     industrialSE.decorate,
    "复制":     industrialSE.duplicate,
    "炼化":     industrialSE.refine,
    "建造":     industrialSE.build,
    "建造机器人":industrialSE.buildRobot,
    "科研":     industrialSE.research,
    "勘探":     industrialSE.discover,
    "取消":     industrialSE.cancelPlan,
    "执行":     industrialSE.enactPlan,
    "计划":     industrialSE.showPlan,
    "转让工厂": industrialSE.transferFactory,
    
    "预售":     marketSE.presellMineral,
    "购买":     marketSE.buyMineral,
    "预订":     marketSE.prebuyMineral,
    "售卖":     marketSE.sellMineral,
    "拍卖":     marketSE.preauctionMineral,
    "投标":     marketSE.bidMineral,
    "矿市":     marketSE.mineralMarket,
    
    "强制执行":distraint,
    "国库":treasuryAction
})



