#!/usr/bin/env python3
import os
import re
from collections import OrderedDict

def extract_vocabulary_from_file(file_path):
    """Extract vocabulary from a single markdown file."""
    vocabulary = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split content by # headers (Indonesian words)
        sections = re.split(r'\n# ([^\n]+)', content)
        
        # Skip the first section (usually frontmatter or empty)
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                indonesian_word = sections[i].strip()
                definitions = sections[i + 1].strip()
                
                # Parse the definitions
                lines = definitions.split('\n')
                english_translations = []
                chinese_translations = []
                
                current_english = ""
                current_chinese = ""
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if line contains English (has parentheses with explanation)
                    if '(' in line and ')' in line:
                        current_english = line
                    # Check if line contains Chinese characters
                    elif re.search(r'[\u4e00-\u9fff]', line):
                        current_chinese = line
                        # When we have both English and Chinese, add to vocabulary
                        if current_english and current_chinese:
                            english_translations.append(current_english)
                            chinese_translations.append(current_chinese)
                            current_english = ""
                            current_chinese = ""
                
                # Combine all translations
                if english_translations and chinese_translations:
                    english_combined = "; ".join(english_translations)
                    chinese_combined = "; ".join(chinese_translations)
                    vocabulary.append((indonesian_word, chinese_combined, english_combined))
                elif english_translations:
                    # If only English available
                    english_combined = "; ".join(english_translations)
                    vocabulary.append((indonesian_word, "", english_combined))
                elif chinese_translations:
                    # If only Chinese available
                    chinese_combined = "; ".join(chinese_translations)
                    vocabulary.append((indonesian_word, chinese_combined, ""))
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return vocabulary

def find_kosakata_files(bipa3_path):
    """Find all Kosakata files in BIPA3 directory."""
    kosakata_files = []
    
    for root, dirs, files in os.walk(bipa3_path):
        if 'Kosakata' in root:
            for file in files:
                if file.endswith('.md'):
                    kosakata_files.append(os.path.join(root, file))
    
    return kosakata_files

def main():
    bipa3_path = "/Users/wozsun/Library/Mobile Documents/iCloud~md~obsidian/Documents/Docs/BIPA/BIPA3"
    output_path = os.path.join(bipa3_path, "汇总词汇表.md")
    
    # Find all Kosakata files
    kosakata_files = find_kosakata_files(bipa3_path)
    print(f"Found {len(kosakata_files)} Kosakata files")
    
    # Extract vocabulary from all files
    all_vocabulary = {}  # Use dict to remove duplicates
    
    for file_path in kosakata_files:
        print(f"Processing: {os.path.relpath(file_path, bipa3_path)}")
        vocab = extract_vocabulary_from_file(file_path)
        
        for indonesian, chinese, english in vocab:
            if indonesian not in all_vocabulary:
                all_vocabulary[indonesian] = (chinese, english)
            else:
                # If word exists, combine translations
                existing_chinese, existing_english = all_vocabulary[indonesian]
                combined_chinese = existing_chinese
                combined_english = existing_english
                
                # Add new Chinese translation if different
                if chinese and chinese not in existing_chinese:
                    combined_chinese = f"{existing_chinese}; {chinese}" if existing_chinese else chinese
                
                # Add new English translation if different
                if english and english not in existing_english:
                    combined_english = f"{existing_english}; {english}" if existing_english else english
                
                all_vocabulary[indonesian] = (combined_chinese, combined_english)
    
    # Sort vocabulary alphabetically
    sorted_vocabulary = OrderedDict(sorted(all_vocabulary.items()))
    
    # Create markdown table
    markdown_content = """# BIPA3 汇总词汇表

本表格汇总了BIPA3课程中所有单元的词汇，已去除重复项。

| 印尼语 | 中文翻译 | 英文翻译和解释 |
|--------|----------|----------------|
"""
    
    for indonesian, (chinese, english) in sorted_vocabulary.items():
        # Escape pipe characters in content
        indonesian_escaped = indonesian.replace('|', '\\|')
        chinese_escaped = chinese.replace('|', '\\|')
        english_escaped = english.replace('|', '\\|')
        
        markdown_content += f"| {indonesian_escaped} | {chinese_escaped} | {english_escaped} |\n"
    
    # Add statistics
    markdown_content += f"\n---\n\n**统计信息：**\n- 总词汇量：{len(sorted_vocabulary)} 个单词\n- 处理文件数：{len(kosakata_files)} 个文件\n"
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"\n词汇表已生成：{output_path}")
    print(f"总共提取了 {len(sorted_vocabulary)} 个不重复的词汇")

if __name__ == "__main__":
    main()
