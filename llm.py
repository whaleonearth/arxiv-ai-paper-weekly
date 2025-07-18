import os
from pathlib import Path
from typing import Optional, List
from llama_cpp import Llama
from openai import OpenAI
from loguru import logger
from time import sleep

GLOBAL_LLM = None

def discover_local_models(models_dir: str = "models") -> Optional[dict]:
    """Auto-discover local models in the models directory.
    
    Args:
        models_dir: Directory to search for models
        
    Returns:
        Dict with model info if found, None otherwise
    """
    models_path = Path(models_dir)
    if not models_path.exists():
        logger.info(f"Models directory '{models_dir}' not found")
        return None
    
    logger.info(f"Scanning for local models in '{models_dir}'...")
    
    # Look for GGUF models (llama-cpp-python)
    gguf_files = list(models_path.glob("*.gguf"))
    if gguf_files:
        model_file = gguf_files[0]
        logger.info(f"Found GGUF model: {model_file}")
        return {
            "type": "gguf",
            "path": str(model_file),
            "name": model_file.name
        }
    
    # Look for transformers models (safetensors, bin files)
    safetensors_files = list(models_path.glob("*.safetensors"))
    bin_files = list(models_path.glob("*.bin"))
    
    if safetensors_files or bin_files:
        # For transformers, we need the directory containing the model files
        logger.info(f"Found transformers model files in: {models_path}")
        return {
            "type": "transformers", 
            "path": str(models_path),
            "name": models_path.name
        }
    
    # Look for model subdirectories (common for HuggingFace models)
    model_dirs = [d for d in models_path.iterdir() if d.is_dir()]
    for model_dir in model_dirs:
        # Check if directory contains model files
        has_config = (model_dir / "config.json").exists()
        has_model = any(model_dir.glob("*.safetensors")) or any(model_dir.glob("*.bin"))
        
        if has_config and has_model:
            logger.info(f"Found transformers model directory: {model_dir}")
            return {
                "type": "transformers",
                "path": str(model_dir), 
                "name": model_dir.name
            }
    
    logger.info("No compatible local models found")
    return None

def load_local_gguf_model(model_path: str) -> Llama:
    """Load a GGUF model using llama-cpp-python.
    
    Args:
        model_path: Path to the GGUF model file
        
    Returns:
        Loaded Llama model
    """
    logger.info(f"Loading GGUF model from: {model_path}")
    return Llama(
        model_path=model_path,
        n_ctx=5_000,
        n_threads=4,
        verbose=False,
    )

def load_local_transformers_model(model_path: str):
    """Load a transformers model using HuggingFace transformers.
    
    Args:
        model_path: Path to the model directory
        
    Returns:
        Loaded model and tokenizer
    """
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        logger.info(f"Loading transformers model from: {model_path}")
        
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype="auto"
        )
        
        return {"model": model, "tokenizer": tokenizer}
    except ImportError:
        logger.error("transformers library not installed. Install with: pip install transformers torch")
        raise
    except Exception as e:
        logger.error(f"Failed to load transformers model: {e}")
        raise

class LLM:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None, 
                 lang: str = "English", use_local_model: bool = False):
        self.model = model
        self.lang = lang
        self.local_model_info = None
        
        if use_local_model:
            # Try to auto-discover and load local model
            self.local_model_info = discover_local_models()
            
            if self.local_model_info:
                logger.info(f"Using local model: {self.local_model_info['name']}")
                
                if self.local_model_info["type"] == "gguf":
                    self.llm = load_local_gguf_model(self.local_model_info["path"])
                    self.model_type = "gguf"
                elif self.local_model_info["type"] == "transformers":
                    self.llm = load_local_transformers_model(self.local_model_info["path"])
                    self.model_type = "transformers"
            else:
                logger.warning("No local model found, falling back to API mode")
                if not api_key:
                    raise ValueError("No local model found and no API key provided")
                self.llm = OpenAI(api_key=api_key, base_url=base_url)
                self.model_type = "api"
        elif api_key:
            # Use API mode
            logger.info("Using cloud LLM API")
            self.llm = OpenAI(api_key=api_key, base_url=base_url)
            self.model_type = "api"
        else:
            # Fallback to default local model (backward compatibility)
            logger.info("Using default local model (Qwen)")
            self.llm = Llama.from_pretrained(
                repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
                filename="qwen2.5-3b-instruct-q4_k_m.gguf",
                n_ctx=5_000,
                n_threads=4,
                verbose=False,
            )
            self.model_type = "gguf"

    def generate(self, messages: list[dict]) -> str:
        """Generate text using the loaded model."""
        if self.model_type == "api":
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.llm.chat.completions.create(
                        messages=messages, 
                        temperature=0, 
                        model=self.model
                    )
                    break
                except Exception as e:
                    logger.error(f"API attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    sleep(3)
            return response.choices[0].message.content
            
        elif self.model_type == "gguf":
            response = self.llm.create_chat_completion(messages=messages, temperature=0)
            return response["choices"][0]["message"]["content"]
            
        elif self.model_type == "transformers":
            # Simple text generation for transformers models
            try:
                model = self.llm["model"]
                tokenizer = self.llm["tokenizer"]
                
                # Convert messages to a single prompt (simple approach)
                prompt = ""
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    prompt += f"{role}: {content}\n"
                prompt += "assistant:"
                
                import torch
                inputs = tokenizer.encode(prompt, return_tensors="pt")
                with torch.no_grad():
                    outputs = model.generate(
                        inputs,
                        max_new_tokens=500,
                        temperature=0.1,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id
                    )
                
                response = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
                return response.strip()
                
            except Exception as e:
                logger.error(f"Transformers generation failed: {e}")
                return "Error generating response with local model"

def set_global_llm(api_key: str = None, base_url: str = None, model: str = None, 
                   lang: str = "English", use_local_model: bool = False):
    """Set the global LLM instance."""
    global GLOBAL_LLM
    GLOBAL_LLM = LLM(
        api_key=api_key, 
        base_url=base_url, 
        model=model, 
        lang=lang,
        use_local_model=use_local_model
    )

def get_llm() -> LLM:
    """Get the global LLM instance."""
    if GLOBAL_LLM is None:
        logger.info("No global LLM found, creating a default one. Use `set_global_llm` to set a custom one.")
        set_global_llm()
    return GLOBAL_LLM