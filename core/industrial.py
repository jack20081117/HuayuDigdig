from tools import setTimeTask, drawtable, send, sigmoid, sqrtmoid, smartInterval, generateTime, isPrime, getnowtime, generateTimeStamp
from model import User, Plan
from update import updateEfficiency, updatePlan
from globalConfig import mysql,effisValueDict, fuelFactorDict
from numpy import log
import numpy as np

def expense_calculator(multiplier:float,duplication:int,primary_scale:int,secondary_scale:int,
                       tech:float,efficiency:float,factoryNum:int,fuel_factor:float,useLogDivisor=True):
    """
    加工耗费计算函数
    :param multiplier: 随加工种类变化的因子
    :param duplication: 加工份数
    :param primary_scale:
    :param secondary_scale:
    :param tech: 该工种科技
    :param efficiency: 该工种效率
    :param factoryNum: 调拨 工厂数
    :param fuel_factor:
    :param useLogDivisor:
    :return: 该加工需要的产能点数、时间与燃油
    """


    workUnitsRequired = multiplier * duplication * primary_scale * log(log(secondary_scale) + 1)
    if useLogDivisor:
        workUnitsRequired /= log(primary_scale)
    timeRequired, fuelRequired = time_fuel_calculator(workUnitsRequired, efficiency, tech, factoryNum, fuel_factor)

    return workUnitsRequired, timeRequired, fuelRequired

def time_fuel_calculator(workUnitsRequired, efficiency, tech, factoryNum, fuel_factor):
    adjustedFactoryNum = (1 - sigmoid(tech + 0.25 * efficiency) ** factoryNum) / (1 - sigmoid(tech + 0.25 * efficiency))
    timeRequired = workUnitsRequired / (sigmoid(efficiency) * adjustedFactoryNum)
    fuelRequired = workUnitsRequired / (fuel_factor * sqrtmoid(tech) * sigmoid(efficiency))#所用燃油

    return round(timeRequired), round(fuelRequired)

