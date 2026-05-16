# KnowledgeGraph

使用 Python 对航空航天、变构飞行器与装备维修相关 PDF 语料进行文本提取、实体抽取、关系抽取、评估与可视化。

## 项目简介

本项目围绕“从领域文档中构建完整知识图谱”这一目标实现了一条可复现的处理流水线，核心特点包括：

- 面向 PDF 语料的文本提取与清洗
- 基于领域词典与 jieba 的实体抽取
- 基于正则模板、`A的B` 结构与触发词共现的关系抽取
- 输出可追溯的三元组结果，包含 `evidence` 与 `doc` 字段
- 支持 3D 图谱可视化与 Neo4j 图数据库导入
- 提供金标准生成与 Precision / Recall / F1 评测脚本

项目语料主要覆盖以下领域：

- 飞行器
- 变构飞行器
- 维修类装备与系统

## 项目结构

注意：**实际可执行脚本位于 `knowledgeGraph/` 目录下**，运行命令时需要先进入该目录。

```text
.
├── data/                             # 仓库根目录下的原始资料
├── knowledgeGraph/                   # 项目主目录
│   ├── data/                         # 知识图谱构建所用 PDF 语料
│   ├── dict/                         # 领域词典与关系模板
│   ├── schema/                       # Schema 定义
│   ├── output/                       # 中间结果与最终结果
│   ├── graph/                        # Neo4j 与 3D 可视化脚本
│   ├── evaluation/                   # 金标准生成与评估脚本
│   ├── pdf_parser.py                 # PDF 文本提取
│   ├── build_ontology.py             # 词典构建与可选 schema/patterns 生成
│   ├── sentence_segmenter.py         # 分句
│   ├── sentence_cleaner.py           # 句子清洗
│   ├── entity_extractor.py           # 实体抽取
│   ├── relation_extractor.py         # 关系抽取
│   └── 知识图谱完整技术报告.md        # 详细技术报告
└── README.md
```

## 技术路线

整条流水线如下：

1. PDF 文本提取：从 `knowledgeGraph/data/` 中递归读取 PDF，提取文本层内容
2. 构建词典：从提取文本中挖掘飞行器与维修领域实体词典
3. 句子切分：将全文拆分为句子级 JSONL
4. 句子清洗：去除角标、图表说明、排版空白并统一标点
5. 实体抽取：利用 jieba + 用户词典扫描语料并统计实体频次
6. 关系抽取：结合正则模板、`A的B` 结构和触发词共现生成三元组
7. 可视化与存储：生成 3D HTML 图谱，并可导入 Neo4j
8. 评估：生成金标准并输出评测报告

## 运行环境

建议使用 Python 3.10 及以上版本。

项目代码中实际使用或依赖到的第三方库主要包括：

- PyMuPDF (`fitz`)
- jieba
- neo4j

部分历史或说明文档中还提到过以下可选方案：

- pdfplumber
- PaddleOCR
- pdf2image

如果你准备补充扫描件 OCR 流程，可再按需安装相关依赖。

## 安装依赖

仓库当前未提供现成的 `requirements.txt`，可以先手动安装核心依赖：

```bash
pip install pymupdf jieba neo4j
```

如果你在中国大陆环境下安装较慢，建议自行配置国内 PyPI 镜像后再安装。

## 快速开始

先进入项目主目录：

```bash
cd knowledgeGraph
```

然后按顺序执行：

```bash
python pdf_parser.py
python build_ontology.py
python sentence_segmenter.py
python sentence_cleaner.py
python entity_extractor.py
python relation_extractor.py
python graph/visualizer.py
python evaluation/generate_gold_standard.py
python evaluation/evaluate.py
```

如果你需要把结果导入 Neo4j，可额外执行：

```bash
python graph/neo4j_builder.py
```

## 各阶段输入与输出

### 1. PDF 文本提取

脚本：`knowledgeGraph/pdf_parser.py`

输入：

- `knowledgeGraph/data/**/*.pdf`

输出：

- `knowledgeGraph/output/extracted_text/*.txt`
- `knowledgeGraph/output/extracted_text/catalog.json`

说明：

- 会根据路径关键字推断文档领域
- 对疑似扫描版 PDF 进行跳过
- 已存在的输出文本会直接跳过，便于重复运行

### 2. 领域词典构建

脚本：`knowledgeGraph/build_ontology.py`

默认输出：

- `knowledgeGraph/dict/flight_entities.txt`
- `knowledgeGraph/dict/maintenance_entities.txt`

可选输出：

