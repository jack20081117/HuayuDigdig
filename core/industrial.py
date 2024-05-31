from datetime import datetime
from tools import setTimeTask, drawtable, send, sigmoid, sqrtmoid, smart_interval, generateTime, is_prime, getnowtime
from model import User, Plan
from update import updateEfficiency, updatePlan
from globalConfig import mysql
from numpy import log


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

    decomp_eff=user.effis[0]

    assert duplication>=1,'制定生产计划失败:倍数无效！'
    assert ingredient>1,'制定生产计划失败:原料无效！'
    assert divide>1,'制定生产计划失败:产物无效！'
    assert divide<ingredient,'制定生产计划失败:产物无效！'
    assert factory_num>=1,'制定生产计划失败:工厂数无效！'
    assert factory_num<=user.factory_num,'制定生产计划失败:您没有足够工厂！'
    assert not ingredient%divide,'制定生产计划失败:路径无效！'

    nowtime: int = getnowtime()
    starttime = nowtime

    minor_product = min(divide, int(ingredient / divide))
    work_units_required = 4 * duplication * minor_product * log(log(ingredient) + 1) / \
                          (log(minor_product) * factory_num)
    time_required = work_units_required / sigmoid(decomp_eff)
    fuel_required = factory_num * time_required / (4 * sqrtmoid(user.industrial_tech))

    products:dict = {divide:duplication, int(ingredient / divide):duplication}

    ingredients:dict = {0: round(fuel_required), ingredient: duplication}

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

    synth_eff = user.effis[1]

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    for ingredient in ingredient_list:
        assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert factory_num >= 1, '制定生产计划失败:工厂数无效！'
    assert factory_num <= user.factory_num, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    ingredients = {}
    final_product = 1
    for ingredient in ingredient_list:

        final_product *= ingredient
        ingredients[ingredient] = duplication

    work_units_required = 4 * duplication * final_product * log(log(final_product) + 1) / \
                          (log(final_product) * factory_num)
    time_required = work_units_required / (sigmoid(synth_eff))
    fuel_required = factory_num * time_required / (4 * sqrtmoid(user.industrial_tech))

    products:dict = {final_product: duplication}

    ingredients[0] = round(fuel_required)

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

    duplicate_eff = user.effis[2]

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert factory_num >= 1, '制定生产计划失败:工厂数无效！'
    assert factory_num <= user.factory_num, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    work_units_required = duplication * ingredient * log(log(ingredient) + 1) / factory_num
    time_required = work_units_required / (sigmoid(duplicate_eff))
    fuel_required = factory_num * time_required / (sqrtmoid(user.industrial_tech))

    products: dict = {ingredient: duplication * 2}

    ingredients: dict = {0: round(fuel_required), ingredient: duplication}

    planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=2, factory_num=factory_num,
                      ingredients=ingredients, products=products, time_enacted=starttime, time_required=time_required,
                      work_units_required=work_units_required, enacted=False)
    plan.add(mysql)

    ans = '编号为%s的复制计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！。' % (planID, factory_num,
                                                                fuel_required, smart_interval(time_required),
                                                                )

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

    decorate_eff = user.effis[3]

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert factory_num >= 1, '制定生产计划失败:工厂数无效！'
    assert factory_num <= user.factory_num, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    work_units_required = duplication * (ingredient + 1) * log(log(ingredient + 1) + 1) / \
                          (log(ingredient + 1) * factory_num)
    time_required = work_units_required / \
                    (sigmoid(decorate_eff))
    fuel_required = factory_num * time_required / (2 * sqrtmoid(user.industrial_tech))

    products: dict = {ingredient + 1: duplication}

    ingredients: dict = {0: round(fuel_required), ingredient: duplication}

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

    refine_eff = user.effis[4]

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert is_prime(ingredient), '制定生产计划失败:原料无效，炼油需要质数矿石！'
    assert factory_num >= 1, '制定生产计划失败:工厂数无效！'
    assert factory_num <= user.factory_num, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = getnowtime()
    starttime = nowtime

    work_units_required = duplication * ingredient * log(log(ingredient) + 1) / \
                          (log(ingredient) * factory_num)
    time_required = work_units_required / sigmoid(refine_eff)
    fuel_required = factory_num * time_required / (2 * sqrtmoid(user.refine_tech)) - 1.055

    if ingredient > 64:
        products: dict = {0: duplication * ingredient}
        ingredients: dict = {0: fuel_required, ingredient: duplication}
    else:
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
            starttime: int = int(datetime.strptime(message_list[2], '%Y-%m-%d,%H:%M:%S').timestamp())
    except ValueError:
        return '设置失败:请按照规定格式进行执行！'

    user: User = User.find(qid, mysql)
    plan: Plan = Plan.find(planID, mysql)

    assert plan, '不存在此计划！'
    assert plan.qid == qid, '您无权执行此计划！'

    factory_num = user.factory_num
    idle_factory_num = factory_num - user.busy_factory_num
    ans = ''
    if idle_factory_num < plan.factory_num and starttime != nowtime:
        ans += '提醒：您现在工厂数量不足，请确保计划执行时您有足够空闲工厂。\n'

    setTimeTask(enaction_wrapper, starttime, plan)

    ans = '设置成功！该计划将在指定时间开始执行。编号:%d' % planID

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
    fuel_required = idle_factory_num * time_required / (2 * sqrtmoid(tech))
    ingredients[0] = round(fuel_required)
    success: bool = True
    ans = ""

    for mId, mNum in ingredients.items():
        if mId == 0:
            mName = "燃油",
        else:
            mName = "矿物%s" % mId
        if not mineral[mId] <= mNum:
            ans += "%s不足！您目前有%s，计划%s需要%s单位。\n" % (mName, mineral[mId], plan.planID, mNum)
            success = False

    if not success:
        return ans
    else:
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
        for mid, mnum in enumerate(ingredients):
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
