"""
LLM Controller
Manages LLM inference with multiple providers:
- OpenRouter (free models: qwen3-coder, nemotron, trinity, etc.)
- DeepSeek (fallback)
- MLX local (Apple Silicon)

Provides unified interface for all agents.
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import json
import asyncio
import os
from loguru import logger

from app.config import get_settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> str:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is available."""
        pass


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter-based LLM provider for free models.
    
    Supports models like:
    - qwen/qwen3-coder:free
    - qwen/qwen3-next-80b-a3b-instruct:free
    - nvidia/nemotron-3-super-120b-a12b:free
    - arcee-ai/trinity-large-preview:free
    - stepfun/step-3.5-flash:free
    - openai/gpt-oss-120b:free
    """
    
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self._client = None
    
    async def _get_client(self):
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(timeout=120.0)
            except ImportError:
                import aiohttp
                self._client = None  # Will use aiohttp directly
        return self._client
    
    async def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> str:
        """Generate text using OpenRouter API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://finagent.local",
            "X-Title": "FinAgent"
        }
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except ImportError:
            # Fallback to aiohttp
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    data = await response.json()
                    if "choices" in data:
                        return data["choices"][0]["message"]["content"]
                    elif "error" in data:
                        error_msg = data["error"].get("message", str(data["error"]))
                        logger.error(f"OpenRouter API error: {error_msg}")
                        raise Exception(f"OpenRouter error: {error_msg}")
                    else:
                        raise Exception(f"Unexpected response: {data}")


