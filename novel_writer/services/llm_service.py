"""
LLM服務層 - 處理語言模型調用和回應解析

這個模組包含了從 novel_writer.py 中提取的 LLMService 類，
該類負責處理語言模型的調用和回應解析。

依賴項：
- APIConnector: API連接器，處理實際的API調用
- TextFormatter: 文本格式化工具
- TaskType: 任務類型枚舉
- JSONParseException: JSON解析異常
- JSONParser: JSON解析工具
- PromptManager: Prompt管理器
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Callable

from ..models import TaskType, JSONParseException
from ..core import JSONParser, PromptManager

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM服務層
    
    負責處理語言模型的調用，包括：
    - 調用LLM API
    - 處理回應內容
    - JSON解析和重試機制
    - 思考內容提取
    - 錯誤處理
    
    依賴項：
    - APIConnector: 處理API調用
    - JSONParser: 解析JSON回應
    - PromptManager: 管理系統提示詞和token限制
    """
    
    def __init__(self, api_connector, debug_callback: Callable = None):
        """
        初始化LLM服務
        
        Args:
            api_connector: API連接器實例
            debug_callback: 調試回調函數，用於輸出調試信息
        """
        self.api_connector = api_connector
        self.debug_callback = debug_callback or (lambda x: None)
        self.json_retry_max = 3  # JSON解析重試次數
    
    def call_llm_with_thinking(self, prompt: str, task_type, 
                              max_tokens: int = None, use_planning_model: bool = False) -> Optional[Dict]:
        """
        使用thinking模式調用LLM，包含JSON解析重試機制
        
        Args:
            prompt: 用戶提示詞
            task_type: 任務類型（TaskType枚舉）
            max_tokens: 最大token數量，如果為None則使用任務類型的默認值
            use_planning_model: 是否使用規劃模型
            
        Returns:
            解析後的JSON數據字典，如果失敗則返回None
            
        Raises:
            JSONParseException: 當JSON解析重試失敗時
            Exception: 其他API調用異常
        """
        # 這裡需要導入 PromptManager 來獲取token限制和系統提示詞
        # PromptManager already imported
        
        if max_tokens is None:
            max_tokens = PromptManager.get_token_limit(task_type)
        
        system_prompt = PromptManager.create_system_prompt(task_type)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        self.debug_callback(f"\n=== {task_type.value.upper()} 任務開始 ===")
        self.debug_callback(f"使用token限制: {max_tokens}")
        
        # JSON解析重試循環
        for json_attempt in range(self.json_retry_max):
            try:
                self.debug_callback(f"📤 正在調用API... (JSON解析嘗試 {json_attempt + 1}/{self.json_retry_max})")
                
                result = self.api_connector.call_api(messages, max_tokens, use_planning_model=use_planning_model)
                content = result.get("content", "")
                
                self.debug_callback(f"✅ API調用成功，回應長度: {len(content)} 字符")
                
                # 嘗試提取並顯示思考內容
                thinking_content = self._extract_thinking_content(content)
                if thinking_content:
                    self.debug_callback(f"🧠 思考過程:\n{thinking_content}")
                
                self.debug_callback(f"📝 API完整回應:\n{content}")
                
                # 這裡需要導入 JSONParser 來解析JSON
                # JSONParser and JSONParseException already imported
                
                json_data = JSONParser.extract_json_from_content(content)
                
                if json_data:
                    self.debug_callback("✅ JSON解析成功")
                    self.debug_callback(f"📋 解析結果:\n{json.dumps(json_data, ensure_ascii=False, indent=2)}")
                    return json_data
                else:
                    self.debug_callback(f"❌ JSON解析失敗 (嘗試 {json_attempt + 1}/{self.json_retry_max})")
                    self.debug_callback(f"📄 原始回應內容:\n{content}")
                    self.debug_callback(f"📄 回應內容類型: {type(content)}")
                    self.debug_callback(f"📄 回應長度: {len(content)}")
                    
                    # 如果不是最後一次嘗試，修改prompt並重試
                    if json_attempt < self.json_retry_max - 1:
                        self.debug_callback("🔄 準備重試，調整prompt以強調JSON格式...")
                        messages = self._enhance_json_prompt(messages, json_attempt + 1)
                        continue
                    else:
                        self.debug_callback("❌ JSON解析重試次數已用盡")
                        raise JSONParseException("經過多次重試仍無法解析JSON回應")
                        
            except Exception as e:
                # 檢查是否是JSON解析異常
                if "JSONParseException" in str(type(e)):
                    # JSON解析異常，繼續重試循環
                    if json_attempt == self.json_retry_max - 1:
                        raise
                    continue
                else:
                    self.debug_callback(f"❌ LLM調用失敗: {str(e)}")
                    raise
        
        # 理論上不會到達這裡
        # JSONParseException already imported
        raise JSONParseException("JSON解析重試機制異常結束")
    
    def _enhance_json_prompt(self, messages: List[Dict], retry_count: int) -> List[Dict]:
        """
        增強JSON格式要求的prompt
        
        根據重試次數調整提示詞的強度，逐漸加強對JSON格式的要求
        
        Args:
            messages: 原始消息列表
            retry_count: 重試次數
            
        Returns:
            增強後的消息列表
        """
        enhanced_messages = messages.copy()
        
        # 根據重試次數調整策略
        if retry_count == 1:
            # 第一次重試：強調JSON格式
            json_emphasis = """

⚠️ 重要提醒：請務必嚴格按照JSON格式回應！
- 必須使用```json```代碼塊包圍JSON內容
- 確保JSON語法正確，所有字符串都用雙引號包圍
- 不要在JSON前後添加任何解釋文字
- 確保所有括號和逗號都正確配對

示例格式：
```json
{
    "key": "value"
}
```"""
            
        elif retry_count == 2:
            # 第二次重試：更嚴格的要求
            json_emphasis = """

🚨 最後警告：JSON格式要求！
- 只能輸出JSON，不要任何其他文字
- 使用標準JSON語法，不要使用單引號
- 確保所有數字不要用引號包圍
- 確保布爾值使用true/false而不是True/False
- 陣列和物件的最後一個元素後不要有逗號

嚴格按照以下格式：
```json
{
    "required_field": "必填內容"
}
```

立即輸出JSON，不要任何解釋！"""
        
        else:
            # 其他情況的通用強調
            json_emphasis = """

📋 JSON格式檢查清單：
✓ 使用```json```代碼塊
✓ 所有字符串用雙引號
✓ 數字不用引號
✓ 布爾值用true/false
✓ 最後元素無逗號
✓ 括號正確配對

請立即輸出正確的JSON格式！"""
        
        # 修改用戶消息，添加JSON格式強調
        if enhanced_messages and enhanced_messages[-1]["role"] == "user":
            enhanced_messages[-1]["content"] += json_emphasis
        
        return enhanced_messages
    
    def _extract_thinking_content(self, content: str) -> Optional[str]:
        """
        從API回應中提取思考內容
        
        支持多種思考標記格式：
        - <thinking>...</thinking>
        - <think>...</think>
        - 【思考】...【/思考】
        - 思考：...
        - Thinking: ...
        
        Args:
            content: API回應內容
            
        Returns:
            提取的思考內容，如果沒有找到則返回None
        """
        try:
            # 嘗試匹配常見的思考標記格式
            thinking_patterns = [
                # <thinking>...</thinking> 格式
                (r'<thinking>(.*?)</thinking>', re.DOTALL | re.IGNORECASE),
                # <think>...</think> 格式
                (r'<think>(.*?)</think>', re.DOTALL | re.IGNORECASE),
                # 【思考】...【/思考】格式
                (r'【思考】(.*?)【/思考】', re.DOTALL),
                # 思考：...（結束標記可能不明確）
                (r'思考[：:](.*?)(?=\n\n|\n[^思]|$)', re.DOTALL),
                # Thinking: ... 格式
                (r'Thinking[：:]?(.*?)(?=\n\n|\n[^T]|$)', re.DOTALL | re.IGNORECASE),
            ]
            
            for pattern, flags in thinking_patterns:
                matches = re.findall(pattern, content, flags)
                if matches:
                    # 取第一個匹配的思考內容
                    thinking_text = matches[0].strip()
                    if thinking_text and len(thinking_text) > 10:  # 確保不是空內容
                        return thinking_text
            
            # 如果沒有找到明確的思考標記，嘗試檢測可能的思考內容
            # 查找在JSON之前的文本內容，可能包含思考過程
            json_start = content.find('```json')
            if json_start > 50:  # 如果JSON前有足夠的內容
                pre_json_content = content[:json_start].strip()
                # 檢查是否包含思考相關的關鍵詞
                thinking_keywords = ['思考', '分析', '考慮', 'thinking', 'consider', 'analyze']
                if any(keyword in pre_json_content.lower() for keyword in thinking_keywords):
                    # 取最後幾段作為可能的思考內容
                    lines = pre_json_content.split('\n')
                    if len(lines) > 2:
                        potential_thinking = '\n'.join(lines[-3:]).strip()
                        if len(potential_thinking) > 20:
                            return potential_thinking
            
            return None
            
        except Exception as e:
            # 如果提取過程出錯，記錄但不影響主流程
            logger.debug(f"提取思考內容時發生錯誤: {str(e)}")
            return None


# 使用範例：
# 
# # 初始化服務
# api_connector = APIConnector(config)
# llm_service = LLMService(api_connector, debug_callback=print)
# 
# # 調用LLM
# result = llm_service.call_llm_with_thinking(
#     prompt="請生成一個小說大綱",
#     task_type=TaskType.OUTLINE,
#     max_tokens=8000
# )
# 
# if result:
#     print(f"生成的大綱: {result}")