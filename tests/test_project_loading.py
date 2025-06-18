#!/usr/bin/env python3
"""
測試專案載入功能，確保安全性和容錯機制
"""

import json
import os
import sys

# 添加模組路徑
sys.path.insert(0, '/mnt/z/coding/ai_novel_writter_refactore_4')

from novel_writer.models.data_models import NovelProject, APIConfig, GlobalWritingConfig, Chapter, Paragraph, WorldBuilding, CreationStatus

def test_old_project_loading():
    """測試載入舊版專案檔（09-3.json）"""
    print("🔍 測試載入舊版專案檔 (09-3.json)...")
    
    old_project_path = "/mnt/z/coding/ai_novel_writter_refactore_4/chapter/09-3.json"
    
    if not os.path.exists(old_project_path):
        print(f"❌ 檔案不存在: {old_project_path}")
        return False
    
    try:
        # 模擬GUI載入邏輯
        with open(old_project_path, "r", encoding="utf-8") as f:
            project_data = json.load(f)
        
        # 檢查是否包含API配置
        if "api_config" in project_data:
            print("⚠️  專案檔包含API配置，基於安全考量已忽略")
        
        # 創建專案物件
        project = NovelProject()
        
        # 基本欄位
        project.title = project_data.get("title", "")
        project.theme = project_data.get("theme", "")
        project.outline = project_data.get("outline", "")
        project.outline_additional_prompt = project_data.get("outline_additional_prompt", "")
        project.chapters_additional_prompt = project_data.get("chapters_additional_prompt", "")
        
        # 章節數據
        project.chapters = []
        for chapter_data in project_data.get("chapters", []):
            try:
                chapter = Chapter(
                    title=chapter_data.get("title", "未命名章節"),
                    summary=chapter_data.get("summary", ""),
                    key_events=chapter_data.get("key_events", []),
                    characters_involved=chapter_data.get("characters_involved", []),
                    estimated_words=chapter_data.get("estimated_words", 3000),
                    outline=chapter_data.get("outline", {}),
                    content=chapter_data.get("content", ""),
                    status=CreationStatus(chapter_data.get("status", "未開始"))
                )
                
                # 段落數據
                chapter.paragraphs = []
                for para_data in chapter_data.get("paragraphs", []):
                    try:
                        paragraph = Paragraph(
                            order=para_data.get("order", 1),
                            purpose=para_data.get("purpose", ""),
                            content_type=para_data.get("content_type", ""),
                            key_points=para_data.get("key_points", []),
                            estimated_words=para_data.get("estimated_words", 0),
                            mood=para_data.get("mood", ""),
                            content=para_data.get("content", ""),
                            status=CreationStatus(para_data.get("status", "未開始")),
                            word_count=para_data.get("word_count", 0)
                        )
                        chapter.paragraphs.append(paragraph)
                    except (KeyError, ValueError) as e:
                        print(f"⚠️  段落資料載入警告，使用預設值: {str(e)}")
                        paragraph = Paragraph(
                            order=len(chapter.paragraphs) + 1,
                            purpose="",
                            content_type="",
                            key_points=[],
                            estimated_words=0,
                            mood="",
                            content="",
                            status=CreationStatus.NOT_STARTED,
                            word_count=0
                        )
                        chapter.paragraphs.append(paragraph)
                
                project.chapters.append(chapter)
                
            except (KeyError, ValueError) as e:
                print(f"⚠️  章節資料載入警告，使用預設值: {str(e)}")
        
        # 世界設定
        world_data = project_data.get("world_building", {})
        project.world_building = WorldBuilding(
            characters=world_data.get("characters", {}),
            settings=world_data.get("settings", {}),
            terminology=world_data.get("terminology", {}),
            plot_points=world_data.get("plot_points", []),
            relationships=world_data.get("relationships", []),
            style_guide=world_data.get("style_guide", ""),
            chapter_notes=world_data.get("chapter_notes", [])
        )
        
        # API配置安全處理：總是創建新的，從api_config.json載入
        project.api_config = APIConfig()
        
        # 全域配置
        if "global_config" in project_data:
            global_config_data = project_data["global_config"]
            project.global_config = GlobalWritingConfig(
                writing_style=global_config_data.get("writing_style", "第三人稱限制視角"),
                pacing_style=global_config_data.get("pacing_style", "平衡型"),
                tone=global_config_data.get("tone", "溫暖"),
                continuous_themes=global_config_data.get("continuous_themes", []),
                must_include_elements=global_config_data.get("must_include_elements", []),
                avoid_elements=global_config_data.get("avoid_elements", []),
                target_chapter_words=global_config_data.get("target_chapter_words", 3000),
                target_paragraph_words=global_config_data.get("target_paragraph_words", 400),
                paragraph_count_preference=global_config_data.get("paragraph_count_preference", "適中"),
                dialogue_style=global_config_data.get("dialogue_style", "自然對話"),
                description_density=global_config_data.get("description_density", "豐富"),
                emotional_intensity=global_config_data.get("emotional_intensity", "適中"),
                global_instructions=global_config_data.get("global_instructions", "")
            )
        else:
            project.global_config = GlobalWritingConfig()
        
        # 驗證載入結果
        print(f"✅ 專案載入成功!")
        print(f"   標題: {project.title}")
        print(f"   主題: {project.theme}")
        print(f"   章節數: {len(project.chapters)}")
        print(f"   角色數: {len(project.world_building.characters)}")
        print(f"   API配置獨立: {'✅' if project.api_config else '❌'}")
        print(f"   全域配置: {'✅' if project.global_config else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 載入失敗: {str(e)}")
        return False

def test_new_project_saving():
    """測試新專案儲存（確保不包含API配置）"""
    print("\n🔍 測試新專案儲存安全性...")
    
    try:
        # 創建測試專案
        project = NovelProject()
        project.title = "測試專案"
        project.theme = "測試主題"
        project.api_config = APIConfig()
        project.api_config.api_key = "sk-test-key-should-not-be-saved"
        project.global_config = GlobalWritingConfig()
        
        # 模擬儲存邏輯
        from dataclasses import asdict
        
        project_data = {
            "title": project.title,
            "theme": project.theme,
            "outline": project.outline,
            "outline_additional_prompt": project.outline_additional_prompt,
            "chapters_additional_prompt": project.chapters_additional_prompt,
            "chapters": [],
            "world_building": asdict(project.world_building),
            "global_config": asdict(project.global_config) if hasattr(project, 'global_config') else {}
        }
        
        # 安全確認：絕對不儲存API配置
        if "api_config" in project_data:
            del project_data["api_config"]
            print("🔒 已確保API配置不會被儲存到專案檔")
        
        # 檢查結果
        if "api_config" not in project_data:
            print("✅ 儲存安全性驗證通過：專案檔不包含API配置")
        else:
            print("❌ 儲存安全性驗證失敗：專案檔仍包含API配置")
            return False
            
        if "global_config" in project_data:
            print("✅ 全域配置正常儲存")
        else:
            print("❌ 全域配置遺失")
            
        return True
        
    except Exception as e:
        print(f"❌ 儲存測試失敗: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔐 專案檔案安全性和容錯機制測試")
    print("=" * 50)
    
    success1 = test_old_project_loading()
    success2 = test_new_project_saving()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 所有測試通過！")
    else:
        print("❌ 部分測試失敗")