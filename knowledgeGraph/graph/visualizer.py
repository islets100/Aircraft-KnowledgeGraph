import os
import json
import webbrowser

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIPLES_FILE = os.path.join(base_dir, 'output', 'triples.json')
OUTPUT_DIR = os.path.join(base_dir, 'output')

def visualize_3d_graph(max_nodes=1000, output_file="graph_3d.html"):
    if not os.path.exists(TRIPLES_FILE):
        print(f"找不到 triples.json，请先运行抽取代码！")
        return
        
    with open(TRIPLES_FILE, 'r', encoding='utf-8') as f:
        triples = json.load(f)

    # 统计实体频次
    entity_freq = {}
    for t in triples:
        entity_freq[t["source_name"]] = entity_freq.get(t["source_name"], 0) + 1
        entity_freq[t["target_name"]] = entity_freq.get(t["target_name"], 0) + 1

    top_entities = set(e for e, _ in sorted(entity_freq.items(), key=lambda x: -x[1])[:max_nodes])

    # 组装供 force-graph 解析的节点与边
    nodes = []
    links = []
    added_nodes = set()

    for t in triples:
        s, t_node = t["source_name"], t["target_name"]
        if s in top_entities and t_node in top_entities:
            if s not in added_nodes:
                nodes.append({"id": s, "name": s, "group": t.get("source_type", "Concept"), "val": (entity_freq[s]**0.5)*2})
                added_nodes.add(s)
            if t_node not in added_nodes:
                nodes.append({"id": t_node, "name": t_node, "group": t.get("target_type", "Concept"), "val": (entity_freq[t_node]**0.5)*2})
                added_nodes.add(t_node)
            
            links.append({
                "source": s,
                "target": t_node,
                "label": t["relation"]
            })

    graph_data = {"nodes": nodes, "links": links}

    # 这是基于 WebGL 的 3D 渲染核心代码
    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>星图：空天飞行器与维保 3D全网知识域</title>
    <style>
        body { margin: 0; padding: 0; overflow: hidden; background-color: #050510; }
        #graph-container { width: 100vw; height: 100vh; }
        #ui-panel {
            position: absolute;
            top: 20px;
            left: 20px;
            color: #0ff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: rgba(10, 20, 40, 0.85);
            padding: 20px;
            border-left: 4px solid #0ff;
            border-radius: 4px;
            pointer-events: none;
            box-shadow: 0 0 15px rgba(0,255,255,0.2);
            z-index: 999;
        }
        h1 { margin: 0 0 10px 0; font-size: 20px; text-transform: uppercase; letter-spacing: 2px;}
        p { margin: 5px 0; font-size: 13px; color: #ccc; }
        .highlight { color: #fff; font-weight: bold; }
    </style>
    <script src="https://unpkg.com/3d-force-graph"></script>
</head>
<body>
    <div id="ui-panel">
        <h1>星图·空天与维保 3D知识域</h1>
        <p>基于原生三元组动态生成的3D引力知识库</p>
        <p>当前渲染节点数: """ + str(len(nodes)) + """</p>
        <p>当前渲染结构边: """ + str(len(links)) + """</p>
        <p><br/><span class="highlight">引力场漫游交互指南：</span></p>
        <p>• [视角缩放] 滚动实体鼠标滚轮</p>
        <p>• [视角旋转] 按住左键拖拽旋转</p>
        <p>• [水平位移] 按住右键拖拽画幅</p>
        <p>• [锁定追踪] 左键点击某节点自动贴近追踪</p>
    </div>
    <div id="graph-container"></div>

    <script>
        const gData = """ + json.dumps(graph_data, ensure_ascii=False) + """;
        
        const element = document.getElementById('graph-container');
        const Graph = ForceGraph3D()(element)
            .graphData(gData)
            .nodeAutoColorBy('group')
            .nodeVal('val')
            .nodeLabel(node => `${node.name} [${node.group}]`)
            .linkWidth(0.6)
            .linkOpacity(0.3)
            .linkDirectionalArrowLength(4)
            .linkDirectionalArrowRelPos(1)
            .linkDirectionalParticles(2)
            .linkDirectionalParticleSpeed(d => 0.005)
            .onNodeClick(node => {
                // 点击自动飞行靠近
                const distance = 80;
                const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
                const newPos = (node.x || node.y || node.z)
                    ? { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }
                    : { x: 0, y: 0, z: distance };
                Graph.cameraPosition(newPos, node, 2000);
            });
    </script>
</body>
</html>"""

    output_path = os.path.join(OUTPUT_DIR, output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
        
    print(f"\n=========================================")
    print(f"3D引擎渲染完毕，不仅彻底解决了重叠，效果也远超普通2D散点！")
    print(f"可视化已自动保存到: {output_path}")
    print(f"=========================================\n")
    try:
        webbrowser.open('file://' + os.path.realpath(output_path))
    except:
        pass

if __name__ == "__main__":
    visualize_3d_graph()