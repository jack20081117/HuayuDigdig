## 项目架构（软件架构）
|层级|名称|相应模块|
|-|-|-|
|1|网关|api|
|2|分发|script|
|3|分层业务|userServices,mineralDigDig,mineralMarket,stockMarket,debtMarket|
|4|更新业务|updateServices|
|5|数据模型|model|
|6|数据管理|orm|
|7|底层函数|tools|
|8|底层配置|config|
|-|-|以下为非bot内部架构|
|9|数据库|MySQL,SQLite|
|10|日志|logging|
|11|处理器|Python 3.11|

说明：
- 仅在`orm`数据管理层和其上层`model`数据模型层可以调用数据库，其他地方的调用都必须建立模型。