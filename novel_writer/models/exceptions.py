"""
小說寫作器的例外類型定義
"""


class APIException(Exception):
    """API相關例外"""
    pass


class JSONParseException(Exception):
    """JSON解析例外"""
    pass