def decompose(messageList: list[str], qid: str):
    """
    制定分解计划
    :param messageList: 分解 原矿 目标产物 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """
    assert len(messageList) == 5, '制定生产计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    try:
        ingredient: int = int(messageList[1])
        divide: int = int(messageList[2])
        duplication: int = int(messageList[3])
        factoryNum: int = int(messageList[4])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    decomp_eff=user.effis[0]#用户的分解效率

    assert duplication>=1,'制定生产计划失败:倍数无效！'
    assert ingredient>1,'制定生产计划失败:原料无效！'
    assert divide>1,'制定生产计划失败:产物无效！'
    assert divide<ingredient,'制定生产计划失败:产物无效！'
    assert factoryNum>=1,'制定生产计划失败:工厂数无效！'
    assert factoryNum<=user.factoryNum,'制定生产计划失败:您没有足够工厂！'
    assert not ingredient%divide,'制定生产计划失败:路径无效！'

    nowtime: int = getnowtime()
    starttime = nowtime

    minorProduct = min(divide, ingredient // divide)

    workUnitsRequired, timeRequired, fuelRequired = \
        expense_calculator(4,duplication,minorProduct,ingredient,user.tech['industrial'],decomp_eff,factoryNum,4)

    products:dict = {divide:duplication, (ingredient // divide):duplication}#生成产品

    ingredients:dict = {0: fuelRequired, ingredient: duplication}#所需原料

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=0, factoryNum=factoryNum,
                      ingredients=ingredients, products=products, timeEnacted=starttime, timeRequired=timeRequired,
                      workUnitsRequired=workUnitsRequired, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的分解计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！产物：%s, %s。' % (planID, factoryNum,
                                                                         fuelRequired, smartInterval(timeRequired),
                                                                         divide, ingredient / divide)

    return ans


def synthesize(messageList: list[str], qid: str):
    """
    制定合成计划
    :param messageList: 合成 原料1 原料2 (... 原料n) 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 提示信息
    """
    assert len(messageList) >= 5, '制定生产计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    ingredientList = []

    try:
        for i in range(1, len(messageList) - 2):
            ingredient: int = int(messageList[i])
            ingredientList.append(ingredient)
        duplication: int = int(messageList[-2])
        factoryNum: int = int(messageList[-1])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    synth_eff = user.effis[1]#用户的合成效率

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    for ingredient in ingredientList:
        assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert factoryNum >= 1, '制定生产计划失败:工厂数无效！'
    assert factoryNum <= user.factoryNum, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    ingredients = {}#所需原料
    finalProduct = 1
    for ingredient in ingredientList:

        finalProduct *= ingredient
        ingredients[ingredient] = duplication

    workUnitsRequired, timeRequired, fuelRequired = \
        expense_calculator(4,duplication,finalProduct,finalProduct,user.tech['industrial'],synth_eff,factoryNum,4)

    products:dict = {finalProduct: duplication}#生成产品

    ingredients[0] = fuelRequired

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=1, factoryNum=factoryNum,
                      ingredients=ingredients, products=products, timeEnacted=starttime, timeRequired=timeRequired,
                      workUnitsRequired=workUnitsRequired, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的合成计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！产物：%s。' % (planID, factoryNum,
                                                                     fuelRequired, smartInterval(timeRequired),
                                                                     finalProduct)

    return ans


def duplicate(messageList: list[str], qid: str):
    """
    制定复制计划
    :param messageList: 复制 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """
    assert len(messageList) == 4, '制定生产计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    try:
        ingredient: int = int(messageList[1])
        duplication: int = int(messageList[2])
        factoryNum: int = int(messageList[3])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    duplicate_eff = user.effis[2]#用户的复制效率

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert factoryNum >= 1, '制定生产计划失败:工厂数无效！'
    assert factoryNum <= user.factoryNum, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    workUnitsRequired, timeRequired, fuelRequired = \
        expense_calculator(1,duplication,ingredient+64,ingredient+64,
                           user.tech['industrial'],duplicate_eff,factoryNum,1,useLogDivisor=False)

    products: dict = {ingredient: duplication * 2}#生成成品

    ingredients: dict = {0: fuelRequired, ingredient: duplication}#所需原料

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=2, factoryNum=factoryNum,
                      ingredients=ingredients, products=products, timeEnacted=starttime, timeRequired=timeRequired,
                      workUnitsRequired=workUnitsRequired, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的复制计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！。' % (planID, factoryNum,
                                                                fuelRequired, smartInterval(timeRequired))

    return ans


def decorate(messageList: list[str], qid: str):
    """
    制定修饰计划
    :param messageList: 修饰 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """

    assert len(messageList) == 4, '制定生产计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    try:
        ingredient: int = int(messageList[1])
        duplication: int = int(messageList[2])
        factoryNum: int = int(messageList[3])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    decorate_eff = user.effis[3]#用户的修饰效率

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert factoryNum >= 1, '制定生产计划失败:工厂数无效！'
    assert factoryNum <= user.factoryNum, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    workUnitsRequired, timeRequired, fuelRequired = \
        expense_calculator(1,duplication,ingredient+1,ingredient+1,user.tech['industrial'],decorate_eff,factoryNum,2)

    products: dict = {ingredient + 1: duplication}#生成产品

    ingredients: dict = {0: fuelRequired, ingredient: duplication}#所需原料

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=3, factoryNum=factoryNum,
                      ingredients=ingredients, products=products, timeEnacted=starttime, timeRequired=timeRequired,
                      workUnitsRequired=workUnitsRequired, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的修饰计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！产物：%s。' % (planID, factoryNum,
                                                                     fuelRequired, smartInterval(timeRequired),
                                                                     ingredient + 1)

    return ans


