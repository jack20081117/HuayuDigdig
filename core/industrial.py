from datetime import datetime
from tools import setTimeTask, drawtable, send, sigmoid, sqrtmoid, smart_interval, generateTime, is_prime, getnowtime, generateTimeStamp
from model import User, Plan
from update import updateEfficiency, updatePlan
from globalConfig import mysql,effisValueDict
from numpy import log


def expense_calculator(multiplier:float,duplication:int,primary_scale:int,secondary_scale:int,
                       tech:float,efficiency:float,factory_num:int,fuel_factor:float,use_log_divisor=True):
    """
    加工耗费计算函数
    :param multiplier: 随加工种类变化的因子
    :param duplication: 加工份数
    :param primary_scale:
    :param secondary_scale:
    :param tech: 该工种科技
    :param efficiency: 该工种效率
    :param factory_num: 调拨 工厂数
    :param fuel_factor:
    :param use_log_divisor:
    :return: 该加工需要的产能点数、时间与燃油
    """

    work_units_required = multiplier * duplication * primary_scale * log(log(secondary_scale) + 1)
    if use_log_divisor:
        work_units_required /= log(primary_scale)
    time_required = work_units_required / (sigmoid(efficiency) * factory_num)
    fuel_required = work_units_required / (fuel_factor * sqrtmoid(tech) * sigmoid(efficiency))#所用燃油

    return round(work_units_required), round(time_required), round(fuel_required)


def decompose(message_list: list[str], qid: str):
    """
    制定分解计划
    :param message_list: 分解 原矿 目标产物 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """
    assert len(message_list) == 5, '制定生产计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    try:
        ingredient: int = int(message_list[1])
        divide: int = int(message_list[2])
        duplication: int = int(message_list[3])
        factory_num: int = int(message_list[4])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    decomp_eff=user.effis[0]#用户的分解效率

    assert duplication>=1,'制定生产计划失败:倍数无效！'
    assert ingredient>1,'制定生产计划失败:原料无效！'
    assert divide>1,'制定生产计划失败:产物无效！'
    assert divide<ingredient,'制定生产计划失败:产物无效！'
    assert factory_num>=1,'制定生产计划失败:工厂数无效！'
    assert factory_num<=user.factory_num,'制定生产计划失败:您没有足够工厂！'
    assert not ingredient%divide,'制定生产计划失败:路径无效！'

    nowtime: int = getnowtime()
    starttime = nowtime

    minor_product = min(divide, ingredient // divide)

    work_units_required, time_required, fuel_required = \
        expense_calculator(4,duplication,minor_product,ingredient,user.industrial_tech,decomp_eff,factory_num,4)

    products:dict = {divide:duplication, (ingredient // divide):duplication}#生成产品

    ingredients:dict = {0: fuel_required, ingredient: duplication}#所需原料

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=0, factory_num=factory_num,
                      ingredients=ingredients, products=products, time_enacted=starttime, time_required=time_required,
                      work_units_required=work_units_required, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的分解计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！产物：%s, %s。' % (planID, factory_num,
                                                                         fuel_required, smart_interval(time_required),
                                                                         divide, ingredient / divide)

    return ans


def synthesize(message_list: list[str], qid: str):
    """
    制定合成计划
    :param message_list: 合成 原料1 原料2 (... 原料n) 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 提示信息
    """
    assert len(message_list) >= 5, '制定生产计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    ingredient_list = []

    try:
        for i in range(1, len(message_list) - 2):
            ingredient: int = int(message_list[i])
            ingredient_list.append(ingredient)
        duplication: int = int(message_list[-2])
        factory_num: int = int(message_list[-1])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    synth_eff = user.effis[1]#用户的合成效率

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    for ingredient in ingredient_list:
        assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert factory_num >= 1, '制定生产计划失败:工厂数无效！'
    assert factory_num <= user.factory_num, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    ingredients = {}#所需原料
    final_product = 1
    for ingredient in ingredient_list:

        final_product *= ingredient
        ingredients[ingredient] = duplication

    work_units_required, time_required, fuel_required = \
        expense_calculator(4,duplication,final_product,final_product,user.industrial_tech,synth_eff,factory_num,4)

    products:dict = {final_product: duplication}#生成产品

    ingredients[0] = fuel_required

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=1, factory_num=factory_num,
                      ingredients=ingredients, products=products, time_enacted=starttime, time_required=time_required,
                      work_units_required=work_units_required, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的合成计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！产物：%s。' % (planID, factory_num,
                                                                     fuel_required, smart_interval(time_required),
                                                                     final_product)

    return ans


def duplicate(message_list: list[str], qid: str):
    """
    制定复制计划
    :param message_list: 复制 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """
    assert len(message_list) == 4, '制定生产计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    try:
        ingredient: int = int(message_list[1])
        duplication: int = int(message_list[2])
        factory_num: int = int(message_list[3])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    duplicate_eff = user.effis[2]#用户的复制效率

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert factory_num >= 1, '制定生产计划失败:工厂数无效！'
    assert factory_num <= user.factory_num, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    work_units_required, time_required, fuel_required = \
        expense_calculator(1,duplication,ingredient+64,ingredient+64,
                           user.industrial_tech,duplicate_eff,factory_num,1,use_log_divisor=False)

    products: dict = {ingredient: duplication * 2}#生成成品

    ingredients: dict = {0: fuel_required, ingredient: duplication}#所需原料

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=2, factory_num=factory_num,
                      ingredients=ingredients, products=products, time_enacted=starttime, time_required=time_required,
                      work_units_required=work_units_required, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的复制计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！。' % (planID, factory_num,
                                                                fuel_required, smart_interval(time_required))

    return ans


