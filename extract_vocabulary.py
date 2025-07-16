#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob
import sys
from collections import defaultdict
from datetime import datetime

def extract_chinese_translations(text):
    """
    从文本中提取中文翻译，按英文定义分组

    参数:
        text (str): 包含中英文混合内容的文本

    返回:
        list: 翻译组列表，每个组包含同一英文定义下的所有中文翻译

    处理逻辑:
        - 英文行作为分组标志，中文行为翻译内容
        - 支持中文逗号分隔的同义词
        - 智能处理括号内容，避免错误分割
    """
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

def add_vocabulary_to_file(file_path, vocabulary):
    """
    将生成的词汇表直接插入到原词汇文件中

    参数:
        file_path (str): 目标文件的绝对路径
        vocabulary (dict): 词汇字典，键为印尼语单词，值为翻译组列表

    功能说明:
        - 在YAML front matter之后插入词汇表
        - 如果文件已存在词汇表，则替换为新版本
        - 词汇表使用加粗标题和Markdown表格格式
        - 词汇按字母顺序排序
        - 自动处理文件编码和错误情况
    """
    if not vocabulary:
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # 生成词汇表内容
        vocab_content = "\n**词汇表**\n\n| 印尼语 | 中文翻译 |\n|--------|----------|\n"

        # 按字母顺序排序
        for word in sorted(vocabulary.keys()):
            translations = merge_translations([vocabulary[word]])
            vocab_content += f"| {word} | {translations} |\n"

        vocab_content += "\n---\n"

        # 找到YAML front matter的结束位置
        if original_content.startswith('---\n'):
            end_pos = original_content.find('\n---\n', 4)
            if end_pos != -1:
                # 在YAML front matter之后插入词汇表
                yaml_part = original_content[:end_pos + 5]  # 包含结束的---\n
                rest_content = original_content[end_pos + 5:]

                # 检查是否已经存在词汇表，如果存在则替换
                if "**词汇表**" in rest_content:
                    # 找到词汇表的结束位置（下一个---或文件末尾）
                    vocab_start = rest_content.find("**词汇表**")
                    vocab_end = rest_content.find("\n---\n", vocab_start)
                    if vocab_end == -1:
                        # 如果找不到结束标记，查找下一个#标题
                        vocab_end = rest_content.find("\n# ", vocab_start)
                        if vocab_end == -1:
                            vocab_end = len(rest_content)
                    else:
                        vocab_end += 5  # 包含\n---\n

                    # 替换现有词汇表
                    new_content = yaml_part + vocab_content + rest_content[vocab_end:]
                else:
                    # 添加新词汇表
                    new_content = yaml_part + vocab_content + rest_content

                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                print(f"词汇表已添加到文件: {file_path}")
    except Exception as e:
        print(f"添加词汇表到文件时出错: {e}")

def extract_vocabulary_from_file(file_path):
    """
    从单个Markdown词汇文件中提取所有词汇条目

    参数:
        file_path (str): 词汇文件的绝对路径

    返回:
        dict: 词汇字典，键为印尼语单词，值为该单词的所有翻译组

    文件格式要求:
        - 使用"# 单词名"格式标记每个词条
        - 词条内容包含中英文混合的释义
        - 支持多行翻译和英文定义分组
        - 自动忽略YAML front matter和无效内容
    """
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
    """
    智能合并多个来源的翻译组，去除重复并优化格式

    参数:
        translation_groups_list (list): 翻译组列表的列表

    返回:
        str: 合并后的翻译字符串，组内用逗号分隔，组间用分号分隔

    处理规则:
        1. 全局去重：移除完全重复的翻译
        2. "的"字优化：保留不带"的"的版本，去除重复的带"的"版本
        3. 保持分组结构：不同英文定义的翻译用分号分隔
        4. 组内同义词：用中文逗号连接

    示例:
        输入: [["好的", "良好"], ["好", "不错的"]]
        输出: "好，良好；不错"
    """
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

def main():
    # 检查帮助参数
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              BIPA印尼语词汇提取工具
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 功能特性：
   • 自动提取Markdown词汇文件中的印尼语-中文词汇对
   • 保持按英文定义分组的复杂词汇结构
   • 智能处理多义词并自动去除重复翻译
   • 自动为所有词汇文件嵌入词汇表并生成汇总文件

🚀 使用方法：

1️⃣  批量处理所有BIPA3词汇文件：
   python3 extract_vocabulary.py

   • 扫描BIPA3目录下所有词汇文件
   • 生成汇总词汇表：BIPA3/Kosakata.md
   • 自动为所有词汇文件嵌入词汇表

📄 文件格式要求：
   • 词汇文件使用"# 单词名"标记词条

📊 输出格式：
   • 汇总文件：BIPA3目录下的"Kosakata.md"
   • 自动嵌入：为所有词汇文件嵌入词汇表

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)
        return

    # 查找所有BIPA3下的词汇文件
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

        # 为所有文件添加词汇表
        if vocab:
            add_vocabulary_to_file(file_path, vocab)
            print(f"  - 已添加词汇表到文件内")

        for word, translation_groups in vocab.items():
            all_vocabulary[word].extend(translation_groups)

    print(f"总共提取到 {len(all_vocabulary)} 个印尼语单词")

    # 生成markdown表格
    markdown_content = f"""**统计信息：**

- 总词汇数量：{len(all_vocabulary)} 个
- 提取时间：{datetime.now().strftime('%Y年%m月%d日')}
- 处理文件数：{len(vocab_files)} 个

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
    print(f"已为 {len(vocab_files)} 个文件添加了词汇表")

if __name__ == "__main__":
    main()
