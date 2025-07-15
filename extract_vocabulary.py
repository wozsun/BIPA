#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
词汇提取工具

用法：
1. 导出所有BIPA3词汇文件：
   python3 extract_vocabulary.py

2. 导出指定文件的词汇：
   python3 extract_vocabulary.py "BIPA/BIPA3/1.Simak/Kosakata/某个文件.md"
   或使用绝对路径：
   python3 extract_vocabulary.py "/完整路径/某个文件.md"

示例：
   python3 extract_vocabulary.py "BIPA/BIPA3/1.Simak/Kosakata/U1.md"
"""

import os
import re
import glob
import sys
from collections import defaultdict
from datetime import datetime

def extract_chinese_translations(text):
    """从文本中提取中文翻译，按英文定义分组"""
    translation_groups = []  # 每个元素是一个词义组（对应一个英文定义）
    lines = text.split('\n')
    current_group_translations = []

    for line in lines:
        line = line.strip()

        # 如果是英文行，结束当前组并开始新组
        if line and not re.search(r'[\u4e00-\u9fff]', line):
            if current_group_translations:
                translation_groups.append(current_group_translations)
                current_group_translations = []
            continue

        # 如果是中文行，添加到当前组
        if re.search(r'[\u4e00-\u9fff]', line):
            # 按中文逗号分割同义词
            if '，' in line:
                # 分割时要考虑括号内的内容不被分割
                parts = []
                current_part = ""
                paren_level = 0

                i = 0
                while i < len(line):
                    char = line[i]
                    if char in '（(':
                        paren_level += 1
                        current_part += char
                    elif char in '）)':
                        paren_level -= 1
                        current_part += char
                    elif char == '，' and paren_level == 0:
                        if current_part.strip():
                            parts.append(current_part.strip())
                        current_part = ""
                    else:
                        current_part += char
                    i += 1

                if current_part.strip():
                    parts.append(current_part.strip())

                current_group_translations.extend(parts)
            else:
                # 整行作为一个翻译
                current_group_translations.append(line.strip())

    # 添加最后一个组
    if current_group_translations:
        translation_groups.append(current_group_translations)

    return translation_groups

def extract_vocabulary_from_file(file_path):
    """从单个文件中提取词汇"""
    vocabulary = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return vocabulary

    # 按 # 分割内容，每个部分对应一个单词
    sections = content.split('\n# ')

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().split('\n')
        if not lines:
            continue

        # 第一行是印尼语单词（可能包含前导的#）
        indonesian_word = lines[0].replace('#', '').strip()
        if not indonesian_word or indonesian_word.startswith('---'):
            continue

        # 提取中文翻译
        remaining_text = '\n'.join(lines[1:])
        translation_groups = extract_chinese_translations(remaining_text)

        if translation_groups:
            vocabulary[indonesian_word] = translation_groups

    return vocabulary

def merge_translations(translation_groups_list):
    """合并翻译组，组内去重用中文逗号分隔，组间用中文分号分隔，全局去重重复翻译"""
    if not translation_groups_list:
        return ""

    # 合并所有来源的翻译组
    all_groups = []
    for groups in translation_groups_list:
        all_groups.extend(groups)

    if not all_groups:
        return ""

    # 首先收集所有翻译进行全局"的"字处理
    all_translations = []
    for group in all_groups:
        if group:
            all_translations.extend(group)

    # 全局处理"的"字去重
    unique_translations = []
    seen = set()
    for trans in all_translations:
        if trans not in seen:
            unique_translations.append(trans)
            seen.add(trans)

    # 处理"的"字去重（全局范围）
    final_global_translations = []
    used = set()

    for i, trans in enumerate(unique_translations):
        if i in used:
            continue

        # 检查是否有对应的"的"字版本
        de_version = trans + "的"
        non_de_version = trans[:-1] if trans.endswith("的") else None

        # 如果当前词不带"的"，检查是否有带"的"的版本
        if de_version in unique_translations:
            de_index = unique_translations.index(de_version)
            used.add(de_index)
            final_global_translations.append(trans)  # 保留不带"的"的版本
        # 如果当前词带"的"，检查是否有不带"的"的版本
        elif non_de_version and non_de_version in unique_translations:
            non_de_index = unique_translations.index(non_de_version)
            if non_de_index not in used:
                used.add(i)  # 跳过当前带"的"的版本
                continue
            else:
                final_global_translations.append(trans)
        else:
            final_global_translations.append(trans)

        used.add(i)

    # 创建全局去重后的翻译集合
    global_unique_set = set(final_global_translations)

    # 处理每个组，保持组的结构但只保留全局去重后的翻译
    processed_groups = []

    for group in all_groups:
        if not group:
            continue

        # 过滤组内翻译，只保留全局去重后存在的翻译
        group_translations = []
        for trans in group:
            if trans in global_unique_set:
                group_translations.append(trans)
                # 从全局集合中移除，避免在后续组中重复出现
                global_unique_set.discard(trans)

        if group_translations:
            processed_groups.append('，'.join(group_translations))

    # 使用中文分号连接不同的组
    return '；'.join(processed_groups)

def export_single_file_vocabulary(file_path):
    """导出单个文件的词汇"""
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return

    print(f"处理文件: {file_path}")
    vocab = extract_vocabulary_from_file(file_path)

    if not vocab:
        print("文件中没有找到词汇")
        return

    print(f"从文件中提取到 {len(vocab)} 个印尼语单词")

    # 生成markdown表格
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    markdown_content = f"""**文件词汇统计：**

