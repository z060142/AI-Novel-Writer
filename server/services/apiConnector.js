const axios = require('axios');
const APIConfig = require('../models/APIConfig'); // Assuming path

// Basic logger
const logger = {
    info: (msg) => console.log(\`[ApiConnector INFO] \${msg}\`),
    warn: (msg) => console.warn(\`[ApiConnector WARN] \${msg}\`),
    error: (msg) => console.error(\`[ApiConnector ERROR] \${msg}\`)
};

class APIException extends Error {
    constructor(message, status) {
        super(message);
        this.name = "APIException";
        this.status = status;
    }
}

class ApiConnector {
    constructor(apiConfig) {
        if (!(apiConfig instanceof APIConfig)) {
            logger.warn('ApiConnector initialized with invalid APIConfig. Using default.');
            this.config = new APIConfig();
        } else {
            this.config = apiConfig;
        }
        this.debugCallback = (msg) => logger.info(msg); // Default debug callback
    }

    setDebugCallback(callback) {
        this.debugCallback = callback;
    }

    async callApi(messages, max_tokens = 2000, temperature = 0.7, use_planning_model = false) {
        const currentConfig = use_planning_model && this.config.use_planning_model
            ? {
                provider: this.config.planning_provider || this.config.provider,
                apiKey: this.config.planning_api_key || this.config.api_key,
                baseUrl: this.config.planning_base_url || this.config.base_url,
                model: this.config.planning_model || this.config.model,
              }
            : {
                provider: this.config.provider,
                apiKey: this.config.api_key,
                baseUrl: this.config.base_url,
                model: this.config.model,
              };

        if (!currentConfig.apiKey) {
            this.debugCallback('❌ API Key is missing.');
            throw new APIException("API Key is missing.", 401);
        }
        this.debugCallback(\`💡 Using model: \${currentConfig.model} from \${currentConfig.provider} at \${currentConfig.baseUrl}\`);

        let lastError = null;
        for (let attempt = 0; attempt < this.config.max_retries; attempt++) {
            try {
                this.debugCallback(\`📤 API call attempt \${attempt + 1}/\${this.config.max_retries}\`);
                let response;
                if (currentConfig.provider === 'openai' || currentConfig.provider === 'custom' || currentConfig.provider.includes('ollama') || currentConfig.provider.includes('lm-studio') || current_config.provider.includes('localai') || current_config.provider.includes('text-generation-webui') || current_config.provider.includes('vllm')) {
                    response = await this._callOpenAICompatAPI(messages, max_tokens, temperature, currentConfig);
                } else if (currentConfig.provider === 'anthropic') {
                    response = await this._callAnthropicAPI(messages, max_tokens, temperature, currentConfig);
                } else {
                    throw new APIException(\`Unsupported API provider: \${currentConfig.provider}\`, 400);
                }
                return response;
            } catch (e) {
                lastError = e;
                this.debugCallback(\`⚠️ API call attempt \${attempt + 1} failed: \${e.message}\`);
                if (e instanceof APIException && (e.status === 401 || e.status === 403 || e.status === 429)) {
                    // Don't retry on auth errors or rate limits immediately
                    throw e;
                }
                if (attempt === this.config.max_retries - 1) {
                    this.debugCallback('❌ API call failed after max retries.');
                    throw new APIException(\`API call failed after \${this.config.max_retries} retries: \${lastError.message}\`, lastError.status || 500);
                }
                // Wait a bit before retrying (optional, simple delay)
                await new Promise(resolve => setTimeout(resolve, 500 * (attempt + 1)));
            }
        }
        // Should not be reached if max_retries > 0
        throw lastError || new APIException('API call failed.', 500);
    }

    async _callOpenAICompatAPI(messages, max_tokens, temperature, config) {
        const headers = {
            "Authorization": \`Bearer \${config.apiKey}\`,
            "Content-Type": "application/json"
        };
        const body = {
            model: config.model,
            messages: messages,
            max_tokens: max_tokens,
            temperature: temperature
        };
        if (this.config.disable_thinking) { // Check global config for disable_thinking
            body.thinking = false;
        }

        try {
            const response = await axios.post(\`\${config.baseUrl}/chat/completions\`, body, {
                headers: headers,
                timeout: this.config.timeout * 1000 // axios timeout is in ms
            });

            if (response.data && response.data.choices && response.data.choices[0]) {
                return {
                    content: response.data.choices[0].message.content,
                    usage: response.data.usage,
                    model: response.data.model || config.model
                };
            } else {
                throw new APIException('Invalid response structure from OpenAI compatible API.', 500);
            }
        } catch (error) {
            if (error.response) {
                throw new APIException(\`OpenAI API Error: \${error.response.status} \${JSON.stringify(error.response.data)}\`, error.response.status);
            } else if (error.request) {
                throw new APIException('No response received from OpenAI API.', 504);
            } else {
                throw new APIException(\`Error setting up OpenAI API request: \${error.message}\`, 500);
            }
        }
    }

    async _callAnthropicAPI(messages, max_tokens, temperature, config) {
        const headers = {
            "x-api-key": config.apiKey,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        };

        let system_message = "";
        let user_messages = messages;
        if (messages && messages[0] && messages[0].role === "system") {
            system_message = messages[0].content;
            user_messages = messages.slice(1);
        }

        const body = {
            model: config.model,
            max_tokens: max_tokens,
            temperature: temperature,
            messages: user_messages,
        };
        if (system_message) {
            body.system = system_message;
        }

        try {
            const response = await axios.post(\`\${config.baseUrl}/messages\`, body, { // Anthropic base URL might not need /v1
                headers: headers,
                timeout: this.config.timeout * 1000
            });

            if (response.data && response.data.content && response.data.content[0]) {
                return {
                    content: response.data.content[0].text,
                    usage: response.data.usage,
                    model: response.data.model || config.model // Anthropic response might have model in `response.data.model` or similar
                };
            } else {
                throw new APIException('Invalid response structure from Anthropic API.', 500);
            }
        } catch (error) {
            if (error.response) {
                throw new APIException(\`Anthropic API Error: \${error.response.status} \${JSON.stringify(error.response.data)}\`, error.response.status);
            } else if (error.request) {
                throw new APIException('No response received from Anthropic API.', 504);
            } else {
                throw new APIException(\`Error setting up Anthropic API request: \${error.message}\`, 500);
            }
        }
    }
}

module.exports = { ApiConnector, APIException };
