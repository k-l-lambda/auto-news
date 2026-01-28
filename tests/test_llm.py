#!/usr/bin/env python3
"""Test basic LLM functions of auto-news"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables from .env files
from dotenv import load_dotenv

# First load API keys from other-mcp (contains SUBAGENT_* vars)
other_mcp_env = os.path.expanduser("~/work/other-mcp/.env")
if os.path.exists(other_mcp_env):
    load_dotenv(other_mcp_env)
    # Map SUBAGENT_* to OPENAI_* for auto-news compatibility
    if os.getenv("SUBAGENT_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.getenv("SUBAGENT_API_KEY")
    if os.getenv("SUBAGENT_BASE_URL") and not os.getenv("OPENAI_API_BASE"):
        os.environ["OPENAI_API_BASE"] = os.getenv("SUBAGENT_BASE_URL")

# Then load auto-news specific config (won't override existing vars)
load_dotenv()

from llm_agent import LLMAgentCategoryAndRanking, LLMAgentSummary, LLMAgentGeneric


def test_generic_agent():
    """Test basic LLM call with generic agent"""
    print("\n" + "="*60)
    print("Testing LLMAgentGeneric")
    print("="*60)

    agent = LLMAgentGeneric()
    agent.init_prompt("Respond with a single word. What is 1+1? Answer: {content}")
    agent.init_llm()

    result = agent.run("calculate")
    print(f"Result: {result}")
    return result


def test_category_ranking():
    """Test category and ranking agent"""
    print("\n" + "="*60)
    print("Testing LLMAgentCategoryAndRanking")
    print("="*60)

    agent = LLMAgentCategoryAndRanking()
    agent.init_prompt()
    agent.init_llm()

    test_text = """
    OpenAI released GPT-4 Turbo with 128k context window.
    The new model shows significant improvements in coding tasks.
    CEO Sam Altman announced this at DevDay 2023.
    """

    result = agent.run(test_text)
    print(f"Result: {result}")
    return result


def test_summary_agent():
    """Test summary agent"""
    print("\n" + "="*60)
    print("Testing LLMAgentSummary")
    print("="*60)

    agent = LLMAgentSummary()
    agent.init_prompt(translation_enabled=False)
    agent.init_llm()

    test_text = """
    Artificial intelligence has made remarkable progress in recent years.
    Large language models like GPT-4 can now perform complex reasoning tasks.
    These models are trained on vast amounts of text data from the internet.
    They use transformer architecture with attention mechanisms.
    The applications range from chatbots to code generation to scientific research.
    However, there are also concerns about AI safety and alignment.
    Researchers are working on making AI systems more reliable and trustworthy.
    """

    result = agent.run(test_text)
    print(f"Result: {result}")
    return result


if __name__ == "__main__":
    print("Auto-News LLM Test Suite")
    print(f"Using API: {os.getenv('OPENAI_API_BASE', 'default OpenAI')}")
    print(f"Model: {os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')}")

    try:
        # Test 1: Generic agent (simplest)
        test_generic_agent()
        print("\n✓ Generic agent test passed")

        # Test 2: Category and ranking
        test_category_ranking()
        print("\n✓ Category and ranking test passed")

        # Test 3: Summary agent
        test_summary_agent()
        print("\n✓ Summary agent test passed")

        print("\n" + "="*60)
        print("All tests passed! Auto-News LLM functions are working.")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
