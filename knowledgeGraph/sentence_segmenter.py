import os
import glob
import re
import json

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(WORKSPACE_DIR, "output", "extracted_text")
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "output", "sentences")

def split_into_sentences(text):
    """
    按照中文标点符号进行分句
    """
    # 按照断句符切分，并保留标点符号
    text = re.sub(r'([。！？；!?;\n])', r'\1\n', text)
    # 按行分割
    sentences = text.split('\n')
    # 清洗：去空白，过滤过短句子
    valid_sentences = []
    for s in sentences:
        s = s.strip()
        if len(s) > 3:  # 过滤非常短的无意义字符
            valid_sentences.append(s)
    return valid_sentences

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    search_pattern = os.path.join(INPUT_DIR, "**", "*.txt")
    txt_files = glob.glob(search_pattern, recursive=True)

    print(f"找到 {len(txt_files)} 个文本文件准备分句...")

    total_sentences = 0
    for idx, file_path in enumerate(txt_files):
        doc_name = os.path.basename(file_path).replace('.txt', '')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        sentences = split_into_sentences(content)
        total_sentences += len(sentences)

        out_file = os.path.join(OUTPUT_DIR, f"{doc_name}.jsonl")
        with open(out_file, 'w', encoding='utf-8') as f_out:
            for s in sentences:
                record = {
                    "doc": doc_name,
                    "sentence": s
                }
                f_out.write(json.dumps(record, ensure_ascii=False) + '\n')
                
        print(f"[{idx+1}/{len(txt_files)}] {doc_name}: 生成 {len(sentences)} 个句子")

    print(f"\n全部完成！共提取 {total_sentences} 个句子，存放在 {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
