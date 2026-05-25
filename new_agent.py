import re
import requests
import math
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from fastapi import FastAPI, Query
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException

# 导入城市映射管理器
from city_mapper import get_city_mapper

# ==================== 1. 配置项 ====================
CONFIG = {
    "QWEN3_API_KEY": "sk-xnpiyfuxkwecqkbaasguiziaggozkgfauzrvcyzzbbfywfth",
    "QWEN3_BASE_URL": "https://api.siliconflow.cn/v1",
    "QWEN3_MODEL": "Qwen/Qwen3-7B-Instruct",
    "WEATHER_API_KEY": "SpAX_n4E16cZ3B_uZ",
    "CONFIDENCE_THRESHOLD": 0.7,
    "MAX_RETRY_TIMES": 3,
    "DEFAULT_TOP_K": 5,
    "SIMILARITY_THRESHOLD": 0.7
}


# ==================== 2. 工具类（修复版） ====================
class WeatherTool:
    def __init__(self, api_key: str, mapping_file: str = "city_mapping.json"):
        self.api_key = api_key
        self.city_mapper = get_city_mapper(mapping_file)

    def _auto_fix_location(self, location: str) -> str:
        """全自动城市/区/县名称修正"""
        if not location:
            return location

        location = location.strip()
        original_location = location
        location = self.city_mapper.get_city(location)

        if original_location != location:
            print(f"📍 已将县级城市 '{original_location}' 映射到地级市 '{location}'")

        location = location.replace("市", "").replace("区", "").replace("县", "").strip()
        return location

    def run(self, city: str) -> Tuple[str, float]:
        """查询天气 - 从天气预报中获取当前数据（包含湿度、风力）"""
        original_city = city
        city = self._auto_fix_location(city)

        # 先获取今天的天气预报数据（包含湿度和风力）
        url_forecast = f"https://api.seniverse.com/v3/weather/daily.json?key={self.api_key}&location={city}&language=zh-Hans&unit=c&start=0&days=1"

        try:
            print(f"正在查询 {city} 的天气...")
            response = requests.get(url_forecast, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if "results" in data and len(data["results"]) > 0:
                    result_data = data["results"][0]
                    location_info = result_data.get("location", {})
                    daily_data = result_data.get("daily", [])

                    if daily_data:
                        today = daily_data[0]

                        # 获取今天的详细数据
                        text_day = today.get("text_day", "未知")
                        text_night = today.get("text_night", "")
                        high = today.get("high", "?")
                        low = today.get("low", "?")
                        humidity = today.get("humidity", "暂无数据")
                        wind_direction = today.get("wind_direction", "未知")
                        wind_speed = today.get("wind_speed", "未知")

                        # 获取当前温度（从实时API）
                        current_temp = self._get_current_temperature(city)

                        display_city = original_city if original_city != city else city
                        location_name = location_info.get("name", display_city)

                        result_lines = [f"📍 {display_city}的天气信息："]

                        # 天气描述
                        if text_night and text_night != text_day:
                            weather_desc = f"{text_day}（夜间{text_night}）"
                        else:
                            weather_desc = text_day
                        result_lines.append(f"🌤️ 天气：{weather_desc}")

                        # 温度
                        if current_temp:
                            result_lines.append(f"🌡️ 当前温度：{current_temp}°C")
                            result_lines.append(f"📊 全天温度：{low}°C ~ {high}°C")
                        else:
                            result_lines.append(f"🌡️ 温度：{low}°C ~ {high}°C")

                        # 湿度和风力
                        result_lines.append(f"💧 湿度：{humidity}%")
                        result_lines.append(f"🌬️ 风向：{wind_direction}")
                        result_lines.append(f"💨 风速：{wind_speed}km/h")

                        # 天气建议
                        try:
                            temp_high = int(high)
                            temp_low = int(low)
                            avg_temp = (temp_high + temp_low) // 2

                            if avg_temp > 30:
                                result_lines.append("💡 建议：天气炎热，注意防暑降温，多喝水")
                            elif avg_temp < 10:
                                result_lines.append("💡 建议：天气寒冷，注意添衣保暖")
                            elif "雨" in text_day:
                                result_lines.append("💡 建议：有雨天气，出门记得带伞")
                            elif "雪" in text_day:
                                result_lines.append("💡 建议：有雪天气，注意出行安全")
                        except:
                            pass

                        result_lines.append(f"📍 位置：{location_name}")

                        return "\n".join(result_lines), 0.95

        except Exception as e:
            print(f"天气查询异常: {e}")

        return f"无法获取{original_city}的天气信息，请稍后重试。", 0.2

    def _get_current_temperature(self, city: str) -> Optional[str]:
        """获取当前温度"""
        url = f"https://api.seniverse.com/v3/weather/now.json?key={self.api_key}&location={city}&language=zh-Hans&unit=c"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "results" in data and len(data["results"]) > 0:
                    return data["results"][0]["now"].get("temperature")
        except:
            pass
        return None

    def get_forecast(self, city: str, days: int = 3) -> Tuple[str, float]:
        """查询天气预报，返回结果和置信度"""
        original_city = city
        city = self._auto_fix_location(city)

        url = f"https://api.seniverse.com/v3/weather/daily.json?key={self.api_key}&location={city}&language=zh-Hans&unit=c&start=0&days={days}"
        try:
            print(f"正在查询 {city} 未来{days}天天气预报...")
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if "results" in data and len(data["results"]) > 0:
                    result_data = data["results"][0]
                    location_info = result_data.get("location", {})
                    daily_data = result_data.get("daily", [])

                    display_city = original_city if original_city != city else city
                    location_name = location_info.get("name", display_city)

                    forecast_lines = [f"📅 {location_name}未来{days}天天气预报："]
                    forecast_lines.append("=" * 50)

                    for day in daily_data:
                        date = day.get("date", "未知日期")
                        text_day = day.get("text_day", "未知")
                        text_night = day.get("text_night", "")
                        high = day.get("high", "?")
                        low = day.get("low", "?")
                        humidity = day.get("humidity", "未知")
                        wind_direction = day.get("wind_direction", "未知")
                        wind_speed = day.get("wind_speed", "未知")

                        forecast_lines.append(f"📅 {date}")

                        if text_night and text_night != text_day:
                            forecast_lines.append(f"  白天：{text_day}，夜间：{text_night}")
                        else:
                            forecast_lines.append(f"  天气：{text_day}")

                        forecast_lines.append(f"  温度：{low}°C ~ {high}°C")
                        forecast_lines.append(f"  湿度：{humidity}%")
                        forecast_lines.append(f"  风向：{wind_direction}")
                        forecast_lines.append(f"  风速：{wind_speed}km/h")

                        # 添加温差提示
                        try:
                            temp_diff = int(high) - int(low)
                            if temp_diff > 10:
                                forecast_lines.append(f"  ⚠️ 温馨提示：昼夜温差{temp_diff}°C，注意适时添衣")
                        except:
                            pass

                        forecast_lines.append("-" * 40)

                    return "\n".join(forecast_lines), 0.93
                else:
                    print(f"预报API返回格式异常")
            else:
                print(f"预报API返回错误码: {response.status_code}")
        except Exception as e:
            print(f"预报请求异常: {e}")

        return f"无法获取{original_city}的天气预报。", 0.2


def get_current_time(_: str = "") -> Tuple[str, float]:
    """获取当前时间，返回结果和置信度"""
    now = datetime.now()
    weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
    result = f"🕐 当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')} {weekday}"
    return result, 0.99


def calculator(expression: str) -> Tuple[str, float]:
    """科学计算器，返回结果和置信度"""
    allowed_chars = set("0123456789+-*/()., log sqrt abs ")
    clean_expr = expression.strip().replace("^", "**")

    if any(c not in allowed_chars and not c.isalnum() and c not in "logsqrtabs" for c in clean_expr):
        return f"计算失败：表达式包含不安全字符", 0.1

    clean_expr = clean_expr.replace("log", "math.log")
    clean_expr = clean_expr.replace("sqrt", "math.sqrt")
    clean_expr = clean_expr.replace("abs", "abs")

    try:
        result = eval(clean_expr, {"__builtins__": {}, "math": math, "abs": abs})
        result_str = f"🧮 {expression} = {result:.6f}" if isinstance(result, float) else f"🧮 {expression} = {result}"
        return result_str, 0.98
    except Exception as e:
        return f"计算失败：{e}", 0.1


class HotNewsTool:
    """热搜工具 - 支持区分平台的UAPI接口"""

    # UAPI API配置
    API_URL = "https://uapis.cn/api/v1/misc/hotboard"

    # 支持的46个平台列表
    SUPPORTED_PLATFORMS = {
        "微博": "weibo",
        "知乎": "zhihu",
        "知乎日报": "zhihu-daily",
        "百度": "baidu",
        "抖音": "douyin",
        "快手": "kuaishou",
        "B站": "bilibili",
        "A站": "acfun",
        "头条": "toutiao",
        "腾讯新闻": "qq-news",
        "网易新闻": "netease-news",
        "新浪新闻": "sina-news",
        "澎湃新闻": "thepaper",
        "豆瓣电影": "douban-movie",
        "豆瓣小组": "douban-group",
        "虎扑": "hupu",
        "NGA": "ngabbs",
        "V2EX": "v2ex",
        "酷安": "coolapk",
        "36氪": "36kr",
        "少数派": "sspai",
        "IT之家": "ithome",
        "CSDN": "csdn",
        "掘金": "juejin",
        "简书": "jianshu",
        "果壳": "guokr",
        "虎嗅": "huxiu",
        "爱范儿": "ifanr",
        "贴吧": "tieba",
        "吾爱破解": "52pojie",
        "微信读书": "weread",
        "原神": "genshin",
        "崩坏3": "honkai",
        "星穹铁道": "starrail",
        "英雄联盟": "lol",
        "历史上的今天": "history",
        "天气预警": "weatheralarm",
        "地震速报": "earthquake"
    }

    def get_hotlist(self, platform: str = None) -> Tuple[str, float]:
        """获取指定平台的热搜"""
        # 如果没有指定平台，返回支持的平台列表
        if not platform:
            return self._get_platforms_list(), 0.90

        # 获取平台对应的英文标识
        platform_key = self.SUPPORTED_PLATFORMS.get(platform)
        if not platform_key:
            # 尝试模糊匹配
            for key, value in self.SUPPORTED_PLATFORMS.items():
                if platform in key or key in platform:
                    platform_key = value
                    platform = key
                    break

        if not platform_key:
            return f"❌ 不支持的平台：{platform}\n\n支持的平台请查看列表", 0.1

        try:
            print(f"正在获取 {platform} 热搜数据...")
            params = {"type": platform_key}

            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 检查返回数据
            if "list" not in data or not data["list"]:
                return f"未找到{platform}的热搜数据", 0.2

            return self._format_hotlist(platform, data["list"]), 0.95

        except requests.exceptions.Timeout:
            return f"获取{platform}热搜超时，请稍后重试", 0.1
        except requests.exceptions.ConnectionError:
            return f"网络连接失败，请检查网络后重试", 0.1
        except Exception as e:
            return f"请求失败：{str(e)}", 0.1

    def _format_hotlist(self, platform: str, hot_list: List) -> str:
        """格式化热搜数据"""
        if not hot_list:
            return f"未找到{platform}的热搜数据"

        # 取前10条
        hot_data = hot_list[:10] if len(hot_list) >= 10 else hot_list

        result_lines = []
        result_lines.append(f"📊 {platform} 热搜榜 TOP{len(hot_data)}：")
        result_lines.append("=" * 50)

        for idx, item in enumerate(hot_data, 1):
            title = item.get("title", "无标题")
            hot_value = item.get("hot_value", "未知")
            url = item.get("url", "")

            # 热度显示
            hot_display = self._format_hot_value(hot_value)

            # 热度等级emoji
            hot_emoji = self._get_hot_emoji(hot_value)

            result_lines.append(f"{idx:2d}. {hot_emoji} {title}")
            if hot_display:
                result_lines.append(f"    热度：{hot_display}")
            if url and url.startswith('http'):
                result_lines.append(f"    🔗 {url[:80]}")
            result_lines.append("")

        return "\n".join(result_lines)

    def _format_hot_value(self, hot_value) -> str:
        """格式化热度值"""
        try:
            if isinstance(hot_value, str):
                if '万' in hot_value:
                    return hot_value
                if hot_value.isdigit():
                    hot_num = int(hot_value)
                else:
                    return hot_value
            else:
                hot_num = int(hot_value)

            if hot_num >= 100000000:
                return f"{hot_num / 100000000:.1f}亿"
            elif hot_num >= 10000:
                return f"{hot_num / 10000:.1f}万"
            return str(hot_num)
        except:
            return str(hot_value) if hot_value != "未知" else ""

    def _get_hot_emoji(self, hot_value) -> str:
        """根据热度返回emoji"""
        try:
            if isinstance(hot_value, str):
                if '万' in hot_value:
                    num = float(hot_value.replace('万', ''))
                    hot_num = int(num * 10000)
                else:
                    hot_num = int(hot_value) if hot_value.isdigit() else 0
            else:
                hot_num = int(hot_value)

            if hot_num > 10000000:
                return "🔥🔥🔥🔥"
            elif hot_num > 1000000:
                return "🔥🔥🔥"
            elif hot_num > 500000:
                return "🔥🔥"
            elif hot_num > 100000:
                return "🔥"
            else:
                return "⭐"
        except:
            return "⭐"

    def _get_platforms_list(self) -> str:
        """获取平台列表"""
        platforms = list(self.SUPPORTED_PLATFORMS.keys())
        result_lines = ["📱 支持的热搜平台列表（共{}个）：".format(len(platforms))]
        result_lines.append("=" * 50)

        # 按6列分组显示
        for i in range(0, len(platforms), 6):
            group = platforms[i:i + 6]
            # 格式化每行，固定宽度
            formatted = []
            for g in group:
                formatted.append(g.ljust(8))
            result_lines.append("  " + "  ".join(formatted))

        result_lines.append("=" * 50)
        result_lines.append("💡 输入平台名称即可查询对应热搜")
        result_lines.append("   示例：微博、抖音、B站、知乎、头条")
        return "\n".join(result_lines)

    def list_platforms(self) -> str:
        """列出支持的平台"""
        return self._get_platforms_list()

    def get_all_platforms(self) -> List[str]:
        """获取所有支持的平台列表"""
        return list(self.SUPPORTED_PLATFORMS.keys())


# ==================== 3. Agent决策层（修复版） ====================
class TaskClassifier:
    """任务分类器 - 基于Qwen3实现"""

    def __init__(self, llm):
        self.llm = llm
        self.prompt = PromptTemplate(
            template="""
你是一个任务分类器。根据用户输入，判断应该使用哪个工具。

用户输入：{user_input}

可能的任务类型：
- calculator: 数学计算、算术运算（如：1+1、乘法、除法、平方根等）
- weather_query: 天气查询（如：北京天气、今天热吗、会不会下雨）
- weather_forecast: 天气预报（如：明天天气、未来三天天气）
- hotnews_query: 热搜查询（如：微博热搜、抖音热榜、今天有什么热点）
- current_time: 时间查询（如：现在几点、今天星期几、当前日期）
- unknown: 无法确定的任务

请只返回JSON格式，不要有其他文字：
{{"task_type": "任务类型", "parameters": {{}}}}

注意：对于计算问题，task_type必须是"calculator"。
""",
            input_variables=["user_input"]
        )
        self.parser = JsonOutputParser()

    def classify(self, user_input: str) -> Dict[str, Any]:
        """分类用户输入"""
        try:
            prompt = self.prompt.format(user_input=user_input)
            response = self.llm.invoke(prompt)

            # 清理响应内容
            content = response.content.strip()
            # 提取JSON部分
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]

            result = json.loads(content)

            # 确保必要的字段存在
            if "task_type" not in result:
                result["task_type"] = "unknown"
            if "parameters" not in result:
                result["parameters"] = {}

            # 简单的关键词匹配作为备选
            if result["task_type"] == "unknown":
                if any(word in user_input for word in ["计算", "多少", "等于", "+", "-", "*", "/", "×", "÷"]):
                    result["task_type"] = "calculator"
                elif any(word in user_input for word in ["天气", "气温", "温度", "下雨", "晴天"]):
                    result["task_type"] = "weather_query"
                elif any(word in user_input for word in ["热搜", "热榜", "热点", "微博", "抖音"]):
                    result["task_type"] = "hotnews_query"
                elif any(word in user_input for word in ["时间", "几点", "日期", "星期"]):
                    result["task_type"] = "current_time"

            return result

        except Exception as e:
            print(f"分类错误: {e}")
            # 降级处理：使用关键词匹配
            if any(word in user_input for word in ["计算", "多少", "等于", "+", "-", "*", "/", "×", "÷"]):
                return {"task_type": "calculator", "confidence": 0.5, "parameters": {}}
            elif any(word in user_input for word in ["天气", "气温", "温度"]):
                return {"task_type": "weather_query", "confidence": 0.5, "parameters": {}}
            elif any(word in user_input for word in ["热搜", "热榜"]):
                return {"task_type": "hotnews_query", "confidence": 0.5, "parameters": {}}
            elif any(word in user_input for word in ["时间", "几点"]):
                return {"task_type": "current_time", "confidence": 0.5, "parameters": {}}
            else:
                return {"task_type": "unknown", "confidence": 0.0, "parameters": {}}


