"""
文本格式化服務模組
負責小說內容的格式化處理，包括引號、段落、對話和標點符號的統一處理。
"""

import re
from typing import Optional


class TextFormatter:
    """文本格式化器"""
    
    @staticmethod
    def format_novel_content(content: str, use_traditional_quotes: bool = True) -> str:
        """格式化小說內容"""
        if not content:
            return content
        
        # 統一引號
        if use_traditional_quotes:
            # 將所有英文引號轉換為中文引號
            content = re.sub(r'"([^"]*)"', r'「\1」', content)
            content = re.sub(r'"([^"]*)"', r'「\1」', content)
            content = re.sub(r'"([^"]*)"', r'「\1」', content)
        else:
            # 將所有中文引號轉換為英文引號
            content = re.sub(r'「([^」]*)」', r'"\1"', content)
        
        # 處理段落分行
        content = TextFormatter._format_paragraphs(content)
        
        # 處理對話格式
        content = TextFormatter._format_dialogue(content, use_traditional_quotes)
        
        # 清理多餘的空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 確保句子結尾有適當的標點
        content = TextFormatter._fix_punctuation(content)
        
        return content.strip()
    
    @staticmethod
    def _format_paragraphs(content: str) -> str:
        """格式化段落分行"""
        # 在句號、感嘆號、問號後添加換行（如果後面不是換行的話）
        content = re.sub(r'([。！？])([^」\n])', r'\1\n\n\2', content)
        
        # 在引號結束後如果有句號等，也要換行
        content = re.sub(r'([」])([。！？])([^」\n])', r'\1\2\n\n\3', content)
        
        # 處理對話後的描述
        content = re.sub(r'([」])([^。！？\n][^」]*?[。！？])', r'\1\n\n\2', content)
        
        return content
    
    @staticmethod
    def _format_dialogue(content: str, use_traditional_quotes: bool) -> str:
        """格式化對話"""
        if use_traditional_quotes:
            # 確保對話前有適當的分行
            content = re.sub(r'([。！？])(\s*)([^」\n]*?)「', r'\1\n\n\3「', content)
        else:
            # 確保對話前有適當的分行
            content = re.sub(r'([。！？])(\s*)([^"\n]*?)"', r'\1\n\n\3"', content)
        
        return content
    
    @staticmethod
    def _fix_punctuation(content: str) -> str:
        """修復標點符號"""
        # 確保句子結尾有標點
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not re.search(r'[。！？」"]$', line):
                # 如果行末沒有標點，添加句號
                if re.search(r'[a-zA-Z0-9\u4e00-\u9fff]$', line):
                    line += '。'
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)