def refine(messageList: list[str], qid: str):
    """
    制定炼化计划
    :param messageList: 炼化 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """

    assert len(messageList) == 4, '制定生产计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    try:
        ingredient: int = int(messageList[1])
        duplication: int = int(messageList[2])
        factoryNum: int = int(messageList[3])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    refine_eff = user.effis[4]#用户的炼化效率

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert isPrime(ingredient), '制定生产计划失败:原料无效，炼油需要质数矿石！'
    assert factoryNum >= 1, '制定生产计划失败:工厂数无效！'
    assert factoryNum <= user.factoryNum, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    workUnitsRequired, timeRequired, fuelRequired = \
        expense_calculator(2,duplication,ingredient,ingredient,user.tech['refine'],refine_eff,factoryNum,4)

    fuelRequired -= 1 # 消除负收益

    if ingredient > 64:
        products: dict = {0: duplication * ingredient}
        ingredients: dict = {0: fuelRequired, ingredient: duplication}
    else:#对较小的质数，可以使用炼化出的燃油重炼化，防止炼化燃油无法进行
        products: dict = {0: duplication * (ingredient - fuelRequired)}
        ingredients: dict = {0: 0, ingredient: duplication}

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=4, factoryNum=factoryNum,
                      ingredients=ingredients, products=products, timeEnacted=starttime, timeRequired=timeRequired,
                      workUnitsRequired=workUnitsRequired, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的炼化计划制定成功！按照此计划，%s个工厂将被调用，预估消耗%s单位燃油和%s时间！' % (planID, factoryNum,
                                                               fuelRequired, smartInterval(timeRequired),
                                                               )

    return ans

def research(messageList:list[str], qid: str):
    """
    制定科研计划
    :param messageList: 研究 科技名 试剂1 试剂2 (... 试剂n) 是否接续主线(1/0) 调拨工厂数
    :param qid: 制定者的qq号
    :return: 提示信息
    """
    assert len(messageList) >= 6, '制定科研计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    ingredientList = []

    try:
        for i in range(2, len(messageList) - 2):
            ingredient: int = int(messageList[i])
            ingredientList.append(ingredient)
        techName = str(messageList[1])
        continuation: int = int(messageList[-2])
        factoryNum: int = int(messageList[-1])
    except ValueError:
        return '制定科研计划失败:请按照规定格式进行计划！'

    techEff = user.effis[6]#用户的科研效率
    techNameDict = {'开采': 'extract', '加工': 'industrial', '炼油': 'refine'}

    assert techName in techNameDict, '制定科研计划失败:科技名无效！'
    assert continuation in [1,0], '制定科研计划失败:接续指令无效！'
    for ingredient in ingredientList:
        assert ingredient > 1, '制定科研计划失败:试剂无效！'
    assert factoryNum >= 1, '制定科研计划失败:工厂数无效！'
    assert factoryNum <= user.factoryNum, '制定科研计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    techName = techNameDict[techName]
    techCards = user.techCards[techName]

    ingredients = {}#所需原料
    ans = ''
    techPath = ingredientList


    if continuation or len(techCards) == 0:
        for ingredient in ingredientList:
            ingredients.setdefault(ingredient, 0)
            ingredients[ingredient] += 1
        if techCards:
            techPath = techCards[0] + ingredientList
        work_modifier = (np.log(np.array(techPath)).average() / 10 + 1)
        workUnitsRequired = (1200 + 600 * len(ingredientList)) * work_modifier
        timeRequired, fuelRequired = time_fuel_calculator(workUnitsRequired, techEff, 0, factoryNum, 4)
    else:
        commonSequenceLengths = []
        for i in range(len(techCards)):
            commonSequenceLength = 0
            for j in range(min(len(techCards[i]),len(ingredientList))):
                if techCards[i][j] == ingredientList[j]:
                    commonSequenceLength += 1
                    continue
                else:
                    commonSequenceLengths.append(commonSequenceLength)
                    break
        bestMatch = np.argmax(np.array(commonSequenceLengths))
        matchAmount = commonSequenceLengths[bestMatch]
        assert matchAmount < len(ingredientList), '您当前输入的序列是您已知的技术路径的子序列，不必重复研发！'
        if matchAmount > 0:
            ans+='您当前制定的科研计划与您已知的第%s科研路径在前%s级重合，将自动接续该技术路径进行研究！\n' % (bestMatch, matchAmount)
        else:
            ans+='您将制定一个全新的科研计划，与您已知的科研路径无重合之处！\n'
        divergentPath = ingredientList[matchAmount:]
        work_modifier = (np.log(np.array(techPath)).average() / 10 + 1)
        workUnitsRequired = (1200 + 600 * len(divergentPath)) * work_modifier
        timeRequired, fuelRequired = time_fuel_calculator(workUnitsRequired, techEff, 0, factoryNum, 4)
        for ingredient in divergentPath:
            ingredients.setdefault(ingredient, 0)
            ingredients[ingredient] += 1

    products:dict = {}#生成产品

    ingredients[0] = fuelRequired

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=6, factoryNum=factoryNum,
                      ingredients=ingredients, products=products, timeEnacted=starttime, timeRequired=timeRequired,
                      workUnitsRequired=workUnitsRequired, techName=techName,
                      techPath=techPath, enacted=False)
    plan.add(mysql)


    ans += '编号为%s的科研计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！' % (planID, factoryNum,
                                                                     fuelRequired, smartInterval(timeRequired),
                                                                     )
    return ans

