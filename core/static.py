import imgkit, markdown
from datetime import datetime
from globalConfig import imgkit_config

def returnTime(m,q):
    """
    返回当前时间
    """
    return '当前时间为:%s'%datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def getHelp(message_list:list[str],qid:str):
    with open('help_msg.md','r',encoding='utf-8') as help_msg:
        html=markdown.markdown(help_msg.read())
    imgkit.from_string(html,'../go-cqhttp/data/images/help.png',config=imgkit_config,css='./style.css')
    ans='[CQ:image,file=help.png]'
    return ans
