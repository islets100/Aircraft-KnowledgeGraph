import os
import glob
import re
import json

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(WORKSPACE_DIR, "output", "sentences")
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "output", "sentences_cleaned")

def clean_sentence(text):
    """
    对句子进行深度清洗降噪
    """
    if not text:
        return text

    # 1. 清除学术论文的“幽灵引用”，例如 [12], [1-3], [1, 2]
    # 但要小心别把正常的括号删了
    text = re.sub(r'\[\s*\d+\s*(?:-\s*\d+\s*|,\s*\d+\s*)*\]', '', text)
    
    # 2. 清除图表引导符，例如 (如图3-1所示), （见表2）
    text = re.sub(r'[（\(](?:如图|见图|图|表|见表).*?[）\)]', '', text)
    
    # 3. 中英文标点规范化
    punctuation_map = {
        ',': '，',
        '(': '（',
        ')': '）',
        ':': '：',
        ';': '；',
        '?': '？',
        '!': '！'
    }
    for eng_punc, zh_punc in punctuation_map.items():
        text = text.replace(eng_punc, zh_punc)
        
    # 4. 消除异常的内嵌空格 (由于PDF排版导致的分离)
    # 为防止把英文单词连在一起(如 "PID Controller" 变成 "PIDController")，
    # 我们可以稍微安全一点，只去除中文之间的空格，也可以直接全局去除所有空白符。
    # 这里我们采用全局去除所有空白符的简单粗暴但有效的方式。
    text = re.sub(r'\s+', '', text)
    
    return text

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    search_pattern = os.path.join(INPUT_DIR, "*.jsonl")
    jsonl_files = glob.glob(search_pattern)

    print(f"找到 {len(jsonl_files)} 个句子文件准备进行深度清洗...")

    total_cleaned = 0
    for idx, file_path in enumerate(jsonl_files):
        doc_name = os.path.basename(file_path)
        out_file = os.path.join(OUTPUT_DIR, doc_name)
        
        valid_count = 0
        with open(file_path, 'r', encoding='utf-8') as f_in, \
             open(out_file, 'w', encoding='utf-8') as f_out:
            
            for line in f_in:
                if not line.strip():
                    continue
                record = json.loads(line)
                original_sentence = record.get("sentence", "")
                
                cleaned_sentence = clean_sentence(original_sentence)
                
                # 清洗完如果太短(比如变成了空白)就过滤掉
                if len(cleaned_sentence) > 3:
                    record["sentence"] = cleaned_sentence
                    f_out.write(json.dumps(record, ensure_ascii=False) + '\n')
                    valid_count += 1
        
        total_cleaned += valid_count
        print(f"[{idx+1}/{len(jsonl_files)}] {doc_name}: 生成清洗后句子 {valid_count} 个")

    print(f"\n全部清洗完成！共保留 {total_cleaned} 个高质量句子，存放在 {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
