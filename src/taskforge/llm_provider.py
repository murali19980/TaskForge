import json
import logging
import re
import asyncio
import warnings
from typing import Type, Protocol, Any
import httpx
from pydantic import BaseModel
from taskforge.models import (
    CategoriesResponse,
    TasksResponse,
    DependencyMapResponse,
    Task,
    UsageStats
)
from taskforge.config import settings
from taskforge.exceptions import LLMOutputError

logger = logging.getLogger("taskforge.llm_provider")

def _strip_markdown_json(text: str) -> str:
    """Extracts the first valid JSON object from the text using stripping and fallback extraction."""
    text = text.strip()
    
    # 1. Strip markdown code fences if present (e.g. ```json, ```js, ```)
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # 2. Try loading as-is
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 3. Fallback: Extract using brace counting to handle trailing/leading text and nested structures
    first_brace = text.find("{")
    if first_brace == -1:
        return text

    brace_count = 0
    in_string = False
    escape = False

    for i in range(first_brace, len(text)):
        char = text[i]
        
        # Track if we are inside a string to ignore braces in string literals
        if char == '"' and not escape:
            in_string = not in_string
        
        # Track escape characters inside string
        if char == '\\' and in_string:
            escape = not escape
        else:
            escape = False

        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found the end of the JSON object
                    candidate = text[first_brace:i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        pass
    
    # 4. If brace counter didn't find a complete object, give up cleanly
    return text


class BaseLLMProvider(Protocol):
    async def generate_json(self, prompt: str, expected_schema: Type[BaseModel]) -> tuple[BaseModel, UsageStats]:
        """Sends prompt to LLM and returns validated Pydantic model response with UsageStats."""
        ...

class OllamaProvider:
    def __init__(self, host: str = None, model: str = None):
        self.host = host or settings.OLLAMA_HOST
        self.model = model or settings.OLLAMA_MODEL
        logger.info(f"OllamaProvider initialized with host={self.host}, model={self.model}")

    async def generate_json(self, prompt: str, expected_schema: Type[BaseModel]) -> tuple[BaseModel, UsageStats]:
        url = f"{self.host.rstrip('/')}/api/generate"

        # We pass the schema directly to Ollama's format field to force JSON conforming to the schema
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": expected_schema.model_json_schema(),
            "options": {
                "temperature": 0.1
            }
        }

        import hashlib
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:12]
        logger.debug(f"Sending request to Ollama with prompt hash: {prompt_hash}")

        async with httpx.AsyncClient(timeout=float(settings.LLM_REQUEST_TIMEOUT)) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                response_text = data.get("response", "").strip()

                response_hash = hashlib.sha256(response_text.encode()).hexdigest()[:12]
                logger.debug(f"Raw Ollama response hash: {response_hash}")

                # Strip markdown wrappers
                response_text = _strip_markdown_json(response_text)

                # Parse response_text into JSON
                parsed_json = json.loads(response_text)

                # Validate using Pydantic model
                model_inst = expected_schema.model_validate(parsed_json)

                # Extract token usage from Ollama metadata
                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)
                total_tokens = prompt_tokens + completion_tokens

                usage = UsageStats(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_usd=0.0
                )

                return model_inst, usage

            except httpx.HTTPStatusError as e:
                logger.error(f"Ollama returned HTTP error status: {e.response.status_code}")
                raise
            except httpx.HTTPError as e:
                logger.error(f"HTTP error contacting Ollama: {str(e)}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Ollama returned invalid JSON. Error: {str(e)}")
                raise LLMOutputError(f"Ollama returned invalid JSON: {str(e)}")
            except Exception as e:
                logger.error(f"Validation or unexpected error: {str(e)}")
                raise

