import os
import glob
import json
import jieba
from collections import defaultdict

# -----------------
# 1. 路径和配置
# -----------------
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
DICT_DIR = os.path.join(WORKSPACE_DIR, "dict")
DATA_OUT_DIR = os.path.join(WORKSPACE_DIR, "output")
SCHEMA_PATH = os.path.join(WORKSPACE_DIR, "schema", "schema.json")

FLIGHT_DICT = os.path.join(DICT_DIR, "flight_entities.txt")
MAINTENANCE_DICT = os.path.join(DICT_DIR, "maintenance_entities.txt")
OUTPUT_ENTITIES_PATH = os.path.join(DATA_OUT_DIR, "entities.json")

def load_schema_entity_types():
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    return schema.get("entity_types", {})

# -----------------
# 2. 实体分类映射器 (Heuristic Mapper)
# -----------------
def determine_entity_type(word, schema_entity_types):
    """
    根据词缀或词特征将实体映射到 schema_json 里的细粒度类型
    """
    word_str = str(word)
    
    # 包含系统、模块、装置等的部件
    if any(suffix in word_str for suffix in ["系统", "模块", "装置", "结构", "换向阀", "泵", "油箱", "起落架", "机身"]):
        if "液" in word_str or "油" in word_str:
            return "HydraulicComponent"
        return "Component"
        
    if any(suffix in word_str for suffix in ["面", "舵", "鸭翼", "襟翼", "尾翼", "副翼", "减速板"]):
        return "ControlSurface"
        
    if "布局" in word_str or "翼型" in word_str:
        return "AerodynamicLayout"
        
    if any(suffix in word_str for suffix in ["飞行器", "飞机", "型号", "星舰", "战斗机", "机", "无人机"]) and not "发" in word_str and not "计算机" in word_str:
        return "Aircraft"
        
    if any(suffix in word_str for suffix in ["发动机", "推进", "火箭"]):
        return "Engine"
        
    if any(suffix in word_str for suffix in ["材料", "合金", "金属", "隔热", "复合", "胶", "润滑", "剂"]):
        if "胶" in word_str or "剂" in word_str or "油" in word_str:
            return "Consumable"
        return "Material"
        
    if any(suffix in word_str for suffix in ["比", "数", "角", "系数", "压力", "温度", "速度", "马赫"]):
        return "Parameter"
        
    if any(suffix in word_str for suffix in ["技术", "分析", "方法", "CFD", "风洞", "规划", "试验", "控制"]):
        return "Technology"
        
    if any(suffix in word_str for suffix in ["泄露", "泄漏", "故障", "磨损", "过热", "堵塞", "开裂", "裂纹", "腐蚀", "卡滞", "断裂", "异响", "抖动", "告警"]):
        if "原因" in word_str or "引起" in word:
            return "FaultCause"
        if any(sym in word_str for sym in ["异响", "抖动", "灯亮"]):
            return "Symptom"
        return "FailureMode"
        
    if any(suffix in word_str for suffix in ["拆卸", "检测", "清洗", "更换", "润滑", "紧固", "调整"]):
        return "Maintenance"
        
    if any(suffix in word_str for suffix in ["扳手", "万用表", "灯", "表", "千斤顶", "设备", "台", "计算机"]):
        if "计算机" in word_str or "导航" in word_str or "通信" in word_str or "雷达" in word_str:
            return "AvionicsSystem"
        if "测试" in word_str or "风洞" in word_str or "台" in word_str:
            return "TestingFacility"
        return "Tool"
        
    if any(suffix in word_str for suffix in ["管", "孔", "传感器"]):
        return "Sensor"
        
    if any(suffix in word_str for suffix in ["波音", "空客", "商飞", "NASA", "局"]):
        return "Organization"
        
    if any(suffix in word_str for suffix in ["起飞", "巡航", "再入", "滑翔", "超声速", "降落"]):
        return "FlightState"

    # 若无法命中任何后缀分类，托底映射为 'Concept' 或根据来源词典分类
    return "Concept"


def extract_entities():
    print("开始加载分词与实体抽取模块...")
    # 1. 初始化 jieba 与加载动态挖掘的词典
    if os.path.exists(FLIGHT_DICT):
        jieba.load_userdict(FLIGHT_DICT)
        print(f"已加载飞行器实体词典: {FLIGHT_DICT}")
    if os.path.exists(MAINTENANCE_DICT):
        jieba.load_userdict(MAINTENANCE_DICT)
        print(f"已加载维修设备实体词典: {MAINTENANCE_DICT}")
        
    # 加载有效的挖掘词列表，提高匹配速度
    valid_entities = set()
    for dict_path in [FLIGHT_DICT, MAINTENANCE_DICT]:
        if os.path.exists(dict_path):
            with open(dict_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    word = line.strip().split()[0]
                    # 过滤单字
                    if len(word) > 1:
                        valid_entities.add(word)

    schema_types = load_schema_entity_types()
    
    # 实体统计： key = word, value = dict {type, frequency, docs: set()}
    entity_stats = defaultdict(lambda: {"type": "", "frequency": 0, "docs": set()})
    
    # 2. 遍历 output/ 下所有提取好的数据
    search_pattern = os.path.join(DATA_OUT_DIR, "**", "*.txt")
    sentence_files = glob.glob(search_pattern, recursive=True)

    print(f"正在扫描 {len(sentence_files)} 份文档提纯数据...")

    # 3. 开始扫描与特征提取
    for file_path in sentence_files:
        doc_name = os.path.basename(file_path).replace('.txt', '')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.endswith('.jsonl'):
                for line in f:
                    if not line.strip(): continue
                    try:
                        record = json.loads(line)
                        text = record.get("text", "")
                    except:
                        text = line
            else:
                text = f.read()
                
            # 分词
            words = jieba.cut(text)
            for word in words:
                # 只收集在挖出词库中的专业名词
                if word in valid_entities:
                    entity_stats[word]["frequency"] += 1
                    entity_stats[word]["docs"].add(doc_name)
                    # 初始化分类
                    if not entity_stats[word]["type"]:
                        entity_stats[word]["type"] = determine_entity_type(word, schema_types)

    # 4. 结构化输出整理并过滤低质节点
    results = []
    entity_id = 1
    
    for word, attrs in entity_stats.items():
        if attrs["frequency"] >= 2: # 过滤仅出现过1次的噪音词
            results.append({
                "id": f"ENT_{entity_id:04d}",
                "name": word,
                "type": attrs["type"],
                "frequency": attrs["frequency"],
                "source_docs": list(attrs["docs"])
            })
            entity_id += 1
            
    # 排序：按词频倒序
    results.sort(key=lambda x: x['frequency'], reverse=True)
    
    # 写入 JSON
    with open(OUTPUT_ENTITIES_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    print(f"\n=> 实体抽取完成！共有效抽取并分类了 {len(results)} 个核心实体。")
    print(f"=> 结果已保存至 {OUTPUT_ENTITIES_PATH}")
    
    # Simple summary metric distribution
    type_counts = defaultdict(int)
    for r in results:
        type_counts[r['type']] += 1
    print("\n--- 细粒度实体分类统计 ---")
    for t, count in sorted(type_counts.items(), key=lambda item: item[1], reverse=True):
        print(f"{t}: {count} 个")

if __name__ == "__main__":
    extract_entities()
