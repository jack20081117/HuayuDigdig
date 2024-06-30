from staticFunctions import setTimeTask,drawtable,isPrime,\
    getnowtime, generateTimeStamp,generateTimeStr,generateTime,smartInterval,\
    expenseCalculator,timeFuelCalculator,WURCalculator,expr2modifier
from model import User, Plan
from update import updateEfficiency, updateEnaction
from globalConfig import mysql,effisValueDict, fuelFactorDict, factoryWUR, robotWUR, storageWUR
import numpy as np


class IndustrialService(object):
    def __init__(self):
        pass

    @staticmethod
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
        assert 1e7>ingredient>1,'制定生产计划失败:原料无效！'
        assert divide>1,'制定生产计划失败:产物无效！'
        assert divide<ingredient,'制定生产计划失败:产物无效！'
        assert factoryNum>=1,'制定生产计划失败:工厂数无效！'
        assert factoryNum<=user.factoryNum,'制定生产计划失败:您没有足够工厂！'
        assert not ingredient%divide,'制定生产计划失败:路径无效！'

        nowtime: int = getnowtime()

        minorProduct = min(divide, ingredient // divide)

        workUnitsRequired, timeRequired, fuelRequired = \
            expenseCalculator(4,duplication,minorProduct,ingredient,[ingredient, divide, ingredient // divide],user.expr,
                              user.tech['industrial'],decomp_eff,factoryNum,fuelFactorDict[0])

        products:dict = {divide:duplication, (ingredient // divide):duplication}#生成产品
        if divide==ingredient//divide:
            products[divide]*=2

        ingredients:dict = {0: fuelRequired, ingredient: duplication}#所需原料

        planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
        plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=0, factoryNum=factoryNum,
                        ingredients=ingredients, products=products, timeEnacted=nowtime, timeRequired=timeRequired,
                        workUnitsRequired=workUnitsRequired, enacted=False)
        plan.add(mysql)

        ans = '编号为%s的分解计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！产物：%s, %s。' % (planID, factoryNum,
                                                                            fuelRequired, smartInterval(timeRequired),
                                                                            divide, ingredient // divide)

        return ans

    @staticmethod
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
            assert 1e7 > ingredient > 1, '制定生产计划失败:原料无效！'
        assert factoryNum >= 1, '制定生产计划失败:工厂数无效！'
        assert factoryNum <= user.factoryNum, '制定生产计划失败:您没有足够工厂！'

        nowtime: int = getnowtime()

        ingredients = {}#所需原料
        finalProduct = 1
        deductableWUR = 0
        for ingredient in ingredientList:
            finalProduct *= ingredient
            ingredients.setdefault(ingredient,0)
            ingredients[ingredient] += duplication
            if not isPrime(ingredient):
                deductableWUR += WURCalculator(4, duplication, ingredient, ingredient, [ingredient], user.expr)

        #workUnitsRequired, timeRequired, fuelRequired = \
        #    expenseCalculator(4,duplication,finalProduct,finalProduct,user.tech['industrial'],synth_eff,factoryNum,fuelFactorDict[1])

        workUnitsRequired = WURCalculator(2.5, duplication, finalProduct, (len(ingredientList)-1)*finalProduct, ingredientList+[finalProduct], user.expr)
        workUnitsRequired -= deductableWUR

        timeRequired, fuelRequired = \
            timeFuelCalculator(workUnitsRequired,
                               synth_eff,
                               user.tech['industrial'],
                               factoryNum,
                               fuelFactorDict[1])

        products:dict = {finalProduct: duplication} #生成产品

        ingredients[0] = fuelRequired

        planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
        plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=1, factoryNum=factoryNum,
                        ingredients=ingredients, products=products, timeEnacted=nowtime, timeRequired=timeRequired,
                        workUnitsRequired=workUnitsRequired, enacted=False)
        plan.add(mysql)

        ans = '编号为%s的合成计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！产物：%s。' % (planID, factoryNum,
                                                                        fuelRequired, smartInterval(timeRequired),
                                                                        finalProduct)

        return ans

    @staticmethod
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
        assert 1e7 > ingredient > 1, '制定生产计划失败:原料无效！'
        assert factoryNum >= 1, '制定生产计划失败:工厂数无效！'
        assert factoryNum <= user.factoryNum, '制定生产计划失败:您没有足够工厂！'

        nowtime: int = getnowtime()

        workUnitsRequired, timeRequired, fuelRequired = \
            expenseCalculator(1,duplication,ingredient+32,ingredient+32,[ingredient],user.expr,
                            user.tech['industrial'],duplicate_eff,factoryNum,fuelFactorDict[2],useLogDivisor=False)

        products: dict = {ingredient: duplication * 2}#生成成品

        ingredients: dict = {0: fuelRequired, ingredient: duplication}#所需原料

        planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
        plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=2, factoryNum=factoryNum,
                        ingredients=ingredients, products=products, timeEnacted=nowtime, timeRequired=timeRequired,
                        workUnitsRequired=workUnitsRequired, enacted=False)
        plan.add(mysql)

        ans = '编号为%s的复制计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！' % (planID, factoryNum,
                                                                    fuelRequired, smartInterval(timeRequired))

        return ans

    @staticmethod
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
        assert 1e7 > ingredient > 1, '制定生产计划失败:原料无效！'
        assert factoryNum >= 1, '制定生产计划失败:工厂数无效！'
        assert factoryNum <= user.factoryNum, '制定生产计划失败:您没有足够工厂！'

        nowtime: int = getnowtime()

        workUnitsRequired, timeRequired, fuelRequired = \
            expenseCalculator(1,duplication,ingredient+1,ingredient+1,[ingredient,ingredient+1],user.expr,
                              user.tech['industrial'],decorate_eff,factoryNum,fuelFactorDict[3])

        products: dict = {ingredient + 1: duplication}#生成产品

        ingredients: dict = {0: fuelRequired, ingredient: duplication}#所需原料

        planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
        plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=3, factoryNum=factoryNum,
                        ingredients=ingredients, products=products, timeEnacted=nowtime, timeRequired=timeRequired,
                        workUnitsRequired=workUnitsRequired, enacted=False)
        plan.add(mysql)

        ans = '编号为%s的修饰计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！产物：%s。' % (planID, factoryNum,
                                                                        fuelRequired, smartInterval(timeRequired),
                                                                        ingredient + 1)

        return ans

    @staticmethod
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
        assert 1e7 > ingredient > 1, '制定生产计划失败:原料无效！'
        assert isPrime(ingredient), '制定生产计划失败:原料无效，炼油需要质数矿石！'
        assert factoryNum >= 1, '制定生产计划失败:工厂数无效！'
        assert factoryNum <= user.factoryNum, '制定生产计划失败:您没有足够工厂！'

        nowtime: int = getnowtime()
        workUnitsRequired, timeRequired, fuelRequired = \
            expenseCalculator(2,duplication,ingredient,ingredient,[ingredient],user.expr,
                              user.tech['refine'],refine_eff,factoryNum,fuelFactorDict[4])

        fuelRequired -= 1 # 消除负收益是否采用对数平均

        products: dict = {0: duplication * ingredient}
        ingredients: dict = {0: fuelRequired, ingredient: duplication}

        ans = ''
        if ingredient in [3, 7, 31, 127, 8191]: #梅森素数获得双倍燃油
            products[0]*=2
        if ingredient <= 128:
            ans+= '由于您的矿石较小，您不必预先准备燃油来执行该计划！\n'

        #if ingredient > 64:
        #    products: dict = {0: duplication * ingredient}
        #    ingredients: dict = {0: fuelRequired, ingredient: duplication}
        #else:#对较小的质数，可以使用炼化出的燃油重炼化，防止炼化燃油无法进行
        #    products: dict = {0: duplication * (ingredient - fuelRequired)}
        #    ingredients: dict = {0: 0, ingredient: duplication}

        planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
        plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=4, factoryNum=factoryNum,
                        ingredients=ingredients, products=products, timeEnacted=nowtime, timeRequired=timeRequired,
                        workUnitsRequired=workUnitsRequired, enacted=False)
        plan.add(mysql)

        ans += '编号为%s的炼化计划制定成功！按照此计划，%s个工厂将被调用，预估消耗%s单位燃油和%s时间！' % (planID, factoryNum,
                                                                fuelRequired, smartInterval(timeRequired))
        return ans

    @staticmethod
    def build(messageList: list[str], qid: str):
        """
        制定工厂建造计划
        :param messageList: 建造工厂 建材 调拨工厂数
        :param qid: 制定者的qq号
        :return: 提示信息
        """

        assert len(messageList) == 3, '制定建造计划失败:请按照规定格式进行计划！'
        user: User = User.find(qid, mysql)
        try:
            material:int = int(messageList[1])
            factoryNum: int = int(messageList[-1])
        except ValueError:
            return '制定建造计划失败:请按照规定格式进行计划！'

        assert factoryNum >= 1, '制定建造计划失败:工厂数无效！'
        assert factoryNum <= user.factoryNum, '制定建造计划失败:您没有足够工厂！'
        assert material in [2,4,6,8,10,12], '制定建造计划失败：您无法使用这种建材！'

        nowtime:int=getnowtime()

        buildeff = user.effis[5]

        materialDict = {2:25, 4:12, 6:9, 8:8, 10:7, 12:7}
        workUnitsRequired = factoryWUR * expr2modifier(material)
        timeRequired, fuelRequired = timeFuelCalculator(factoryWUR,buildeff,0,factoryNum,fuelFactorDict[5])
        ingredients = {0:fuelRequired, material:materialDict[material]}

        planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
        plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=5, factoryNum=factoryNum,
                        ingredients=ingredients, products={'factory':1}, timeEnacted=nowtime, timeRequired=timeRequired,
                        workUnitsRequired=workUnitsRequired, enacted=False)
        plan.add(mysql)

        ans = '编号为%s的建造计划制定成功！按照此计划，%s个工厂将被调用，预估消耗%s单位燃油和%s时间！' % (planID, factoryNum,
                                                                    fuelRequired, smartInterval(timeRequired),
                                                                    )

        return ans

    @staticmethod
    def buildRobot(messageList: list[str], qid: str):
        """
        制定机器人建造计划
        :param messageList: 建造机器人 建材 调拨工厂数
        :param qid: 制定者的qq号
        :return: 提示信息
        """

        assert len(messageList) == 3, '制定建造计划失败:请按照规定格式进行计划！'
        user: User = User.find(qid, mysql)
        try:
            material: int = int(messageList[1])
            factoryNum: int = int(messageList[-1])
        except ValueError:
            return '制定建造计划失败:请按照规定格式进行计划！'

        assert factoryNum >= 1, '制定建造计划失败:工厂数无效！'
        assert factoryNum <= user.factoryNum, '制定建造计划失败:您没有足够工厂！'
        assert material in [3, 6, 9, 12, 15, 18], '制定建造计划失败：您无法使用这种建材！'

        nowtime: int = getnowtime()

        buildeff = user.effis[5]

        materialDict = {3: 9, 6: 7, 9: 4, 12: 4, 15: 3, 18: 3}
        workUnitsRequired = robotWUR * expr2modifier(material)
        timeRequired, fuelRequired = timeFuelCalculator(robotWUR, buildeff, 0, factoryNum, fuelFactorDict[5])
        ingredients = {0: fuelRequired, material: materialDict[material]}

        planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
        plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=5, factoryNum=factoryNum,
                        ingredients=ingredients, products={'robot':1}, timeEnacted=nowtime, timeRequired=timeRequired,
                        workUnitsRequired=workUnitsRequired, enacted=False)
        plan.add(mysql)

        ans = '编号为%s的建造计划制定成功！按照此计划，%s个工厂将被调用，预估消耗%s单位燃油和%s时间！' % (planID, factoryNum,
                                                                fuelRequired, smartInterval(timeRequired),
                                                                )

        return ans

    @staticmethod
    def buildStorage(messageList: list[str], qid: str):
        """
        制定仓库建造计划
        :param messageList: 建造仓库 建材 调拨工厂数
        :param qid: 制定者的qq号
        :return: 提示信息
        """

        assert len(messageList) == 3, '制定建造计划失败:请按照规定格式进行计划！'
        user: User = User.find(qid, mysql)
        try:
            material: int = int(messageList[1])
            factoryNum: int = int(messageList[-1])
        except ValueError:
            return '制定建造计划失败:请按照规定格式进行计划！'

        assert factoryNum >= 1, '制定建造计划失败:工厂数无效！'
        assert factoryNum <= user.factoryNum, '制定建造计划失败:您没有足够工厂！'
        assert material in [4, 9, 16, 25, 36, 49], '制定建造计划失败：您无法使用这种建材！'

        nowtime: int = getnowtime()

        buildeff = user.effis[5]

        materialDict = {4: 12, 9: 6, 16: 4, 25: 3, 36: 2, 49: 2}
        workUnitsRequired = robotWUR * expr2modifier(material)
        timeRequired, fuelRequired = timeFuelCalculator(storageWUR, buildeff, 0, factoryNum, fuelFactorDict[5])
        ingredients = {0: fuelRequired, material: materialDict[material]}

        planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
        plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=5, factoryNum=factoryNum,
                        ingredients=ingredients, products={'storage':1}, timeEnacted=nowtime, timeRequired=timeRequired,
                        workUnitsRequired=workUnitsRequired, enacted=False)
        plan.add(mysql)

        ans = '编号为%s的建造计划制定成功！按照此计划，%s个工厂将被调用，预估消耗%s单位燃油和%s时间！' % (planID, factoryNum,
                                                                fuelRequired, smartInterval(timeRequired),
                                                                )

        return ans


    @staticmethod
    def research(messageList:list[str], qid: str):
        """
        制定科研计划
        :param messageList: 研究 科技名 试剂1 试剂2 (... 试剂n) 是否接续主线(1/0) 调拨工厂数
        :param qid: 制定者的qq号
        :return: 提示信息
        """
        assert len(messageList) >= 5, '制定科研计划失败:请按照规定格式进行计划！'
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
            assert 1e6 > ingredient > 1, '制定科研计划失败:试剂无效！'
        assert factoryNum >= 1, '制定科研计划失败:工厂数无效！'
        assert factoryNum <= user.factoryNum, '制定科研计划失败:您没有足够工厂！'

        nowtime: int = getnowtime()

        techName = techNameDict[techName]  #将中文输入的techname转换成系统命名
        techCards = user.techCards[techName]
        # techCard是一个字典，分别储存了用户对每一类科技的探索。每一个value都是一个二维list，代表着一行行可行的科技路径
        # 玩家的最终科技水平是由user.techCards[techName][0]的长度决定的，这个科技线被称为主线

        ingredients = {}#所需原料
        ans = ''
        techPath = ingredientList


        if continuation or len(techCards) == 0: #如果第一次研发，或是接续研发
            for ingredient in ingredientList:
                ingredients.setdefault(ingredient, 0)
                ingredients[ingredient] += 1
            if techCards:
                techPath = techCards[0] + ingredientList
            work_modifier = (np.log(np.array(techPath)).mean() / 10 + 1)
            # 原料的对数的平均数会影响研发时间。如果使用昂贵材料，那么成功概率会增加，但是时间也会略微延长。
            workUnitsRequired = (1200 + 600 * len(ingredientList)) * work_modifier
            # 接序研究的时间主要考虑接续长度
            timeRequired, fuelRequired = timeFuelCalculator(workUnitsRequired, techEff, 0, factoryNum, fuelFactorDict[6])
        else: #如果是fork或者另起炉灶
            commonSequenceLengths = [] #自动匹配相似度最高的路径节约时间成本
            for i in range(len(techCards)):
                commonSequenceLength = 0
                for j in range(min(len(techCards[i]),len(ingredientList))):
                    if techCards[i][j] == ingredientList[j]: #匹配相似度
                        commonSequenceLength += 1
                        continue
                    else:
                        commonSequenceLengths.append(commonSequenceLength) #记载相似度
                        break
            bestMatch = np.argmax(np.array(commonSequenceLengths)) #最相关已知科技路径
            matchAmount = commonSequenceLengths[bestMatch] #相关度
            assert matchAmount < len(ingredientList), '您当前输入的序列是您已知的技术路径的子序列，不必重复研发！'
            if matchAmount > 0:
                ans+='您当前制定的科研计划与您已知的第%s科研路径在前%s级重合，将自动接续该技术路径进行研究！\n' % (bestMatch, matchAmount)
            else:
                ans+='您将制定一个全新的科研计划，与您已知的科研路径无重合之处！\n'
            divergentPath = ingredientList[matchAmount:]
            work_modifier = (np.log(np.array(techPath)).mean() / 10 + 1)
            workUnitsRequired = (1200 + 600 * len(divergentPath)) * work_modifier
            timeRequired, fuelRequired = timeFuelCalculator(workUnitsRequired, techEff, 0, factoryNum, fuelFactorDict[6])
            for ingredient in divergentPath:
                ingredients.setdefault(ingredient, 0)
                ingredients[ingredient] += 1

        products:dict = {}#生成产品

        ingredients[0] = fuelRequired

        planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
        plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=6, factoryNum=factoryNum,
                        ingredients=ingredients, products=products, timeEnacted=nowtime, timeRequired=timeRequired,
                        workUnitsRequired=workUnitsRequired, techName=techName,
                        techPath=techPath, enacted=False)
        plan.add(mysql)


        ans += '编号为%s的科研计划制定成功！按照此计划，%s个工厂将被调用，预计消耗%s单位燃油和%s时间！' % (planID, factoryNum,
                                                                        fuelRequired, smartInterval(timeRequired),
                                                                        )
        return ans

    @staticmethod
    def discover(messageList: list[str], qid: str):
        """
        制定勘探计划
        :param messageList: 勘探 预期规模 调拨工厂数
        :param qid: 制定者的qq号
        :return: 提示信息
        """
        assert len(messageList) == 3, '制定勘探计划失败:请按照规定格式进行计划！'
        user: User = User.find(qid, mysql)
        try:
            scale: int = int(messageList[1])
            factoryNum: int = int(messageList[-1])
        except ValueError:
            return '制定勘探计划失败:请按照规定格式进行计划！'
        assert factoryNum >= 1, '制定勘探计划失败:工厂数无效！'
        assert factoryNum <= user.factoryNum, '制定勘探计划失败:您没有足够工厂！'
        assert 100<scale<100000, "制定勘探计划失败：预期规模太大或者太小！"

        nowtime:int=getnowtime()

        discoveff = user.effis[7]

        workUnitsRequired = 10000 + np.sqrt(scale)*300
        timeRequired, fuelRequired = timeFuelCalculator(workUnitsRequired, discoveff, 0, factoryNum, fuelFactorDict[7])
        ingredients = {0: fuelRequired}

        planID: int = max([0] + [plan.planID for plan in Plan.findAll(mysql)]) + 1
        plan: Plan = Plan(planID=planID, qid=qid, schoolID=user.schoolID, jobtype=7, factoryNum=factoryNum,
                        ingredients=ingredients, products={}, timeEnacted=nowtime, timeRequired=timeRequired,
                        workUnitsRequired=workUnitsRequired, enacted=False)
        plan.add(mysql)

        ans = '编号为%s的勘探计划制定成功！按照此计划，%s个工厂将被调用，预估消耗%s单位燃油和%s时间！' % (planID, factoryNum,
                                                                fuelRequired, smartInterval(timeRequired),
                                                                )

        return ans

    @staticmethod
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
                starttime: int = nowtime + 3
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

        plan.timeEnacted=starttime
        plan.timeRequired=0
        plan.save(mysql)

        setTimeTask(updateEnaction, starttime, plan)

        ans += '设置成功！该计划将在指定时间开始执行。编号:%d' % planID

        return ans

    @staticmethod
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
                    mineral[mid] += round(mnum * (nowtime - plan.timeEnacted) / plan.timeRequired)  # 燃油按剩余时间比例返还
                else:
                    mineral[mid] += mnum
            if plan.jobtype == 5: #建工任务特判建筑许可证
                user.misc[2] -= 1
                user.misc.setdefault(1,0)
                user.misc[1] += 1

            enactedPlanTypes = user.enactedPlanTypes  # 取消当前门类的生产状态
            enactedPlanTypes[plan.jobtype] -= 1
            user.enactedPlanTypes = enactedPlanTypes

            user.busyFactoryNum -= plan.factoryNum  # 释放被占用的工厂

            ans = "计划取消成功，矿石以及部分未消耗燃料已经返还到您的账户。"

        plan.remove(mysql)
        user.save(mysql)

        return ans

    @staticmethod
    def showPlan(messageList:list[str],qid:str):
        """
        查看计划
        :param messageList: 计划
        :param qid: 查看者的qq号
        :return: 自己拥有的生产计划
        """
        plans:list[Plan]=Plan.findAll(mysql,where='qid=?',args=(qid,))
        planData=[["计划编号","生产类型","调拨工厂数","原料","产品","用时","状态","结束时间"]]
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
                elif pId=='factory':
                    products.append('工厂:1个')
                elif pId=='robot':
                    products.append('采矿机器人:1个')
                elif pId=='storage':
                    products.append('仓库:1片')
                else:
                    products.append('矿石%s:%s个'%(pId,pNum))
            planData.append([
                plan.planID,
                effisValueDict[plan.jobtype],
                plan.factoryNum,
                ','.join(ingredients),
                ','.join(products),
                smartInterval(plan.timeRequired),
                '已开工' if plan.enacted else '未开工',
                generateTimeStr(plan.timeEnacted+plan.timeRequired) if plan.enacted else '无'
            ])
        drawtable(planData,'plan.png')

        ans='[CQ:image,file=plan.png]'
        return ans

    @staticmethod
    def transferFactory(messageList:list[str],qid:str):
        """
        :param messageList: 转让工厂 数量 转让对象(学号/q+QQ号）
        :param qid: 转让者的qq号
        :return: 转让提示信息
        """
        assert len(messageList) == 3, '转让工厂失败:您的转让格式不正确！'
        nowtime=getnowtime()
        try:
            transferNum:int=int(messageList[1])
            newOwnerID:str=str(messageList[2])
        except ValueError:
            return '转让工厂失败:您的输入格式不正确！'

        user=User.find(qid,mysql)
        assert transferNum < user.factoryNum,'转让工厂失败:您不能转让自带的一个工厂！'
        assert transferNum <= user.factoryNum - user.busyFactoryNum, '转让工厂失败:您不能转让正在工作中的工厂！'

        if newOwnerID.startswith("q"):
            # 通过QQ号查找对方
            tqid: str = newOwnerID[1:]
            newOwner: User = User.find(tqid, mysql)
            assert newOwner, "转让工厂失败:QQ号为%s的用户未注册！" % tqid
        else:
            tschoolID: str = newOwnerID
            # 通过学号查找
            assert User.findAll(mysql, 'schoolID=?', (tschoolID,)), "转让工厂失败:学号为%s的用户未注册！" % tschoolID
            newOwner: User = User.findAll(mysql, 'schoolID=?', (tschoolID,))[0]

        #assert newCreditor.qid != debt.debitor, "转让债权失败:不能转让给债务人！"
        newOwner.factoryNum += transferNum
        user.factoryNum -= transferNum

        user.save(mysql)
        newOwner.save(mysql)
        ans = '转让工厂成功！%s个工厂已成功转让给%s，您还有%s个工厂' % (transferNum, newOwnerID, user.factoryNum)

        return ans