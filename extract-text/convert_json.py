import re
import json
from pathlib import Path

def process_chunk(chunk_id, day, path, lines):
    """处理单个chunk并生成JSON结构"""
    text_lines = []
    roles = set()
    
    # 正则匹配角色对话
    role_pattern = re.compile(r'^(\w+):\s*(.+)$')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 解析角色对话
        match = role_pattern.match(line)
        if match:
            role, dialogue = match.groups()
            if role != "extend":
                roles.add(role)
            text_lines.append(line)
        else:
            # 旁白处理
            text_lines.append(line)
    
    return {
        "chunk_id": chunk_id,
        "day": day,
        "path": path,
        "text": "\n".join(text_lines),
        "roles": sorted(roles)
    }

def convert_files(input_dir, output_dir):
    """转换目录下所有文件"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    chunks = []
    current_chunk = []
    chunk_counter = 0

    
    for zh_file in input_path.glob("day*.txt"):
        # 解析天数
        match = re.fullmatch(r'day(\d+)(.*?)$', zh_file.stem)
        if not match:
            print(zh_file.stem)
            continue
            
        day = int(match.group(1))
        path = match.group(2)  # 提取路径标识如 AB/FG
        print(day, path)
        # 读取文件内容
        with open(zh_file, 'r', encoding='utf-8') as f:
            content = f.read().splitlines()
        
        for line in content:
            # 检测chunk开始
            if line.startswith("CHUNK"):
                if current_chunk:
                    chunk_counter += 1
                    c = process_chunk(chunk_counter, day, path, current_chunk)
                    if len(c["text"]):
                        chunks.append(c)
                    current_chunk = []
                continue
            current_chunk.append(line)
        
        # 处理最后一个chunk
        if current_chunk:
            chunk_counter += 1
            c = process_chunk(chunk_counter, day, path, current_chunk)
            if len(c["text"]):
                chunks.append(c)
        
    # 写入JSON文件
    output_file = output_path / f"dialogs.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    convert_files("output/zh", "output/json")