class ToolSelector:
    """工具选择策略"""

    def __init__(self, tools: List[Dict[str, Any]]):
        self.tools = tools
        self.task_tool_mapping = {
            "weather_query": "天气查询",
            "weather_forecast": "天气预报",
            "hotnews_query": "热榜查询",
            "calculator": "科学计算器",
            "current_time": "当前时间"
        }

    def select_tool(self, task_type: str) -> Optional[Dict[str, Any]]:
        """基于任务类型选择工具"""
        if task_type in self.task_tool_mapping:
            tool_name = self.task_tool_mapping[task_type]
            for tool in self.tools:
                if tool["name"] == tool_name:
                    return tool
        return None


# ==================== 4. 动态RAG优化 ====================
class DynamicRAG:
    """动态RAG优化模块"""

    def __init__(self):
        self.default_top_k = CONFIG["DEFAULT_TOP_K"]
        self.default_similarity = CONFIG["SIMILARITY_THRESHOLD"]

    def adjust_retrieval_params(self, confidence: float) -> Tuple[int, float]:
        """根据置信度调整检索参数"""
        if confidence < 0.5:
            return min(self.default_top_k * 2, 10), max(self.default_similarity - 0.2, 0.5)
        elif confidence < 0.7:
            return self.default_top_k + 2, self.default_similarity - 0.1
        else:
            return self.default_top_k, self.default_similarity

    def retry_mechanism(self, tool_func, input_data, max_retry: int = CONFIG["MAX_RETRY_TIMES"]) -> Tuple[str, float]:
        """失败重试机制"""
        retry_count = 0
        final_result = ""
        final_confidence = 0.0

        while retry_count < max_retry:
            try:
                if isinstance(input_data, tuple):
                    result, confidence = tool_func(*input_data)
                else:
                    result, confidence = tool_func(input_data)
            except Exception as e:
                result = f"执行失败: {e}"
                confidence = 0.0

            print(f"重试次数：{retry_count + 1} | 置信度：{confidence:.2f}")

            if confidence >= CONFIG["CONFIDENCE_THRESHOLD"]:
                final_result = result
                final_confidence = confidence
                break

            retry_count += 1

        if final_confidence < CONFIG["CONFIDENCE_THRESHOLD"] and final_result:
            final_result = f"{final_result}"
        elif not final_result:
            final_result = "经过多次尝试后仍无法获取结果"

        return final_result, final_confidence


