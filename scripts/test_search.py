#!/usr/bin/env python3
"""Test web search and scraping functionality."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.graph.workflow import get_workflow


async def test_search_workflow():
    """Test the complete search workflow."""
    
    workflow = get_workflow()
    
    # Test queries
    test_queries = [
        "What is Python?",  # Should NOT search (general knowledge)
        "What happened in tech news today?",  # Should search
        "Who won the latest Super Bowl?",  # Should search
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Testing: {query}")
        print('='*80)
        
        try:
            response = await workflow.run(
                session_id="test-session",
                user_query=query,
                messages=[]
            )
            
            print(f"\n📝 Response:\n{response}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*80)
        await asyncio.sleep(2)  # Rate limiting


if __name__ == "__main__":
    print("🧪 Testing Web Search & Scraping System\n")
    asyncio.run(test_search_workflow())
