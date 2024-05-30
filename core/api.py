from flask import Flask,request
from script import handle
from update import init
from tools import setCrontab
from globalConfig import mysql
import warnings
import signal
warnings.filterwarnings('ignore')

app=Flask(__name__)

init()

setCrontab(init)

@app.route('/',methods=['POST'])
def post():
    # 这里对消息进行分发，暂时先设置一个简单的分发
    res=request.get_json()
    if res.get('message_type')=='private':  # 说明有好友发送信息过来
        handle(res,group=False)
    elif res.get('message_type')=='group':
        handle(res,group=True)

    return 'OK'

def shutdownApp(signum, frame):
    from globalConfig import connection
    print('HuayuDigDig 后端正在关闭……')
    connection.close()
    raise SystemExit(0)

if mysql:
    signal.signal(signal.SIGINT, shutdownApp)

if __name__=='__main__':
    app.run("127.0.0.1",port=5701,debug=True)  # 注意，这里的端口要和配置文件中的保持一致