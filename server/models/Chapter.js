const { CreationStatus } = require('./enums');
const Paragraph = require('./Paragraph');

class Chapter {
    constructor({
        title,
        summary,
        key_events = [],
        characters_involved = [],
        estimated_words = 3000,
        outline = {},
        paragraphs = [],
        content = "",
        status = CreationStatus.NOT_STARTED
    }) {
        this.title = title;
        this.summary = summary;
        this.key_events = key_events || [];
        this.characters_involved = characters_involved || [];
        this.estimated_words = estimated_words;
        this.outline = outline || {};
        this.paragraphs = (paragraphs || []).map(p => p instanceof Paragraph ? p : new Paragraph(p));
        this.content = content;
        this.status = status;
    }
}

module.exports = Chapter;
