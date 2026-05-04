#!/usr/bin/env python3
import docx

def read_docx(file_path):
    """Read content from docx file"""
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        return f"Error reading {file_path}: {e}"

# Read all 5 scripts
scripts = {
    "警告别惹总裁的小娇妻": "/Users/hsinli/Downloads/reference_new/100集1分钟女主闪婚都市甜宠小程序剧《警告！别惹总裁的小娇妻》抖音姜十七（含前10集）爆款.docx",
    "总裁老公是豪门": "/Users/hsinli/Downloads/reference_new/《总裁老公是豪门》拉片.docx",
    "退婚后被财阀大佬娇养": "/Users/hsinli/Downloads/reference_new/《退婚后，她被财阀大佬娇养了》短剧拆解.docx",
    "护国战神": "/Users/hsinli/Downloads/reference_new/1分钟100集男频战神擦边小程序剧《护国战神：征战钓鱼岛》10集实力编剧.doc",
    "武神归来": "/Users/hsinli/Downloads/reference_new/1分钟都市打脸爽剧《武神归来》战神（人物+大纲+100集剧本）爆款10集完本.docx"
}

for name, path in scripts.items():
    print(f"\n{'='*80}")
    print(f"Script: {name}")
    print('='*80)
    content = read_docx(path)
    # Print first 5000 chars to see structure
    print(content[:5000])
    print(f"\n... [Total length: {len(content)} chars]")
