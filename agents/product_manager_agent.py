"""
Product Manager Agent for AI Development Pipeline
Converts user requirements into comprehensive Product Requirements Documents (PRDs)
"""

from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent
from utils.constants import AgentType


class ProductManagerAgent(BaseAgent):
    """
    Product Manager Agent
    
    Responsibilities:
    - Create comprehensive Product Requirements Documents (PRDs)
    - Define user stories and acceptance criteria
    - Prioritize features (Must-have, Should-have, Nice-to-have)
    - Clarify ambiguous requirements
    - Create technical specifications
    - Define success metrics and KPIs
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize Product Manager Agent"""
        super().__init__(
            agent_type=AgentType.PRODUCT_MANAGER,
            agent_id=agent_id
        )
        
        self.logger.info("Product Manager Agent initialized")
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [
            "Create PRD from requirements",
            "Define user stories",
            "Prioritize features",
            "Clarify requirements",
            "Create technical specifications",
            "Define success metrics"
        ]
    
    async def execute_task(self, task: Dict) -> Dict:
        """
        Execute a task assigned to Product Manager
        
        Args:
            task: Task dictionary with task details
        
        Returns:
            Result dictionary
        """
        task_type = task.get("type", "create_prd")
        
        handlers = {
            "create_prd": self.create_prd,
            "clarify_requirements": self.clarify_requirements,
            "prioritize_features": self.prioritize_features,
            "create_user_stories": self.create_user_stories,
        }
        
        handler = handlers.get(task_type)
        
        if not handler:
            raise ValueError(f"Unknown task type: {task_type}")
        
        return await handler(task)
    
    async def create_prd(self, task: Dict) -> Dict:
        """
        Create a comprehensive Product Requirements Document
        
        Args:
            task: Task with 'requirements' and 'project_path'
        
        Returns:
            Result with PRD file path
        """
        requirements = task.get("requirements", "")
        project_name = task.get("project_name", "")
        project_path = task.get("project_path", "")
        
        await self.log_action("create_prd", "started", {
            "project": project_name,
            "requirements_length": len(requirements)
        })
        
        # Create comprehensive prompt for Claude Code
        prompt = f"""
You are an experienced Product Manager creating a comprehensive Product Requirements Document (PRD).

Project: {project_name}
User Requirements:
{requirements}

Create a detailed PRD in Markdown format and save it as docs/PRD.md

The PRD MUST include these sections:

# 1. PRODUCT OVERVIEW
- Product vision and mission
- Target audience
- Key value proposition
- Product goals and objectives

# 2. USER PERSONAS
- Define 2-3 detailed user personas
- Include demographics, goals, pain points, and behaviors
- Describe their typical use cases

# 3. USER STORIES
- Write comprehensive user stories in format: "As a [user type], I want [goal], so that [benefit]"
- Organize by user persona
- Include acceptance criteria for each story
- Minimum 10-15 user stories covering all major features

# 4. FEATURE REQUIREMENTS
Organize features by priority:

## 4.1 Must-Have Features (MVP)
- List all essential features for launch
- Include detailed description for each
- Specify acceptance criteria

## 4.2 Should-Have Features
- Important but not critical for MVP
- Include detailed descriptions

## 4.3 Nice-to-Have Features
- Desirable features for future iterations
- Brief descriptions

# 5. TECHNICAL REQUIREMENTS
- Technology stack recommendations
- Architecture considerations
- Database requirements
- API specifications (if applicable)
- Third-party integrations
- Performance requirements
- Security requirements
- Scalability considerations

# 6. USER INTERFACE & EXPERIENCE
- Key UI/UX principles for this product
- Main user flows
- Wireframe descriptions for key screens
- Accessibility requirements

# 7. SUCCESS METRICS & KPIs
- Define measurable success metrics
- User engagement KPIs
- Business metrics
- Technical performance metrics
- How success will be measured

# 8. TIMELINE & MILESTONES
- Estimated development phases
- Key milestones
- Suggested sprint breakdown
- Launch timeline

# 9. RISKS & MITIGATION STRATEGIES
- Identify potential risks
- Technical risks
- Business risks
- Mitigation strategies for each

# 10. ASSUMPTIONS & DEPENDENCIES
- Key assumptions made in this PRD
- External dependencies
- Resource requirements

# 11. OPEN QUESTIONS
- List any questions that need clarification
- Areas requiring further research

Make the PRD:
- Comprehensive and detailed
- Professional and well-structured
- Actionable for development teams
- Clear and unambiguous
- Realistic and achievable

First ensure the docs/ directory exists, then create the PRD.md file.
"""
        
        try:
            # Call Claude Code to create PRD
            result = await self.call_claude_code(
                prompt=prompt,
                project_path=project_path,
                allowed_tools=["Write", "Edit", "Read", "Bash"]
            )
            
            prd_path = Path(project_path) / "docs" / "PRD.md"
            
            # Verify PRD was created
            if prd_path.exists():
                await self.log_action("create_prd", "completed", {
                    "prd_path": str(prd_path),
                    "file_size": prd_path.stat().st_size
                })
                
                # Send status update
                await self.send_status_update(
                    "prd_created",
                    {
                        "project": project_name,
                        "prd_path": str(prd_path)
                    }
                )
                
                return {
                    "success": True,
                    "prd_path": str(prd_path),
                    "project_name": project_name,
                    "message": "PRD created successfully"
                }
            else:
                raise FileNotFoundError("PRD file was not created")
                
        except Exception as e:
            await self.log_action("create_prd", "failed", {
                "error": str(e)
            })
            raise
    
    async def clarify_requirements(self, task: Dict) -> Dict:
        """
        Clarify ambiguous requirements by asking questions
        
        Args:
            task: Task with 'requirements' and 'project_path'
        
        Returns:
            Result with clarification questions
        """
        requirements = task.get("requirements", "")
        project_path = task.get("project_path", "")
        
        prompt = f"""
Analyze these requirements and identify ambiguities or missing information:

{requirements}

Create a document called docs/CLARIFICATION_QUESTIONS.md with:

1. A list of questions that would help clarify the requirements
2. Specific areas that need more detail
3. Potential assumptions that should be validated
4. Technical decisions that need to be made

Format each question clearly and explain why it's important.
"""
        
        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Read"]
        )
        
        return {
            "success": True,
            "message": "Clarification questions created",
            "file_path": f"{project_path}/docs/CLARIFICATION_QUESTIONS.md"
        }
    
    async def create_user_stories(self, task: Dict) -> Dict:
        """
        Extract and create detailed user stories from PRD
        
        Args:
            task: Task with 'prd_path' and 'project_path'
        
        Returns:
            Result with user stories file
        """
        prd_path = task.get("prd_path", "")
        project_path = task.get("project_path", "")
        
        prompt = f"""
Read the PRD at {prd_path} and create a comprehensive user stories document.

Create docs/USER_STORIES.md with:

1. All user stories from the PRD, expanded and detailed
2. Each story should have:
   - Story title
   - User persona
   - Story description (As a... I want... So that...)
   - Acceptance criteria (clear, testable conditions)
   - Story points estimate (1, 2, 3, 5, 8, 13)
   - Priority (High, Medium, Low)
   - Dependencies (if any)

3. Organize stories by epic/feature area
4. Include a story map showing relationships

Make sure every story is:
- Independent (can be developed separately)
- Valuable (provides clear value to users)
- Estimable (can be estimated)
- Small (can be completed in one sprint)
- Testable (has clear acceptance criteria)
"""
        
        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Read"],
            context_files=[prd_path]
        )
        
        return {
            "success": True,
            "message": "User stories created",
            "file_path": f"{project_path}/docs/USER_STORIES.md"
        }
    
    async def prioritize_features(self, task: Dict) -> Dict:
        """
        Prioritize features using MoSCoW method
        
        Args:
            task: Task with 'features' list and 'project_path'
        
        Returns:
            Result with prioritized features
        """
        features = task.get("features", [])
        project_path = task.get("project_path", "")
        
        features_text = "\n".join([f"- {f}" for f in features])
        
        prompt = f"""
Analyze and prioritize these features using the MoSCoW method:

{features_text}

Create docs/FEATURE_PRIORITIZATION.md with:

# Must Have (Critical for MVP)
- List features that are absolutely essential
- Explain why each is critical

# Should Have (Important but not critical)
- List features that are important
- Explain the impact if not included

# Could Have (Nice to have)
- List desirable features
- Explain the value they would add

# Won't Have (Not now)
- List features to defer
- Explain why they're being deferred

For each feature, also consider:
- User impact
- Technical complexity
- Dependencies
- Business value
- Risk

Provide a recommended implementation order.
"""
        
        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Read"]
        )
        
        return {
            "success": True,
            "message": "Features prioritized",
            "file_path": f"{project_path}/docs/FEATURE_PRIORITIZATION.md"
        }
    
    async def create_prd_from_scratch(
        self,
        requirements: str,
        project_name: str,
        project_path: str
    ) -> Dict:
        """
        Convenience method to create PRD from user requirements
        
        Args:
            requirements: User requirements text
            project_name: Name of the project
            project_path: Path to project directory
        
        Returns:
            Result dictionary with PRD path
        """
        task = {
            "type": "create_prd",
            "requirements": requirements,
            "project_name": project_name,
            "project_path": project_path
        }
        
        return await self.create_prd(task)


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