def enactPlan(messageList: list[str], qid: str):
    """
    激活计划，开始执行生产
    :param messageList: 执行 计划编号 执行时间
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """

    assert len(messageList) == 3, '设置失败:请按照规定格式进行执行！'
    nowtime: int = getnowtime()
    try:
        planID: int = int(messageList[1])
        if messageList[2] == '现在' or messageList[2] == 'now':
            starttime: int = nowtime
        elif generateTime(messageList[2]):
            starttime: int = nowtime + generateTime(messageList[2])
        else:
            starttime: int = generateTimeStamp(messageList[2])
    except ValueError:
        return '设置失败:请按照规定格式进行执行！'

    user: User = User.find(qid, mysql)
    plan: Plan = Plan.find(planID, mysql)

    assert plan, '不存在此计划！'
    assert plan.qid == qid, '您无权执行此计划！'

    factoryNum = user.factoryNum#用户所有的工厂数
    idleFactoryNum = factoryNum - user.busyFactoryNum
    ans = ''
    if idleFactoryNum < plan.factoryNum and starttime != nowtime:
        ans += '提醒：您现在工厂数量不足，请确保计划执行时您有足够空闲工厂。\n'

    setTimeTask(enaction_wrapper, starttime, plan)

    ans += '设置成功！该计划将在指定时间开始执行。编号:%d' % planID

    return ans


def enaction_wrapper(plan: Plan):
    send(plan.qid, enaction(plan), False)


