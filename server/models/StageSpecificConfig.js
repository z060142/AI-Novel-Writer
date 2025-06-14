class StageSpecificConfig {
    constructor({
        additional_prompt = "",
        creativity_level = 0.7, // 0-1
        detail_level = "適中", // "簡潔", "適中", "詳細"
        focus_aspects = [],
        word_count_strict = false,
        length_preference = "auto" // "short", "medium", "long", "auto"
    } = {}) {
        this.additional_prompt = additional_prompt;
        this.creativity_level = creativity_level;
        this.detail_level = detail_level;
        this.focus_aspects = focus_aspects || [];
        this.word_count_strict = word_count_strict;
        this.length_preference = length_preference;
    }
}

module.exports = StageSpecificConfig;
