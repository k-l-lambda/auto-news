#!/usr/bin/env python3
"""
Test script for markdown to Notion blocks conversion.
"""
import re
import json


def parse_inline_formatting(text):
    """
    Parse inline markdown formatting and convert to Notion rich_text array.
    Supports: **bold**, *italic*, `code`
    """
    rich_text = []

    # Pattern to match **bold**, *italic*, `code`
    pattern = r'(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|([^*`]+))'

    pos = 0
    for match in re.finditer(pattern, text):
        full_match = match.group(0)

        if full_match.startswith('**') and full_match.endswith('**'):
            # Bold
            content = match.group(2)
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"bold": True}
            })
        elif full_match.startswith('*') and full_match.endswith('*') and not full_match.startswith('**'):
            # Italic
            content = match.group(3)
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"italic": True}
            })
        elif full_match.startswith('`') and full_match.endswith('`'):
            # Code
            content = match.group(4)
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"code": True}
            })
        else:
            # Plain text
            content = match.group(5)
            if content:
                rich_text.append({
                    "type": "text",
                    "text": {"content": content}
                })

    return rich_text if rich_text else [{"type": "text", "text": {"content": text}}]


def markdown_to_notion_blocks(markdown_text):
    """
    Convert markdown text to Notion blocks.

    Supports:
    - ## Heading 2
    - ### Heading 3
    - **bold** and *italic* inline
    - 1. Numbered lists
    - - Bullet lists
    - Regular paragraphs
    """
    blocks = []
    lines = markdown_text.strip().split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Heading 2: ## Title
        if line.startswith('## '):
            content = line[3:].strip()
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": parse_inline_formatting(content)
                }
            })
            i += 1
            continue

        # Heading 3: ### Title
        if line.startswith('### '):
            content = line[4:].strip()
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": parse_inline_formatting(content)
                }
            })
            i += 1
            continue

        # Numbered list: 1. Item
        if re.match(r'^\d+\.\s', line):
            content = re.sub(r'^\d+\.\s*', '', line)
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": parse_inline_formatting(content)
                }
            })
            i += 1
            continue

        # Bullet list: - Item or * Item
        if line.startswith('- ') or line.startswith('* '):
            content = line[2:].strip()
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": parse_inline_formatting(content)
                }
            })
            i += 1
            continue

        # Regular paragraph - collect consecutive non-empty lines
        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith('#') and not re.match(r'^[\d\-\*]\s', lines[i].strip()):
            para_lines.append(lines[i].rstrip())
            i += 1

        para_text = ' '.join(para_lines)
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": parse_inline_formatting(para_text)
            }
        })

    return blocks


def test_conversion():
    """Test the markdown to Notion blocks conversion."""

    test_markdown = """## [Source: Hacker News]

**Why Read This:** 这篇文章探讨了AI领域的最新突破，对技术从业者和投资者都有重要参考价值。

### Key Insights

1. **深度学习新范式**: 文章介绍了一种全新的训练方法，可以将模型效率提升30%。

2. **市场影响**: 预计这项技术将在未来两年内重塑AI芯片市场格局。

3. **实践建议**: 开发者应该关注以下几点：
   - 学习新的优化技术
   - 更新现有的模型架构

### Summary

这是一个*重要*的技术突破，值得密切关注。代码示例：`model.train()`
"""

    print("=" * 60)
    print("INPUT MARKDOWN:")
    print("=" * 60)
    print(test_markdown)

    print("\n" + "=" * 60)
    print("OUTPUT NOTION BLOCKS:")
    print("=" * 60)

    blocks = markdown_to_notion_blocks(test_markdown)

    for i, block in enumerate(blocks):
        print(f"\nBlock {i + 1}: {block['type']}")
        block_content = block[block['type']]
        if 'rich_text' in block_content:
            for rt in block_content['rich_text']:
                text = rt['text']['content']
                annotations = rt.get('annotations', {})
                style = []
                if annotations.get('bold'):
                    style.append('BOLD')
                if annotations.get('italic'):
                    style.append('ITALIC')
                if annotations.get('code'):
                    style.append('CODE')
                style_str = f" [{', '.join(style)}]" if style else ""
                print(f"  - \"{text}\"{style_str}")

    print("\n" + "=" * 60)
    print("JSON OUTPUT (for Notion API):")
    print("=" * 60)
    print(json.dumps(blocks[:3], indent=2, ensure_ascii=False))  # First 3 blocks

    return blocks


if __name__ == "__main__":
    test_conversion()
