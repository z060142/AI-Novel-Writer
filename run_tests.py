#!/usr/bin/env python3
"""
測試執行器 - 執行所有測試並生成報告
"""

import unittest
import sys
import os
import time
from io import StringIO

def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("🧪 小說寫作器重構測試套件")
    print("=" * 60)
    
    # 添加專案根目錄到路徑
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # 發現並執行所有測試
    start_time = time.time()
    
    # 創建測試套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 測試模組列表
    test_modules = [
        'tests.models.test_enums',
        'tests.models.test_data_models', 
        'tests.models.test_exceptions',
        'tests.services.test_text_formatter',
        'tests.services.test_api_connector',
        'tests.services.test_llm_service',
        'tests.core.test_json_parser',
        'tests.core.test_prompt_builder',
        'tests.utils.test_decorators',
        'tests.test_integration'
    ]
    
    # 載入所有測試
    test_count = 0
    failed_modules = []
    
    for module_name in test_modules:
        try:
            module_suite = loader.loadTestsFromName(module_name)
            suite.addTest(module_suite)
            test_count += module_suite.countTestCases()
            print(f"✅ 載入測試模組: {module_name}")
        except Exception as e:
            print(f"❌ 載入測試模組失敗: {module_name} - {e}")
            failed_modules.append(module_name)
    
    print(f"\n📊 總共載入 {test_count} 個測試案例")
    
    if failed_modules:
        print(f"⚠️  {len(failed_modules)} 個模組載入失敗: {', '.join(failed_modules)}")
    
    print("\n" + "=" * 60)
    print("🚀 開始執行測試...")
    print("=" * 60)
    
    # 執行測試
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True
    )
    
    result = runner.run(suite)
    
    # 計算執行時間
    end_time = time.time()
    execution_time = end_time - start_time
    
    # 生成測試報告
    print("\n" + "=" * 60)
    print("📋 測試執行報告")
    print("=" * 60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    successful = total_tests - failures - errors - skipped
    
    print(f"總測試數量: {total_tests}")
    print(f"✅ 成功: {successful}")
    print(f"❌ 失敗: {failures}")
    print(f"🔥 錯誤: {errors}")
    print(f"⏭️  跳過: {skipped}")
    print(f"⏱️  執行時間: {execution_time:.2f} 秒")
    
    # 成功率
    if total_tests > 0:
        success_rate = (successful / total_tests) * 100
        print(f"📈 成功率: {success_rate:.1f}%")
    
    # 詳細錯誤報告
    if failures:
        print("\n❌ 失敗詳情:")
        for i, (test, trace) in enumerate(result.failures, 1):
            print(f"\n{i}. {test}")
            print("-" * 40)
            print(trace)
    
    if errors:
        print("\n🔥 錯誤詳情:")
        for i, (test, trace) in enumerate(result.errors, 1):
            print(f"\n{i}. {test}")
            print("-" * 40)
            print(trace)
    
    # 模組測試狀態總結
    print("\n" + "=" * 60)
    print("📦 模組測試狀態")
    print("=" * 60)
    
    module_status = {
        '🏗️  Models': ['test_enums', 'test_data_models', 'test_exceptions'],
        '⚙️  Services': ['test_text_formatter', 'test_api_connector', 'test_llm_service'],
        '🧠 Core': ['test_json_parser', 'test_prompt_builder'],
        '🛠️  Utils': ['test_decorators'],
        '🔗 Integration': ['test_integration']
    }
    
    for category, test_files in module_status.items():
        category_success = True
        for test_file in test_files:
            if any(test_file in failure[0].id() for failure in result.failures + result.errors):
                category_success = False
                break
        
        status = "✅" if category_success else "❌"
        print(f"{status} {category}")
    
    print("\n" + "=" * 60)
    
    # 最終結論
    if failures == 0 and errors == 0:
        print("🎉 所有測試通過！重構後的系統運行正常。")
        print("\n✨ 重構成果:")
        print("   • 模組化架構運作良好")
        print("   • 所有功能保持完整")
        print("   • 錯誤處理機制正常")
        print("   • 整合測試通過")
        return True
    else:
        print("⚠️  部分測試失敗，需要進一步檢查和修復。")
        return False


def run_specific_test(test_name):
    """執行特定測試"""
    print(f"🎯 執行特定測試: {test_name}")
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    """主函數"""
    if len(sys.argv) > 1:
        # 執行特定測試
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
    else:
        # 執行所有測試
        success = run_all_tests()
    
    # 根據測試結果設置退出代碼
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()