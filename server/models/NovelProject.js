const APIConfig = require('./APIConfig');
const Chapter = require('./Chapter');
const GlobalWritingConfig = require('./GlobalWritingConfig');
const WorldBuilding = require('./WorldBuilding');

class NovelProject {
    constructor({
        title = "",
        theme = "",
        outline = "",
        outline_additional_prompt = "",
        chapters_additional_prompt = "",
        chapters = [],
        world_building = {}, // Will be instance of WorldBuilding
        current_context = "",
        api_config = {}, // Will be instance of APIConfig
        global_config = {} // Will be instance of GlobalWritingConfig
    } = {}) {
        this.title = title;
        this.theme = theme;
        this.outline = outline;
        this.outline_additional_prompt = outline_additional_prompt;
        this.chapters_additional_prompt = chapters_additional_prompt;
        this.chapters = (chapters || []).map(c => c instanceof Chapter ? c : new Chapter(c));
        this.world_building = world_building instanceof WorldBuilding ? world_building : new WorldBuilding(world_building);
        this.current_context = current_context;
        this.api_config = api_config instanceof APIConfig ? api_config : new APIConfig(api_config);
        this.global_config = global_config instanceof GlobalWritingConfig ? global_config : new GlobalWritingConfig(global_config);
    }
}

module.exports = NovelProject;
