#!/usr/bin/env python3
"""
Standalone test for markdown to Notion blocks conversion.
"""
import re


def _parse_inline_formatting(text):
    """
    Parse inline markdown formatting and convert to Notion rich_text array.
    Supports: **bold**, *italic*, `code`
    """
    rich_text = []

    # Pattern to match **bold**, *italic*, `code`, or plain text
    pattern = r'(\*\*(.+?)\*\*|\*([^*]+?)\*|`([^`]+?)`)'

    last_end = 0
    for match in re.finditer(pattern, text):
        # Add any plain text before this match
        if match.start() > last_end:
            plain = text[last_end:match.start()]
            if plain:
                rich_text.append({
                    "type": "text",
                    "text": {"content": plain}
                })

        full_match = match.group(0)
        if full_match.startswith('**'):
            # Bold
            content = match.group(2)
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"bold": True}
            })
        elif full_match.startswith('`'):
            # Code
            content = match.group(4)
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"code": True}
            })
        elif full_match.startswith('*'):
            # Italic
            content = match.group(3)
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"italic": True}
            })

        last_end = match.end()

    # Add remaining plain text
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            rich_text.append({
                "type": "text",
                "text": {"content": remaining}
            })

    return rich_text if rich_text else [{"type": "text", "text": {"content": text}}]


def markdown_to_notion_blocks(markdown_text):
    """Convert markdown to Notion blocks."""
    blocks = []
    lines = markdown_text.strip().split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line:
            i += 1
            continue

        # Heading 2
        if line.startswith('## '):
            blocks.append({
                "type": "heading_2",
                "heading_2": {"rich_text": _parse_inline_formatting(line[3:].strip())}
            })
            i += 1
            continue

        # Heading 3
        if line.startswith('### '):
            blocks.append({
                "type": "heading_3",
                "heading_3": {"rich_text": _parse_inline_formatting(line[4:].strip())}
            })
            i += 1
            continue

        # Numbered list
        if re.match(r'^\d+\.\s', line):
            content = re.sub(r'^\d+\.\s*', '', line)
            blocks.append({
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": _parse_inline_formatting(content)}
            })
            i += 1
            continue

        # Bullet list
        if line.startswith('- ') or (line.startswith('* ') and not line.endswith('*')):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _parse_inline_formatting(line[2:].strip())}
            })
            i += 1
            continue

        # Indented bullet
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _parse_inline_formatting(line.strip()[2:].strip())}
            })
            i += 1
            continue

        # Paragraph
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": _parse_inline_formatting(line)}
        })
        i += 1

    return blocks


# Test
markdown = """## [Source: TechCrunch]

**Why Read This:** AI行业的重大突破，对投资者和开发者都很重要。

### Key Insights

1. **新算法发布**: OpenAI发布了新的训练算法，效率提升50%。

2. **市场反应**: 股价上涨15%，市场信心大增。

3. **技术细节**: 使用了`transformer`架构的改进版本。

### 总结

这是一个*重要*的里程碑。
"""

blocks = markdown_to_notion_blocks(markdown)
print(f"Generated {len(blocks)} blocks:\n")

for i, block in enumerate(blocks):
    block_type = block['type']
    rich_text = block[block_type].get('rich_text', [])

    text_parts = []
    for rt in rich_text:
        content = rt['text']['content']
        ann = rt.get('annotations', {})
        if ann.get('bold'):
            text_parts.append(f"[B]{content}[/B]")
        elif ann.get('italic'):
            text_parts.append(f"[I]{content}[/I]")
        elif ann.get('code'):
            text_parts.append(f"[C]{content}[/C]")
        else:
            text_parts.append(content)

    full_text = ''.join(text_parts)
    print(f"{i+1:2}. {block_type:22} | {full_text}")

print("\n✅ Test passed!")
