from model import *
from config import *
from tools import send
import userServices
import mineralDigdig
import mineralMarket
import stockMarket

def dealWithRequest(funcStr:str,message_list:list[str],qid:str):
    if funcStr in commands:
        ans=commands[funcStr](message_list,qid)
    else:
        ans="未知命令:请输入'帮助'以获取帮助信息！"
    return ans

def handle(res,group):
    ans:str=''  #回复给用户的内容
    if group:#是群发消息
        message:str=res.get("raw_message")
        qid:str=res.get('sender').get('user_id')  #发消息者的qq号
        gid:str=res.get('group_id')  #群的qq号
        if gid not in group_ids:
            return None
        if "[CQ:at,qq=2470751924]" not in message:#必须在自己被at的情况下才能作出回复
            return None

        message_list:list=message.split(' ')
        funcStr:str=message_list[1]
        message_list.pop(0)  #忽略at本身

        try:
            ans=dealWithRequest(funcStr,message_list,qid)
            send(gid,ans,group=True)
        except AssertionError as err:
            send(gid,err,group=True)

    else:
        message:str=res.get("raw_message")
        qid:str=res.get('sender').get('user_id')
        message_list:list=message.split(' ')
        funcStr:str=message_list[0]

        try:
            ans=dealWithRequest(funcStr,message_list,qid)
            send(qid,ans,group=False)
        except AssertionError as err:
            send(qid,err,group=False)