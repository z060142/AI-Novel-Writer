class WorldBuilding {
    constructor({
        characters = {},
        settings = {},
        terminology = {},
        plot_points = [],
        relationships = [],
        style_guide = "",
        chapter_notes = []
    } = {}) {
        this.characters = characters || {};
        this.settings = settings || {};
        this.terminology = terminology || {};
        this.plot_points = plot_points || [];
        this.relationships = relationships || [];
        this.style_guide = style_guide;
        this.chapter_notes = chapter_notes || [];
    }
}

module.exports = WorldBuilding;