- `knowledgeGraph/schema/schema.json`
- `knowledgeGraph/dict/patterns.json`

命令示例：

```bash
python build_ontology.py
python build_ontology.py --write-schema-patterns
python build_ontology.py --write-schema-patterns --force
```

说明：

- 默认只更新词典，不覆盖已手工维护的 schema 和关系模板
- 加上 `--write-schema-patterns` 后，才会生成或覆盖 schema / patterns

### 3. 分句与清洗

脚本：

- `knowledgeGraph/sentence_segmenter.py`
- `knowledgeGraph/sentence_cleaner.py`

输出：

- `knowledgeGraph/output/sentences/*.jsonl`
- `knowledgeGraph/output/sentences_cleaned/*.jsonl`

说明：

- 分句后保留 `doc` 与 `sentence` 字段
- 清洗阶段主要处理引用角标、图表括号、半角标点与空白噪声

### 4. 实体抽取

脚本：`knowledgeGraph/entity_extractor.py`

输出：

- `knowledgeGraph/output/entities.json`

实体结果包含：

- `id`
- `name`
- `type`
- `frequency`
- `source_docs`

说明：

- 通过 `jieba.load_userdict` 加载飞行器和维修类词典
- 基于白名单命中和词频过滤保留核心实体
- 当前实现中，频次小于 2 的实体会被过滤

### 5. 关系抽取

脚本：`knowledgeGraph/relation_extractor.py`

输入：

- `knowledgeGraph/output/entities.json`
- `knowledgeGraph/dict/patterns.json`
- `knowledgeGraph/output/sentences_cleaned/*.jsonl`

输出：

- `knowledgeGraph/output/triples.json`

三元组结果包含：

- `source_id`
- `source_name`
- `source_type`
- `relation`
- `target_id`
- `target_name`
- `target_type`
- `evidence`
- `doc`

说明：

- 先执行正则模板匹配
- 再补充 `A的B` 所有格结构抽取
- 在结果不足时启用触发词共现增强召回
- 使用全局去重集合去除重复三元组

### 6. 可视化

脚本：`knowledgeGraph/graph/visualizer.py`

输出：

- `knowledgeGraph/output/graph_3d.html`

说明：

- 根据三元组统计高频实体并构建子图
- 生成可在浏览器中交互浏览的 3D 力导向图谱

### 7. Neo4j 导入

脚本：`knowledgeGraph/graph/neo4j_builder.py`

说明：

- 会读取 `triples.json` 并导入 Neo4j
- 默认逻辑会先清空数据库再重建
- 运行前需要先修改脚本中的 Neo4j 连接配置

> 注意：当前代码文件里写死了 Neo4j 账号和密码，实际使用前建议改为你自己的本地配置，不要直接提交真实密码。

### 8. 评估

脚本：

- `knowledgeGraph/evaluation/generate_gold_standard.py`
- `knowledgeGraph/evaluation/evaluate.py`

输出：

- `knowledgeGraph/evaluation/gold_annotations.json`
- `knowledgeGraph/evaluation/metrics_report.md`

说明：

- 当前金标准为脚本抽样生成的协议化评测集
- 更适合课程展示与流程打通
- 如果用于更严谨的研究或论文场景，建议替换为人工标注金标准

## 当前结果概况

根据现有评测报告 `knowledgeGraph/evaluation/metrics_report.md`：

- Precision：78.64%
- Recall：83.85%
- F1：81.16%

说明：以上结果依赖当前 `triples.json` 与金标准生成策略，重新运行后可能会变化。


## 注意事项

1. 仓库根目录和项目脚本目录不是同一层，执行脚本前请先进入 `knowledgeGraph/`。
2. `pdf_parser.py` 使用的是 `knowledgeGraph/data/`，不是仓库根目录下的 `data/`。
3. `graph/neo4j_builder.py` 默认会清空 Neo4j 数据库，请谨慎使用。
4. 当前评估脚本使用的是协议化生成金标准，不等同于严格人工标注评测。
5. 当前仓库没有统一依赖文件，后续建议补充 `requirements.txt` 以便复现。

## 后续可改进方向

- 为扫描版 PDF 增加 OCR 分支
- 补充 `requirements.txt`
- 将 Neo4j 配置改为环境变量或配置文件读取
- 增加命令行参数，减少脚本中的硬编码路径
- 将评估集升级为人工标注数据
- 补充一个统一的一键执行入口

## 参考文档

- [knowledgeGraph/知识图谱完整技术报告.md](knowledgeGraph/知识图谱完整技术报告.md)
