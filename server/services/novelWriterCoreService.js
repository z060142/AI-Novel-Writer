const { LLMService, APIException, JSONParseException } = require('./llmService');
const DynamicPromptBuilder = require('./dynamicPromptBuilder');
const { TaskType, CreationStatus } = require('../models/enums');
const NovelProject = require('../models/NovelProject');
const Chapter = require('../models/Chapter');
const Paragraph = require('../models/Paragraph');
const GlobalWritingConfig = require('../models/GlobalWritingConfig');
const StageSpecificConfig = require('../models/StageSpecificConfig');
const WorldBuilding = require('../models/WorldBuilding');
const { TextFormatter } = require('../utils/textFormatter');


// Basic logger
const logger = {
    info: (msg) => console.log(\`[NWCoreService INFO] \${msg}\`),
    warn: (msg) => console.warn(\`[NWCoreService WARN] \${msg}\`),
    error: (msg) => console.error(\`[NWCoreService ERROR] \${msg}\`)
};

class NovelWriterCoreService {
    constructor(llmService) {
        if (!(llmService instanceof LLMService)) {
            throw new Error("NovelWriterCoreService requires an instance of LLMService.");
        }
        this.llmService = llmService;
        // Stage configs will be passed per call or managed externally (e.g. within NovelProject instance)
    }

    // Helper to get prompt builder
    _getPromptBuilder(novelProject) {
        return new DynamicPromptBuilder(novelProject.global_config || new GlobalWritingConfig());
    }

    async generateOutline(novelProject, stageConfig = new StageSpecificConfig()) {
        logger.info(\`Generating outline for: \${novelProject.title}\`);
        const promptBuilder = this._getPromptBuilder(novelProject);
        const prompt = promptBuilder.buildOutlinePrompt(novelProject.title, novelProject.theme, stageConfig);

        const result = await this.llmService.callLlmWithThinking(prompt, TaskType.OUTLINE, null, true); // Use planning model
        if (result) {
            novelProject.outline = JSON.stringify(result, null, 2); // Store raw JSON string
            this._updateWorldBuildingFromOutlineData(novelProject.world_building, result);
            logger.info('Outline generated and world building updated from outline data.');
            return result; // Return parsed JSON
        }
        return null;
    }

    async divideChapters(novelProject, stageConfig = new StageSpecificConfig()) {
        logger.info(\`Dividing chapters for: \${novelProject.title}\`);
        if (!novelProject.outline) throw new Error("Outline must be generated before dividing chapters.");

        const promptBuilder = this._getPromptBuilder(novelProject);
        const prompt = promptBuilder.buildChapterDivisionPrompt(novelProject.outline, stageConfig);

        const result = await this.llmService.callLlmWithThinking(prompt, TaskType.CHAPTERS, null, true); // Use planning model
        if (result && result.chapters) {
            novelProject.chapters = result.chapters.map(ch_data => new Chapter(ch_data));
            logger.info(\`Chapters divided: \${novelProject.chapters.length}\`);
            return novelProject.chapters;
        }
        return [];
    }

    async generateChapterOutline(novelProject, chapterIndex, stageConfig = new StageSpecificConfig()) {
        if (chapterIndex < 0 || chapterIndex >= novelProject.chapters.length) throw new Error("Invalid chapter index.");
        const chapter = novelProject.chapters[chapterIndex];
        logger.info(\`Generating outline for chapter \${chapterIndex + 1}: \${chapter.title}\`);

        const promptBuilder = this._getPromptBuilder(novelProject);
        const worldContext = this._getWorldContext(novelProject.world_building);
        const prompt = promptBuilder.buildChapterOutlinePrompt(chapter.title, chapter.summary, novelProject.outline, worldContext, stageConfig);

        const result = await this.llmService.callLlmWithThinking(prompt, TaskType.CHAPTER_OUTLINE, null, true);
        if (result && result.outline) {
            chapter.outline = result.outline; // Store parsed JSON directly
            logger.info(\`Chapter \${chapterIndex + 1} outline generated.\`);
            return chapter.outline;
        }
        return null;
    }

    async divideParagraphs(novelProject, chapterIndex, stageConfig = new StageSpecificConfig()) {
        if (chapterIndex < 0 || chapterIndex >= novelProject.chapters.length) throw new Error("Invalid chapter index.");
        const chapter = novelProject.chapters[chapterIndex];
        if (!chapter.outline || Object.keys(chapter.outline).length === 0) throw new Error("Chapter outline must be generated first.");
        logger.info(\`Dividing paragraphs for chapter \${chapterIndex + 1}: \${chapter.title}\`);

        const promptBuilder = this._getPromptBuilder(novelProject);
        const chapterOutlineJson = JSON.stringify(chapter.outline, null, 2);
        const prompt = promptBuilder.buildParagraphDivisionPrompt(chapter.title, chapterOutlineJson, stageConfig);

        const result = await this.llmService.callLlmWithThinking(prompt, TaskType.PARAGRAPHS, null, true);
        if (result && result.paragraphs) {
            chapter.paragraphs = result.paragraphs.map(p_data => new Paragraph(p_data));
            logger.info(\`Paragraphs divided for chapter \${chapterIndex + 1}: \${chapter.paragraphs.length}\`);
            return chapter.paragraphs;
        }
        return [];
    }

    async writeParagraph(novelProject, chapterIndex, paragraphIndex, stageConfig = new StageSpecificConfig(), selectedContext = "") {
        if (chapterIndex < 0 || chapterIndex >= novelProject.chapters.length) throw new Error("Invalid chapter index.");
        const chapter = novelProject.chapters[chapterIndex];
        if (paragraphIndex < 0 || paragraphIndex >= chapter.paragraphs.length) throw new Error("Invalid paragraph index.");
        const paragraph = chapter.paragraphs[paragraphIndex];
        logger.info(\`Writing paragraph \${paragraphIndex + 1} for chapter \${chapterIndex + 1}\`);

        paragraph.status = CreationStatus.IN_PROGRESS;

        const promptBuilder = this._getPromptBuilder(novelProject);
        const context = {
            chapter_index: chapterIndex,
            paragraph_index: paragraphIndex,
            paragraph: paragraph,
            chapter: chapter,
            previous_content: this._getPreviousParagraphsContent(chapter, paragraphIndex)
        };

        const prompt = promptBuilder.buildParagraphWritingPrompt(context, stageConfig, novelProject.api_config, selectedContext);

        try {
            const result = await this.llmService.callLlmWithThinking(prompt, TaskType.WRITING, null, false); // Use main model
            if (result && typeof result.content === 'string') {
                const formattedContent = TextFormatter.formatNovelContent(result.content, novelProject.api_config.use_traditional_quotes);
                paragraph.content = formattedContent;
                paragraph.word_count = formattedContent.split('').length; // Simple char count, refine if needed
                paragraph.status = CreationStatus.COMPLETED;
                logger.info(\`Paragraph \${paragraphIndex + 1} written. Word count: \${paragraph.word_count}\`);

                // Auto-update world building after writing
                await this.updateWorldBuildingFromContent(novelProject, formattedContent, chapterIndex, paragraphIndex);
                return paragraph.content;
            } else {
                 paragraph.status = CreationStatus.ERROR;
                 logger.warn('Paragraph writing failed or content missing from LLM response.');
            }
        } catch (e) {
            paragraph.status = CreationStatus.ERROR;
            logger.error(\`Error writing paragraph: \${e.message}\`);
            throw e; // Rethrow to be handled by API endpoint
        }
        return "";
    }

    async updateWorldBuildingFromContent(novelProject, content, chapterIndex, paragraphIndex) {
        logger.info(\`Updating world building from content of Ch\${chapterIndex+1}-P\${paragraphIndex+1}\`);
        const promptBuilder = this._getPromptBuilder(novelProject);
        const worldSummary = this._getWorldSummary(novelProject.world_building);
        const prompt = promptBuilder.buildWorldBuildingExtractionPrompt(content, worldSummary);

        try {
            const result = await this.llmService.callLlmWithThinking(prompt, TaskType.WORLD_BUILDING, null, true); // Use planning model
            if (result) {
                let hasNewContent = false;
                const wb = novelProject.world_building;

                (result.new_characters || []).forEach(char => {
                    if (char.name && !wb.characters[char.name]) { wb.characters[char.name] = char.desc; hasNewContent = true; }
                });
                (result.new_settings || []).forEach(setting => {
                    if (setting.name && !wb.settings[setting.name]) { wb.settings[setting.name] = setting.desc; hasNewContent = true; }
                });
                (result.new_terms || []).forEach(term => {
                    if (term.term && !wb.terminology[term.term]) { wb.terminology[term.term] = term.def; hasNewContent = true; }
                });
                (result.plot_points || []).forEach(plot => {
                    if (plot && !wb.plot_points.includes(plot)) { wb.plot_points.push(plot); hasNewContent = true; }
                });

                if(hasNewContent && chapterIndex !== undefined && paragraphIndex !== undefined) {
                    const chapterTitle = novelProject.chapters[chapterIndex] ? novelProject.chapters[chapterIndex].title : "Unknown Chapter";
                    const note = \`Extracted from Chapter \${chapterIndex + 1} ("\${chapterTitle}"), Paragraph \${paragraphIndex + 1}.\`;
                    wb.chapter_notes.push(note);
                }
                logger.info('World building updated from content.');
                return true;
            }
        } catch (error) {
            logger.error(\`Failed to update world building from content: \${error.message}\`);
        }
        return false;
    }

    _updateWorldBuildingFromOutlineData(worldBuilding, outlineData) {
        if (outlineData.main_characters) {
            outlineData.main_characters.forEach(char => {
                if (char.name && char.desc && !worldBuilding.characters[char.name]) {
                    worldBuilding.characters[char.name] = char.desc;
                }
            });
        }
        if (outlineData.world_setting && !worldBuilding.settings["Overall World Setting"]) {
             worldBuilding.settings["Overall World Setting"] = outlineData.world_setting;
        }
    }

    _getWorldContext(worldBuilding) {
        let context = [];
        if (worldBuilding.characters && Object.keys(worldBuilding.characters).length > 0) {
            context.push("Characters:");
            for (const [name, desc] of Object.entries(worldBuilding.characters)) {
                context.push(\`- \${name}: \${desc}\`);
            }
        }
        // Add settings, terminology similarly
        return context.join('\n');
    }

    _getWorldSummary(worldBuilding) {
        let summary = [];
        if (worldBuilding.characters) summary.push(\`Known Characters: \${Object.keys(worldBuilding.characters).slice(0,10).join(', ')}\`);
        // Add settings, terminology
        return summary.length > 0 ? summary.join('\n') : "No existing world settings.";
    }

    _getPreviousParagraphsContent(chapter, currentParagraphIndex) {
        if (currentParagraphIndex === 0) return "";
        // Get content of 1-2 previous paragraphs
        const startIndex = Math.max(0, currentParagraphIndex - 2);
        let content = [];
        for (let i = startIndex; i < currentParagraphIndex; i++) {
            if (chapter.paragraphs[i] && chapter.paragraphs[i].content) {
                content.push(\`===== Paragraph \${i + 1} (Completed) =====\n\${chapter.paragraphs[i].content}\`);
            }
        }
        return content.join("\n\n");
    }
}

module.exports = NovelWriterCoreService;
