from datetime import datetime
from matplotlib import pyplot as plt
from apscheduler.schedulers.background import BackgroundScheduler as bgsc


plt.rcParams['font.family']=['Microsoft YaHei']


def drawtable(data:list,filename:str):
    """
    将市场信息绘制成表格
    :param data: 要绘制的表格数据
    :param filename: 存储图片地址
    :return:
    """
    fig,ax=plt.subplots()
    table=ax.table(cellText=data,loc='center')
    table.auto_set_font_size(False)
    #table.set_fontsize(10)

    for key,cell in table.get_celld().items():
        cell.set_text_props(fontsize=8,ha='center',va='center')

    table.auto_set_column_width(col=list(range(len(data[0]))))

    ax.axis('off')
    plt.savefig('../go-cqhttp/data/images/%s'%filename)

def setInterval(func:callable,interval:int,*args,**kwargs):
    """
    定时触发任务
    :param func: 要触发的任务（函数）
    :param interval: 触发间隔（s）
    :param args: 任务参数
    """
    scheduler=bgsc()
    scheduler.add_job(func,"interval",args=args,kwargs=kwargs,seconds=interval)
    scheduler.start()

def setCrontab(func:callable,*args,**kwargs):
    """
    定时触发任务
    :param func: 要触发的任务（函数）
    :param args: 任务参数
    """
    scheduler=bgsc()
    scheduler.add_job(func,'cron',minute=0,args=args,kwargs=kwargs)
    scheduler.start()

def setTimeTask(func:callable,runtime:int,*args,**kwargs):
    """
    定时触发任务
    :param func: 要触发的任务（函数）
    :param runtime: 触发时间timestamps
    :param args: 任务参数
    """
    scheduler=bgsc()
    scheduler.add_job(func,"date",args=args,kwargs=kwargs,run_date=datetime.fromtimestamp(float(runtime)))
    scheduler.start()
  