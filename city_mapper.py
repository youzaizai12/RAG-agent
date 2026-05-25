import json
import os
from typing import Optional, Dict, List
from pathlib import Path


class CityMappingManager:
    """城市映射管理器 - 负责加载和管理县级城市到地级市的映射"""

    def __init__(self, mapping_file: str = "city_mapping.json"):
        """
        初始化城市映射管理器

        Args:
            mapping_file: 映射文件路径
        """
        self.mapping_file = mapping_file
        self.mappings = {}  # 扁平化的映射字典
        self.province_mappings = {}  # 按省份组织的映射
        self._load_mappings()

    def _load_mappings(self):
        """加载映射数据"""
        # 尝试从文件加载
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.province_mappings = data.get('mappings', {})
                    # 扁平化处理
                    for province, cities in self.province_mappings.items():
                        for county, city in cities.items():
                            self.mappings[county] = city
                print(f"✅ 成功加载 {len(self.mappings)} 个县级城市映射")
            except Exception as e:
                print(f"⚠️ 加载映射文件失败: {e}，使用默认映射")
                self._load_default_mappings()
        else:
            print(f"⚠️ 映射文件 {self.mapping_file} 不存在，使用默认映射")
            self._load_default_mappings()

    def _load_default_mappings(self):
        """加载默认映射（内置数据）"""
        self.mappings = {
            # 四川省
            "双流": "成都", "双流区": "成都", "郫都": "成都", "郫都区": "成都",
            "都江堰": "成都", "彭州": "成都", "邛崃": "成都", "崇州": "成都",
            # 江苏省
            "昆山": "苏州", "常熟": "苏州", "张家港": "苏州", "太仓": "苏州",
            "江阴": "无锡", "宜兴": "无锡",
            # 浙江省
            "义乌": "金华", "东阳": "金华", "永康": "金华", "慈溪": "宁波",
            "余姚": "宁波", "乐清": "温州", "瑞安": "温州",
            # 广东省
            "增城": "广州", "从化": "广州", "番禺": "广州", "宝安": "深圳",
            "龙岗": "深圳", "南山": "深圳", "顺德": "佛山", "南海": "佛山",
        }
        print(f"✅ 加载默认映射: {len(self.mappings)} 个县级城市")

    def get_city(self, county: str) -> str:
        """
        获取县级城市对应的地级市

        Args:
            county: 县级城市名称

        Returns:
            地级市名称，如果没有映射则返回原名称
        """
        # 清理输入
        county_clean = county.replace("市", "").replace("区", "").replace("县", "").strip()

        # 查找映射
        if county_clean in self.mappings:
            return self.mappings[county_clean]

        return county

    def is_county(self, location: str) -> bool:
        """判断是否是县级城市"""
        location_clean = location.replace("市", "").replace("区", "").replace("县", "").strip()
        return location_clean in self.mappings

    def add_mapping(self, county: str, city: str, province: str = None):
        """
        动态添加映射

        Args:
            county: 县级城市名称
            city: 地级市名称
            province: 省份（可选）
        """
        county_clean = county.replace("市", "").replace("区", "").replace("县", "").strip()
        self.mappings[county_clean] = city

        # 如果提供了省份，也更新省份映射
        if province:
            if province not in self.province_mappings:
                self.province_mappings[province] = {}
            self.province_mappings[province][county_clean] = city

        # 保存到文件
        self.save_mappings()

    def save_mappings(self):
        """保存映射到文件"""
        data = {
            "version": "1.0",
            "last_update": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": "县级城市到地级市的映射表",
            "mappings": self.province_mappings
        }

        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 映射已保存到 {self.mapping_file}")
        except Exception as e:
            print(f"⚠️ 保存映射失败: {e}")

    def get_all_counties(self) -> List[str]:
        """获取所有县级城市列表"""
        return list(self.mappings.keys())

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            "total_counties": len(self.mappings),
            "provinces": len(self.province_mappings),
            "mapping_file": self.mapping_file
        }

    def search(self, keyword: str) -> Dict[str, str]:
        """搜索包含关键词的县级城市"""
        results = {}
        for county, city in self.mappings.items():
            if keyword in county or keyword in city:
                results[county] = city
        return results


# 单例模式，全局使用
_city_mapper_instance = None


def get_city_mapper(mapping_file: str = "city_mapping.json") -> CityMappingManager:
    """获取城市映射管理器单例"""
    global _city_mapper_instance
    if _city_mapper_instance is None:
        _city_mapper_instance = CityMappingManager(mapping_file)
    return _city_mapper_instance