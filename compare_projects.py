#!/usr/bin/env python3
"""
比較舊版專案檔和新版專案檔的差異
回答用戶問題：「有沒有舊專案有，新專案沒有的東西?」
"""

import json
import os

def compare_project_structures():
    """比較專案結構差異"""
    print("🔍 比較舊版專案檔 (09-3.json) 與新版專案檔 (113.json) 的結構差異")
    print("=" * 70)
    
    old_project_path = "/mnt/z/coding/ai_novel_writter_refactore_4/chapter/09-3.json"
    new_project_path = "/mnt/z/coding/ai_novel_writter_refactore_4/chapter/113.json"
    
    if not os.path.exists(old_project_path):
        print(f"❌ 舊版專案檔不存在: {old_project_path}")
        return
        
    if not os.path.exists(new_project_path):
        print(f"❌ 新版專案檔不存在: {new_project_path}")
        return
    
    try:
        # 載入兩個專案檔
        with open(old_project_path, "r", encoding="utf-8") as f:
            old_project = json.load(f)
        
        with open(new_project_path, "r", encoding="utf-8") as f:
            new_project = json.load(f)
        
        # 獲取所有鍵
        old_keys = set(old_project.keys())
        new_keys = set(new_project.keys())
        
        # 比較頂層結構
        print("📋 頂層欄位比較:")
        print(f"   舊版專案欄位: {sorted(old_keys)}")
        print(f"   新版專案欄位: {sorted(new_keys)}")
        
        # 舊專案有但新專案沒有的
        old_only = old_keys - new_keys
        if old_only:
            print(f"\n❗ 舊專案有但新專案沒有的欄位: {sorted(old_only)}")
        else:
            print(f"\n✅ 舊專案沒有獨有的頂層欄位")
        
        # 新專案有但舊專案沒有的
        new_only = new_keys - old_keys
        if new_only:
            print(f"   新專案有但舊專案沒有的欄位: {sorted(new_only)}")
        else:
            print(f"   新專案沒有新增的頂層欄位")
        
        # 共同欄位
        common_keys = old_keys & new_keys
        print(f"   共同欄位: {sorted(common_keys)}")
        
        # 詳細分析主要差異
        print("\n🔍 詳細差異分析:")
        
        # 分析章節結構
        if "chapters" in old_project and "chapters" in new_project:
            old_chapters = old_project["chapters"]
            new_chapters = new_project["chapters"]
            
            print(f"   章節數量: 舊版 {len(old_chapters)} vs 新版 {len(new_chapters)}")
            
            if old_chapters and new_chapters:
                # 比較章節結構
                old_chapter_keys = set(old_chapters[0].keys()) if old_chapters else set()
                new_chapter_keys = set(new_chapters[0].keys()) if new_chapters else set()
                
                chapter_old_only = old_chapter_keys - new_chapter_keys
                chapter_new_only = new_chapter_keys - old_chapter_keys
                
                if chapter_old_only:
                    print(f"   章節結構 - 舊版獨有: {sorted(chapter_old_only)}")
                if chapter_new_only:
                    print(f"   章節結構 - 新版新增: {sorted(chapter_new_only)}")
                
                # 比較段落結構
                old_paragraphs = old_chapters[0].get("paragraphs", [])
                new_paragraphs = new_chapters[0].get("paragraphs", [])
                
                if old_paragraphs and new_paragraphs:
                    old_para_keys = set(old_paragraphs[0].keys()) if old_paragraphs else set()
                    new_para_keys = set(new_paragraphs[0].keys()) if new_paragraphs else set()
                    
                    para_old_only = old_para_keys - new_para_keys
                    para_new_only = new_para_keys - old_para_keys
                    
                    if para_old_only:
                        print(f"   段落結構 - 舊版獨有: {sorted(para_old_only)}")
                    if para_new_only:
                        print(f"   段落結構 - 新版新增: {sorted(para_new_only)}")
        
        # 分析世界設定結構
        if "world_building" in old_project and "world_building" in new_project:
            old_world = old_project["world_building"]
            new_world = new_project["world_building"]
            
            old_world_keys = set(old_world.keys()) if old_world else set()
            new_world_keys = set(new_world.keys()) if new_world else set()
            
            world_old_only = old_world_keys - new_world_keys
            world_new_only = new_world_keys - old_world_keys
            
            if world_old_only:
                print(f"   世界設定 - 舊版獨有: {sorted(world_old_only)}")
            if world_new_only:
                print(f"   世界設定 - 新版新增: {sorted(world_new_only)}")
        
        # 特別檢查API配置
        print(f"\n🔒 安全性分析:")
        if "api_config" in old_project:
            print(f"   ❌ 舊版專案包含API配置（安全風險）")
            if "api_key" in old_project["api_config"]:
                api_key = old_project["api_config"]["api_key"]
                if api_key:
                    print(f"   ⚠️  舊版專案包含API密鑰: {api_key[:10]}...")
                else:
                    print(f"   ✅ 舊版專案API密鑰為空")
        else:
            print(f"   ✅ 舊版專案沒有API配置")
            
        if "api_config" in new_project:
            print(f"   ❌ 新版專案包含API配置（不應該出現）")
        else:
            print(f"   ✅ 新版專案正確地不包含API配置")
        
        # 內容比較
        print(f"\n📚 內容分析:")
        print(f"   舊版標題: {old_project.get('title', 'N/A')}")
        print(f"   新版標題: {new_project.get('title', 'N/A')}")
        
        # 世界設定內容量比較
        if "world_building" in old_project and "world_building" in new_project:
            old_chars = len(old_project["world_building"].get("characters", {}))
            new_chars = len(new_project["world_building"].get("characters", {}))
            old_settings = len(old_project["world_building"].get("settings", {}))
            new_settings = len(new_project["world_building"].get("settings", {}))
            
            print(f"   角色數量: 舊版 {old_chars} vs 新版 {new_chars}")
            print(f"   場景數量: 舊版 {old_settings} vs 新版 {new_settings}")
        
        print(f"\n✅ 比較完成！")
        
    except Exception as e:
        print(f"❌ 比較失敗: {str(e)}")

if __name__ == "__main__":
    compare_project_structures()