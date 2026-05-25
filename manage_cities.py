#!/usr/bin/env python3
"""
城市映射管理工具
用于添加、删除、查询县级城市映射
"""

import sys
import csv
from city_mapper import get_city_mapper


def print_help():
    """打印帮助信息"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                 城市映射管理工具                              ║
╚══════════════════════════════════════════════════════════════╝

使用方法：
═══════════════════════════════════════════════════════════════

1. 查看所有县级城市
   python manage_cities.py list

2. 搜索城市
   python manage_cities.py search <关键词>
   例如：python manage_cities.py search 双流

3. 添加映射
   python manage_cities.py add <县级市> <地级市> [省份]
   例如：python manage_cities.py add 义乌 金华 浙江省

4. 删除映射
   python manage_cities.py remove <县级市>
   例如：python manage_cities.py remove 义乌

5. 查看统计信息
   python manage_cities.py stats

6. 批量导入（从CSV文件）
   python manage_cities.py import <文件名>
   CSV格式：县级市,地级市,省份

7. 导出到CSV
   python manage_cities.py export <文件名>

8. 导出到JSON备份
   python manage_cities.py backup

═══════════════════════════════════════════════════════════════
    """)


def list_cities(mapper):
    """列出所有县级城市"""
    counties = mapper.get_all_counties()
    print(f"\n📊 共有 {len(counties)} 个县级城市：")
    print("═" * 60)

    # 按省份分组显示
    for province, cities in mapper.province_mappings.items():
        print(f"\n📍 【{province}】")
        print("-" * 50)
        # 每行显示4个
        items = list(cities.items())
        for i in range(0, len(items), 4):
            row = items[i:i + 4]
            line = "  "
            for county, city in row:
                line += f"{county}→{city}  |  "
            print(line)


def search_cities(mapper, keyword):
    """搜索城市"""
    results = mapper.search(keyword)
    if results:
        print(f"\n🔍 找到 {len(results)} 个匹配项：")
        print("═" * 60)
        for county, city in results.items():
            print(f"  {county} → {city}")
    else:
        print(f"❌ 未找到包含 '{keyword}' 的城市")


def add_mapping(mapper, county, city, province=None):
    """添加映射"""
    if mapper.is_county(county):
        confirm = input(f"⚠️ 城市 '{county}' 已存在映射，是否覆盖？(y/n): ")
        if confirm.lower() != 'y':
            print("❌ 操作取消")
            return

    mapper.add_mapping(county, city, province)
    print(f"✅ 已添加映射: {county} → {city}")


def remove_mapping(mapper, county):
    """删除映射"""
    if not mapper.is_county(county):
        print(f"❌ 未找到城市 '{county}'")
        return

    # 显示要删除的映射
    target_city = mapper.get_city(county)
    print(f"将要删除: {county} → {target_city}")

    # 确认删除
    confirm = input("确认删除？(y/n): ")
    if confirm.lower() == 'y':
        if mapper.remove_mapping(county):
            print(f"✅ 已删除映射: {county}")
        else:
            print(f"❌ 删除失败")


def show_stats(mapper):
    """显示统计信息"""
    stats = mapper.get_statistics()
    print("\n📊 城市映射统计信息：")
    print("═" * 60)
    print(f"  县级城市总数: {stats['total_counties']}")
    print(f"  涉及省份数: {stats['provinces']}")
    print(f"  映射文件: {stats['mapping_file']}")

    # 显示各省份统计
    print("\n📈 各省份县级城市数量：")
    print("-" * 50)
    for province, cities in sorted(mapper.province_mappings.items()):
        print(f"  {province}: {len(cities)} 个")


def import_from_csv(mapper, filename):
    """从CSV文件批量导入"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # 尝试跳过标题行
            first_row = next(reader)
            if first_row[0].lower() in ['县级市', 'county', '城市']:
                pass  # 跳过标题行
            else:
                # 如果不是标题行，处理第一行数据
                if len(first_row) >= 2:
                    county, city = first_row[0], first_row[1]
                    province = first_row[2] if len(first_row) > 2 else None
                    mapper.add_mapping(county, city, province)

            count = 1
            for row in reader:
                if len(row) >= 2 and row[0].strip():
                    county, city = row[0].strip(), row[1].strip()
                    province = row[2].strip() if len(row) > 2 and row[2].strip() else None
                    if county and city:
                        mapper.add_mapping(county, city, province)
                        count += 1

            print(f"✅ 成功导入 {count} 条映射")
    except FileNotFoundError:
        print(f"❌ 文件 {filename} 不存在")
    except Exception as e:
        print(f"❌ 导入失败: {e}")


def export_to_csv(mapper, filename):
    """导出到CSV文件"""
    try:
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['县级城市', '地级市', '省份'])
            for province, cities in mapper.province_mappings.items():
                for county, city in cities.items():
                    writer.writerow([county, city, province])
        print(f"✅ 已导出到 {filename}")
    except Exception as e:
        print(f"❌ 导出失败: {e}")


def backup_mappings(mapper):
    """备份映射数据"""
    filename = mapper.export_to_json()
    print(f"✅ 已备份到 {filename}")


def main():
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower()
    mapper = get_city_mapper()

    if command == "list":
        list_cities(mapper)
    elif command == "search" and len(sys.argv) >= 3:
        search_cities(mapper, sys.argv[2])
    elif command == "add" and len(sys.argv) >= 4:
        county = sys.argv[2]
        city = sys.argv[3]
        province = sys.argv[4] if len(sys.argv) >= 5 else None
        add_mapping(mapper, county, city, province)
    elif command == "remove" and len(sys.argv) >= 3:
        remove_mapping(mapper, sys.argv[2])
    elif command == "stats":
        show_stats(mapper)
    elif command == "import" and len(sys.argv) >= 3:
        import_from_csv(mapper, sys.argv[2])
    elif command == "export" and len(sys.argv) >= 3:
        export_to_csv(mapper, sys.argv[2])
    elif command == "backup":
        backup_mappings(mapper)
    else:
        print_help()


if __name__ == "__main__":
    main()