def decorate(message_list: list[str], qid: str):
    """
    制定修饰计划
    :param message_list: 修饰 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """

    assert len(message_list) == 4, '制定生产计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    try:
        ingredient: int = int(message_list[1])
        duplication: int = int(message_list[2])
        factory_num: int = int(message_list[3])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    decorate_eff = user.effis[3]#用户的修饰效率

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert factory_num >= 1, '制定生产计划失败:工厂数无效！'
    assert factory_num <= user.factory_num, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    work_units_required, time_required, fuel_required = \
        expense_calculator(1,duplication,ingredient+1,ingredient+1,user.industrial_tech,decorate_eff,factory_num,2)

    products: dict = {ingredient + 1: duplication}#生成产品

    ingredients: dict = {0: fuel_required, ingredient: duplication}#所需原料

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=3, factory_num=factory_num,
                      ingredients=ingredients, products=products, time_enacted=starttime, time_required=time_required,
                      work_units_required=work_units_required, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的修饰计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！产物：%s。' % (planID, factory_num,
                                                                     fuel_required, smart_interval(time_required),
                                                                     ingredient + 1)

    return ans


def refine(message_list: list[str], qid: str):
    """
    制定炼化计划
    :param message_list: 炼化 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """

    assert len(message_list) == 4, '制定生产计划失败:请按照规定格式进行计划！'
    user: User = User.find(qid, mysql)
    try:
        ingredient: int = int(message_list[1])
        duplication: int = int(message_list[2])
        factory_num: int = int(message_list[3])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    refine_eff = user.effis[4]#用户的炼化效率

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert is_prime(ingredient), '制定生产计划失败:原料无效，炼油需要质数矿石！'
    assert factory_num >= 1, '制定生产计划失败:工厂数无效！'
    assert factory_num <= user.factory_num, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    work_units_required, time_required, fuel_required = \
        expense_calculator(2,duplication,ingredient,ingredient,user.refine_tech,refine_eff,factory_num,4)

    fuel_required -= 1 # 消除负收益

    if ingredient > 64:
        products: dict = {0: duplication * ingredient}
        ingredients: dict = {0: fuel_required, ingredient: duplication}
    else:#对较小的质数，可以使用炼化出的燃油重炼化，防止炼化燃油无法进行
        products: dict = {0: duplication * (ingredient - fuel_required)}
        ingredients: dict = {0: 0, ingredient: duplication}

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=4, factory_num=factory_num,
                      ingredients=ingredients, products=products, time_enacted=starttime, time_required=time_required,
                      work_units_required=work_units_required, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的炼化计划制定成功！按照此计划，%s个工厂将被调用，预估消耗%s单位燃油和%s时间！' % (planID, factory_num,
                                                               fuel_required, smart_interval(time_required),
                                                               )

    return ans


