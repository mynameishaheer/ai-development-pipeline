"""
Complete End-to-End Workflow Test
Demonstrates: User Request → PRD → GitHub → Feature Implementation
"""

import asyncio
from pathlib import Path

from agents.master_agent import MasterAgent


async def test_complete_pipeline():
    """
    Test the complete autonomous development pipeline
    """
    
    print("=" * 80)
    print("🚀 COMPLETE AI DEVELOPMENT PIPELINE TEST")
    print("=" * 80)
    print()
    
    # Initialize Master Agent
    print("🤖 Initializing Master Agent...")
    master = MasterAgent()
    print(f"✅ Master Agent ready")
    print()
    
    # User request
    user_request = """
    Build a simple task management API with these features:
    
    1. User authentication (register, login)
    2. Create, read, update, delete tasks
    3. Mark tasks as complete
    4. Filter tasks by status
    5. Assign tasks to users
    
    Use FastAPI for the backend.
    """
    
    print("📝 User Request:")
    print("-" * 80)
    print(user_request)
    print("-" * 80)
    print()
    
    # Process through Master Agent
    print("⚙️  Processing through AI Development Pipeline...")
    print("   This will take 2-3 minutes...")
    print()
    
    result = await master.handle_new_project(
        message=user_request,
        user_id="test_user"
    )
    
    print(result)
    print()
    print("=" * 80)
    print("✅ PIPELINE TEST COMPLETE")
    print("=" * 80)


async def test_discord_integration():
    """
    Simulate Discord bot interaction
    """
    print("=" * 80)
    print("💬 DISCORD BOT SIMULATION")
    print("=" * 80)
    print()
    
    master = MasterAgent()
    
    # Simulate Discord command: !new <description>
    print("User types: !new Build a blog with user auth and comments")
    print()
    
    response = await master.handle_new_project(
        message="Build a blog with user auth and comments",
        user_id="discord_user_123"
    )
    
    print("Bot responds:")
    print(response)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--discord":
        asyncio.run(test_discord_integration())
    else:
        asyncio.run(test_complete_pipeline())
