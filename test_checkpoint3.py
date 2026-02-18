"""
End-to-End Test for Checkpoint 3
Demonstrates complete workflow: PRD → GitHub Repo → Issues

This test will:
1. Create a Product Manager agent
2. Generate a PRD for the Gated Community project
3. Create a Project Manager agent  
4. Set up GitHub repository
5. Create issues from the PRD
6. Display results
"""

import asyncio
from pathlib import Path
from datetime import datetime

from agents.product_manager_agent import ProductManagerAgent
from agents.project_manager_agent import ProjectManagerAgent


async def test_complete_workflow():
    """
    Test the complete agent workflow
    """
    
    print("=" * 70)
    print("🚀 CHECKPOINT 3: END-TO-END WORKFLOW TEST")
    print("=" * 70)
    print()
    
    # Configuration
    project_name = "gated-community-system"
    project_description = "Comprehensive gated community management platform"
    
    requirements = """
    Build a gated community management system with the following features:
    
    1. Resident Management
       - Register and manage resident information
       - Track unit ownership and occupancy
       - Maintain contact details
    
    2. Billing System
       - Generate monthly maintenance bills
       - Track payments and dues
       - Send payment reminders
       - Generate billing reports
    
    3. Visitor Management
       - Pre-register visitors
       - Track visitor entry and exit
       - Generate visitor passes
       - Maintain visitor logs
    
    4. Facility Booking
       - Book community facilities (clubhouse, gym, pool)
       - Manage booking calendar
       - Handle booking conflicts
    
    5. Complaint Management
       - Submit and track complaints
       - Assign to relevant staff
       - Track resolution status
    
    Target Users: Residents, Admin staff, Security guards
    Technology: FastAPI (backend) + React (frontend)
    Database: PostgreSQL
    """
    
    # Step 1: Create Product Manager and generate PRD
    print("📋 STEP 1: Creating Product Manager Agent")
    print("-" * 70)
    pm_agent = ProductManagerAgent(agent_id="pm_main")
    print(f"✅ Created: {pm_agent}")
    print(f"   Capabilities: {', '.join(pm_agent.get_capabilities()[:3])}...")
    print()
    
    # Set up project directory
    project_path = Path.home() / "ai-dev-pipeline" / "projects" / project_name
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "docs").mkdir(exist_ok=True)
    
    print("📝 STEP 2: Generating PRD")
    print("-" * 70)
    print("⏳ This will take 2-3 minutes...")
    print()
    
    prd_result = await pm_agent.create_prd_from_scratch(
        requirements=requirements,
        project_name="Gated Community Management System",
        project_path=str(project_path)
    )
    
    if prd_result["success"]:
        prd_file = Path(prd_result['prd_path'])
        size_kb = prd_file.stat().st_size / 1024
        
        print(f"✅ PRD Created Successfully!")
        print(f"   📄 Path: {prd_result['prd_path']}")
        print(f"   📏 Size: {size_kb:.2f} KB")
        print()
    else:
        print("❌ PRD creation failed!")
        return
    
    # Step 3: Create Project Manager
    print("🗂️  STEP 3: Creating Project Manager Agent")
    print("-" * 70)
    proj_mgr = ProjectManagerAgent(agent_id="pm_github")
    print(f"✅ Created: {proj_mgr}")
    print(f"   Capabilities: {', '.join(proj_mgr.get_capabilities()[:4])}...")
    print()
    
    # Step 4: Set up complete GitHub project
    print("🐙 STEP 4: Setting up GitHub Repository")
    print("-" * 70)
    print("⏳ Creating repository, branches, labels, and issues...")
    print("   This may take 2-3 minutes...")
    print()
    
    setup_result = await proj_mgr.setup_complete_project({
        "project_name": project_name,
        "description": project_description,
        "prd_path": prd_result['prd_path']
    })
    
    if setup_result["success"]:
        print("✅ GitHub Project Setup Complete!")
        print()
        print("📊 RESULTS:")
        print("-" * 70)
        
        # Repository info
        if "repository" in setup_result:
            repo_info = setup_result["repository"]
            print(f"📦 Repository: {repo_info.get('repo_url', 'N/A')}")
            print(f"   Clone URL: {repo_info.get('clone_url', 'N/A')}")
        
        # Issues info
        if "issues" in setup_result:
            issues_info = setup_result["issues"]
            print(f"\n📋 Issues Created: {issues_info.get('issues_created', 0)}")
            
            if issues_info.get("issues"):
                print("\n   First 5 issues:")
                for i, issue in enumerate(issues_info["issues"][:5], 1):
                    print(f"   #{issue.get('number')}: {issue.get('title')}")
                    print(f"      URL: {issue.get('url')}")
        
        # Steps completed
        print(f"\n✅ Steps Completed: {len(setup_result.get('steps_completed', []))}")
        for step in setup_result.get('steps_completed', []):
            print(f"   ✓ {step.replace('_', ' ').title()}")
        
        print()
        print("=" * 70)
        print("🎉 WORKFLOW TEST COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Visit the GitHub repository to see the created issues")
        print("2. Development agents can now be assigned to implement features")
        print("3. Each agent will create PRs that Project Manager will merge")
        print()
        
    else:
        print("❌ GitHub setup failed!")
        print(setup_result)


async def test_agents_only():
    """
    Quick test to just verify agents can be created
    """
    print("🧪 Quick Agent Creation Test")
    print("-" * 70)
    
    # Test Product Manager
    pm = ProductManagerAgent()
    print(f"✅ Product Manager: {pm}")
    print(f"   Status: {pm.get_status()}")
    
    # Test Project Manager
    proj_mgr = ProjectManagerAgent()
    print(f"✅ Project Manager: {proj_mgr}")
    print(f"   Status: {proj_mgr.get_status()}")
    
    print("\n✅ Both agents created successfully!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick test mode
        asyncio.run(test_agents_only())
    else:
        # Full end-to-end test
        asyncio.run(test_complete_workflow())