def enactPlan(message_list: list[str], qid: str):
    """
    激活计划，开始执行生产
    :param message_list: 执行 计划编号 执行时间
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """

    assert len(message_list) == 3, '设置失败:请按照规定格式进行执行！'
    nowtime: int = getnowtime()
    try:
        planID: int = int(message_list[1])
        if message_list[2] == '现在' or message_list[2] == 'now':
            starttime: int = nowtime
        elif generateTime(message_list[2]):
            starttime: int = nowtime + generateTime(message_list[2])
        else:
            starttime: int = generateTimeStamp(message_list[2])
    except ValueError:
        return '设置失败:请按照规定格式进行执行！'

    user: User = User.find(qid, mysql)
    plan: Plan = Plan.find(planID, mysql)

    assert plan, '不存在此计划！'
    assert plan.qid == qid, '您无权执行此计划！'

    factory_num = user.factory_num#用户所有的工厂数
    idle_factory_num = factory_num - user.busy_factory_num
    ans = ''
    if idle_factory_num < plan.factory_num and starttime != nowtime:
        ans += '提醒：您现在工厂数量不足，请确保计划执行时您有足够空闲工厂。\n'

    setTimeTask(enaction_wrapper, starttime, plan)

    ans += '设置成功！该计划将在指定时间开始执行。编号:%d' % planID

    return ans


def enaction_wrapper(plan: Plan):
    send(plan.qid, enaction(plan), False)


def enaction(plan: Plan):
    qid = plan.qid
    user: User = User.find(qid, mysql)
    required_factory_num = plan.factory_num
    idle_factory_num = user.factory_num - user.busy_factory_num
    assert required_factory_num <= idle_factory_num, "计划执行失败：工厂不足！"
    updateEfficiency(user, 0)

    mineral: dict = user.mineral

    ingredients: dict = plan.ingredients

    if plan.jobtype == 4:  # 特判炼油科技
        tech = user.refine_tech
    else:
        tech = user.industrial_tech

    time_required = plan.work_units_required / sigmoid(user.effis[plan.jobtype])
    fuel_required = round(idle_factory_num * time_required / (2 * sqrtmoid(tech)))
    ingredients[0] = fuel_required
    success: bool = True
    ans = ""

    for mId, mNum in ingredients.items():
        if mId == 0:
            mName = "燃油"
        else:
            mName = "矿物%s" % mId
        if mineral.get(mId,0) < mNum:
            ans += "%s不足！您目前有%d，计划%d需要%d单位。\n" % (mName, mineral.get(mId,0), plan.planID, mNum)
            success = False

    if success:
        ans += "计划%s成功开工！按照当前效率条件，需消耗%s时间，%s单位燃油。" % (plan.planID,
                                                      smart_interval(time_required), round(fuel_required))
        for mId, mNum in ingredients.items():
            mineral[mId] -= mNum
            if mineral[mId] <= 0: mineral.pop(mId)

        user.mineral = mineral
        user.busy_factory_num += required_factory_num
        enacted_plan_types = user.enacted_plan_types
        enacted_plan_types.setdefault(plan.jobtype, 0)
        enacted_plan_types[plan.jobtype] += 1
        user.save(mysql)

        nowtime = getnowtime()
        plan.enacted = True
        plan.time_enacted = nowtime
        plan.time_required = time_required
        plan.save(mysql)

        setTimeTask(updatePlan, nowtime + round(time_required), plan)
    return ans


def cancelPlan(message_list: list[str], qid: str):
    """
    取消计划
    :param message_list: 取消 计划编号
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """
    assert len(message_list) == 2, '设置失败:请按照规定格式进行取消！'
    try:
        planID: int = int(message_list[1])
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
                mineral[mid] += mnum * (nowtime - plan.time_enacted) / plan.time_required  # 燃油按剩余时间比例返还
            else:
                mineral[mid] += mnum

        enacted_plan_types = user.enacted_plan_types  # 取消当前门类的生产状态
        enacted_plan_types[plan.jobtype] -= 1
        user.enacted_plan_types = enacted_plan_types

        user.busy_factory_num -= plan.factory_num  # 释放被占用的工厂

        ans = "计划取消成功，矿石以及部分未消耗燃料已经返还到您的账户。"

    plan.remove(mysql)
    user.save(mysql)

    return ans

def showPlan(message_list:list[str],qid:str):
    """
    查看计划
    :param message_list: 计划
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
        planData.append([plan.planID,effisValueDict[plan.jobtype],plan.factory_num,','.join(ingredients),','.join(products),smart_interval(plan.time_required)])
    drawtable(planData,'plan.png')
    ans='[CQ:image,file=plan.png]'
    return ans