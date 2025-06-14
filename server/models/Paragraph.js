const { CreationStatus } = require('./enums');

class Paragraph {
    constructor({
        order,
        purpose,
        content_type = "",
        key_points = [],
        estimated_words = 0,
        mood = "",
        content = "",
        status = CreationStatus.NOT_STARTED,
        word_count = 0
    }) {
        this.order = order;
        this.purpose = purpose;
        this.content_type = content_type;
        this.key_points = key_points || [];
        this.estimated_words = estimated_words;
        this.mood = mood;
        this.content = content;
        this.status = status;
        this.word_count = word_count;
    }
}

module.exports = Paragraph;