def enaction(plan: Plan):
    qid = plan.qid
    user: User = User.find(qid, mysql)
    requiredFactoryNum = plan.factoryNum
    idleFactoryNum = user.factoryNum - user.busyFactoryNum
    assert requiredFactoryNum <= idleFactoryNum, "计划执行失败：工厂不足！"
    updateEfficiency(user, 0)

    mineral: dict = user.mineral

    ingredients: dict = plan.ingredients

    if plan.jobtype == 4:  # 特判炼油科技
        tech = user.tech['refine']
    else:
        tech = user.tech['industrial']

    timeRequired, fuelRequired = \
    time_fuel_calculator(plan.workUnitsRequired,
                         user.effis[plan.jobtype],
                         tech,
                         requiredFactoryNum,
                         fuelFactorDict[plan.jobtype])

    if fuelRequired>64:
        ingredients[0] = fuelRequired

    success: bool = True
    ans = ""

    for mId, mNum in ingredients.items():
        if mId == 0:
            mName = "燃油"
        else:
            mName = "矿物%s" % mId
        if mId not in mineral:
            mineral[mId]=0
        if mineral[mId] < mNum:
            ans += "%s不足！您目前有%d，计划%d需要%d单位。\n" % (mName, mineral[mId], plan.planID, mNum)
            success = False

    if success:
        ans += "计划%s成功开工！按照当前效率条件，需消耗%s时间，%s单位燃油。" % (plan.planID,
                                                      smartInterval(timeRequired), round(fuelRequired))
        for mId, mNum in ingredients.items():
            mineral[mId] -= mNum
            if mineral[mId] <= 0: mineral.pop(mId)

        user.mineral = mineral
        user.busyFactoryNum += requiredFactoryNum
        enactedPlanTypes = user.enactedPlanTypes
        enactedPlanTypes.setdefault(plan.jobtype, 0)
        enactedPlanTypes[plan.jobtype] += 1
        user.save(mysql)

        nowtime = getnowtime()
        plan.enacted = True
        plan.timeEnacted = nowtime
        plan.timeRequired = timeRequired
        plan.save(mysql)

        setTimeTask(updatePlan, nowtime + round(timeRequired), plan)
    return ans


def cancelPlan(messageList: list[str], qid: str):
    """
    取消计划
    :param messageList: 取消 计划编号
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """
    assert len(messageList) == 2, '设置失败:请按照规定格式进行取消！'
    try:
        planID: int = int(messageList[1])
    except ValueError:
        return '设置失败:请按照规定格式进行执行！'

    user: User = User.find(qid, mysql)
    plan: Plan = Plan.find(planID, mysql)
    nowtime = getnowtime()

    assert plan, '不存在此计划！'
    assert plan.qid == qid, '您无权取消此计划！'

    if not plan.enacted:
        ans = '计划取消成功！'
    else:
        updateEfficiency(user, 0)  # 没有完成生产任务带来的超额增加，但是此前在生产中的时间不会导致该项效率下降。
        mineral: dict[int,int] = user.mineral
        ingredients: dict = plan.ingredients
        for mid, mnum in ingredients.items():
            if mid not in mineral:
                mineral[mid] = 0
            if mid == 0:
                mineral[mid] += mnum * (nowtime - plan.timeEnacted) / plan.timeRequired  # 燃油按剩余时间比例返还
            else:
                mineral[mid] += mnum

        enactedPlanTypes = user.enactedPlanTypes  # 取消当前门类的生产状态
        enactedPlanTypes[plan.jobtype] -= 1
        user.enactedPlanTypes = enactedPlanTypes

        user.busyFactoryNum -= plan.factoryNum  # 释放被占用的工厂

        ans = "计划取消成功，矿石以及部分未消耗燃料已经返还到您的账户。"

    plan.remove(mysql)
    user.save(mysql)

    return ans

def showPlan(messageList:list[str],qid:str):
    """
    查看计划
    :param messageList: 计划
    :param qid: 查看者的qq号
    :return: 自己拥有的生产计划
    """
    plans:list[Plan]=Plan.findAll(mysql,where='qid=?',args=(qid,))
    planData=[["计划编号","生产类型","调拨工厂数","原料","产品","用时"]]
    if not plans:
        return '您目前未制定生产计划！'
    for plan in plans:
        ingredients=[]
        for iId,iNum in plan.ingredients.items():
            if iId==0:
                ingredients.append('燃油:%s单位'%iNum)
            else:
                ingredients.append('矿石%s:%s个'%(iId,iNum))
        products=[]
        for pId,pNum in plan.products.items():
            if pId==0:
                products.append('燃油:%s单位'%pNum)
            else:
                products.append('矿石%s:%s个'%(pId,pNum))
        planData.append([plan.planID,effisValueDict[plan.jobtype],plan.factoryNum,','.join(ingredients),','.join(products),smartInterval(plan.timeRequired)])
    drawtable(planData,'plan.png')
    ans='[CQ:image,file=plan.png]'
    return ans