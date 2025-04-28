import re
from pathlib import Path

def process_lines(lines, is_translation=False):
    """
    解析给定行列表，提取对话和旁白条目。
    Returns: list of (type, role, text)
    """
    entries = []
    dialogue_pattern = re.compile(r'^\s*(\w+)\s+"(.*?)"')
    narration_pattern = re.compile(r'^\s*"(.*?)"')
    for line in lines:
        dialogue_match = dialogue_pattern.match(line)
        if dialogue_match:
            role, content = dialogue_match.group(1), dialogue_match.group(2)
            if is_translation and '\\n' in content:
                content = content.split('\\n', 1)[1].strip()
            entries.append(('dialogue', role, content.strip()))
            continue
        narration_match = narration_pattern.match(line)
        if narration_match:
            content = narration_match.group(1)
            if is_translation and '\\n' in content:
                content = content.split('\\n', 1)[1].strip()
            entries.append(('narration', None, content.strip()))
    return entries

def process_trans_lines(lines):
    """
    解析给定行列表，提取对话和旁白条目。
    Returns: list of (type, role, text)
    """
    entries = []
    dialogue_pattern = re.compile(r'^\s*(\w+)\s+"(.*?)"')
    narration_pattern = re.compile(r'^\s*"(.*?)"')
    for line in lines:
        dialogue_match = dialogue_pattern.match(line)
        if dialogue_match:
            role, content = dialogue_match.group(1), dialogue_match.group(2)
            sp = content.split('\\n', 1)
            if len(sp) == 2:
                orig, trans = sp
                entries.append(('dialogue', role, orig.strip(), trans.strip()))
            continue
        narration_match = narration_pattern.match(line)
        if narration_match:
            content = narration_match.group(1)
            sp = content.split('\\n', 1)
            if len(sp) == 2:
                orig, trans = sp
                entries.append(('narration', None, orig.strip(), trans.strip()))
    return entries


def extract_dialogue():
    base_dir = Path("unpack-rpy")
    translation_dir = base_dir / "tl" / "chinese"
    output_dir = Path("o")
    output_dir.mkdir(exist_ok=True)
    (output_dir / "en").mkdir(exist_ok=True)
    (output_dir / "zh").mkdir(exist_ok=True)

    for main_file in base_dir.glob("Day*.rpy"):
        match = re.search(r'Day\s*(11\sA\+B)', main_file.name)
        if not match:
            continue
        day = match.group(1)
        print(day)
        # 读取主文件和翻译文件所有行
        main_lines = main_file.read_text(encoding='utf-8').splitlines()
        trans_path = translation_dir / main_file.name
        trans_entries = []
        if trans_path.exists():
            trans_entries = process_trans_lines(
                trans_path.read_text(encoding='utf-8').splitlines())

        # 根据连续且相同的缩进分块
        chunks = []
        current_chunk = []
        current_indent = None
        for line in main_lines:
            if not line.strip():
                # 空行也加入当前块
                if current_chunk is not None:
                    current_chunk.append(line)
                continue
            indent = len(line) - len(line.lstrip(' '))
            if current_indent is None:
                current_indent = indent
                current_chunk = [line]
            elif indent == current_indent:
                current_chunk.append(line)
            else:
                chunks.append(current_chunk)
                current_indent = indent
                current_chunk = [line]
        if current_chunk:
            chunks.append(current_chunk)
        print("file ", day, len(trans_entries), ", chunks", len(chunks), max([len(chunk) for chunk in chunks]))
        # 处理每个块，生成输出
        en_lines = []
        zh_lines = []
        for idx, chunk in enumerate(chunks, start=1):
            # 标注 CHUNK
            en_lines.append(f"CHUNK {idx}")
            zh_lines.append(f"CHUNK {idx}")
            # 解析条目
            main_entries = process_lines(chunk)
            # 对齐翻译条目
            for m_type, m_role, m_text in main_entries:
                # 获取对应翻译
                for t_type, t_role, t_orig, t_text in trans_entries:

                    # 只配对相同类型和角色
                    if ((m_type == t_type and m_role == t_role) or m_role == "extend") and m_text == t_orig:
                        if m_type == 'dialogue':
                            en_lines.append(f"{m_role}: {m_text}")
                            zh_lines.append(f"{m_role}: {t_text}")
                        else:
                            en_lines.append(m_text)
                            zh_lines.append(t_text)
                        break
                else:
                    # 如果不匹配，只输出英文，并保持翻译索引不变
                    if m_type == 'dialogue':
                        en_lines.append(f"{m_role}: {m_text}")
                        zh_lines.append('')
                    else:
                        en_lines.append(m_text)
                        zh_lines.append('')

        print(len(en_lines))
        # 写入文件
        en_path = output_dir / 'en' / f"day{day}.txt"
        zh_path = output_dir / 'zh' / f"day{day}.txt"
        print(en_path, zh_path)
        en_path.write_text("\n".join(en_lines), encoding='utf-8')
        zh_path.write_text("\n".join(zh_lines), encoding='utf-8')

if __name__ == '__main__':
    extract_dialogue()
