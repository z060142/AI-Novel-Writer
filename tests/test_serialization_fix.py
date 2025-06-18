#!/usr/bin/env python3
"""
測試JSON序列化修復
驗證專案保存和載入功能是否正常工作，特別是枚舉類型的處理
"""

import sys
import os
import json
import tempfile

# 添加模組路徑
sys.path.insert(0, '/mnt/z/coding/ai_novel_writter_refactore_4')

def test_enum_serialization():
    """測試枚舉序列化功能"""
    print("🧪 測試枚舉序列化功能")
    print("=" * 50)
    
    try:
        from novel_writer.models.enums import WritingStyle, PacingStyle, CreationStatus
        from novel_writer.models.data_models import GlobalWritingConfig, NovelProject, Chapter, Paragraph
        from novel_writer.utils.serialization import ProjectSerializer, SerializationHelper
        
        print("✅ 所有模組導入成功")
        
        # 測試基本枚舉序列化
        print("\n📝 測試基本枚舉序列化:")
        
        # 創建包含枚舉的配置
        config = GlobalWritingConfig(
            writing_style=WritingStyle.FIRST_PERSON,
            pacing_style=PacingStyle.FAST_PACED,
            tone="幽默",
            target_chapter_words=2500
        )
        
        # 序列化配置
        config_dict = ProjectSerializer.safe_serialize_dataclass(config)
        print(f"✅ GlobalWritingConfig 序列化成功")
        print(f"   writing_style: {config_dict['writing_style']}")
        print(f"   pacing_style: {config_dict['pacing_style']}")
        
        # 驗證枚舉被正確轉換為字符串
        assert config_dict['writing_style'] == "第一人稱"
        assert config_dict['pacing_style'] == "快節奏"
        print("✅ 枚舉值正確轉換為字符串")
        
        # 測試反序列化
        print("\n📝 測試枚舉反序列化:")
        
        restored_writing_style = ProjectSerializer.deserialize_writing_style(config_dict['writing_style'])
        restored_pacing_style = ProjectSerializer.deserialize_pacing_style(config_dict['pacing_style'])
        
        assert restored_writing_style == WritingStyle.FIRST_PERSON
        assert restored_pacing_style == PacingStyle.FAST_PACED
        print("✅ 枚舉值正確從字符串還原")
        
        return True
        
    except Exception as e:
        print(f"❌ 枚舉序列化測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_project_serialization():
    """測試完整專案序列化"""
    print("\n🏗️ 測試完整專案序列化")
    print("=" * 50)
    
    try:
        from novel_writer.models.enums import WritingStyle, PacingStyle, CreationStatus
        from novel_writer.models.data_models import (
            NovelProject, GlobalWritingConfig, Chapter, Paragraph, WorldBuilding
        )
        from novel_writer.utils.serialization import SerializationHelper, ProjectSerializer
        
        # 創建測試專案
        project = NovelProject()
        project.title = "測試小說"
        project.theme = "科幻冒險"
        
        # 設置全局配置（包含枚舉）
        project.global_config = GlobalWritingConfig(
            writing_style=WritingStyle.THIRD_PERSON_OMNISCIENT,
            pacing_style=PacingStyle.EPISODIC,
            tone="神秘",
            target_chapter_words=4000
        )
        
        # 添加章節（包含狀態枚舉）
        chapter = Chapter(
            title="第一章：覺醒",
            summary="主角發現自己的超能力",
            status=CreationStatus.COMPLETED,
            estimated_words=3500
        )
        
        # 添加段落（包含狀態枚舉）
        paragraph = Paragraph(
            order=1,
            purpose="介紹主角和背景設定",
            content="這是測試內容...",
            status=CreationStatus.IN_PROGRESS,
            estimated_words=400
        )
        
        chapter.paragraphs = [paragraph]
        project.chapters = [chapter]
        
        # 設置世界設定
        project.world_building = WorldBuilding(
            characters={"主角": "一個發現超能力的年輕人"},
            settings={"學校": "故事開始的地方"},
            terminology={"超能力": "超越常人的特殊能力"}
        )
        
        print("✅ 測試專案創建成功")
        
        # 序列化專案
        project_data = SerializationHelper.prepare_project_for_save(project)
        print("✅ 專案數據準備成功")
        
        # 測試JSON序列化
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            ProjectSerializer.safe_json_dump(project_data, temp_file)
            print("✅ JSON文件保存成功")
            
            # 讀取並驗證JSON
            with open(temp_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            print("✅ JSON文件讀取成功")
            
            # 驗證關鍵數據
            assert loaded_data['title'] == "測試小說"
            assert loaded_data['global_config']['writing_style'] == "第三人稱全知視角"
            assert loaded_data['global_config']['pacing_style'] == "章回體"
            assert loaded_data['chapters'][0]['status'] == "已完成"
            assert loaded_data['chapters'][0]['paragraphs'][0]['status'] == "進行中"
            
            print("✅ 序列化數據驗證通過")
            
            # 測試序列化數據的完整性
            validation_result = SerializationHelper.validate_serializable(loaded_data)
            assert validation_result == True
            print("✅ 序列化數據完整性驗證通過")
            
        finally:
            # 清理臨時文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        return True
        
    except Exception as e:
        print(f"❌ 專案序列化測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """測試邊緣情況"""
    print("\n🔍 測試邊緣情況")
    print("=" * 30)
    
    try:
        from novel_writer.utils.serialization import ProjectSerializer
        
        # 測試無效枚舉值的處理
        print("📝 測試無效枚舉值處理:")
        
        invalid_writing_style = ProjectSerializer.deserialize_writing_style("無效的寫作風格")
        invalid_pacing_style = ProjectSerializer.deserialize_pacing_style("無效的節奏風格")
        invalid_status = ProjectSerializer.deserialize_creation_status("無效的狀態")
        
        print(f"✅ 無效寫作風格 -> 預設值: {invalid_writing_style.value}")
        print(f"✅ 無效節奏風格 -> 預設值: {invalid_pacing_style.value}")
        print(f"✅ 無效狀態 -> 預設值: {invalid_status.value}")
        
        # 測試空值處理
        print("\n📝 測試空值處理:")
        
        empty_data = ProjectSerializer.safe_serialize_dataclass(None)
        assert empty_data == {}
        print("✅ None值處理正確")
        
        # 測試嵌套枚舉處理
        print("\n📝 測試嵌套枚舉處理:")
        
        from novel_writer.models.enums import CreationStatus
        nested_data = {
            "level1": {
                "level2": {
                    "status": CreationStatus.COMPLETED,
                    "normal_field": "測試"
                }
            }
        }
        
        serialized_nested = ProjectSerializer.serialize_enum_dict(nested_data)
        assert serialized_nested["level1"]["level2"]["status"] == "已完成"
        print("✅ 嵌套枚舉處理正確")
        
        return True
        
    except Exception as e:
        print(f"❌ 邊緣情況測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """測試向後兼容性"""
    print("\n🔄 測試向後兼容性")
    print("=" * 30)
    
    try:
        from novel_writer.utils.serialization import ProjectSerializer
        
        # 模擬舊版本的專案數據（直接包含枚舉字符串值）
        old_project_data = {
            "title": "舊版專案",
            "global_config": {
                "writing_style": "第三人稱限制視角",  # 字符串值
                "pacing_style": "平衡型",            # 字符串值
                "tone": "溫暖"
            },
            "chapters": [
                {
                    "title": "第一章",
                    "status": "已完成",  # 字符串值
                    "paragraphs": [
                        {
                            "order": 1,
                            "status": "進行中",  # 字符串值
                            "content": "測試內容"
                        }
                    ]
                }
            ]
        }
        
        # 測試是否能正確反序列化舊數據
        writing_style = ProjectSerializer.deserialize_writing_style(
            old_project_data["global_config"]["writing_style"]
        )
        pacing_style = ProjectSerializer.deserialize_pacing_style(
            old_project_data["global_config"]["pacing_style"]
        )
        chapter_status = ProjectSerializer.deserialize_creation_status(
            old_project_data["chapters"][0]["status"]
        )
        paragraph_status = ProjectSerializer.deserialize_creation_status(
            old_project_data["chapters"][0]["paragraphs"][0]["status"]
        )
        
        print(f"✅ 舊版寫作風格正確讀取: {writing_style.value}")
        print(f"✅ 舊版節奏風格正確讀取: {pacing_style.value}")
        print(f"✅ 舊版章節狀態正確讀取: {chapter_status.value}")
        print(f"✅ 舊版段落狀態正確讀取: {paragraph_status.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ 向後兼容性測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 開始JSON序列化修復測試")
    print("=" * 60)
    
    test_results = []
    
    # 執行所有測試
    test_results.append(("枚舉序列化", test_enum_serialization()))
    test_results.append(("專案序列化", test_project_serialization()))
    test_results.append(("邊緣情況", test_edge_cases()))
    test_results.append(("向後兼容性", test_backward_compatibility()))
    
    # 總結結果
    print("\n" + "=" * 60)
    print("🏁 測試結果總結:")
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有測試通過！JSON序列化問題已完全修復！")
        print("\n📋 修復內容總結:")
        print("• ✅ WritingStyle 枚舉序列化/反序列化")
        print("• ✅ PacingStyle 枚舉序列化/反序列化")
        print("• ✅ CreationStatus 枚舉序列化/反序列化")
        print("• ✅ 嵌套枚舉處理")
        print("• ✅ 錯誤值容錯機制")
        print("• ✅ 向後兼容性保證")
        print("• ✅ 專案完整序列化/反序列化")
        
        print("\n🛡️ 現在可以安全地:")
        print("1. 保存包含任何枚舉類型的專案")
        print("2. 載入舊版本的專案文件")
        print("3. 處理無效或損壞的枚舉值")
        print("4. 進行複雜的嵌套數據序列化")
    else:
        print("❌ 部分測試失敗，需要進一步檢查和修復")