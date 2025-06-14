const { WritingStyle, PacingStyle } = require('./enums');

class GlobalWritingConfig {
    constructor({
        writing_style = WritingStyle.THIRD_PERSON_LIMITED,
        pacing_style = PacingStyle.BALANCED,
        tone = "溫暖",
        continuous_themes = [],
        must_include_elements = [],
        avoid_elements = [],
        target_chapter_words = 3000,
        target_paragraph_words = 300,
        paragraph_count_preference = "適中", // "簡潔", "適中", "詳細"
        dialogue_style = "自然對話",
        description_density = "適中", // "簡潔", "適中", "豐富"
        emotional_intensity = "適中", // "克制", "適中", "濃烈"
        global_instructions = ""
    } = {}) {
        this.writing_style = writing_style;
        this.pacing_style = pacing_style;
        this.tone = tone;
        this.continuous_themes = continuous_themes || [];
        this.must_include_elements = must_include_elements || [];
        this.avoid_elements = avoid_elements || [];
        this.target_chapter_words = target_chapter_words;
        this.target_paragraph_words = target_paragraph_words;
        this.paragraph_count_preference = paragraph_count_preference;
        this.dialogue_style = dialogue_style;
        this.description_density = description_density;
        this.emotional_intensity = emotional_intensity;
        this.global_instructions = global_instructions;
    }
}

module.exports = GlobalWritingConfig;
