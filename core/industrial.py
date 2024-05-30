from datetime import datetime
from tools import setTimeTask,drawtable,send,sigmoid,smart_interval,generateTime,is_prime
from model import User,Plan
from globalConfig import mysql
from numpy import log

def decompose(message_list:list[str],qid:str):
    """
    制定分解计划
    :param message_list: 分解 原矿 目标产物 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """
    assert len(message_list)==5,'制定生产计划失败:请按照规定格式进行计划！'
    user:User=User.find(qid,mysql)
    try:
        ingredient:int=int(message_list[1])
        divide:int=int(message_list[2])
        duplication:int=int(message_list[3])
        factory_num:int=int(message_list[4])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    user_effis:list=list(eval(user.effis))
    decomp_eff=user_effis[0]

    assert duplication>=1,'制定生产计划失败:倍数无效！'
    assert ingredient>1,'制定生产计划失败:原料无效！'
    assert divide>1,'制定生产计划失败:产物无效！'
    assert divide<ingredient,'制定生产计划失败:产物无效！'
    assert factory_num>=1,'制定生产计划失败:工厂数无效！'
    assert factory_num<=user.factory_num,'制定生产计划失败:您没有足够工厂！'
    assert not ingredient%divide,'制定生产计划失败:路径无效！'

    nowtime:int=round(datetime.timestamp(datetime.now()))
    starttime=nowtime


    minor_product = min(divide, int(ingredient / divide))
    time_required = 4 * duplication * minor_product * log(log(ingredient)+1) / \
                    (sigmoid(decomp_eff) * log(minor_product) * factory_num)
    fuel_required = factory_num * time_required / (4 * sigmoid(user.industrial_tech))


    product_dict:dict = {divide:duplication, int(ingredient / divide):duplication}
    products = str(product_dict)

    ingredient_dict:dict = {0: round(fuel_required), ingredient: duplication}
    ingredients = str(ingredient_dict)


    planID:int=max([0]+[plan.tradeID for plan in Plan.findAll(mysql)])+1
    plan:Plan=Plan(planID=planID,qid=qid,schoolID=user.schoolID,jobtype=0,factory_num=factory_num,
                    ingredients=ingredients,products=products,time_enacted=starttime,time_required=time_required,
                    enacted=False)
    plan.add(mysql)

    ans = '编号为%s的分解计划制定成功！按照此计划，%s个工厂将被调用，消耗%s单位燃油和%s时间！产物：%s, %s。'%(planID,factory_num,
                                                                        fuel_required,smart_interval(time_required),
                                                                        divide,ingredient/divide)

    return ans

def synthesize(message_list:list[str],qid:str):
    """
    制定合成计划
    :param message_list: 合成 原料1 原料2 (... 原料n) 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 提示信息
    """
    assert len(message_list) >= 5, '制定生产计划失败:请按照规定格式进行计划！'
    user:User=User.find(qid,mysql)
    ingredient_list = []

    try:
        for i in range(1, len(message_list) - 2):
            ingredient:int=int(message_list[i])
            ingredient_list.append(ingredient)
        duplication: int = int(message_list[-2])
        factory_num: int = int(message_list[-1])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    user_effis:list = list(eval(user.effis))
    synth_eff = user_effis[1]

    assert duplication >= 1, '制定生产计划失败:倍数无效！'
    for ingredient in ingredient_list:
        assert ingredient > 1, '制定生产计划失败:原料无效！'
    assert factory_num >= 1, '制定生产计划失败:工厂数无效！'
    assert factory_num <= user.factory_num, '制定生产计划失败:您没有足够工厂！'

    nowtime: int = round(datetime.timestamp(datetime.now()))
    starttime = nowtime

    ingredient_dict = {}
    final_product = 1
    for ingredient in ingredient_list:
        final_product*= ingredient
        ingredient_dict[ingredient] = duplication

    time_required = 4 * duplication * final_product * log(log(final_product)+1) / \
                    (sigmoid(synth_eff) * log(final_product) * factory_num)
    fuel_required = factory_num * time_required / (4 * sigmoid(user.industrial_tech))


    product_dict:dict = {final_product: duplication}
    products = str(product_dict)

    ingredient_dict[0] = round(fuel_required)
    ingredients = str(ingredient_dict)

    planID: int = max([0] + [plan.tradeID for plan in Plan.findAll(mysql)]) + 1
    plan: Plan = Plan(tradeID=planID, qid=qid, schoolID=user.schoolID, jobtype=1, factory_num=factory_num,
                      ingredients=ingredients, products=products, time_enacted=starttime, time_required=time_required,
                      enacted=False)
    plan.add(mysql)

    ans = '编号为%s的合成计划制定成功！按照此计划，%s个工厂将被调用，消耗%s单位燃油和%s时间！产物：%s。'%(planID,factory_num,
                                                         fuel_required,smart_interval(time_required),final_product)

    return ans

