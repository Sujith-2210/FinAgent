"""
Base Agent Class
Foundation for all specialized agents in the multi-agent system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

from app.llm.controller import llm_controller
from app.privacy.access_control import access_controller


class AgentResult(BaseModel):
    """Standard result from agent execution."""
    success: bool
    output: Dict[str, Any]
    reasoning_steps: List[str] = []
    context_accessed: List[str] = []
    confidence: str = "MEDIUM"
    execution_time_ms: float = 0


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Each agent must:
    - Define its system prompt
    - Declare read/write layer permissions
    - Implement the process method
    - Return structured output
    """
    
    def __init__(self):
        self.name: str = "base_agent"
        self.description: str = "Base agent class"
        self.system_prompt: str = ""
        self.read_layers: Set[str] = set()
        self.write_layers: Set[str] = set()
        self._reasoning_steps: List[str] = []
        self._context_accessed: List[str] = []
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Define the expected input schema."""
        pass
    
    @property
    @abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        """Define the expected output schema."""
        pass
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input and return structured output.
        
        This is the main logic of the agent.
        """
        pass
    
    async def run(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute the agent with input validation and logging.
        
        This is the public interface for invoking an agent.
        """
        start_time = datetime.utcnow()
        self._reasoning_steps = []
        self._context_accessed = []
        
        logger.info(f"Running agent: {self.name}")
        
        try:
            # Process the input
            output = await self.process(input_data)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return AgentResult(
                success=True,
                output=output,
                reasoning_steps=self._reasoning_steps,
                context_accessed=self._context_accessed,
                confidence=output.get("confidence", "MEDIUM"),
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Agent {self.name} failed: {e}")
            return AgentResult(
                success=False,
                output={"error": str(e)},
                reasoning_steps=self._reasoning_steps,
                context_accessed=self._context_accessed,
                confidence="LOW",
                execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
    
    def add_reasoning_step(self, step: str):
        """Add a reasoning step to the trace."""
        self._reasoning_steps.append(step)
        logger.debug(f"[{self.name}] {step}")
    
    def add_structured_reasoning(
        self, 
        step_type: str, 
        input_state: str, 
        output_state: str, 
        confidence: float = 0.8
    ):
        """
        Add structured chain-of-thought reasoning step.
        
        Args:
            step_type: Type of reasoning (e.g., 'INTENT_CLASSIFICATION', 'DATA_ANALYSIS', 'DECISION')
            input_state: Description of input/observations
            output_state: Description of conclusion/action
            confidence: Confidence level 0.0-1.0
        """
        structured_step = {
            "type": step_type,
            "input": input_state,
            "output": output_state,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        self._reasoning_steps.append(f"[{step_type}] {input_state} → {output_state} (conf: {confidence:.0%})")
        logger.debug(f"[{self.name}] Structured: {structured_step}")
    
    def record_context_access(self, layer: str):
        """Record that a context layer was accessed."""
        if access_controller.can_read(self.name, layer):
            self._context_accessed.append(layer)
        else:
            logger.warning(f"Agent {self.name} not permitted to access {layer}")
    
    async def invoke_llm(
        self, 
        prompt: str, 
        include_system_prompt: bool = True
    ) -> Dict[str, Any]:
        """
        Invoke the LLM with the agent's system prompt.
        
        Returns structured JSON output.
        """
        system = self.system_prompt if include_system_prompt else None
        
        return await llm_controller.invoke_agent(
            agent_name=self.name,
            system_prompt=system,
            input_data={"prompt": prompt},
            output_schema=self.output_schema
        )
    
    def get_permissions(self) -> Dict[str, List[str]]:
        """Get the agent's context access permissions."""
        return access_controller.get_agent_permissions(self.name)