# ==================== 5. 记忆机制 ====================
class ConversationMemory:
    """会话记忆机制"""

    def __init__(self):
        self.memory_store = {}

    def add_memory(self, session_id: str, user_input: str, agent_response: str):
        """添加会话记忆"""
        if session_id not in self.memory_store:
            self.memory_store[session_id] = []

        self.memory_store[session_id].append({
            "user": user_input,
            "agent": agent_response,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        if len(self.memory_store[session_id]) > 10:
            self.memory_store[session_id] = self.memory_store[session_id][-10:]

    def get_memory(self, session_id: str) -> str:
        """获取会话记忆"""
        if session_id not in self.memory_store or not self.memory_store[session_id]:
            return "暂无历史会话记忆"

        memory_lines = ["【历史会话记忆】"]
        for idx, item in enumerate(self.memory_store[session_id][-5:], 1):
            memory_lines.append(f"{idx}. 用户：{item['user']}")
            memory_lines.append(f"   Agent：{item['agent'][:100]}...")
            memory_lines.append(f"   时间：{item['timestamp']}")

        return "\n".join(memory_lines)

    def clear_memory(self, session_id: str):
        """清空会话记忆"""
        if session_id in self.memory_store:
            del self.memory_store[session_id]


# ==================== 6. 强化版ReAct Agent ====================
class RAGEnhancedReActAgent:
    def __init__(self, llm, tools: List[Dict[str, Any]]):
        self.llm = llm
        self.tools = tools
        self.task_classifier = TaskClassifier(llm)
        self.tool_selector = ToolSelector(tools)
        self.dynamic_rag = DynamicRAG()
        self.memory = ConversationMemory()

    def _format_tools(self) -> str:
        return "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])

    def _run_tool_with_retry(self, tool_name: str, tool_input) -> Tuple[str, float]:
        """调用工具并触发重试机制"""
        for tool in self.tools:
            if tool["name"] == tool_name:
                try:
                    print(f"🔧 执行: {tool_name}({tool_input if tool_input else '无'})")
                    result, confidence = self.dynamic_rag.retry_mechanism(tool["func"], tool_input)
                    print(f"✅ 返回: {result[:100]}... | 置信度: {confidence:.2f}")
                    return result, confidence
                except Exception as e:
                    return f"工具执行出错: {e}", 0.0
        return f"未找到工具: {tool_name}", 0.0

    def run(self, user_input: str, session_id: str = "default", max_iterations: int = 3, verbose: bool = True) -> str:
        """运行Agent"""
        memory_context = self.memory.get_memory(session_id)

        # 直接进行分类和工具调用，不进行多轮迭代
        if verbose:
            print(f"\n{'=' * 50} 第 1 轮 {'=' * 50}")

        # 任务分类
        task_info = self.task_classifier.classify(user_input)
        if verbose:
            print(f"📊 任务分类: {json.dumps(task_info, ensure_ascii=False)}")

        task_type = task_info.get("task_type", "unknown")
        parameters = task_info.get("parameters", {})

        # 根据任务类型调用对应的工具
        if task_type == "calculator":
            # 提取表达式
            expr = user_input
            # 移除中文关键词
            for kw in ["计算", "等于", "多少", "是"]:
                expr = expr.replace(kw, "")
            result, _ = self._run_tool_with_retry("科学计算器", expr)
        elif task_type == "weather_query":
            # 提取城市名
            city = user_input
            for kw in ["天气", "气温", "温度", "怎么样", "如何", "今天", "查询"]:
                city = city.replace(kw, "")
            city = city.strip()
            if not city:
                city = "北京"
            result, _ = self._run_tool_with_retry("天气查询", city)
        elif task_type == "weather_forecast":
            city = user_input
            for kw in ["预报", "未来", "天气", "查询"]:
                city = city.replace(kw, "")
            city = city.strip()
            if not city:
                city = "北京"
            result, _ = self._run_tool_with_retry("天气预报", city)
        elif task_type == "hotnews_query":
            platform = None
            for p in HotNewsTool.SUPPORTED_PLATFORMS.keys():
                if p in user_input:
                    platform = p
                    break
            result, _ = self._run_tool_with_retry("热榜查询", platform if platform else "")
        elif task_type == "current_time":
            result, _ = get_current_time("")
        else:
            result = f"我能帮你处理天气查询、热搜查看、计算和时间查询。请问你需要什么帮助？"

        # 保存记忆
        self.memory.add_memory(session_id, user_input, result)

        return result


# ==================== 7. 交互式菜单系统 ====================
class EnhancedInteractiveMenu:
    """增强版交互式菜单系统"""

    def __init__(self, agent, mapping_file: str = "city_mapping.json"):
        self.agent = agent
        self.weather_tool = WeatherTool(api_key=CONFIG["WEATHER_API_KEY"], mapping_file=mapping_file)
        self.hotnews_tool = HotNewsTool()
        self.city_mapper = get_city_mapper(mapping_file)
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def display_menu(self):
        """显示主菜单"""
        print("\n" + "=" * 60)
        print("🤖 RAG增强版AI助手 - 功能菜单（Qwen3模型）")
        print("=" * 60)
        print("1️⃣  天气查询（实时温度+湿度+风力）")
        print("2️⃣  天气预报（未来3-7天）")
        print("3️⃣  热搜查询（30+平台）")
        print("4️⃣  科学计算器")
        print("5️⃣  当前时间")
        print("6️⃣  AI对话模式")
        print("7️⃣  查看会话记忆")
        print("8️⃣  清空会话记忆")
        print("9️⃣  查看城市映射统计")
        print("0️⃣  退出")
        print("=" * 60)

    def weather_menu(self):
        """天气查询子菜单"""
        print("\n🌤️ 天气查询")
        print("支持城市：地级市（如：成都、苏州）、县级市（如：双流、昆山）")
        city = input("请输入城市名称：").strip()

        if city:
            if self.city_mapper.is_county(city):
                target = self.city_mapper.get_city(city)
                print(f"ℹ️ 检测到县级城市，将自动映射到：{target}")

            print("\n正在查询天气，请稍候...")
            result, confidence = self.weather_tool.run(city)
            print(f"\n{result}")
            print(f"📊 数据可靠性：{confidence:.0%}")
        else:
            print("❌ 城市名称不能为空！")

    def forecast_menu(self):
        """天气预报子菜单"""
        print("\n📅 天气预报")
        print("支持城市：地级市（如：成都、苏州）、县级市（如：双流、昆山）")
        city = input("请输入城市名称：").strip()

        if city:
            if self.city_mapper.is_county(city):
                target = self.city_mapper.get_city(city)
                print(f"ℹ️ 检测到县级城市，将自动映射到：{target}")

            days_input = input("请输入预报天数（1-7，默认3天）：").strip()
            days = int(days_input) if days_input.isdigit() and 1 <= int(days_input) <= 7 else 3

            print(f"\n正在查询 {city} 未来{days}天天气预报...")
            result, confidence = self.weather_tool.get_forecast(city, days)
            print(f"\n{result}")
            print(f"📊 数据可靠性：{confidence:.0%}")
        else:
            print("❌ 城市名称不能为空！")

    def hotnews_menu(self):
        """热搜查询子菜单"""
        print("\n📊 热搜查询")
        print("支持平台：微博、知乎、百度、抖音、B站、头条等30+平台")
        print("直接回车查看所有支持平台列表")
        platform = input("请输入平台名称：").strip()

        print("\n正在获取热搜数据...")
        result, confidence = self.hotnews_tool.get_hotlist(platform if platform else None)

        print(f"\n{result}")
        print(f"📊 数据可靠性：{confidence:.0%}")

    def calculator_menu(self):
        """计算器子菜单"""
        print("\n🧮 科学计算器")
        print("支持：+ - * / () ^ log sqrt abs")
        print("示例：2^10, sqrt(16), log(100), abs(-5)")
        expression = input("请输入表达式：").strip()
        if expression:
            result, confidence = calculator(expression)
            print(f"\n{result}")
            print(f"📊 计算可靠性：{confidence:.0%}")

    def view_memory_menu(self):
        """查看会话记忆"""
        print("\n📝 会话记忆")
        memory = self.agent.memory.get_memory(self.session_id)
        print(memory)

    def clear_memory_menu(self):
        """清空会话记忆"""
        print("\n🗑️ 清空会话记忆")
        confirm = input("确定要清空吗？(y/n)：").strip().lower()
        if confirm == 'y':
            self.agent.memory.clear_memory(self.session_id)
            print("✅ 会话记忆已清空")
        else:
            print("取消清空操作")

    def show_mapping_stats(self):
        """显示城市映射统计"""
        stats = self.city_mapper.get_statistics()
        print("\n📊 城市映射统计信息：")
        print("═" * 60)
        print(f"  支持县级城市数: {stats['total_counties']}")
        print(f"  涉及省份数: {stats['provinces']}")
        print(f"  映射文件: {stats['mapping_file']}")

        print("\n📝 映射示例：")
        print("-" * 50)
        counties = list(self.city_mapper.mappings.keys())[:10]
        for county in counties:
            city = self.city_mapper.get_city(county)
            print(f"  {county} → {city}")

    def ai_chat_menu(self):
        """AI对话模式"""
        print("\n🤖 AI智能对话模式")
        print("我可以帮你：")
        print("  • 查询天气（地级市、县级市都支持）")
        print("  • 查看热搜（微博、知乎、抖音等）")
        print("  • 数学计算")
        print("  • 时间查询")
        print("\n示例问题：")
        print("  - 成都天气怎么样？")
        print("  - 双流区今天热吗？")
        print("  - 看看微博热搜")
        print("  - 计算 123 * 456")
        print("\n输入 'back' 返回主菜单\n")

        while True:
            user_input = input("👤 你：").strip()
            if user_input.lower() in ['back', '返回', 'exit']:
                break
            if not user_input:
                continue

            print("\n🤖 AI思考中...\n")
            result = self.agent.run(user_input, self.session_id, verbose=True)
            print(f"🤖 AI：{result}\n")

    def run(self):
        """运行主循环"""
        print("\n🎉 欢迎使用RAG增强版AI助手！")
        print("✨ 功能特点：")
        print(f"   • 支持 {self.city_mapper.get_statistics()['total_counties']} 个县级城市自动映射")
        print("   • 天气查询包含温度、湿度、风力信息")
        print("   • 热搜查询支持30+平台（真实数据）")
        print("   • 智能会话记忆")
        print("   • 科学计算器")

        while True:
            self.display_menu()
            choice = input("\n请选择功能（0-9）：").strip()

            if choice == '0':
                print("\n👋 再见！")
                break
            elif choice == '1':
                self.weather_menu()
            elif choice == '2':
                self.forecast_menu()
            elif choice == '3':
                self.hotnews_menu()
            elif choice == '4':
                self.calculator_menu()
            elif choice == '5':
                result, confidence = get_current_time("")
                print(f"\n{result}")
                print(f"📊 可靠性：{confidence:.0%}")
            elif choice == '6':
                self.ai_chat_menu()
            elif choice == '7':
                self.view_memory_menu()
            elif choice == '8':
                self.clear_memory_menu()
            elif choice == '9':
                self.show_mapping_stats()
            else:
                print("❌ 无效选择，请重新输入！")

            input("\n按回车键继续...")


# ==================== 8. 模块级别的初始化 ====================
# 初始化Qwen3模型
try:
    chat_model = ChatOpenAI(
        openai_api_key=CONFIG["QWEN3_API_KEY"],
        base_url=CONFIG["QWEN3_BASE_URL"],
        model=CONFIG["QWEN3_MODEL"],
        temperature=0.2,
    )
    print("✅ Qwen3模型初始化成功")
except Exception as e:
    print(f"⚠️ Qwen3模型初始化失败: {e}")
    chat_model = None

# 初始化工具
weather_tool = WeatherTool(api_key=CONFIG["WEATHER_API_KEY"])
hotnews_tool = HotNewsTool()

# 工具列表
tools = [
    {"name": "天气查询", "func": weather_tool.run, "description": "查询实时天气，支持地级市和县级市"},
    {"name": "天气预报", "func": weather_tool.get_forecast, "description": "查询未来天气预报"},
    {"name": "当前时间", "func": get_current_time, "description": "获取当前时间"},
    {"name": "科学计算器", "func": calculator, "description": "计算数学表达式"},
    {"name": "热榜查询", "func": hotnews_tool.get_hotlist, "description": "查询热搜榜"}
]

# 初始化Agent
if chat_model:
    agent = RAGEnhancedReActAgent(chat_model, tools)
else:
    agent = None
    print("⚠️ Agent初始化失败")

# ==================== 9. 主程序入口 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("启动交互式菜单")
    print("=" * 60)

    if agent:
        menu = EnhancedInteractiveMenu(agent)
        menu.run()
    else:
        print("Agent初始化失败，无法启动菜单")