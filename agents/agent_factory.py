"""
Agent Factory for AI Development Pipeline
Factory pattern for creating and managing agents
"""

from typing import Dict, Optional, Type
from agents.base_agent import BaseAgent
from agents.product_manager_agent import ProductManagerAgent
from utils.constants import AgentType


class AgentFactory:
    """
    Factory for creating agents
    Manages agent registry and instantiation
    """
    
    # Registry of available agent classes
    _agent_registry: Dict[str, Type[BaseAgent]] = {
        AgentType.PRODUCT_MANAGER: ProductManagerAgent,
        # More agents will be added as they're implemented:
        # AgentType.PROJECT_MANAGER: ProjectManagerAgent,
        # AgentType.BACKEND: BackendAgent,
        # AgentType.FRONTEND: FrontendAgent,
        # AgentType.DATABASE: DatabaseAgent,
        # AgentType.DEVOPS: DevOpsAgent,
        # AgentType.QA: QAAgent,
    }
    
    @classmethod
    def create_agent(
        cls,
        agent_type: str,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> BaseAgent:
        """
        Create an agent of the specified type
        
        Args:
            agent_type: Type of agent to create (from AgentType)
            agent_id: Optional agent ID
            **kwargs: Additional arguments for agent constructor
        
        Returns:
            Agent instance
        
        Raises:
            ValueError: If agent type is not registered
        """
        agent_class = cls._agent_registry.get(agent_type)
        
        if not agent_class:
            available = ", ".join(cls._agent_registry.keys())
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Available types: {available}"
            )
        
        # Create agent
        agent = agent_class(agent_id=agent_id, **kwargs)
        
        return agent
    
    @classmethod
    def register_agent(cls, agent_type: str, agent_class: Type[BaseAgent]):
        """
        Register a new agent type
        
        Args:
            agent_type: Agent type identifier
            agent_class: Agent class
        """
        cls._agent_registry[agent_type] = agent_class
    
    @classmethod
    def get_available_agents(cls) -> list:
        """
        Get list of available agent types
        
        Returns:
            List of agent type strings
        """
        return list(cls._agent_registry.keys())
    
    @classmethod
    def create_all_agents(cls) -> Dict[str, BaseAgent]:
        """
        Create one instance of each available agent type
        
        Returns:
            Dictionary mapping agent_type to agent instance
        """
        agents = {}
        
        for agent_type in cls._agent_registry.keys():
            agents[agent_type] = cls.create_agent(agent_type)
        
        return agents


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def create_product_manager(agent_id: Optional[str] = None) -> ProductManagerAgent:
    """
    Create a Product Manager agent
    
    Args:
        agent_id: Optional agent ID
    
    Returns:
        ProductManagerAgent instance
    """
    return AgentFactory.create_agent(AgentType.PRODUCT_MANAGER, agent_id)


# Future convenience functions:
# def create_project_manager(agent_id: Optional[str] = None) -> ProjectManagerAgent:
#     return AgentFactory.create_agent(AgentType.PROJECT_MANAGER, agent_id)
#
# def create_backend_agent(agent_id: Optional[str] = None) -> BackendAgent:
#     return AgentFactory.create_agent(AgentType.BACKEND, agent_id)
#
# ... etc


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    # Create a product manager
    pm = create_product_manager()
    print(f"Created: {pm}")
    print(f"Capabilities: {pm.get_capabilities()}")
    
    # Get all available agents
    available = AgentFactory.get_available_agents()
    print(f"Available agents: {available}")
    
    # Create all agents (when more are implemented)
    # all_agents = AgentFactory.create_all_agents()
    # for agent_type, agent in all_agents.items():
    #     print(f"{agent_type}: {agent}")
