#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob
from collections import defaultdict
from datetime import datetime

def extract_chinese_translations(text):
    """从文本中提取中文翻译"""
    chinese_translations = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        # 直接跳过所有英文行
        if not re.search(r'[\u4e00-\u9fff]', line):
            continue

        # 匹配包含中文字符的行
        if re.search(r'[\u4e00-\u9fff]', line):
            # 先按分号分割（不同含义的分隔符）
            major_parts = re.split(r'[；]', line)

            for major_part in major_parts:
                major_part = major_part.strip()
                if not major_part:
                    continue

                # 提取完整的中文部分（包括中文括号）
                chinese_match = re.search(r'[\u4e00-\u9fff][^；]*', major_part)
                if chinese_match:
                    chinese_text = chinese_match.group().strip()

                    # 只按逗号分割同义词（保持括号完整）
                    sub_parts = []
                    current_part = ""
                    paren_level = 0

                    for char in chinese_text:
                        if char in '（(':
                            paren_level += 1
                            current_part += char
                        elif char in '）)':
                            paren_level -= 1
                            current_part += char
                        elif char == '，' and paren_level == 0:
                            if current_part.strip():
                                sub_parts.append(current_part.strip())
                            current_part = ""
                        else:
                            current_part += char

                    if current_part.strip():
                        sub_parts.append(current_part.strip())

                    for part in sub_parts:
                        part = part.strip()
                        if part and len(re.sub(r'[（）()]', '', part)) > 1:  # 至少包含2个非括号字符
                            chinese_translations.append(part)

    return chinese_translations

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
        chinese_translations = extract_chinese_translations(remaining_text)

        if chinese_translations:
            vocabulary[indonesian_word] = chinese_translations

    return vocabulary

def merge_translations(translations_list):
    """合并翻译，相近的用逗号分隔，不同意思的用分号分隔"""
    # 去重但保持顺序
    unique_translations = []
    seen = set()
    for trans in translations_list:
        if trans not in seen:
            unique_translations.append(trans)
            seen.add(trans)

    if len(unique_translations) <= 1:
        return '，'.join(unique_translations)

    # 智能分组：根据词汇的语义相似性分组
    # 简单的分组策略：检查是否有相同的字符或词根
    meaning_groups = []
    used = set()

    for i, trans in enumerate(unique_translations):
        if i in used:
            continue

        current_group = [trans]
        used.add(i)

        # 寻找相似的翻译
        for j, other_trans in enumerate(unique_translations):
            if j <= i or j in used:
                continue

            # 检查相似性（更严格的条件）
            similar = False

            # 0. 特殊处理：只是多了一个"的"字的情况
            if trans + "的" == other_trans:
                # 保留不带"的"的版本，标记other_trans为相似但不添加
                similar = True
            elif other_trans + "的" == trans:
                # 如果当前词是带"的"的版本，替换为不带"的"的版本
                current_group[0] = other_trans
                similar = True

            # 1. 一个是另一个的子串（长度差不超过3）
            elif (trans in other_trans or other_trans in trans) and abs(len(trans) - len(other_trans)) <= 3:
                similar = True

            # 2. 有较多共同字符且长度相近
            elif abs(len(trans) - len(other_trans)) <= 2:
                common_chars = set(trans) & set(other_trans)
                # 共同字符数量占较短词汇的比例超过60%
                shorter_len = min(len(trans), len(other_trans))
                if len(common_chars) >= max(2, shorter_len * 0.6):
                    similar = True

            # 3. 包含相同的词根（至少3个连续字符）
            elif len(trans) >= 3 and len(other_trans) >= 3:
                for k in range(len(trans) - 2):
                    if trans[k:k+3] in other_trans:
                        similar = True
                        break

            if similar:
                # 对于"的"字情况，只标记为已使用，不添加到组中
                if not (trans + "的" == other_trans or other_trans + "的" == trans):
                    current_group.append(other_trans)
                used.add(j)

        if current_group:
            meaning_groups.append('，'.join(current_group))

    return '；'.join(meaning_groups)

def main():
    # 查找所有BIPA3下的词汇文件
    base_path = "/Users/wozsun/Library/Mobile Documents/iCloud~md~obsidian/Documents/Docs/BIPA/BIPA3"
    vocab_files = glob.glob(os.path.join(base_path, "**/Kosakata/*.md"), recursive=True)

    print(f"找到 {len(vocab_files)} 个词汇文件")

    # 合并所有词汇
    all_vocabulary = defaultdict(list)

    for file_path in vocab_files:
        print(f"处理文件: {os.path.basename(file_path)}")
        vocab = extract_vocabulary_from_file(file_path)

        for word, translations in vocab.items():
            all_vocabulary[word].extend(translations)

    print(f"总共提取到 {len(all_vocabulary)} 个印尼语单词")

    # 生成markdown表格
    markdown_content = f"""# BIPA3 Kosakata

**统计信息：**

- 总词汇数量：{len(all_vocabulary)} 个
- 提取时间：{datetime.now().strftime('%Y年%m月%d日')}

| 印尼语 | 中文翻译 |
|--------|----------|
"""

    # 按字母顺序排序
    for word in sorted(all_vocabulary.keys()):
        translations = merge_translations(all_vocabulary[word])
        markdown_content += f"| {word} | {translations} |\n"

    # 保存到BIPA3目录
    output_path = "/Users/wozsun/Library/Mobile Documents/iCloud~md~obsidian/Documents/Docs/BIPA/BIPA3/Kosakata.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"词汇表已保存到: {output_path}")
    print(f"共包含 {len(all_vocabulary)} 个单词")

if __name__ == "__main__":
    main()
