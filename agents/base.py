"""Base agent class for all Google ADK agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from google.genai import types


class BaseAgent(ABC):
    """Base class for all AI agents using Google ADK."""

    def __init__(
        self,
        name: str,
        instructions: str,
        model: str = "gemini-2.0-flash-exp",
        tools: Optional[list] = None,
    ):
        """Initialize the agent.
        
        Args:
            name: Agent name
            instructions: System instructions for the agent
            model: Google model to use
            tools: List of tool functions
        """
        self.name = name
        self.instructions = instructions
        self.model = model
        self.tools = tools or []
        self._client = None

    def _get_client(self):
        """Get or create Google ADK client."""
        if self._client is None:
            from google import genai
            from core.config import settings
            
            self._client = genai.Client(
                api_key=settings.google_api_key,
            )
        return self._client

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results.
        
        Args:
            input_data: Input data for the agent
            
        Returns:
            Processing results
        """
        pass

    async def run(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Run the agent with a prompt.
        
        Args:
            prompt: User prompt
            context: Optional context data
            
        Returns:
            Agent response
        """
        client = self._get_client()
        
        # Build messages
        messages = []
        if context:
            messages.append({
                "role": "system",
                "content": f"Context: {context}",
            })
        messages.append({
            "role": "user",
            "content": prompt,
        })
        
        # Call the model
        response = await client.aio.models.generate_content(
            model=self.model,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=self.instructions,
                tools=self.tools,
            ),
        )
        
        return response.text
