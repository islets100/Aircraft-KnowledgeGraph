"""Neo4j 图数据库构建模块"""
import os
import json
from neo4j import GraphDatabase

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIPLES_FILE = os.path.join(base_dir, 'output', 'triples.json')
# 根据个人的Neo4j配置进行修改
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Lsx721099" # 填写密码


class Neo4jBuilder:
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clear_database(self):
        """清空数据库"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("  数据库已清空")

    def create_constraints(self):
        """创建唯一性约束"""
        with self.driver.session() as session:
            entity_types = [
                "Aircraft", "Engine", "Component", "Material", "Parameter",
                "Technology", "Fault", "Maintenance", "Tool", "HydraulicComponent",
                "Software", "PhysicalPhenomenon", "Metric", "ControlSurface",
                "AerodynamicLayout", "Concept", "Location"
            ]
            for etype in entity_types:
                try:
                    session.run(
                        f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{etype}) REQUIRE n.name IS UNIQUE"
                    )
                except Exception as e:
                    print(f"  [Info] 约束 {etype} 已存在或暂无法创建")

    def create_nodes_and_relations(self, triples):
        """一次性事务或者批量执行：采用 MERGE 策略"""
        print(f"开始导入 {len(triples)} 条三元组到 Neo4j...")
        total_rels = 0
        with self.driver.session() as session:
            batch_size = 500
            for i in range(0, len(triples), batch_size):
                batch = triples[i:i + batch_size]
                for t in batch:
                    s_type = t.get("source_type", "Concept")
                    t_type = t.get("target_type", "Concept")
                    rel = t["relation"]
                    
                    query = (
                        f"MERGE (s:{s_type} {{name: $source}}) "
                        f"MERGE (target:{t_type} {{name: $target}}) "
                        f"MERGE (s)-[r:`{rel}`]->(target)"
                    )
                    try:
                        session.run(query,
                                    source=t["source_name"],
                                    target=t["target_name"])
                        total_rels += 1
                    except Exception as e:
                        pass
        return total_rels

    def get_stats(self):
        """获取数据库统计"""
        with self.driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as c").single()["c"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]

        return {
            "total_nodes": node_count,
            "total_relations": rel_count
        }


def build_neo4j_graph():
    """主入口：构建 Neo4j 图数据库"""
    if not os.path.exists(TRIPLES_FILE):
        print(f"找不到文件 {TRIPLES_FILE}！")
        return
        
    with open(TRIPLES_FILE, 'r', encoding='utf-8') as f:
        triples = json.load(f)

    builder = Neo4jBuilder()
    try:
        # 清空
        builder.clear_database()
        # 创建约束
        builder.create_constraints()
        # 导入
        rels_created = builder.create_nodes_and_relations(triples)

        # 统计
        stats = builder.get_stats()
        print(f"\n=========================================")
        print(f"Neo4j 本地库构建/同步完成:")
        print(f"  库中节点总数: {stats['total_nodes']}")
        print(f"  库中关系总数: {stats['total_relations']}")
        print(f"  实际运行写入边: {rels_created}")
        print(f"  您可以打开 Neo4j Browser (http://localhost:7474) 查看知识图谱！")
        print(f"=========================================\n")

        return stats

    except Exception as e:
        print(f"\n[Error] Neo4j 连接失败: {e}")
        print("请确保 Neo4j 服务已启动，并在 graph/neo4j_builder.py 配置了正确的账户和密码 (默认: neo4j/password)。")
        return None
    finally:
        builder.close()


if __name__ == "__main__":
    build_neo4j_graph()