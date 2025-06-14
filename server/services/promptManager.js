const { TaskType } = require('../models/enums');

// Basic logger
const logger = {
    info: (msg) => console.log(\`[PromptManager INFO] \${msg}\`)
};

const TOKEN_LIMITS = {
    [TaskType.OUTLINE]: 8000,
    [TaskType.CHAPTERS]: 12000,
    [TaskType.CHAPTER_OUTLINE]: 6000,
    [TaskType.PARAGRAPHS]: 8000,
    [TaskType.WRITING]: 10000,
    [TaskType.WORLD_BUILDING]: 4000
};

const PromptManager = {
    createSystemPrompt: (taskType) => {
        logger.info(\`Creating system prompt for task type: \${taskType}\`);
        let basePrompt = "You are a professional novel writing assistant. Respond directly with the user's request in JSON format, enclosed in a ```json code block.\n\nIMPORTANT REQUIREMENTS:\n1. Output JSON directly, no extra explanations.\n2. Ensure JSON is correct and complete.\n3. Content should be practical and meet requirements.\n\n";

        const taskPrompts = {
            [TaskType.OUTLINE]: \`Structure Requirements:\n- Word count: 3000-8000 words\nJSON Format:\n{\n    "title": "Novel Title",\n    "summary": "Story Summary",\n    "themes": ["Theme1", "Theme2"],\n    "estimated_chapters": 10,\n    "main_characters": [{"name": "Character Name", "desc": "Character Description"}],\n    "world_setting": "World Setting Description",\n    "story_flow": "Complete story arc - how it starts, evolves, key turning points, and the ending.",\n    "key_moments": ["Key Plot Point 1", "Key Plot Point 2"],\n    "character_arcs": "Growth and change of main characters.",\n    "story_atmosphere": "Overall emotional tone and atmosphere.",\n    "central_conflicts": ["Core Conflict 1"],\n    "story_layers": "Multiple layers of the story - surface plot and deeper meanings."\n}\`,
            [TaskType.CHAPTERS]: \`Structure Requirements:\n- Word count: 2500-6000 words\nJSON Format:\n{\n    "chapters": [\n        {\n            "number": 1,\n            "title": "Chapter Title",\n            "summary": "Chapter summary (max 50 words)",\n            "estimated_words": 3000\n        }\n    ]\n}\`,
            [TaskType.CHAPTER_OUTLINE]: \`Structure Requirements:\n- Word count: 2500-6000 words\nJSON Format:\n{\n    "outline": {\n        "story_spark": "The soul spark of this chapter - what ignites this part of the story?",\n        "rhythm_flow": "Plot rhythm and flow - how the story breathes, accelerates, slows down?",\n        "turning_moments": "Key turning points - what moments change everything?",\n        "emotional_core": "Emotional core - what feeling will run through the chapter?",\n        "story_elements": "Active elements - how will important characters, objects, places participate?",\n        "estimated_paragraphs": 8\n    }\n}\`,
            [TaskType.PARAGRAPHS]: \`JSON Format:\n{\n    "paragraphs": [\n        {\n            "number": 1,\n            "purpose": "Full description of paragraph's purpose and content direction",\n            "estimated_words": 400\n        }\n    ]\n}\`,
            [TaskType.WRITING]: \`JSON Format:\n{\n    "content": "Complete paragraph content",\n    "word_count": 0\n}\`, // Word count will be calculated after generation
            [TaskType.WORLD_BUILDING]: \`JSON Format:\n{\n    "new_characters": [{"name": "Character Name", "desc": "Brief description"}],\n    "new_settings": [{"name": "Location Name", "desc": "Brief description"}],\n    "new_terms": [{"term": "Term", "def": "Brief definition"}],\n    "plot_points": ["Important plot point"]\n}\`
        };

        return basePrompt + (taskPrompts[taskType] || "");
    },

    getTokenLimit: (taskType) => {
        return TOKEN_LIMITS[taskType] || 8000;
    }
};

module.exports = PromptManager;