async def create_prd_for_project(
    requirements: str,
    project_name: str,
    project_path: str
) -> Dict:
    """
    Create a PRD for a project
    
    Args:
        requirements: User requirements
        project_name: Project name
        project_path: Project directory path
    
    Returns:
        Result with PRD path
    """
    pm_agent = ProductManagerAgent()
    
    result = await pm_agent.create_prd_from_scratch(
        requirements=requirements,
        project_name=project_name,
        project_path=project_path
    )
    
    return result


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    import asyncio
    
    async def test_product_manager():
        """Test Product Manager Agent"""
        
        # Create agent
        pm = ProductManagerAgent()
        
        # Test PRD creation
        test_requirements = """
        Build a gated community management system with the following features:
        
        1. Resident Management
        - Register and manage resident information
        - Track unit ownership and occupancy
        - Maintain contact details
        
        2. Billing System
        - Generate monthly maintenance bills
        - Track payments and dues
        - Send payment reminders
        - Generate reports
        
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
        
        Target users: Residents, Admin staff, Security guards
        Technology: Web-based application, mobile-friendly
        """
        
        result = await pm.create_prd_from_scratch(
            requirements=test_requirements,
            project_name="gated-community-management",
            project_path="/tmp/test-project"
        )
        
        print(f"PRD created: {result}")
    
    # Run test
    asyncio.run(test_product_manager())
