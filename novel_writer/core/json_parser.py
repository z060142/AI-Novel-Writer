"""
JSON解析器模組 - 從 novel_writer.py 重構抽取
處理從文本內容中提取和解析JSON數據的邏輯
"""

import json
import re
from typing import Dict, Optional


class JSONParser:
    """JSON解析器 - 重構版"""
    
    @staticmethod
    def extract_json_from_content(content: str) -> Optional[Dict]:
        """從內容中提取JSON"""
        strategies = [
            (r'```json\s*(.*?)\s*```', re.DOTALL),
            (r'```\s*(\{.*?\})\s*```', re.DOTALL),
            (r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL),
        ]
        
        for pattern, flags in strategies:
            matches = re.findall(pattern, content, flags)
            
            for match in matches:
                json_str = match.strip() if isinstance(match, str) else match
                json_str = JSONParser._clean_json_string(json_str)
                
                try:
                    result = json.loads(json_str)
                    if isinstance(result, dict) and result:
                        return result
                except json.JSONDecodeError:
                    continue
        
        return JSONParser._attempt_json_repair(content)
    
    @staticmethod
    def _clean_json_string(json_str: str) -> str:
        """清理JSON字符串"""
        json_str = json_str.lstrip('\ufeff').strip()
        
        start_brace = json_str.find('{')
        if start_brace != -1:
            json_str = json_str[start_brace:]
        
        end_brace = json_str.rfind('}')
        if end_brace != -1:
            json_str = json_str[:end_brace + 1]
        
        return json_str
    
    @staticmethod
    def _attempt_json_repair(content: str) -> Optional[Dict]:
        """嘗試修復損壞的JSON"""
        json_start = content.find('{')
        if json_start == -1:
            return None
        
        json_part = content[json_start:]
        brace_count = 0
        valid_end = -1
        
        for i, char in enumerate(json_part):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    valid_end = i + 1
                    break
        
        if valid_end > 0:
            repaired_json = json_part[:valid_end]
            try:
                return json.loads(repaired_json)
            except json.JSONDecodeError:
                pass
        
        return None