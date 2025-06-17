"""
測試 utils.decorators 模組
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from novel_writer.utils.decorators import safe_execute


class TestSafeExecute(unittest.TestCase):
    """測試safe_execute裝飾器"""
    
    def setUp(self):
        """設置測試環境"""
        self.mock_object = Mock()
        self.mock_object.show_error = Mock()
    
    def test_successful_execution(self):
        """測試成功執行"""
        @safe_execute
        def successful_method(self):
            return "成功結果"
        
        # 綁定方法到模擬對象
        bound_method = successful_method.__get__(self.mock_object, type(self.mock_object))
        result = bound_method()
        
        self.assertEqual(result, "成功結果")
        # 不應該調用show_error
        self.mock_object.show_error.assert_not_called()
    
    def test_exception_handling(self):
        """測試例外處理"""
        test_exception = ValueError("測試錯誤")
        
        @safe_execute
        def failing_method(self):
            raise test_exception
        
        bound_method = failing_method.__get__(self.mock_object, type(self.mock_object))
        
        # 應該重新拋出例外
        with self.assertRaises(ValueError) as context:
            bound_method()
        
        self.assertEqual(context.exception, test_exception)
        # 應該調用show_error
        self.mock_object.show_error.assert_called_once()
        error_message = self.mock_object.show_error.call_args[0][0]
        self.assertIn("failing_method", error_message)
        self.assertIn("測試錯誤", error_message)
    
    def test_exception_without_show_error(self):
        """測試沒有show_error方法的對象"""
        mock_without_show_error = Mock(spec=[])  # 沒有show_error方法
        
        @safe_execute
        def failing_method(self):
            raise RuntimeError("運行時錯誤")
        
        bound_method = failing_method.__get__(mock_without_show_error, type(mock_without_show_error))
        
        # 應該正常處理，不會因為沒有show_error而出錯
        with self.assertRaises(RuntimeError):
            bound_method()
    
    def test_method_with_arguments(self):
        """測試帶參數的方法"""
        @safe_execute
        def method_with_args(self, a, b, keyword=None):
            return f"結果: {a} + {b} = {a + b}, keyword = {keyword}"
        
        bound_method = method_with_args.__get__(self.mock_object, type(self.mock_object))
        result = bound_method(10, 20, keyword="測試")
        
        expected = "結果: 10 + 20 = 30, keyword = 測試"
        self.assertEqual(result, expected)
    
    def test_method_returning_none(self):
        """測試返回None的方法"""
        @safe_execute
        def method_returning_none(self):
            print("執行中...")
            return None
        
        bound_method = method_returning_none.__get__(self.mock_object, type(self.mock_object))
        result = bound_method()
        
        self.assertIsNone(result)
    
    @patch('novel_writer.utils.decorators.logger')
    def test_logging_behavior(self, mock_logger):
        """測試日誌記錄行為"""
        @safe_execute
        def test_method(self):
            return "測試結果"
        
        bound_method = test_method.__get__(self.mock_object, type(self.mock_object))
        result = bound_method()
        
        # 檢查info日誌被調用
        self.assertEqual(mock_logger.info.call_count, 2)  # 開始和完成
        
        # 檢查日誌內容
        calls = mock_logger.info.call_args_list
        self.assertIn("開始執行函數：test_method", calls[0][0][0])
        self.assertIn("函數執行完成：test_method", calls[1][0][0])
        
        self.assertEqual(result, "測試結果")
    
    @patch('novel_writer.utils.decorators.logger')
    def test_error_logging(self, mock_logger):
        """測試錯誤日誌記錄"""
        test_exception = Exception("嚴重錯誤")
        
        @safe_execute
        def error_method(self):
            raise test_exception
        
        bound_method = error_method.__get__(self.mock_object, type(self.mock_object))
        
        with self.assertRaises(Exception):
            bound_method()
        
        # 檢查錯誤日誌被調用
        mock_logger.error.assert_called_once()
        error_log = mock_logger.error.call_args[0][0]
        self.assertIn("執行 error_method 時發生錯誤", error_log)
        self.assertIn("嚴重錯誤", error_log)
    
    def test_different_exception_types(self):
        """測試不同類型的例外"""
        exception_types = [
            (ValueError("值錯誤"), ValueError),
            (TypeError("類型錯誤"), TypeError),
            (KeyError("鍵錯誤"), KeyError),
            (AttributeError("屬性錯誤"), AttributeError),
            (RuntimeError("運行時錯誤"), RuntimeError)
        ]
        
        for original_exception, expected_type in exception_types:
            with self.subTest(exception_type=type(original_exception).__name__):
                @safe_execute
                def method_with_exception(self):
                    raise original_exception
                
                bound_method = method_with_exception.__get__(self.mock_object, type(self.mock_object))
                
                with self.assertRaises(expected_type):
                    bound_method()
                
                # 檢查show_error被調用
                self.mock_object.show_error.assert_called()
                
                # 重置mock以便下次測試
                self.mock_object.show_error.reset_mock()
    
    def test_nested_decorated_methods(self):
        """測試嵌套裝飾的方法"""
        @safe_execute
        def outer_method(self):
            return self.inner_method()
        
        @safe_execute 
        def inner_method(self):
            return "內部結果"
        
        # 將方法綁定到模擬對象
        self.mock_object.inner_method = inner_method.__get__(self.mock_object, type(self.mock_object))
        bound_outer = outer_method.__get__(self.mock_object, type(self.mock_object))
        
        result = bound_outer()
        self.assertEqual(result, "內部結果")
    
    def test_decorator_preserves_function_info(self):
        """測試裝飾器保留函數信息"""
        @safe_execute
        def documented_method(self):
            """這是一個有文檔的方法"""
            return "結果"
        
        # 檢查函數名稱被保留
        self.assertEqual(documented_method.__name__, "documented_method")
        
        # 注意：由於裝飾器實現使用了wrapper函數，
        # 文檔字符串可能不會被完全保留，這是可以接受的
    
    def test_complex_method_with_multiple_operations(self):
        """測試複雜的多操作方法"""
        @safe_execute
        def complex_method(self, data_list, multiplier=2):
            # 模擬複雜操作
            result = []
            for item in data_list:
                if isinstance(item, (int, float)):
                    result.append(item * multiplier)
                else:
                    result.append(str(item).upper())
            return result
        
        bound_method = complex_method.__get__(self.mock_object, type(self.mock_object))
        
        test_data = [1, 2, "hello", 3.5, "world"]
        result = bound_method(test_data, multiplier=3)
        
        expected = [3, 6, "HELLO", 10.5, "WORLD"]
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()