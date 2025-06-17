"""
API連接器模組 - 從 novel_writer.py 重構抽取
處理所有LLM API調用邏輯，支持OpenAI、Anthropic和自訂API
"""

import requests
import logging
from typing import Dict, List, Callable

from ..models import APIConfig, APIException

# 配置日誌
logger = logging.getLogger(__name__)


class APIConnector:
    """LLM API連接器 - 重構版"""
    
    def __init__(self, config: APIConfig, debug_callback: Callable = None):
        self.config = config
        self.debug_callback = debug_callback or (lambda x: None)
        
    def call_api(self, messages: List[Dict], max_tokens: int = 2000, 
                temperature: float = 0.7, use_planning_model: bool = False) -> Dict:
        """調用LLM API with retry logic"""
        
        # 根據是否使用規劃模型選擇配置
        if use_planning_model and self.config.use_planning_model:
            provider = self.config.planning_provider
            api_key = self.config.planning_api_key or self.config.api_key
            base_url = self.config.planning_base_url
            model = self.config.planning_model
            self.debug_callback("💡 使用規劃模型進行API調用")
        else:
            provider = self.config.provider
            api_key = self.config.api_key
            base_url = self.config.base_url
            model = self.config.model
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"API調用嘗試 {attempt + 1}/{self.config.max_retries} (模型: {model})")
                
                if provider == "openai":
                    return self._call_openai_api(messages, max_tokens, temperature, api_key, base_url, model)
                elif provider == "anthropic":
                    return self._call_anthropic_api(messages, max_tokens, temperature, api_key, base_url, model)
                elif provider == "custom":
                    return self._call_custom_api(messages, max_tokens, temperature, api_key, base_url, model)
                else:
                    raise APIException(f"不支持的API提供商: {provider}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"API調用失敗 (嘗試 {attempt + 1}): {str(e)}")
                if attempt == self.config.max_retries - 1:
                    raise APIException(f"API調用失敗，已重試 {self.config.max_retries} 次: {str(e)}")
            except Exception as e:
                logger.error(f"API調用出現未預期錯誤: {str(e)}")
                raise APIException(f"API調用錯誤: {str(e)}")
    
    def _call_openai_api(self, messages: List[Dict], max_tokens: int, 
                        temperature: float, api_key: str, base_url: str, model: str) -> Dict:
        """調用OpenAI格式API"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # 如果啟用了關閉thinking，添加thinking參數
        if self.config.disable_thinking:
            data["thinking"] = False
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=self.config.timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "content": result["choices"][0]["message"]["content"],
                "usage": result.get("usage", {}),
                "model": result.get("model", model)
            }
        else:
            raise APIException(f"API調用失敗: {response.status_code} {response.text}")
    
    def _call_anthropic_api(self, messages: List[Dict], max_tokens: int, 
                           temperature: float, api_key: str, base_url: str, model: str) -> Dict:
        """調用Anthropic API"""
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # 轉換消息格式
        system_message = ""
        if messages and messages[0]["role"] == "system":
            system_message = messages[0]["content"]
            messages = messages[1:]
        
        data = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_message:
            data["system"] = system_message
        
        response = requests.post(
            f"{base_url}/messages",
            headers=headers,
            json=data,
            timeout=self.config.timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "content": result["content"][0]["text"],
                "usage": result.get("usage", {}),
                "model": result.get("model", model)
            }
        else:
            raise APIException(f"API調用失敗: {response.status_code} {response.text}")
    
    def _call_custom_api(self, messages: List[Dict], max_tokens: int, 
                        temperature: float, api_key: str, base_url: str, model: str) -> Dict:
        """調用自訂API"""
        return self._call_openai_api(messages, max_tokens, temperature, api_key, base_url, model)