def duplicate(message_list:list[str],qid:str):
    """
    制定复制计划
    :param message_list: 复制 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """
    assert len(message_list)==4,'制定生产计划失败:请按照规定格式进行计划！'
    user:User=User.find(qid,mysql)
    try:
        ingredient:int=int(message_list[1])
        duplication:int=int(message_list[2])
        factory_num:int=int(message_list[3])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    user_effis:list=list(eval(user.effis))
    duplicate_eff=user_effis[2]

    assert duplication>=1,'制定生产计划失败:倍数无效！'
    assert ingredient>1,'制定生产计划失败:原料无效！'
    assert factory_num>=1,'制定生产计划失败:工厂数无效！'
    assert factory_num<=user.factory_num,'制定生产计划失败:您没有足够工厂！'

    nowtime:int=round(datetime.timestamp(datetime.now()))
    starttime=nowtime

    time_required = duplication * ingredient * log(log(ingredient)+1) / \
                    (sigmoid(duplicate_eff) * factory_num)
    fuel_required = factory_num * time_required / (sigmoid(user.industrial_tech))

    product_dict:dict = {ingredient: duplication*2}
    products = str(product_dict)

    ingredient_dict:dict = {0: round(fuel_required), ingredient: duplication}
    ingredients = str(ingredient_dict)

    planID:int=max([0]+[plan.tradeID for plan in Plan.findAll(mysql)])+1
    plan:Plan=Plan(planID=planID,qid=qid,schoolID=user.schoolID,jobtype=0,factory_num=factory_num,
                    ingredients=ingredients,products=products,time_enacted=starttime,time_required=time_required,
                    enacted=False)
    plan.add(mysql)

    ans = '编号为%s的复制计划制定成功！按照此计划，%s个工厂将被调用，消耗%s单位燃油和%s时间！。'%(planID,factory_num,
                                                                        fuel_required,smart_interval(time_required),
                                                                        )

    return ans

def decorate(message_list:list[str],qid:str):
    """
    制定修饰计划
    :param message_list: 修饰 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """

    assert len(message_list)==4,'制定生产计划失败:请按照规定格式进行计划！'
    user:User=User.find(qid,mysql)
    try:
        ingredient:int=int(message_list[1])
        duplication:int=int(message_list[2])
        factory_num:int=int(message_list[3])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    user_effis:list=list(eval(user.effis))
    decorate_eff=user_effis[3]

    assert duplication>=1,'制定生产计划失败:倍数无效！'
    assert ingredient>1,'制定生产计划失败:原料无效！'
    assert factory_num>=1,'制定生产计划失败:工厂数无效！'
    assert factory_num<=user.factory_num,'制定生产计划失败:您没有足够工厂！'

    nowtime:int=round(datetime.timestamp(datetime.now()))
    starttime=nowtime

    time_required = duplication * (ingredient + 1) * log(log(ingredient + 1)+1) / \
                    (sigmoid(decorate_eff) * log(ingredient + 1) * factory_num)
    fuel_required = factory_num * time_required / (2 * sigmoid(user.industrial_tech))

    product_dict:dict = {ingredient+1:duplication}
    products = str(product_dict)

    ingredient_dict:dict = {0: round(fuel_required), ingredient: duplication}
    ingredients = str(ingredient_dict)


    planID:int=max([0]+[plan.tradeID for plan in Plan.findAll(mysql)])+1
    plan:Plan=Plan(planID=planID,qid=qid,schoolID=user.schoolID,jobtype=0,factory_num=factory_num,
                    ingredients=ingredients,products=products,time_enacted=starttime,time_required=time_required,
                    enacted=False)
    plan.add(mysql)

    ans = '编号为%s的修饰计划制定成功！按照此计划，%s个工厂将被调用，消耗%s单位燃油和%s时间！产物：%s。'%(planID,factory_num,
                                                                        fuel_required,smart_interval(time_required),
                                                                        ingredient+1)

    return ans


def refine(message_list:list[str],qid:str):
    """
    制定炼化计划
    :param message_list: 炼化 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """

    assert len(message_list)==4,'制定生产计划失败:请按照规定格式进行计划！'
    user:User=User.find(qid,mysql)
    try:
        ingredient:int=int(message_list[1])
        duplication:int=int(message_list[2])
        factory_num:int=int(message_list[3])
    except ValueError:
        return '制定生产计划失败:请按照规定格式进行计划！'

    user_effis:list=list(eval(user.effis))
    decorate_eff=user_effis[3]

    assert duplication>=1,'制定生产计划失败:倍数无效！'
    assert ingredient>1,'制定生产计划失败:原料无效！'
    assert is_prime(ingredient),'制定生产计划失败:原料无效，炼油需要质数矿石！'
    assert factory_num>=1,'制定生产计划失败:工厂数无效！'
    assert factory_num<=user.factory_num,'制定生产计划失败:您没有足够工厂！'

    nowtime:int=round(datetime.timestamp(datetime.now()))
    starttime=nowtime

    time_required = duplication * (ingredient) * log(log(ingredient)+1) / \
                    (sigmoid(decorate_eff) * log(ingredient) * factory_num)
    fuel_required = factory_num * time_required / (sigmoid(user.refine_tech))

    product_dict:dict = {0: duplication*ingredient}
    products = str(product_dict)

    ingredient_dict:dict = {0: round(fuel_required), ingredient: duplication}
    ingredients = str(ingredient_dict)


    planID:int=max([0]+[plan.tradeID for plan in Plan.findAll(mysql)])+1
    plan:Plan=Plan(planID=planID,qid=qid,schoolID=user.schoolID,jobtype=0,factory_num=factory_num,
                    ingredients=ingredients,products=products,time_enacted=starttime,time_required=time_required,
                    enacted=False)
    plan.add(mysql)

    ans = '编号为%s的炼化计划制定成功！按照此计划，%s个工厂将被调用，消耗%s单位燃油和%s时间！'%(planID,factory_num,
                                                                        fuel_required,smart_interval(time_required),
                                                                        )

    return ans

def enactPlan(message_list:list[str],qid:str):
    """
    制定炼化计划
    :param message_list: 炼化 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """

    return ans


def cancelPlan(message_list: list[str], qid: str):
    """
    制定炼化计划
    :param message_list: 炼化 原料 份数 调拨工厂数
    :param qid: 制定者的qq号
    :return: 制定提示信息
    """

    return ans