- 源文件：{os.path.basename(file_path)}
- 词汇数量：{len(vocab)} 个
- 提取时间：{datetime.now().strftime('%Y年%m月%d日')}

| 印尼语 | 中文翻译 |
|--------|----------|
"""

    # 按字母顺序排序
    for word in sorted(vocab.keys()):
        translations = merge_translations([vocab[word]])
        markdown_content += f"| {word} | {translations} |\n"

    # 保存到同目录下，文件名加上_vocabulary后缀
    output_path = os.path.join(os.path.dirname(file_path), f"{file_name}_vocabulary.md")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"单文件词汇表已保存到: {output_path}")
    print(f"共包含 {len(vocab)} 个单词")

    return output_path

def main():
    # 检查帮助参数
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print("""
词汇提取工具使用说明：

1. 导出所有BIPA3词汇文件：
   python3 extract_vocabulary.py

2. 导出指定文件的词汇：
   python3 extract_vocabulary.py "文件路径/文件名.md"

示例：
   python3 extract_vocabulary.py "BIPA/BIPA2/3.Baca/Kosakata/U1.md"

输出：
- 单文件导出：在源文件同目录下生成 "文件名_vocabulary.md"
- 全部文件导出：在BIPA3目录下生成 "Kosakata.md"
        """)
        return

    # 检查命令行参数
    if len(sys.argv) > 1:
        # 如果提供了文件路径参数，导出单个文件
        file_path = sys.argv[1]
        if not os.path.isabs(file_path):
            # 如果是相对路径，转换为绝对路径
            base_path = "/Users/wozsun/Library/Mobile Documents/iCloud~md~obsidian/Documents/Docs"
            file_path = os.path.join(base_path, file_path)

        export_single_file_vocabulary(file_path)
        return

    # 默认行为：查找所有BIPA3下的词汇文件
    base_path = "/Users/wozsun/Library/Mobile Documents/iCloud~md~obsidian/Documents/Docs/BIPA/BIPA3"
    vocab_files = glob.glob(os.path.join(base_path, "**/Kosakata/*.md"), recursive=True)

    print(f"找到 {len(vocab_files)} 个词汇文件")

    if not vocab_files:
        print("没有找到任何词汇文件！")
        print(f"搜索路径: {base_path}")
        return

    # 合并所有词汇
    all_vocabulary = defaultdict(list)

    for file_path in vocab_files:
        print(f"处理文件: {os.path.basename(file_path)}")
        vocab = extract_vocabulary_from_file(file_path)

        for word, translation_groups in vocab.items():
            all_vocabulary[word].extend(translation_groups)

    print(f"总共提取到 {len(all_vocabulary)} 个印尼语单词")

    # 生成markdown表格
    markdown_content = f"""**统计信息：**

- 总词汇数量：{len(all_vocabulary)} 个
- 提取时间：{datetime.now().strftime('%Y年%m月%d日')}

| 印尼语 | 中文翻译 |
|--------|----------|
"""

    # 按字母顺序排序
    for word in sorted(all_vocabulary.keys()):
        translations = merge_translations([all_vocabulary[word]])
        markdown_content += f"| {word} | {translations} |\n"

    # 保存到BIPA3目录
    output_path = "/Users/wozsun/Library/Mobile Documents/iCloud~md~obsidian/Documents/Docs/BIPA/BIPA3/Kosakata.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"词汇表已保存到: {output_path}")
    print(f"共包含 {len(all_vocabulary)} 个单词")

if __name__ == "__main__":
    main()
