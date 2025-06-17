"""
測試 services.text_formatter 模組
"""

import unittest
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from novel_writer.services.text_formatter import TextFormatter


class TestTextFormatter(unittest.TestCase):
    """測試文字格式化器"""
    
    def test_quote_conversion_to_traditional(self):
        """測試英文引號轉繁體中文引號"""
        text = '小明說："你好世界！"今天天氣很好。'
        result = TextFormatter.format_novel_content(text, use_traditional_quotes=True)
        expected = '小明說：「你好世界！」今天天氣很好。'
        self.assertEqual(result, expected)
    
    def test_quote_conversion_to_english(self):
        """測試繁體中文引號轉英文引號"""
        text = '小明說：「你好世界！」今天天氣很好。'
        result = TextFormatter.format_novel_content(text, use_traditional_quotes=False)
        expected = '小明說："你好世界！"今天天氣很好。'
        self.assertEqual(result, expected)
    
    def test_nested_quotes_traditional(self):
        """測試嵌套引號轉換（繁體）"""
        text = '他說："她告訴我\'明天見\'。"'
        result = TextFormatter.format_novel_content(text, use_traditional_quotes=True)
        # 外層應該是「」，內層是『』
        self.assertIn('「', result)
        self.assertIn('」', result)
        
    def test_paragraph_formatting(self):
        """測試段落格式化"""
        text = "這是第一句。這是第二句！這是第三句？接下來還有內容。"
        result = TextFormatter.format_novel_content(text)
        
        # 檢查是否在句號、驚嘆號、問號後添加了換行
        self.assertIn('。\n', result)
        self.assertIn('！\n', result) 
        self.assertIn('？\n', result)
    
    def test_dialogue_formatting_traditional(self):
        """測試對話格式化（繁體引號）"""
        text = '小明走過來。「你好！」他熱情地說道。「今天天氣真好。」'
        result = TextFormatter.format_novel_content(text, use_traditional_quotes=True)
        
        # 檢查對話前是否有換行
        lines = result.split('\n')
        dialogue_lines = [line for line in lines if '「' in line]
        self.assertTrue(len(dialogue_lines) > 0)
    
    def test_dialogue_formatting_english(self):
        """測試對話格式化（英文引號）"""
        text = '小明走過來。"你好！"他熱情地說道。"今天天氣真好。"'
        result = TextFormatter.format_novel_content(text, use_traditional_quotes=False)
        
        # 檢查對話格式
        self.assertIn('"', result)
        lines = result.split('\n')
        dialogue_lines = [line for line in lines if '"' in line]
        self.assertTrue(len(dialogue_lines) > 0)
    
    def test_punctuation_fixing(self):
        """測試標點符號修復"""
        text = "這是一個句子 這是另一個句子 還有更多內容"
        result = TextFormatter.format_novel_content(text)
        
        # 檢查是否添加了句號
        self.assertTrue(result.endswith('。'))
        
        # 檢查句子之間是否有適當的標點
        sentences = result.split('\n')
        for sentence in sentences[:-1]:  # 除了最後一句
            if sentence.strip():
                self.assertTrue(sentence.strip().endswith(('。', '！', '？', '：', '；')))
    
    def test_whitespace_cleanup(self):
        """測試空白字符清理"""
        text = "第一段。\n\n\n\n第二段。\n\n\n第三段。"
        result = TextFormatter.format_novel_content(text)
        
        # 檢查是否清理了多餘的空行
        self.assertNotIn('\n\n\n', result)
        
        # 但保留必要的段落分隔
        self.assertIn('\n', result)
    
    def test_empty_content(self):
        """測試空內容"""
        result = TextFormatter.format_novel_content("")
        self.assertEqual(result, "")
        
        result = TextFormatter.format_novel_content("   \n\n   ")
        self.assertEqual(result.strip(), "")
    
    def test_special_characters(self):
        """測試特殊字符處理"""
        text = "這裡有一些特殊字符：——、《》【】〖〗。"
        result = TextFormatter.format_novel_content(text)
        
        # 確保特殊字符被保留
        self.assertIn('——', result)
        self.assertIn('《', result)
        self.assertIn('》', result)
        self.assertIn('【', result)
        self.assertIn('】', result)
    
    def test_mixed_content(self):
        """測試混合內容格式化"""
        text = '''小明來到花園。"這裡真美啊！"他驚嘆道。
        
花園裡有各種花朵：玫瑰、百合、菊花。他想：「我要把這美景記住。」
        
突然，一隻蝴蝶飛過來。'''
        
        result = TextFormatter.format_novel_content(text, use_traditional_quotes=True)
        
        # 檢查引號轉換
        self.assertIn('「', result)
        self.assertIn('」', result)
        self.assertNotIn('"', result)
        
        # 檢查格式化
        self.assertTrue(len(result.strip()) > 0)
        
        # 檢查沒有過多的空行
        self.assertNotIn('\n\n\n\n', result)
    
    def test_complex_dialogue(self):
        """測試複雜對話格式化"""
        text = '''「你在做什麼？」她問道。「我在看書。」他回答。「什麼書？」「一本小說。」'''
        result = TextFormatter.format_novel_content(text, use_traditional_quotes=True)
        
        # 檢查對話格式是否正確
        self.assertIn('「', result)
        self.assertIn('」', result)
        
        # 檢查對話是否適當分行
        lines = result.split('\n')
        dialogue_count = sum(1 for line in lines if '「' in line)
        self.assertGreaterEqual(dialogue_count, 2)


if __name__ == '__main__':
    unittest.main()