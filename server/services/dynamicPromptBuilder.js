const GlobalWritingConfig = require('../models/GlobalWritingConfig'); // Assuming path
const StageSpecificConfig = require('../models/StageSpecificConfig'); // Assuming path
const { WritingStyle, PacingStyle } = require('../models/enums'); // Assuming path

// Basic logger
const logger = {
    info: (msg) => console.log(\`[DynamicPromptBuilder INFO] \${msg}\`)
};

class DynamicPromptBuilder {
    constructor(globalConfig) {
        if (!(globalConfig instanceof GlobalWritingConfig)) {
            logger.info("DynamicPromptBuilder: globalConfig is not an instance of GlobalWritingConfig. Using default.");
            this.globalConfig = new GlobalWritingConfig();
        } else {
            this.globalConfig = globalConfig;
        }
    }

    buildOutlinePrompt(title, theme, stageConfig) {
        if (!(stageConfig instanceof StageSpecificConfig)) stageConfig = new StageSpecificConfig();

        let basePrompt = \`Please generate a complete creative outline for the novel "《\${title}》".

[Basic Information]
- Title: \${title}
- Theme: \${theme}
- Narrative Style: \${this.globalConfig.writing_style}
- Pacing Style: \${this.globalConfig.pacing_style}
- Overall Tone: \${this.globalConfig.tone}\`;

        if (this.globalConfig.continuous_themes && this.globalConfig.continuous_themes.length > 0) {
            basePrompt += \`\n- Core Themes: \${this.globalConfig.continuous_themes.join(', ')}\`;
        }
        if (this.globalConfig.must_include_elements && this.globalConfig.must_include_elements.length > 0) {
            basePrompt += \`\n- Must Include: \${this.globalConfig.must_include_elements.join(', ')}\`;
        }
        if (this.globalConfig.avoid_elements && this.globalConfig.avoid_elements.length > 0) {
            basePrompt += \`\n- Avoid: \${this.globalConfig.avoid_elements.join(', ')}\`;
        }

        basePrompt += \`

[Creative Requirements]
- Estimated Chapters: 10-15 chapters
- Target Words per Chapter: Approx. \${this.globalConfig.target_chapter_words} words
- Detail Level: \${stageConfig.detail_level}
- Creativity: \${this._getCreativityInstruction(stageConfig.creativity_level)}\`;

        if (this.globalConfig.global_instructions && this.globalConfig.global_instructions.trim()) {
            basePrompt += \`

[Global Writing Guidance]
\${this.globalConfig.global_instructions.trim()}\`;
        }

        if (stageConfig.additional_prompt && stageConfig.additional_prompt.trim()) {
            basePrompt += \`

[This Stage's Special Instructions]
\${stageConfig.additional_prompt.trim()}\`;
        }

        if (stageConfig.focus_aspects && stageConfig.focus_aspects.length > 0) {
            basePrompt += \`

[Focus Aspects] Please pay special attention to: \${stageConfig.focus_aspects.join(', ')}\`;
        }
        return basePrompt;
    }

    buildChapterDivisionPrompt(outline, stageConfig) {
        if (!(stageConfig instanceof StageSpecificConfig)) stageConfig = new StageSpecificConfig();
        let basePrompt = \`Based on the following outline, please divide it into chapter structures:

[Overall Outline]
\${outline}

[Division Requirements]
- Number of Chapters: 10-15 chapters
- Target Words per Chapter: \${this.globalConfig.target_chapter_words} words
- Pacing Style: \${this.globalConfig.pacing_style}
- Detail Level: \${stageConfig.detail_level}\`;

        if (this.globalConfig.continuous_themes && this.globalConfig.continuous_themes.length > 0) {
            basePrompt += \`\n- Ensure chapter arrangement reflects: \${this.globalConfig.continuous_themes.join(', ')}\`;
        }

        basePrompt += \`

[Chapter Requirements]
1. Each chapter title should be specific and engaging.
2. Chapter summary should be within \${this._getSummaryLength(stageConfig.detail_level)} words.
3. Ensure plot development aligns with the characteristics of \${this.globalConfig.pacing_style}.
4. Chapter arrangement should support the narrative style of \${this.globalConfig.writing_style}.\`;

        return this._addCommonSuffix(basePrompt, stageConfig);
    }

    buildChapterOutlinePrompt(chapterTitle, chapterSummary, overallOutline, worldContext, stageConfig) {
        if (!(stageConfig instanceof StageSpecificConfig)) stageConfig = new StageSpecificConfig();
        let prompt = \`Generate a detailed outline for Chapter: "\${chapterTitle}".

Chapter Summary: \${chapterSummary}

Overall Novel Outline:
\${overallOutline}

Current World Settings (if any, for context):
\${worldContext}

[Chapter Outline Requirements]
- Detail Level: \${stageConfig.detail_level}
- Creativity: \${this._getCreativityInstruction(stageConfig.creativity_level)}
- Ensure the chapter outline logically flows from the overall outline and sets up subsequent chapters.
- Incorporate elements from world settings if relevant.
\`;
        return this._addCommonSuffix(prompt, stageConfig);
    }

    buildParagraphDivisionPrompt(chapterTitle, chapterOutlineJson, stageConfig) {
        if (!(stageConfig instanceof StageSpecificConfig)) stageConfig = new StageSpecificConfig();
        let prompt = \`Based on the following chapter outline for "\${chapterTitle}", please divide it into specific paragraphs.
Each paragraph should have a clear purpose and key content points.

Chapter Outline:
\${chapterOutlineJson}

[Paragraph Division Requirements]
- Paragraph Count Preference: \${this.globalConfig.paragraph_count_preference}
- Detail Level for Purpose: \${stageConfig.detail_level}
- Estimated Words per Paragraph: Around \${this.globalConfig.target_paragraph_words} words.
\`;
        return this._addCommonSuffix(prompt, stageConfig);
    }


    buildParagraphWritingPrompt(context, stageConfig, apiConfig, selectedContext = "") {
        if (!(stageConfig instanceof StageSpecificConfig)) stageConfig = new StageSpecificConfig();

        const chapterIndex = context.chapter_index;
        const paragraphIndex = context.paragraph_index;
        const paragraph = context.paragraph; // instance of Paragraph model
        const chapter = context.chapter; // instance of Chapter model
        const previousContent = context.previous_content || '';

        const targetWords = this._calculateParagraphWords(paragraph.estimated_words, stageConfig);

        let basePrompt = \`Please write paragraph \${paragraphIndex + 1} of chapter \${chapterIndex + 1}:

[Writing Style]
- Narrative Style: \${this.globalConfig.writing_style}
- Tone: \${this.globalConfig.tone}
- Dialogue Style: \${this.globalConfig.dialogue_style}
- Description Density: \${this.globalConfig.description_density}
- Emotional Intensity: \${this.globalConfig.emotional_intensity}

[Paragraph Task]
- Purpose: \${paragraph.purpose}
- Target Word Count: \${targetWords} words (\${this._getWordCountInstruction(stageConfig.word_count_strict)})
- Mood Requirement: \${paragraph.mood}\`;

        if (paragraph.key_points && paragraph.key_points.length > 0) {
            basePrompt += \`\n- Key Points: \${paragraph.key_points.join(', ')}\`;
        }

        if (this.globalConfig.continuous_themes && this.globalConfig.continuous_themes.length > 0) {
            basePrompt += \`\n\n[Continuous Themes] Consider reflecting: \${this.globalConfig.continuous_themes.join(', ')}\`;
        }
        if (this.globalConfig.must_include_elements && this.globalConfig.must_include_elements.length > 0) {
            basePrompt += \`\n\n[Necessary Elements] Appropriately integrate: \${this.globalConfig.must_include_elements.join(', ')}\`;
        }

        basePrompt += \`\n\n[Chapter Context]
- Chapter Title: \${chapter.title}
- Chapter Goal: \${chapter.summary}\`;

        if (chapter.outline && Object.keys(chapter.outline).length > 0) {
            basePrompt += \`\n- Chapter Outline: \${JSON.stringify(chapter.outline, null, 2)}\`;
        }

        if (selectedContext && selectedContext.trim()) {
            basePrompt += \`\n\n[User-Provided Reference] Please maintain consistency with this user-provided reference content:\n\${selectedContext.trim()}\`;
        }

        if (previousContent) {
            basePrompt += \`\n\n[Previous Content] The following is the preceding paragraph. Continue from it but do not repeat:\n\${previousContent}\`;
        }

        basePrompt += \`\n\n[Length Control]\n\${this._getLengthGuidance(targetWords, stageConfig.length_preference)}\`;

        // Language and quote instruction
        const langInstruction = this._getLanguageInstruction(apiConfig.language, apiConfig.use_traditional_quotes);
        basePrompt = langInstruction + "\n\n" + basePrompt;

        return this._addCommonSuffix(basePrompt, stageConfig);
    }

    buildWorldBuildingExtractionPrompt(content, existingWorldSummary) {
        let prompt = \`Analyze the following paragraph and extract important new information to record for world-building:

Paragraph Content:
\${content}

Known Settings (avoid duplicates):
\${existingWorldSummary}

Requirements:
1. Only extract truly important NEW information.
2. Character descriptions max 15 words, scene descriptions max 15 words, term definitions max 10 words.
3. Ignore minor details and one-off elements.
4. If no important new information, return empty arrays for new_characters, new_settings, new_terms and plot_points.
Output in JSON format.
        \`;
        return prompt;
    }

    _addCommonSuffix(basePrompt, stageConfig) {
        if (this.globalConfig.global_instructions && this.globalConfig.global_instructions.trim()) {
            basePrompt += \`\n\n[Global Writing Guidance]\n\${this.globalConfig.global_instructions.trim()}\`;
        }
        if (stageConfig.additional_prompt && stageConfig.additional_prompt.trim()) {
            basePrompt += \`\n\n[Special Instructions for this Stage]\n\${stageConfig.additional_prompt.trim()}\`;
        }
        if (stageConfig.focus_aspects && stageConfig.focus_aspects.length > 0) {
            basePrompt += \`\n\n[Focus Aspects] Pay special attention to: \${stageConfig.focus_aspects.join(', ')}\`;
        }
        return basePrompt;
    }

    _getCreativityInstruction(level) {
        if (level < 0.3) return "Conservative, closely follow the outline.";
        if (level < 0.7) return "Moderate creativity, can elaborate.";
        return "Bold innovation, feel free to expand significantly.";
    }

    _getSummaryLength(detailLevel) {
        const lengths = {"簡潔": 30, "適中": 50, "詳細": 80};
        return lengths[detailLevel] || 50;
    }

    _calculateParagraphWords(estimated, stageConfig) {
        const baseWords = estimated || this.globalConfig.target_paragraph_words;
        if (stageConfig.length_preference === "short") return Math.floor(baseWords * 0.7);
        if (stageConfig.length_preference === "long") return Math.floor(baseWords * 1.3);
        return baseWords;
    }

    _getWordCountInstruction(strict) {
        return strict ? "Strictly control, margin of error not exceeding 10%." : "Approximate match is fine, can be adjusted moderately.";
    }

    _getLengthGuidance(targetWords, preference) {
        let guidance = \`Target word count: \${targetWords} words\`;
        if (preference === "short") guidance += ", requires concise and powerful language, avoid lengthy descriptions.";
        else if (preference === "long") guidance += ", can enrich details and fully develop the plot.";
        else guidance += ", moderately expand, maintain rhythm.";
        return guidance;
    }

    _getLanguageInstruction(language, useTraditionalQuotes) {
        const langInstructions = {
            "zh-TW": "請使用繁體中文寫作",
            "zh-CN": "請使用簡體中文寫作",
            "en-US": "Please write in English",
            "ja-JP": "日本語で書いてください"
        };
        let base = langInstructions[language] || "請使用繁體中文寫作";
        let quotes = "";
        if (language && language.startsWith("zh")) {
            quotes = useTraditionalQuotes ? "，對話請使用中文引號「」格式" : "，對話請使用英文引號\"\"\"\"格式";
        } else {
            quotes = ", use appropriate quotation marks for dialogue";
        }
        let formatting = language && language.startsWith("zh") ? "。請確保內容分段清晰，每個句子後適當換行，避免所有文字擠在一起。" : ". Please ensure clear paragraph breaks and proper line spacing.";
        return base + quotes + formatting;
    }
}

module.exports = DynamicPromptBuilder;
