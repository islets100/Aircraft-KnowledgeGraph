import os
import re
import json
import fitz  # PyMuPDF

# 配置路径，适配当前 KnowledgeGraph 的目录结构
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "extracted_text")

# 判断是否为纯图片扫描件的阈值 (每页平均字符数)
MIN_TEXT_AVG = 50

def get_domain_from_path(filepath):
    """从路径中推断所属领域"""
    if "变构飞行器" in filepath:
        return "变构飞行器"
    elif "维修类" in filepath:
        return "维修类"
    elif "飞行器" in filepath:
        return "飞行器"
    return "其他"

def is_text_pdf(filepath):
    """
    判断PDF是否可以直接提取文本(非纯扫描件)。
    抽样前几页，如果提取出来的文字太少，就认为是扫描件。
    """
    try:
        doc = fitz.open(filepath)
        n = min(10, doc.page_count)
        if n == 0:
            doc.close()
            return False
        
        total_chars = sum(len(doc[i].get_text().strip()) for i in range(n))
        avg = total_chars / n
        doc.close()
        return avg > MIN_TEXT_AVG
    except Exception:
        return False

def clean_text(text):
    """文本基础清洗"""
    # 去除独立的页码行 
    text = re.sub(r'\n\s*-?\s*\d+\s*-?\s*\n', '\n', text)
    # 尝试把被断行的句子合并
    text = re.sub(r'(?<=[一-鿿])\n(?=[一-鿿])', '', text)
    # 将3个以上的换行压缩为2个（段落分隔）
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 将多个空格压缩为1个
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def process_pdf(filepath):
    """逐页解析单个PDF"""
    doc = fitz.open(filepath)
    text_blocks = []
    
    for page in doc:
        page_text = page.get_text()
        if page_text.strip():
            text_blocks.append(page_text)
            
    doc.close()
    
    raw_text = "\n".join(text_blocks)
    return clean_text(raw_text)

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    catalog = []
    stats = {"total": 0, "extracted": 0, "scanned_skip": 0, "error": 0}
    
    print(f"开始遍历目录: {DATA_DIR} ...")
    
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if not file.lower().endswith(".pdf"):
                continue
                
            stats["total"] += 1
            filepath = os.path.join(root, file)
            domain = get_domain_from_path(filepath)
            
            safe_filename = file.replace(" ", "_").replace(".pdf", ".txt")
            out_filename = f"{domain}_{safe_filename}"
            out_filepath = os.path.join(OUTPUT_DIR, out_filename)
            
            # --- 实时输出策略 ---
            if os.path.exists(out_filepath):
                print(f"  [跳过已存在] {file}")
                stats["extracted"] += 1
                continue
                
            if not is_text_pdf(filepath):
                print(f"  [跳过扫描版] {file}")
                stats["scanned_skip"] += 1
                catalog.append({"file": file, "domain": domain, "status": "scanned_skipped"})
                continue
                
            print(f"  [处理中] {file} ...", end="", flush=True)
            
            try:
                text = process_pdf(filepath)
                # 边解析边写入磁盘
                with open(out_filepath, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f" 完成! {len(text)} 字符")
                stats["extracted"] += 1
                catalog.append({"file": file, "domain": domain, "status": "success", "chars": len(text)})
                
            except Exception as e:
                print(f" 失败! {e}")
                stats["error"] += 1
                catalog.append({"file": file, "domain": domain, "status": "error"})
                
    # 汇总输出
    catalog_path = os.path.join(OUTPUT_DIR, "catalog.json")
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        
    print("\n===== 提取汇总 =====")
    print(f"总计PDF: {stats['total']} 个")
    print(f"成功提取: {stats['extracted']} 个")
    print(f"跳过扫描: {stats['scanned_skip']} 个")
    if stats["error"] > 0:
        print(f"处理失败: {stats['error']} 个")

if __name__ == "__main__":
    main()