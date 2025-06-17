"""
小說寫作器的裝飾器工具
"""

import logging
import traceback
from typing import Callable

logger = logging.getLogger(__name__)


def safe_execute(func: Callable) -> Callable:
    """安全執行裝飾器"""
    def wrapper(self, *args, **kwargs):
        try:
            logger.info(f"開始執行函數：{func.__name__}")
            result = func(self, *args, **kwargs)
            logger.info(f"函數執行完成：{func.__name__}")
            return result
        except Exception as e:
            error_msg = f"執行 {func.__name__} 時發生錯誤: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            if hasattr(self, 'show_error'):
                self.show_error(error_msg)
            raise e
    return wrapper