class DeepSeekProvider(LLMProvider):
    """
    DeepSeek LLM provider (fallback).
    """
    
    def __init__(self, api_key: str, model_name: str = "deepseek-chat"):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://api.deepseek.com/v1"
    
    async def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> str:
        """Generate text using DeepSeek API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except ImportError:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    data = await response.json()
                    if "choices" in data:
                        return data["choices"][0]["message"]["content"]
                    raise Exception(f"DeepSeek error: {data}")


class MLXProvider(LLMProvider):
    """
    MLX-based LLM provider for Apple Silicon.
    
    Uses mlx_vlm for local inference with Gemma 3 4B.
    """
    
    def __init__(self, model_name: str = "mlx-community/gemma-3-4b-it-4bit"):
        self.model_name = model_name
        self._model = None
        self._processor = None
        self._initialized = False
    
    async def initialize(self):
        """Load the model and processor in a thread pool to avoid blocking."""
        if self._initialized:
            return
        
        try:
            from mlx_lm import load
            
            logger.info(f"Loading MLX model: {self.model_name}")
            self._model, self._processor = await asyncio.to_thread(load, self.model_name)
            self._initialized = True
            logger.info("✅ MLX model loaded successfully")
        except ImportError:
            logger.warning("mlx_lm not available. Install with: pip install mlx mlx-lm")
            raise
        except Exception as e:
            logger.error(f"Failed to load MLX model: {e}")
            raise
    
    async def is_available(self) -> bool:
        """Check if MLX is available."""
        try:
            import mlx.core
            from mlx_lm import load
            return True
        except ImportError:
            return False
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> str:
        """Generate text using MLX."""
        if not self._initialized:
            await self.initialize()
        
        try:
            from mlx_lm import generate
            
            if system_prompt:
                formatted_prompt = f"<bos><start_of_turn>user\n{system_prompt}\n\n{prompt}<end_of_turn>\n<start_of_turn>model\n"
            else:
                formatted_prompt = f"<bos><start_of_turn>user\n{prompt}<end_of_turn>\n<start_of_turn>model\n"
            
            if json_mode:
                formatted_prompt = formatted_prompt.replace(
                    "<start_of_turn>model\n",
                    "<start_of_turn>model\nRespond with only valid JSON:\n"
                )
            
            def _generate():
                return generate(
                    self._model, 
                    self._processor, 
                    prompt=formatted_prompt, 
                    verbose=False, 
                    max_tokens=max_tokens
                )
            
            response = await asyncio.to_thread(_generate)
            return response.text if hasattr(response, 'text') else str(response)
            
        except Exception as e:
            logger.error(f"MLX generation failed: {e}")
            raise


class LLMController:
    """
    Central controller for LLM operations.
    
    Features:
    - OpenRouter provider (free models via OpenRouter API)
    - DeepSeek provider (fallback)
    - MLX provider for Apple Silicon (local inference)
    - Automatic fallback chain: OpenRouter → DeepSeek → MLX
    - Structured JSON output
    - Agent-specific prompting
    - Response validation
    """
    
    # Free OpenRouter models available for multi-agent use
    FREE_MODELS = [
        "qwen/qwen3-coder:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "arcee-ai/trinity-large-preview:free",
        "stepfun/step-3.5-flash:free",
        "openai/gpt-oss-120b:free",
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self.provider: Optional[LLMProvider] = None
        self._fallback_providers: List[LLMProvider] = []
        self._initialized = False
    
    async def initialize(self):
        """Initialize the LLM provider with fallback chain."""
        if self._initialized:
            return
        
        providers_to_try = []
        
        # Build provider chain based on config
        provider_name = self.settings.llm_provider.lower()
        
        # OpenRouter (primary for free models)
        if self.settings.openrouter_api_key:
            openrouter = OpenRouterProvider(
                model_name=self.settings.llm_model,
                api_key=self.settings.openrouter_api_key
            )
            providers_to_try.append(("openrouter", openrouter))
        
        # DeepSeek (fallback)
        if self.settings.deepseek_api_key:
            deepseek = DeepSeekProvider(
                api_key=self.settings.deepseek_api_key
            )
            providers_to_try.append(("deepseek", deepseek))
        
        # MLX (local fallback)
        try:
            mlx_provider = MLXProvider(self.settings.llm_model if "mlx" in self.settings.llm_model else "mlx-community/gemma-3-4b-it-4bit")
            if await mlx_provider.is_available():
                providers_to_try.append(("mlx", mlx_provider))
        except Exception:
            pass
        
        # Set primary provider based on config preference
        for name, prov in providers_to_try:
            if name == provider_name:
                self.provider = prov
                break
        
        # If preferred provider not found, use first available
        if self.provider is None and providers_to_try:
            self.provider = providers_to_try[0][1]
            logger.info(f"Using {providers_to_try[0][0]} as LLM provider (preferred {provider_name} not available)")
        
        # Set up fallback chain (all providers except primary)
        for name, prov in providers_to_try:
            if prov != self.provider:
                self._fallback_providers.append(prov)
        
        if self.provider:
            if isinstance(self.provider, MLXProvider):
                await self.provider.initialize()
            provider_type = type(self.provider).__name__
            logger.info(f"✅ LLM Controller initialized with {provider_type} (model: {self.settings.llm_model})")
            logger.info(f"   Fallback providers: {len(self._fallback_providers)}")
        else:
            logger.warning("⚠️ No LLM provider available!")
        
        self._initialized = True
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False
    ) -> str:
        """
        Generate text from prompt with automatic fallback.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            json_mode: If True, enforce JSON output
            
        Returns:
            Generated text
        """
        if not self._initialized:
            await self.initialize()
        
        if self.provider is None:
            return json.dumps({
                "error": "No LLM provider available",
                "message": "Configure OPENROUTER_API_KEY or DEEPSEEK_API_KEY in .env"
            })
            
        # Check cache
        from app.services.cache_service import cache_service
        
        cache_key_parts = [
            prompt, 
            str(system_prompt), 
            str(self.settings.llm_model),
            str(self.settings.llm_max_tokens),
            str(self.settings.llm_temperature),
            str(json_mode)
        ]
        cache_id = "_".join(cache_key_parts)
        
        cached_response = await cache_service.get_llm_cache(cache_id, self.settings.llm_model)
        if cached_response:
            logger.debug("LLM cache hit")
            return cached_response
        
        # Try primary provider, then fallbacks
        all_providers = [self.provider] + self._fallback_providers
        last_error = None
        
        for provider in all_providers:
            try:
                response = await provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=self.settings.llm_max_tokens,
                    temperature=self.settings.llm_temperature,
                    json_mode=json_mode
                )
                
                # Cache the response
                await cache_service.set_llm_cache(cache_id, self.settings.llm_model, response, ttl=3600)
                
                return response
            except Exception as e:
                provider_name = type(provider).__name__
                logger.warning(f"{provider_name} failed: {e}, trying next provider...")
                last_error = e
                continue
        
        logger.error(f"All LLM providers failed. Last error: {last_error}")
        return json.dumps({"error": str(last_error)})
    
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        output_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt with agent role
            output_schema: Expected JSON schema for validation
            
        Returns:
            Parsed JSON response
        """
        enhanced_system = f"""{system_prompt}

IMPORTANT: Your response must be valid JSON matching this schema:
{json.dumps(output_schema, indent=2)}

Respond with only the JSON object, no additional text."""
        
        response = await self.generate(
            prompt=prompt,
            system_prompt=enhanced_system,
            json_mode=True
        )
        
        try:
            response = response.strip()
            
            # Handle markdown code blocks
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            # Extract JSON with balanced brace counting
            start = response.find("{")
            if start == -1:
                raise json.JSONDecodeError("No JSON object found", response, 0)
            
            brace_count = 0
            end = start
            for i in range(start, len(response)):
                if response[i] == '{':
                    brace_count += 1
                elif response[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            if brace_count != 0:
                end = response.rfind("}") + 1
            
            if end > start:
                response = response[start:end]
            
            parsed = json.loads(response)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response}")
            return {"error": "Failed to parse response", "raw": response}
    
    async def invoke_agent(
        self,
        agent_name: str,
        system_prompt: str,
        input_data: Dict[str, Any],
        output_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invoke an agent with structured I/O.
        
        This is the main interface for agent-LLM interaction.
        
        Args:
            agent_name: Name of the agent
            system_prompt: Agent's system prompt
            input_data: Input data for the agent
            output_schema: Expected output schema
            
        Returns:
            Agent's structured output
        """
        logger.info(f"Invoking agent: {agent_name}")
        
        prompt = f"""Input:
{json.dumps(input_data, indent=2, default=str)}

Process this input according to your role and provide the structured output."""
        
        result = await self.generate_structured(
            prompt=prompt,
            system_prompt=system_prompt,
            output_schema=output_schema
        )
        
        logger.debug(f"Agent {agent_name} output: {result}")
        return result


# Singleton instance
llm_controller = LLMController()
