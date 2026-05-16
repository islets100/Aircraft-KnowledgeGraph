# -*- coding: utf-8 -*-
"""
本体与词典构建：从已提取文本挖掘 jieba 用户词典；可选生成/更新 schema.json 与 patterns.json。

默认仅挖掘 flight_entities.txt / maintenance_entities.txt，避免覆盖已手工维护的
schema/schema.json 与 dict/patterns.json。

若需由脚本写入 schema/patterns，请显式传入：
  python build_ontology.py --write-schema-patterns
若已存在手工文件仍要覆盖：
  python build_ontology.py --write-schema-patterns --force
"""
import argparse
import json
import os

import jieba
import jieba.analyse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEXT_DIR = os.path.join(BASE_DIR, "output", "extracted_text")
DICT_DIR = os.path.join(BASE_DIR, "dict")
SCHEMA_DIR = os.path.join(BASE_DIR, "schema")

SCHEMA_PATH = os.path.join(SCHEMA_DIR, "schema.json")
PATTERNS_PATH = os.path.join(DICT_DIR, "patterns.json")

# 旧版中文关系标签 -> relation_extractor / Neo4j 使用的英文关系名
RELATION_EN = {
    "包含组件": "has_component",
    "所属部分": "part_of",
    "发生现象": "has_fault",
    "导致结果": "caused_by",
    "应用技术": "uses_technology",
    "使用材料": "uses_material",
    "具有参数": "has_parameter",
    "控制调节": "controls",
    "提供动力": "powered_by",
    "所需工具": "requires_tool",
    "用于测试": "measured_by",
    "安装于": "located_in",
    "连接于": "connected_to",
    "运行于": "operates_at",
    "演变自": "derived_from",
}


def init_dirs():
    os.makedirs(DICT_DIR, exist_ok=True)
    os.makedirs(SCHEMA_DIR, exist_ok=True)


def build_schema(force: bool = False) -> None:
    """写入 schema/schema.json：中文说明型 entity_types / relation_types（字符串描述）。"""
    if os.path.isfile(SCHEMA_PATH) and not force:
        try:
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            et = data.get("entity_types") or {}
            # 已存在英文细粒度类型（手工 schema）时不覆盖
            if isinstance(et, dict) and "Aircraft" in et:
                print(f"[*] 已存在英文版 {SCHEMA_PATH}，跳过写入（避免覆盖手工配置）。使用 --force 可覆盖。")
                return
        except Exception:
            pass

    schema = {
        "entity_types": {
            "飞行器": "特定型号或种类的飞行器 (如：变构飞行器、无人机、X-37B)",
            "组织机构": "研发、生产或维护机构",
            "气动布局": "飞行器的外形和翼型设计 (如：飞翼布局、鸭翼)",
            "控制面": "用于控制飞行的物理结构 (如：升降舵、减速板)",
            "系统组件": "飞行器或机械的子系统及零件 (如：液压系统、起落架)",
            "动力装置": "提供动力的设备 (如：涡扇发动机、冲压发动机)",
            "传感器件": "各类探测与传感设备 (如：空速管、雷达)",
            "维修工具": "用于检测或维修的专业工具",
            "测试设备": "风洞、仿真台等测试设备",
            "气动参数": "升阻比、马赫数、攻角、阻力系数等",
            "飞行状态": "起飞、巡航、再入、超声速等",
            "物理现象": "激波、烧蚀、热流、边界层等物理现象",
            "工艺方法": "特定的制造、控制或维修技术 (如：自适应控制、CFD)",
            "故障现象": "系统发生的故障类型 (如：磨损、泄漏、短路)",
            "材料": "合金、复合材料、隔热瓦等",
        },
        "relation_types": {
            "所属部分": {"desc": "A属于B的一部分 (如：机翼-属于-飞行器)", "directed": True},
            "包含组件": {"desc": "A包含B (如：飞行器-包含-机翼)", "directed": True},
            "提供动力": {"desc": "A为B提供动力 (如：发动机-提供动力-飞行器)", "directed": True},
            "具有参数": {"desc": "A具备B这项属性指标", "directed": True},
            "发生现象": {"desc": "A发生了B现象 (包括故障或物理现象)", "directed": True},
            "导致结果": {"desc": "A导致了B (因果关系)", "directed": True},
            "应用技术": {"desc": "A应用了B技术或工艺", "directed": True},
            "使用材料": {"desc": "A使用了B材料制造", "directed": True},
            "控制调节": {"desc": "A对B进行控制或调节", "directed": True},
            "用于测试": {"desc": "A用于测试或诊断B", "directed": True},
            "连接于": {"desc": "A物理连接到B", "directed": True},
            "安装于": {"desc": "A安装在B之上", "directed": True},
            "运行于": {"desc": "A在B环境或状态下运行", "directed": True},
            "演变自": {"desc": "A由B演变/衍生而来", "directed": True},
            "共现相关": {"desc": "上下文语义密切相关", "directed": False},
        },
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)
    print(f"[*] Schema 已保存至: {SCHEMA_PATH}")


