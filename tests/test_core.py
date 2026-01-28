#!/usr/bin/env python3
"""Test core auto-news functionality"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
other_mcp_env = os.path.expanduser("~/work/other-mcp/.env")
if os.path.exists(other_mcp_env):
    load_dotenv(other_mcp_env)
    if os.getenv("SUBAGENT_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.getenv("SUBAGENT_API_KEY")
    if os.getenv("SUBAGENT_BASE_URL") and not os.getenv("OPENAI_API_BASE"):
        os.environ["OPENAI_API_BASE"] = os.getenv("SUBAGENT_BASE_URL")
load_dotenv()


def test_imports():
    """Test all core module imports"""
    print("\n" + "="*60)
    print("Testing module imports")
    print("="*60)

    modules = []

    # Core operators
    from ops_base import OperatorBase
    modules.append("ops_base.OperatorBase")

    from ops_rss import OperatorRSS
    modules.append("ops_rss.OperatorRSS")

    from ops_article import OperatorArticle
    modules.append("ops_article.OperatorArticle")

    from ops_youtube import OperatorYoutube
    modules.append("ops_youtube.OperatorYoutube")

    # LLM agents
    from llm_agent import LLMAgentSummary, LLMAgentCategoryAndRanking
    modules.append("llm_agent.LLMAgentSummary")
    modules.append("llm_agent.LLMAgentCategoryAndRanking")

    # Notion
    from notion import NotionAgent
    modules.append("notion.NotionAgent")

    # Utils
    import utils
    modules.append("utils")

    print(f"Successfully imported {len(modules)} modules:")
    for m in modules:
        print(f"  - {m}")

    return True


def test_rss_fetch():
    """Test RSS feed parsing with a public feed"""
    print("\n" + "="*60)
    print("Testing RSS feed parsing")
    print("="*60)

    from ops_rss import OperatorRSS

    op = OperatorRSS()

    # Test with a reliable public RSS feed
    test_feeds = [
        ("HackerNews", "https://hnrss.org/frontpage"),
        # ("BBC News", "http://feeds.bbci.co.uk/news/technology/rss.xml"),
    ]

    for name, url in test_feeds:
        print(f"\nFetching from: {name} ({url})")
        try:
            articles = op._fetch_articles(name, url, count=2)
            print(f"  Fetched {len(articles)} articles")

            if articles:
                article = articles[0]
                print(f"  First article:")
                print(f"    - Title: {article['title'][:50]}...")
                print(f"    - URL: {article['url'][:60]}...")
                print(f"    - Created: {article['created_time']}")

        except Exception as e:
            print(f"  Error: {e}")
            return False

    return True


def test_utils():
    """Test utility functions"""
    print("\n" + "="*60)
    print("Testing utility functions")
    print("="*60)

    import utils

    # Test hash function
    test_str = "test string"
    hash_result = utils.hashcode_md5(test_str.encode('utf-8'))
    print(f"MD5 hash of '{test_str}': {hash_result}")

    # Test str2bool
    assert utils.str2bool("True") == True
    assert utils.str2bool("false") == False
    assert utils.str2bool("1") == True
    print("str2bool() tests passed")

    return True


def test_llm_summary():
    """Test LLM summary agent"""
    print("\n" + "="*60)
    print("Testing LLM Summary Agent")
    print("="*60)

    from llm_agent import LLMAgentSummary

    agent = LLMAgentSummary()
    agent.init_prompt(translation_enabled=False)
    agent.init_llm()

    test_text = """
    The Python programming language was created by Guido van Rossum
    and first released in 1991. Python emphasizes code readability
    with its notable use of significant whitespace. Its language
    constructs and object-oriented approach aim to help programmers
    write clear, logical code for small and large-scale projects.
    """

    result = agent.run(test_text)
    print(f"Summary result: {result[:200]}...")

    return bool(result)


if __name__ == "__main__":
    print("="*60)
    print("Auto-News Core Functionality Test")
    print("="*60)
    print(f"LLM Provider: {os.getenv('LLM_PROVIDER', 'openai')}")
    print(f"Model: {os.getenv('OPENAI_MODEL', 'default')}")

    tests = [
        ("Module Imports", test_imports),
        ("Utility Functions", test_utils),
        ("RSS Feed Parsing", test_rss_fetch),
        ("LLM Summary", test_llm_summary),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
            status = "PASS" if success else "FAIL"
            print(f"\n✓ {name}: {status}")
        except Exception as e:
            results.append((name, False))
            print(f"\n✗ {name}: FAIL - {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    for name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    if passed == total:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed!")
        sys.exit(1)
