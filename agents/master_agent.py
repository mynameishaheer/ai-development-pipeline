"""
Master Agent - Central orchestrator for the AI Development Pipeline
Uses Claude Code CLI programmatically to execute tasks
"""

import asyncio
import subprocess
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import chromadb
import redis


class MasterAgent:
    """
    The Master Agent is the brain of the operation.
    It orchestrates all sub-agents and makes autonomous decisions.
    """
    
    def __init__(self, workspace_dir: str = None):
        if workspace_dir is None:
            workspace_dir = str(Path.home() / "ai-dev-pipeline" / "projects")
        
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize memory system
        memory_path = str(Path.home() / "ai-dev-pipeline" / "memory" / "vector_store")
        self.memory_client = chromadb.PersistentClient(path=memory_path)
        self.memory = self.memory_client.get_or_create_collection(
            name="master_memory"
        )
        
        # Initialize Redis for agent communication
        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Current project state
        self.current_project = None
        self.current_context = {}
        
        print("🧠 Master Agent initialized successfully")
    
    async def call_claude_code(
        self, 
        prompt: str, 
        project_path: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        context_files: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Programmatically invoke Claude Code CLI (ASYNC VERSION)
        
        This is the KEY method that makes everything work!
        Claude Code is scriptable - we can call it from Python.
        
        Args:
            prompt: The instruction to give Claude Code
            project_path: Directory where Claude Code should work
            allowed_tools: List of tools Claude Code can use (e.g., ["Write", "Edit", "Bash"])
            context_files: Files to include in context
        
        Returns:
            Dict with 'stdout', 'stderr', 'return_code'
        """
        
        # Build the command - always include bypass permissions flag
        cmd = ["claude", "-p", prompt, "--dangerously-skip-permissions"]
        
        # Add allowed tools if specified
        if allowed_tools:
            cmd.extend(["--allowed-tools"])
            cmd.extend(allowed_tools)
        
        # Set working directory
        cwd = project_path or str(self.workspace_dir)
        
        print(f"🤖 Calling Claude Code with prompt: {prompt[:100]}...")
        
        try:
            # Execute Claude Code ASYNCHRONOUSLY
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=300  # 5 minute timeout
                )
                stdout = stdout.decode('utf-8')
                stderr = stderr.decode('utf-8')
                return_code = process.returncode
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return {
                    "stdout": "",
                    "stderr": "Command timed out after 5 minutes",
                    "return_code": -1,
                    "success": False
                }
            
            # Log the interaction
            await self.log_interaction(prompt, stdout, stderr)
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "success": return_code == 0
            }
            
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "success": False
            }
    
    async def process_user_message(self, message: str, user_id: str) -> str:
        """
        Main entry point for all user messages
        Analyzes intent and routes to appropriate handler
        
        Args:
            message: User's message/request
            user_id: Unique identifier for the user
        
        Returns:
            Response message to send back to user
        """
        
        print(f"📨 Processing message from {user_id}: {message[:100]}...")
        
        # Store message in memory for context
        await self.store_memory(
            category="user_message",
            content=message,
            metadata={"user_id": user_id, "timestamp": datetime.now().isoformat()}
        )
        
        # Analyze intent using Claude Code
        intent_result = await self.analyze_intent(message)
        intent = intent_result.get("intent", "general_query")
        
        print(f"🎯 Detected intent: {intent}")
        
        # Route to appropriate handler
        handlers = {
            "new_project": self.handle_new_project,
            "code_task": self.handle_code_task,
            "status_check": self.handle_status_check,
            "update_project": self.handle_update_project,
            "deploy": self.handle_deploy,
            "general_query": self.handle_general_query
        }
        
        handler = handlers.get(intent, self.handle_general_query)
        response = await handler(message, user_id)
        
        # Store response in memory
        await self.store_memory(
            category="agent_response",
            content=response,
            metadata={"user_id": user_id, "intent": intent}
        )
        
        return response
    
    async def analyze_intent(self, message: str) -> Dict[str, str]:
        """
        Analyze user message to determine intent
        Uses Claude Code to classify the request
        """
        
        prompt = f"""
        Analyze this user message and determine the intent.
        Return ONLY a JSON object with the intent classification.
        
        Possible intents:
        - new_project: User wants to start a new project
        - code_task: User wants to implement a feature or fix something
        - status_check: User wants to know current project status
        - update_project: User wants to modify existing project
        - deploy: User wants to deploy the project
        - general_query: General question or conversation
        
        User message: "{message}"
        
        Return format:
        {{"intent": "intent_name", "confidence": 0.95, "reasoning": "brief explanation"}}
        """
        
        result = await self.call_claude_code(prompt, allowed_tools=["Write"])
        
        try:
            # Extract JSON from response
            stdout = result.get("stdout", "{}")
            # Claude Code might wrap JSON in markdown - extract it
            if "```json" in stdout:
                json_str = stdout.split("```json")[1].split("```")[0].strip()
            elif "```" in stdout:
                json_str = stdout.split("```")[1].split("```")[0].strip()
            else:
                json_str = stdout.strip()
            
            intent_data = json.loads(json_str)
            return intent_data
        except Exception as e:
            print(f"⚠️ Intent parsing failed: {e}")
            # Fallback to general query if parsing fails
            return {"intent": "general_query", "confidence": 0.5, "reasoning": "Failed to parse"}
    
    async def handle_new_project(self, message: str, user_id: str) -> str:
        """
        Initialize a new project from user description
        This is where the magic happens!
        """
        
        print("🚀 Initializing new project...")
        
        # Create project directory
        project_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_path = self.workspace_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Use Claude Code to initialize the project
        init_prompt = f"""
        Initialize a new project based on this requirement:
        
        "{message}"
        
        Steps to complete:
        1. Analyze the requirements and identify the tech stack needed
        2. Create appropriate directory structure
        3. Initialize git repository
        4. Create README.md with project overview
        5. Create a PLAN.md file outlining the implementation strategy
        6. Set up basic configuration files (package.json, requirements.txt, etc.)
        7. Create .gitignore file
        
        Work in the current directory and create all necessary files.
        Be thorough and professional.
        """
        
        result = await self.call_claude_code(
            prompt=init_prompt,
            project_path=str(project_path),
            allowed_tools=["Write", "Edit", "Bash"]
        )
        
        if result["success"]:
            # Store project info
            self.current_project = {
                "name": project_name,
                "path": str(project_path),
                "created_at": datetime.now().isoformat(),
                "requirements": message,
                "status": "initialized"
            }
            
            # Save project metadata
            await self.save_project_metadata()
            
            response = f"""
✅ **Project Initialized Successfully!**

📁 **Project Name**: {project_name}
📂 **Location**: {project_path}
🕐 **Created**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 **Next Steps**:
I've created the initial structure. Here's what I did:
{result.get('stdout', 'Project initialized')}

Would you like me to proceed with implementing features, or would you like to review the plan first?
            """
        else:
            response = f"""
❌ **Project Initialization Failed**

Error: {result.get('stderr', 'Unknown error')}

I'll try to diagnose and fix this. Please hold on...
            """
        
        return response
    
    async def handle_code_task(self, message: str, user_id: str) -> str:
        """Handle coding tasks for current project"""
        
        if not self.current_project:
            return "❌ No active project. Please start a new project first with your requirements."
        
        project_path = self.current_project["path"]
        
        prompt = f"""
        Implement the following task for the current project:
        
        "{message}"
        
        Context:
        - Project: {self.current_project['name']}
        - Original Requirements: {self.current_project['requirements']}
        
        Steps:
        1. Analyze the current codebase
        2. Identify files that need to be created or modified
        3. Implement the changes
        4. Test the changes if applicable
        5. Commit the changes to git
        
        Be thorough and follow best practices.
        """
        
        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Bash", "Read"]
        )
        
        if result["success"]:
            return f"""
✅ **Task Completed Successfully!**

{result.get('stdout', 'Task completed')}

The changes have been implemented and committed to git.
            """
        else:
            return f"""
❌ **Task Failed**

Error: {result.get('stderr', 'Unknown error')}

I'll analyze the error and try to fix it automatically...
            """
    
    async def handle_status_check(self, message: str = None, user_id: str = None) -> str:
        """Provide status update on current project"""
        
        if not self.current_project:
            return "📊 **Status**: No active project. Ready to start a new one!"
        
        project_path = self.current_project["path"]
        
        # Use Claude Code to analyze project status
        status_prompt = """
        Analyze the current project and provide a status update:
        
        1. List all files in the project
        2. Check git status
        3. Identify completed features
        4. Identify pending tasks (check TODO comments, issues)
        5. Check if there are any errors or warnings
        
        Provide a clear, concise summary.
        """
        
        result = await self.call_claude_code(
            prompt=status_prompt,
            project_path=project_path,
            allowed_tools=["Bash", "Read"]
        )
        
        return f"""
📊 **Project Status**

📁 **Project**: {self.current_project['name']}
🕐 **Created**: {self.current_project['created_at']}

{result.get('stdout', 'Status check completed')}
        """
    
    async def handle_update_project(self, message: str, user_id: str) -> str:
        """Handle project updates and modifications"""
        return await self.handle_code_task(message, user_id)
    
    async def handle_deploy(self, message: str, user_id: str) -> str:
        """Handle deployment requests"""
        
        if not self.current_project:
            return "❌ No active project to deploy."
        
        project_path = self.current_project["path"]
        
        deploy_prompt = """
        Prepare the project for deployment:
        
        1. Create a Dockerfile if it doesn't exist
        2. Create docker-compose.yml for local testing
        3. Ensure all environment variables are documented
        4. Run tests if they exist
        5. Build the project
        6. Create deployment instructions in DEPLOYMENT.md
        
        Do not actually deploy yet, just prepare everything.
        """
        
        result = await self.call_claude_code(
            prompt=deploy_prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Bash"]
        )
        
        return f"""
🚀 **Deployment Preparation Complete**

{result.get('stdout', 'Project is ready for deployment')}

Next steps:
1. Review the DEPLOYMENT.md file
2. Confirm you want to proceed with deployment
3. I'll handle the actual deployment to your staging environment
        """
    
    async def handle_general_query(self, message: str, user_id: str) -> str:
        """Handle general questions and conversations"""
        
        # Retrieve relevant context from memory
        context = await self.retrieve_memory(message, n_results=3)
        
        context_str = "\n".join([
            f"- {doc}" for doc in context.get("documents", [[]])[0]
        ]) if context and context.get("documents") and len(context.get("documents")[0]) > 0 else "No relevant context"
        
        prompt = f"""
        Answer this question from the user:
        
        "{message}"
        
        Relevant context from previous conversations:
        {context_str}
        
        Current project: {self.current_project.get('name') if self.current_project else 'None'}
        
        Provide a helpful, friendly response. If you need more information, ask.
        """
        
        result = await self.call_claude_code(
            prompt=prompt,
            allowed_tools=["Write"]
        )
        
        return result.get("stdout", "I'm here to help! Could you provide more details?")
    
    async def store_memory(self, category: str, content: str, metadata: Dict = None):
        """Store information in vector database for later retrieval"""
        
        memory_id = f"{category}_{datetime.now().timestamp()}"
        
        self.memory.add(
            documents=[content],
            metadatas=[{"category": category, **(metadata or {})}],
            ids=[memory_id]
        )
    
    async def retrieve_memory(self, query: str, n_results: int = 5) -> Dict:
        """Retrieve relevant memories based on query"""
        
        try:
            results = self.memory.query(
                query_texts=[query],
                n_results=n_results
            )
            return results
        except Exception as e:
            print(f"⚠️ Memory retrieval error: {e}")
            return {"documents": [[]]}
    
    async def save_project_metadata(self):
        """Save current project metadata to disk"""
        
        if not self.current_project:
            return
        
        metadata_file = Path(self.current_project["path"]) / ".project_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(self.current_project, f, indent=2)
    
    async def log_interaction(self, prompt: str, stdout: str, stderr: str):
        """Log all Claude Code interactions for debugging"""
        
        log_dir = Path.home() / "ai-dev-pipeline" / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"claude_code_{datetime.now().strftime('%Y%m%d')}.log"
        
        with open(log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Prompt: {prompt}\n")
            f.write(f"Stdout: {stdout}\n")
            f.write(f"Stderr: {stderr}\n")
            f.write(f"{'='*80}\n")


# Example usage
if __name__ == "__main__":
    async def test():
        agent = MasterAgent()
        response = await agent.process_user_message(
            "Create a simple hello world web app",
            "test_user_123"
        )
        print(response)
    
    asyncio.run(test())
