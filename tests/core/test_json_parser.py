"""
測試 core.json_parser 模組
"""

import unittest
import sys
import os
import json

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from novel_writer.core.json_parser import JSONParser


class TestJSONParser(unittest.TestCase):
    """測試JSON解析器"""
    
    def test_extract_from_json_code_block(self):
        """測試從JSON代碼塊提取"""
        content = """
        這是一些說明文字。
        
        ```json
        {
            "title": "測試標題",
            "content": "測試內容",
            "chapters": ["第一章", "第二章"]
        }
        ```
        
        更多說明文字。
        """
        
        result = JSONParser.extract_json_from_content(content)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "測試標題")
        self.assertEqual(result["content"], "測試內容")
        self.assertEqual(len(result["chapters"]), 2)
    
    def test_extract_from_plain_code_block(self):
        """測試從普通代碼塊提取"""
        content = """
        說明文字...
        
        ```
        {
            "name": "測試名稱",
            "value": 42
        }
        ```
        """
        
        result = JSONParser.extract_json_from_content(content)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "測試名稱")
        self.assertEqual(result["value"], 42)
    
    def test_extract_from_bare_json(self):
        """測試從裸露JSON提取"""
        content = """
        這裡有一些JSON：
        {"message": "你好世界", "status": "success"}
        結束。
        """
        
        result = JSONParser.extract_json_from_content(content)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["message"], "你好世界")
        self.assertEqual(result["status"], "success")
    
    def test_extract_with_chinese_content(self):
        """測試包含中文內容的JSON"""
        json_data = {
            "標題": "測試小說",
            "主題": "冒險",
            "角色": ["小明", "小紅", "老師"],
            "章節": {
                "第一章": "開始的故事",
                "第二章": "發展劇情"
            }
        }
        
        content = f"```json\n{json.dumps(json_data, ensure_ascii=False, indent=2)}\n```"
        result = JSONParser.extract_json_from_content(content)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["標題"], "測試小說")
        self.assertEqual(result["主題"], "冒險")
        self.assertEqual(len(result["角色"]), 3)
        self.assertIn("小明", result["角色"])
        self.assertEqual(result["章節"]["第一章"], "開始的故事")
    
    def test_clean_json_string(self):
        """測試JSON字符串清理"""
        # 測試BOM字符清理
        json_with_bom = '\ufeff{"test": "value"}'
        cleaned = JSONParser._clean_json_string(json_with_bom)
        self.assertEqual(cleaned, '{"test": "value"}')
        
        # 測試前後多餘字符清理
        messy_json = '   some text {"key": "value"} trailing text   '
        cleaned = JSONParser._clean_json_string(messy_json)
        self.assertEqual(cleaned, '{"key": "value"}')
        
        # 測試嵌套大括號
        nested_json = 'prefix {"outer": {"inner": "value"}} suffix'
        cleaned = JSONParser._clean_json_string(nested_json)
        self.assertEqual(cleaned, '{"outer": {"inner": "value"}}')
    
    def test_attempt_json_repair(self):
        """測試JSON修復"""
        # 測試不完整的JSON
        incomplete_json = 'some text {"title": "Test", "content": "Some content"'
        result = JSONParser._attempt_json_repair(incomplete_json)
        self.assertIsNone(result)  # 無法修復
        
        # 測試可修復的JSON
        repairable_json = '{"title": "Test", "content": "Value"} extra text'
        result = JSONParser._attempt_json_repair(repairable_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Test")
        self.assertEqual(result["content"], "Value")
        
        # 測試嵌套結構的修復
        nested_repairable = '{"outer": {"inner": "value"}, "other": "data"} garbage'
        result = JSONParser._attempt_json_repair(nested_repairable)
        self.assertIsNotNone(result)
        self.assertEqual(result["outer"]["inner"], "value")
        self.assertEqual(result["other"], "data")
    
    def test_multiple_json_blocks(self):
        """測試多個JSON塊的情況"""
        content = """
        第一個JSON塊：
        ```json
        {"first": "第一個"}
        ```
        
        第二個JSON塊：
        ```json
        {"second": "第二個"}
        ```
        """
        
        result = JSONParser.extract_json_from_content(content)
        
        # 應該返回第一個有效的JSON
        self.assertIsNotNone(result)
        self.assertEqual(result["first"], "第一個")
        self.assertNotIn("second", result)
    
    def test_invalid_json_handling(self):
        """測試無效JSON處理"""
        invalid_contents = [
            "這裡沒有JSON",
            "```json\n這不是JSON\n```",
            "{'invalid': json}",  # 單引號
            "```json\n{incomplete: json\n```",
            "",  # 空內容
            "   \n\n   "  # 只有空白
        ]
        
        for content in invalid_contents:
            with self.subTest(content=content[:20]):
                result = JSONParser.extract_json_from_content(content)
                self.assertIsNone(result)
    
    def test_complex_nested_json(self):
        """測試複雜嵌套JSON"""
        complex_data = {
            "小說": {
                "基本信息": {
                    "標題": "魔法學院",
                    "作者": "測試作者",
                    "類型": ["奇幻", "冒險"]
                },
                "章節": [
                    {
                        "章節號": 1,
                        "標題": "新生入學",
                        "段落": [
                            {"順序": 1, "目的": "場景描述"},
                            {"順序": 2, "目的": "角色介紹"}
                        ]
                    },
                    {
                        "章節號": 2,
                        "標題": "魔法考試",
                        "段落": [
                            {"順序": 1, "目的": "考試準備"},
                            {"順序": 2, "目的": "考試過程"}
                        ]
                    }
                ],
                "世界設定": {
                    "角色": {
                        "主角": "艾莉絲，16歲魔法學徒",
                        "導師": "梅林教授，經驗豐富的魔法師"
                    },
                    "場景": {
                        "學院": "古老的魔法學院，坐落在雲霧繚繞的山頂",
                        "圖書館": "藏有無數魔法書籍的神秘圖書館"
                    }
                }
            }
        }
        
        content = f"```json\n{json.dumps(complex_data, ensure_ascii=False, indent=2)}\n```"
        result = JSONParser.extract_json_from_content(content)
        
        self.assertIsNotNone(result)
        self.assertIn("小說", result)
        self.assertEqual(result["小說"]["基本信息"]["標題"], "魔法學院")
        self.assertEqual(len(result["小說"]["章節"]), 2)
        self.assertEqual(result["小說"]["章節"][0]["標題"], "新生入學")
        self.assertEqual(len(result["小說"]["章節"][0]["段落"]), 2)
        self.assertIn("主角", result["小說"]["世界設定"]["角色"])
    
    def test_json_with_special_characters(self):
        """測試包含特殊字符的JSON"""
        special_data = {
            "對話": "「你好！」他說道。",
            "描述": "天空中飄著雲朵——白色的、柔軟的雲朵。",
            "符號": "★☆♪♫♦♣♠♥",
            "數字": "一、二、三、四、五",
            "標點": "。！？：；，、",
            "引號": "『內層引號』「外層引號」"
        }
        
        content = f"```json\n{json.dumps(special_data, ensure_ascii=False)}\n```"
        result = JSONParser.extract_json_from_content(content)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["對話"], "「你好！」他說道。")
        self.assertEqual(result["描述"], "天空中飄著雲朵——白色的、柔軟的雲朵。")
        self.assertIn("★", result["符號"])
        self.assertEqual(result["引號"], "『內層引號』「外層引號」")
    
    def test_edge_cases(self):
        """測試邊界情況"""
        # 空JSON對象
        result = JSONParser.extract_json_from_content('```json\n{}\n```')
        self.assertEqual(result, {})
        
        # 只有一個值的JSON
        result = JSONParser.extract_json_from_content('```json\n{"key": "value"}\n```')
        self.assertEqual(result, {"key": "value"})
        
        # 數組形式的JSON（應該返回None，因為要求dict）
        result = JSONParser.extract_json_from_content('```json\n["item1", "item2"]\n```')
        self.assertIsNone(result)
        
        # 非常長的JSON字符串
        long_data = {"長字符串": "這是一個非常長的字符串，" * 100}
        content = f"```json\n{json.dumps(long_data, ensure_ascii=False)}\n```"
        result = JSONParser.extract_json_from_content(content)
        self.assertIsNotNone(result)
        self.assertIn("長字符串", result)


if __name__ == '__main__':
    unittest.main()