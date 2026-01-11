"""Agent registry for managing and discovering agents."""

from typing import Dict, Type
from agents.base import BaseAgent


class AgentRegistry:
    """Registry for managing all agents in the system."""

    def __init__(self):
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._instances: Dict[str, BaseAgent] = {}

    def register(self, name: str, agent_class: Type[BaseAgent]):
        """Register an agent class.
        
        Args:
            name: Agent name
            agent_class: Agent class
        """
        self._agents[name] = agent_class

    def get(self, name: str) -> BaseAgent:
        """Get or create an agent instance.
        
        Args:
            name: Agent name
            
        Returns:
            Agent instance
        """
        if name not in self._instances:
            if name not in self._agents:
                raise ValueError(f"Agent '{name}' not registered")
            
            agent_class = self._agents[name]
            self._instances[name] = agent_class()
        
        return self._instances[name]

    def list_agents(self) -> list[str]:
        """List all registered agents.
        
        Returns:
            List of agent names
        """
        return list(self._agents.keys())


# Global registry instance
registry = AgentRegistry()


def register_agent(name: str):
    """Decorator to register an agent.
    
    Args:
        name: Agent name
    """
    def decorator(cls: Type[BaseAgent]):
        registry.register(name, cls)
        return cls
    return decorator