class OpenRouterProvider:
    DEFAULT_MAX_TOKENS = 4096

    def __init__(self, api_key: str = None, model: str = None):
        self._backend_key = settings.OPENROUTER_API_KEY
        self.api_key = api_key or self._backend_key
        self.model = model
        if model:
            self.model_list = [model]
        else:
            self.model_list = settings.openrouter_model_list
            self.model = self.model_list[0] if self.model_list else settings.OPENROUTER_MODEL
        logger.info(f"OpenRouterProvider initialized with models={self.model_list}")

    async def generate_json(self, prompt: str, expected_schema: Type[BaseModel]) -> tuple[BaseModel, UsageStats]:
        effective_key = self._backend_key
        if not effective_key:
            raise ValueError("OpenRouter API key is missing. Set OPENROUTER_API_KEY in your config/.env file.")

        logger.info("Using backend OpenRouter API key (from .env)")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {effective_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TaskForge"
        }

        # Enforce json_object mode and pass the expected schema description in the system prompt
        schema_desc = json.dumps(expected_schema.model_json_schema(), indent=2)
        system_prompt = (
            "You are a helpful software architecture assistant.\n"
            "You MUST return a JSON object that adheres EXACTLY to the following JSON Schema:\n"
            f"{schema_desc}\n"
            "Output only the raw JSON object, without markdown block wrappers or extra text."
        )

        import hashlib
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:12]
        logger.debug(f"Sending request to OpenRouter with prompt hash: {prompt_hash}")

        last_exception = None
        for model in self.model_list:
            logger.info(f"OpenRouter attempting generation using model '{model}'...")
            
            max_attempts = 3
            current_max_tokens = self.DEFAULT_MAX_TOKENS
            try:
                async with httpx.AsyncClient(timeout=float(settings.LLM_REQUEST_TIMEOUT)) as client:
                    for attempt in range(1, max_attempts + 1):
                        payload = {
                            "model": model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt}
                            ],
                            "response_format": {"type": "json_object"},
                            "temperature": 0.1
                        }
                        if current_max_tokens:
                            payload["max_tokens"] = current_max_tokens

                        try:
                            response = await client.post(url, json=payload, headers=headers)
                            response.raise_for_status()
                            data = response.json()

                            # Catch API errors
                            if "error" in data:
                                err_msg = data["error"].get("message", "Unknown OpenRouter error")
                                raise ValueError(f"OpenRouter API returned error: {err_msg}")

                            response_text = data["choices"][0]["message"]["content"].strip()
                            response_hash = hashlib.sha256(response_text.encode()).hexdigest()[:12]
                            logger.debug(f"Raw OpenRouter response hash: {response_hash}")

                            # Strip markdown wrappers
                            response_text = _strip_markdown_json(response_text)

                            parsed_json = json.loads(response_text)
                            model_inst = expected_schema.model_validate(parsed_json)

                            # Extract token usage
                            usage_data = data.get("usage", {})
                            prompt_tokens = usage_data.get("prompt_tokens", 0)
                            completion_tokens = usage_data.get("completion_tokens", 0)
                            total_tokens = usage_data.get("total_tokens", 0)

                            # Price per 1M tokens mapping: (input_cost_usd, output_cost_usd)
                            PRICING = {
                                "google/gemini-2.5-flash:free": (0.0, 0.0),
                                "google/gemini-2.5-flash": (0.075, 0.30),
                                "mistralai/mistral-nemo:free": (0.0, 0.0),
                                "mistralai/mistral-nemo": (0.17, 0.17),
                                "openai/gpt-4o-mini": (0.150, 0.60),
                                "openrouter/free": (0.0, 0.0),
                            }

                            if model in PRICING:
                                rates = PRICING[model]
                            elif model.endswith(":free") or model == "openrouter/free":
                                rates = (0.0, 0.0)
                            else:
                                logger.critical(f"CRITICAL WARNING: Unknown non-free model '{model}' requested. Using fallback rates (0.0, 0.0) but cost may be incurred.")
                                warnings.warn(f"Model '{model}' is not configured in pricing dictionary. Costs may occur.", UserWarning)
                                rates = (0.0, 0.0)
                            input_cost = (prompt_tokens * rates[0]) / 1_000_000
                            output_cost = (completion_tokens * rates[1]) / 1_000_000
                            estimated_cost = input_cost + output_cost

                            usage = UsageStats(
                                prompt_tokens=prompt_tokens,
                                completion_tokens=completion_tokens,
                                total_tokens=total_tokens,
                                estimated_cost_usd=estimated_cost
                            )

                            return model_inst, usage

                        except httpx.HTTPStatusError as e:
                            if e.response.status_code == 429:
                                retry_after = 2.0  # default backoff
                                retry_after_hdr = e.response.headers.get("Retry-After")
                                if retry_after_hdr:
                                    try:
                                        retry_after = float(retry_after_hdr)
                                    except ValueError:
                                        pass
                                logger.warning(
                                    f"OpenRouter rate limit (429) hit for model '{model}'. "
                                    f"Retry-After header: {retry_after_hdr}. "
                                    f"Waiting {retry_after}s before retry attempt {attempt}/{max_attempts}..."
                                )
                                if attempt == max_attempts:
                                    logger.error(f"Max rate limit retries reached for model '{model}'.")
                                    raise
                                await asyncio.sleep(retry_after)
                                continue
                            else:
                                # Only log the status code — never log response body (may contain account/quota data)
                                logger.error(f"OpenRouter returned HTTP error status: {e.response.status_code}")
                                raise
                        except httpx.HTTPError as e:
                            logger.error(f"HTTP error contacting OpenRouter: {str(e)}")
                            raise
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode OpenRouter response as JSON. Error: {str(e)}")
                            if attempt < max_attempts:
                                current_max_tokens = min(int(current_max_tokens * 1.5), 4096)
                                logger.warning(f"Retrying OpenRouter request with max_tokens={current_max_tokens} due to JSONDecodeError (attempt {attempt}/{max_attempts})")
                                continue
                            else:
                                raise LLMOutputError(f"OpenRouter returned invalid JSON: {str(e)}")
                        except Exception as e:
                            logger.error(f"Validation or unexpected error in OpenRouter call: {str(e)}")
                            raise
            except Exception as e:
                logger.warning(f"OpenRouter model '{model}' failed with error: {e}. Trying next model in fallback list...")
                last_exception = e
                continue

        raise last_exception or ValueError("All OpenRouter models in fallback list failed.")

