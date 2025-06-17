#!/usr/bin/env python3
"""
階層式小說編寫器 - 重構版入口點
採用模組化架構，將原本單一檔案拆分為多個模組
"""

import tkinter as tk
import logging

from novel_writer.ui import NovelWriterGUI

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """主函數"""
    try:
        logger.info("啟動階層式小說編寫器 v3.0 (重構版)")
        root = tk.Tk()
        app = NovelWriterGUI(root)
        root.mainloop()
        logger.info("應用程式正常關閉")
    except Exception as e:
        logger.error(f"應用程式啟動失敗: {str(e)}")
        raise


if __name__ == "__main__":
    main()