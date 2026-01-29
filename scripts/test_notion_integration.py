#!/usr/bin/env python3
"""
Test the full integration of markdown to Notion blocks.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from notion import markdown_to_notion_blocks, _parse_inline_formatting

def test_inline_formatting():
    """Test inline formatting parsing."""
    print("=" * 60)
    print("TEST: Inline Formatting")
    print("=" * 60)

    test_cases = [
        "This is **bold** text",
        "This is *italic* text",
        "This is `code` text",
        "**Bold** and *italic* and `code` mixed",
        "No formatting here",
        "**深度学习**: 这是中文测试",
    ]

    for text in test_cases:
        result = _parse_inline_formatting(text)
        print(f"\nInput: {text}")
        print("Output:")
        for rt in result:
            content = rt['text']['content']
            ann = rt.get('annotations', {})
            style = []
            if ann.get('bold'): style.append('B')
            if ann.get('italic'): style.append('I')
            if ann.get('code'): style.append('C')
            style_str = f"[{','.join(style)}]" if style else ""
            print(f"  '{content}' {style_str}")


def test_full_conversion():
    """Test full markdown to blocks conversion."""
    print("\n" + "=" * 60)
    print("TEST: Full Markdown Conversion")
    print("=" * 60)

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

    print(f"\nGenerated {len(blocks)} blocks:\n")
    for i, block in enumerate(blocks):
        block_type = block['type']
        content_key = block_type
        rich_text = block[content_key].get('rich_text', [])

        # Reconstruct text with formatting indicators
        text_parts = []
        for rt in rich_text:
            content = rt['text']['content']
            ann = rt.get('annotations', {})
            if ann.get('bold'):
                text_parts.append(f"**{content}**")
            elif ann.get('italic'):
                text_parts.append(f"*{content}*")
            elif ann.get('code'):
                text_parts.append(f"`{content}`")
            else:
                text_parts.append(content)

        full_text = ''.join(text_parts)
        print(f"{i+1}. [{block_type:20}] {full_text[:60]}...")


def test_notion_summary_method():
    """Test the NotionAgent._createSummaryInPage method."""
    print("\n" + "=" * 60)
    print("TEST: NotionAgent._createSummaryInPage")
    print("=" * 60)

    from notion import NotionAgent

    # Create agent without API key (we're just testing the method)
    class MockNotionAgent(NotionAgent):
        def __init__(self):
            self.api_key = None
            self.api = None
            self.databases = {}

    agent = MockNotionAgent()

    markdown_summary = """## [Source: Hacker News]

**Why Read This:** 技术突破

### Key Insights

1. **Point 1**: Detail here
"""

    blocks = agent._createSummaryInPage(markdown_summary)
    print(f"\nGenerated {len(blocks)} blocks from _createSummaryInPage")

    for i, block in enumerate(blocks):
        print(f"  Block {i+1}: {block.get('type', 'unknown')}")


if __name__ == "__main__":
    test_inline_formatting()
    test_full_conversion()
    test_notion_summary_method()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
