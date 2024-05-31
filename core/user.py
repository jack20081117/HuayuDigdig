import re
from globalConfig import mysql,effisStr,info_msg,player_tax
from model import User

def signup(message_list:list[str],qid:str):
    """
    用户注册
    :param message_list: 注册 学号
    :param qid: 注册者的qq号
    :return: 注册提示信息
    """
    assert len(message_list)==2 and re.match(r'\d{5}',message_list[1]) and len(message_list[1])==5,'注册失败:请注意您的输入格式！'
    schoolID:str=message_list[1]
    assert not User.find(qid,mysql) and not User.findAll(mysql,'schoolID=?',(schoolID,)),'注册失败:您已经注册过，无法重复注册！'
    user=User(
        qid=qid,schoolID=schoolID,money=0,mineral='{}',
        industrial_tech=0.0,extract_tech=0.0,refine_tech=0.0,digable=1,
        factory_num=0,effis='[0.0,0.0,0.0,0.0,0.0,0.0]',mines='[]'
    )#注册新用户
    user.add(mysql)
    ans="注册成功！"
    return ans

def getUserInfo(message_list:list[str],qid:str):
    """
    查询用户个人信息
    :param message_list: 查询
    :param qid: 查询者的qq号
    :return: 查询提示信息
    """
    user:User=User.find(qid,mysql)
    schoolID:str=user.schoolID
    money:int=user.money
    mineral:str=user.mineral
    industrialTech:float=user.industrial_tech
    extractTech:float=user.extract_tech
    refineTech:float=user.refine_tech
    digable:bool=user.digable
    mineral:dict[int,int]=user.mineral
    factory_num:int=user.factory_num
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
    for index in range(6):
        eres+=effisStr[index]+":%s\n" % effis[index]

    mineres:str='' #私有矿井信息
    for mine in mines:
        mineres+='%s,' % mine

    ans:str=info_msg%(qid,schoolID,money,industrialTech,extractTech,refineTech,digable,
                  mres,factory_num,eres,mineres)
    return ans

def pay(message_list:list[str],qid:str):
    """
    :param message_list: 支付 q`QQ号`/`学号` $`金额`
    :param qid: 支付者的qq号
    :return: 支付提示信息
    """
    assert len(message_list)==3,'支付失败:您的支付格式不正确！'
    target=str(message_list[1])
    assert message_list[2].startswith("$"),'支付失败:您的金额格式不正确！'
    try:
        money:int=int(str(message_list[2])[1:])
    except ValueError:
        return "支付失败:您的金额格式不正确！应当为:$`金额`"

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
    tuser.money+=round(money*(1-player_tax))

    user.save(mysql)
    tuser.save(mysql)

    return "支付成功！"