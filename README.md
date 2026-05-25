# RAG增强版AI助手

项目简介
这是一个基于Qwen3模型和ReAct框架的智能助手系统，支持天气查询、热搜获取、科学计算和时间查询等功能。系统具备动态RAG优化、会话记忆机制和县级城市智能映射等特性。

## 功能特性
### 核心功能
1. 天气查询 - 实时温度、湿度、风力信息

2. 天气预报 - 未来3-7天天气预报

3. 热搜查询 - 支持30+平台（微博、抖音、B站、知乎等）

4. 科学计算器 - 支持复杂表达式计算

5. 时间查询 - 当前日期和时间

### 高级特性
1. 县级城市智能映射 - 自动将县级城市映射到地级市

2. 会话记忆 - 记住对话历史

3. 失败重试机制 - 工具调用失败自动重试

4. 动态RAG优化 - 根据置信度调整检索策略

## 系统架构
text
┌─────────────────────────────────────────────────────────┐
│                    EnhancedInteractiveMenu              │
│                      (交互式菜单)                         │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   RAGEnhancedReActAgent                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │TaskClassifier│  │ToolSelector │  │ ConversationMemory│  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐│
│  │                   DynamicRAG                         ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                      工具层                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │WeatherTool│ │HotNewsTool│ │Calculator│ │ CurrentTime│ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                    数据层                                 │
│  ┌──────────────────┐  ┌────────────────────────────┐   │
│  │  CityMapper      │  │  city_mapping.json         │   │
│  │  (城市映射管理)    │  │  (映射数据存储)              │   │
│  └──────────────────┘  └────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
## 安装与配置

1. 环境要求
Python 3.8+

pip 包管理器

2. 安装依赖
bash
pip install requests langchain langchain-openai fastapi numpy

4. API密钥配置
在 new_agent.py 中修改以下配置：

python
CONFIG = {
    "QWEN3_API_KEY": "你的Qwen3 API密钥",
    "QWEN3_BASE_URL": "https://api.siliconflow.cn/v1",
    "QWEN3_MODEL": "Qwen/Qwen3-7B-Instruct",
    "WEATHER_API_KEY": "你的心知天气API密钥",
    # ... 其他配置
}
获取API密钥：

Qwen3模型：访问 SiliconFlow 注册获取

天气API：访问 心知天气 注册获取

使用方法
启动程序
bash
python new_agent.py

交互式菜单
text
============================================================
 RAG增强版AI助手 - 功能菜单（Qwen3模型）
============================================================
1️⃣  天气查询（实时温度+湿度+风力）
2️⃣  天气预报（未来3-7天）
3️⃣  热搜查询（30+平台）
4️⃣  科学计算器
5️⃣  当前时间
6️⃣  AI对话模式
7️⃣  查看会话记忆
8️⃣  清空会话记忆
9️⃣  查看城市映射统计
0️⃣  退出
============================================================
使用示例
天气查询
<img width="617" height="678" alt="image" src="https://github.com/user-attachments/assets/a2a470bb-5067-4456-8535-91815c492ab1" />

热搜查询
<img width="1165" height="675" alt="image" src="https://github.com/user-attachments/assets/bc0ccd31-2400-4ef6-adde-beb987b3f3b8" />

AI对话模式
<img width="640" height="910" alt="image" src="https://github.com/user-attachments/assets/7a0d4171-4df9-4414-a5e8-058088e84f21" />

城市映射管理

管理工具使用

bash
# 查看所有县级城市
python manage_cities.py list

# 搜索城市
python manage_cities.py search 双流

# 添加映射
python manage_cities.py add 义乌 金华 浙江省

# 删除映射
python manage_cities.py remove 义乌

# 查看统计信息
python manage_cities.py stats

# 批量导入（CSV格式）
python manage_cities.py import cities.csv

# 导出映射
python manage_cities.py export cities.csv

# 备份映射数据
python manage_cities.py backup
CSV导入格式
csv
县级城市,地级市,省份
义乌,金华,浙江省
昆山,苏州,江苏省
双流,成都,四川省
支持的热搜平台
平台	平台	平台	平台
微博	知乎	百度	抖音
快手	B站	A站	头条
腾讯新闻	网易新闻	新浪新闻	澎湃新闻
豆瓣电影	豆瓣小组	虎扑	NGA
V2EX	酷安	36氪	少数派
IT之家	CSDN	掘金	简书
果壳	虎嗅	爱范儿	贴吧
吾爱破解	微信读书	原神	崩坏3
星穹铁道	英雄联盟	历史上的今天	天气预警

## 项目文件结构
text
├── new_agent.py          # 主程序文件
├── city_mapper.py        # 城市映射管理器
├── manage_cities.py      # 城市管理工具
├── city_mapping.json     # 城市映射数据（自动生成）
└── README.md             # 项目文档

## 配置说明
主要配置参数
参数	说明	默认值
CONFIDENCE_THRESHOLD	置信度阈值	0.7
MAX_RETRY_TIMES	最大重试次数	3
DEFAULT_TOP_K	默认检索数量	5
SIMILARITY_THRESHOLD	相似度阈值	0.7

## 常见问题
Q1: 县级城市无法识别？
A: 可以使用 manage_cities.py add 命令手动添加映射，或等待系统自动生成 city_mapping.json 文件后手动编辑。

Q2: 天气查询失败？
A: 检查心知天气API密钥是否有效，确保网络连接正常。

Q3: 热搜查询无数据？
A: UAPI接口可能限流，请稍后重试或更换其他平台。

Q4: Qwen3模型初始化失败？
A: 检查API密钥和网络连接，确认SiliconFlow账户余额充足。



支持天气查询、热搜、计算器等基础功能

县级城市自动映射

会话记忆机制