def _normalize_pattern_entry(entry: dict) -> dict:
    """将旧版 {regex, relation, reverse?} 转为 relation_extractor 所需字段。"""
    rel_zh = entry.get("relation", "RELATED_TO")
    relation = RELATION_EN.get(rel_zh, rel_zh)
    if entry.get("reverse"):
        g1, g2 = "target", "source"
    else:
        g1, g2 = "source", "target"
    return {
        "regex": entry["regex"],
        "relation": relation,
        "group1": g1,
        "group2": g2,
    }


def build_custom_patterns(force: bool = False) -> None:
    """写入 dict/patterns.json，顶层为 {\"patterns\": [...]}，与 relation_extractor 一致。"""
    if os.path.isfile(PATTERNS_PATH) and not force:
        try:
            with open(PATTERNS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            n = len(data.get("patterns") or [])
            if n > 5:
                print(
                    f"[*] 已存在 {PATTERNS_PATH}（共 {n} 条规则），跳过写入。"
                    "使用 --write-schema-patterns --force 可覆盖。"
                )
                return
        except Exception:
            pass

    raw_patterns = [
        {"regex": "(.+?)(?:由|包含|包括|分为|涵盖|集成了)(.+?)(?:组成|构成|部分|系统|组件|部件|模块)", "relation": "包含组件"},
        {"regex": "(.+?)是(.+?)的(?:部分|核心|关键部件|下属系统|重要组成部分)", "relation": "所属部分"},
        {"regex": "(.+?)属于(.+?)(?:系统|装置|总成|模块|架构)", "relation": "所属部分"},
        {"regex": "(.+?)(?:发生|出现|导致|造成|引发|引起)(.+?)(?:故障|异常|损坏|误差|失效|漏油|卡滞)", "relation": "发生现象"},
        {"regex": "(.+?)(?:故障|损坏|失效)(?:是由于|因为|原因在于)(.+?)", "relation": "导致结果", "reverse": True},
        {"regex": "由于(.+?)(?:导致|使得|造成)(.+?)(?:发生|出现)", "relation": "导致结果"},
        {"regex": "(.+?)(?:采用|利用|使用|基于|结合了|引入了)(.+?)(?:技术|工艺|算法|方法|策略|网络|模型)", "relation": "应用技术"},
        {"regex": "(.+?)(?:采用|使用|由|借助)(.+?)(?:材料|合金|复合材料|涂层)(?:制成|制造|打造|加工)", "relation": "使用材料"},
        {"regex": "采用(.+?)(?:材料|设计|结构)(?:打造|制造|生产)的(.+?)", "relation": "使用材料", "reverse": True},
        {"regex": "(.+?)(?:具有|达到|满足|具备)(.+?)(?:马赫数|升阻比|系数|参数|特性|性能|能力)", "relation": "具有参数"},
        {"regex": "(.+?)的(.+?)(?:为|等于|在|保持在|高至)(?:[0-9+.]+)", "relation": "具有参数"},
        {"regex": "(.+?)(?:对|向|给)(.+?)(?:进行控制|起到调节|实现平衡|输出指令|产生影响|进行抑制)", "relation": "控制调节"},
        {"regex": "(.+?)(?:控制|操纵|调节|补偿)(.+?)(?:的变化|的运动|的状态)", "relation": "控制调节"},
        {"regex": "(.+?)(?:为|向)(.+?)(?:提供动力|输送动力|驱动|供给能量)", "relation": "提供动力"},
        {"regex": "(.+?)(?:由|依靠)(.+?)(?:驱动|推动|提供推力)", "relation": "提供动力", "reverse": True},
        {"regex": "(.+?)(?:需要|使用|依靠|利用)(.+?)(?:进行测试|进行测量|进行维修|排除故障|检测|诊断)", "relation": "所需工具"},
        {"regex": "(.+?)(?:用于测量|用来测试|用来诊断)(.+?)(?:的状态|的参数|的内容)", "relation": "用于测试"},
        {"regex": "(.+?)安装在(.+?)(?:上|中|内|内部|表层|外部)", "relation": "安装于"},
        {"regex": "(.+?)与(.+?)(?:连接|相连|连接到|交联)", "relation": "连接于"},
        {"regex": "(.+?)(?:运行于|飞行在|适应于)(.+?)(?:环境|剖面|空域|高度)", "relation": "运行于"},
        {"regex": "(.+?)(?:发展为|演变为|衍生出|改进为|升级为)(.+?)", "relation": "演变自", "reverse": True},
    ]
    patterns = [_normalize_pattern_entry(p) for p in raw_patterns]
    out = {"patterns": patterns}
    with open(PATTERNS_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[*] 正则模板已保存至: {PATTERNS_PATH}（共 {len(patterns)} 条）")


def auto_mine_entities():
    """按领域切分文本，分别挖掘飞行器和维修类字典。"""
    print("[*] 正在分领域挖掘实体词汇...")
    if not os.path.isdir(TEXT_DIR):
        print(f"[!] 未找到目录 {TEXT_DIR}，请先运行 pdf_parser.py。")
        return

    domain_texts = {"飞行器与变构": "", "维修类": ""}

    for file in os.listdir(TEXT_DIR):
        if not file.endswith(".txt"):
            continue
        with open(os.path.join(TEXT_DIR, file), "r", encoding="utf-8") as f:
            content = f.read()
            if "维修" in file:
                domain_texts["维修类"] += content + "\n"
            else:
                domain_texts["飞行器与变构"] += content + "\n"

    stop_words = {
        "中心", "背景", "时间", "问题", "结论", "方法", "研究", "发展", "系统",
        "图", "表", "说明", "分析", "情况", "影响", "基础",
    }

    if domain_texts["飞行器与变构"].strip():
        flight_keywords = jieba.analyse.extract_tags(
            domain_texts["飞行器与变构"],
            topK=1200,
            allowPOS=("n", "nr", "ns", "nt", "nz", "eng", "vn", "l"),
        )
        flight_entities = [w for w in flight_keywords if len(w) > 1 and w not in stop_words][:800]
        with open(os.path.join(DICT_DIR, "flight_entities.txt"), "w", encoding="utf-8") as f:
            for word in flight_entities:
                f.write(f"{word} 100 n\n")
        print(f"[*] 建成 [飞行器] 领域实体库，包含 {len(flight_entities)} 个词。")

    if domain_texts["维修类"].strip():
        maint_keywords = jieba.analyse.extract_tags(
            domain_texts["维修类"],
            topK=1200,
            allowPOS=("n", "nr", "ns", "nt", "nz", "vn", "eng", "l"),
        )
        maint_entities = [w for w in maint_keywords if len(w) > 1 and w not in stop_words][:800]
        with open(os.path.join(DICT_DIR, "maintenance_entities.txt"), "w", encoding="utf-8") as f:
            for word in maint_entities:
                f.write(f"{word} 100 n\n")
        print(f"[*] 建成 [维修类] 领域实体库，包含 {len(maint_entities)} 个词。")


def main():
    parser = argparse.ArgumentParser(description="挖掘领域词典；可选写入 schema.json / patterns.json")
    parser.add_argument(
        "--write-schema-patterns",
        action="store_true",
        help="同时写入 schema/schema.json 与 dict/patterns.json（默认不写入，避免覆盖手工文件）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="与 --write-schema-patterns 联用：即使已存在英文 schema 或较多 patterns 也强制覆盖",
    )
    args = parser.parse_args()

    init_dirs()
    if args.write_schema_patterns:
        build_schema(force=args.force)
        build_custom_patterns(force=args.force)
    else:
        print("[*] 未指定 --write-schema-patterns，跳过 schema/patterns 写入（仅更新词典）。")
    auto_mine_entities()


if __name__ == "__main__":
    main()
