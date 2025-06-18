"""
序列化工具模組
處理專案數據的JSON序列化和反序列化，特別是枚舉類型的轉換
"""

import json
from dataclasses import asdict
from enum import Enum
from typing import Any, Dict, List, Union
from ..models.enums import WritingStyle, PacingStyle, CreationStatus, TaskType


class EnumEncoder(json.JSONEncoder):
    """支持枚舉序列化的JSON編碼器"""
    
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class ProjectSerializer:
    """專案序列化工具類"""
    
    @staticmethod
    def serialize_enum_dict(data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """將字典中的枚舉對象轉換為字符串值"""
        result = {}
        for key, value in data_dict.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, dict):
                result[key] = ProjectSerializer.serialize_enum_dict(value)
            elif isinstance(value, list):
                result[key] = ProjectSerializer.serialize_enum_list(value)
            else:
                result[key] = value
        return result
    
    @staticmethod
    def serialize_enum_list(data_list: List[Any]) -> List[Any]:
        """將列表中的枚舉對象轉換為字符串值"""
        result = []
        for item in data_list:
            if isinstance(item, Enum):
                result.append(item.value)
            elif isinstance(item, dict):
                result.append(ProjectSerializer.serialize_enum_dict(item))
            elif isinstance(item, list):
                result.append(ProjectSerializer.serialize_enum_list(item))
            else:
                result.append(item)
        return result
    
    @staticmethod
    def deserialize_writing_style(value: str) -> WritingStyle:
        """反序列化WritingStyle枚舉"""
        for style in WritingStyle:
            if style.value == value:
                return style
        return WritingStyle.THIRD_PERSON_LIMITED  # 預設值
    
    @staticmethod
    def deserialize_pacing_style(value: str) -> PacingStyle:
        """反序列化PacingStyle枚舉"""
        for style in PacingStyle:
            if style.value == value:
                return style
        return PacingStyle.BALANCED  # 預設值
    
    @staticmethod
    def deserialize_creation_status(value: str) -> CreationStatus:
        """反序列化CreationStatus枚舉"""
        for status in CreationStatus:
            if status.value == value:
                return status
        return CreationStatus.NOT_STARTED  # 預設值
    
    @staticmethod
    def deserialize_task_type(value: str) -> TaskType:
        """反序列化TaskType枚舉"""
        for task_type in TaskType:
            if task_type.value == value:
                return task_type
        return TaskType.WRITING  # 預設值
    
    @staticmethod
    def safe_serialize_dataclass(obj: Any) -> Dict[str, Any]:
        """安全地序列化dataclass，處理所有枚舉類型"""
        if obj is None:
            return {}
        
        # 使用asdict轉換為字典
        data_dict = asdict(obj)
        
        # 遞歸處理所有枚舉
        return ProjectSerializer.serialize_enum_dict(data_dict)
    
    @staticmethod
    def safe_json_dump(data: Any, file_path: str, **kwargs) -> None:
        """安全地進行JSON序列化，支持枚舉類型"""
        default_kwargs = {
            'ensure_ascii': False,
            'indent': 2,
            'cls': EnumEncoder
        }
        default_kwargs.update(kwargs)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, **default_kwargs)
    
    @staticmethod
    def safe_json_dumps(data: Any, **kwargs) -> str:
        """安全地進行JSON字符串序列化，支持枚舉類型"""
        default_kwargs = {
            'ensure_ascii': False,
            'indent': 2,
            'cls': EnumEncoder
        }
        default_kwargs.update(kwargs)
        
        return json.dumps(data, **default_kwargs)


class SerializationHelper:
    """序列化輔助工具"""
    
    @staticmethod
    def prepare_project_for_save(project) -> Dict[str, Any]:
        """準備專案數據用於保存"""
        from ..models.data_models import Chapter, Paragraph
        
        # 處理章節數據
        chapters_data = []
        for chapter in project.chapters:
            chapter_dict = ProjectSerializer.safe_serialize_dataclass(chapter)
            chapters_data.append(chapter_dict)
        
        # 處理全局配置
        global_config_dict = ProjectSerializer.safe_serialize_dataclass(
            getattr(project, 'global_config', None)
        )
        
        # 處理世界設定
        world_building_dict = ProjectSerializer.safe_serialize_dataclass(
            project.world_building
        )
        
        project_data = {
            "title": project.title,
            "theme": project.theme,
            "outline": project.outline,
            "outline_additional_prompt": getattr(project, 'outline_additional_prompt', ''),
            "chapters_additional_prompt": getattr(project, 'chapters_additional_prompt', ''),
            "current_context": getattr(project, 'current_context', ''),
            "chapters": chapters_data,
            "world_building": world_building_dict,
            "global_config": global_config_dict
        }
        
        return project_data
    
    @staticmethod
    def validate_serializable(data: Any) -> bool:
        """驗證數據是否可以序列化"""
        try:
            ProjectSerializer.safe_json_dumps(data)
            return True
        except Exception:
            return False