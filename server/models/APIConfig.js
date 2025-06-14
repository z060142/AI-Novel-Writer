class APIConfig {
    constructor({
        base_url = "https://api.openai.com/v1",
        model = "gpt-4",
        provider = "openai",
        api_key = "",
        max_retries = 3,
        timeout = 60,
        language = "zh-TW",
        use_traditional_quotes = true,
        disable_thinking = false,
        use_planning_model = false,
        planning_base_url = "https://api.openai.com/v1",
        planning_model = "gpt-4-turbo",
        planning_provider = "openai",
        planning_api_key = ""
    } = {}) {
        this.base_url = base_url;
        this.model = model;
        this.provider = provider;
        this.api_key = api_key;
        this.max_retries = max_retries;
        this.timeout = timeout;
        this.language = language;
        this.use_traditional_quotes = use_traditional_quotes;
        this.disable_thinking = disable_thinking;
        this.use_planning_model = use_planning_model;
        this.planning_base_url = planning_base_url;
        this.planning_model = planning_model;
        this.planning_provider = planning_provider;
        this.planning_api_key = planning_api_key;
    }
}

module.exports = APIConfig;
