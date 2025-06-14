const TaskType = {
    OUTLINE: "outline",
    CHAPTERS: "chapters",
    CHAPTER_OUTLINE: "chapter_outline",
    PARAGRAPHS: "paragraphs",
    WRITING: "writing",
    WORLD_BUILDING: "world_building"
};

const CreationStatus = {
    NOT_STARTED: "未開始",
    IN_PROGRESS: "進行中",
    COMPLETED: "已完成",
    ERROR: "錯誤"
};

const WritingStyle = {
    FIRST_PERSON: "第一人稱",
    THIRD_PERSON_LIMITED: "第三人稱限制視角",
    THIRD_PERSON_OMNISCIENT: "第三人稱全知視角",
    MULTIPLE_POV: "多重視角"
};

const PacingStyle = {
    SLOW_BURN: "慢熱型",
    FAST_PACED: "快節奏",
    BALANCED: "平衡型",
    EPISODIC: "章回體"
};

module.exports = {
    TaskType,
    CreationStatus,
    WritingStyle,
    PacingStyle
};
