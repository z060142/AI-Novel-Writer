const PromptManager = require('./promptManager');
const { ApiConnector, APIException } = require('./apiConnector');
const { JSONParser, JSONParseException } = require('../utils/jsonParser');
const { TaskType } = require('../models/enums'); // Placeholder for PromptManager items

// Basic logger
const logger = {
    info: (msg) => console.log(\`[LLMService INFO] \${msg}\`),
    warn: (msg) => console.warn(\`[LLMService WARN] \${msg}\`),
    error: (msg) => console.error(\`[LLMService ERROR] \${msg}\`)
};

class LLMService {
    constructor(apiConnector) {
        if (!(apiConnector instanceof ApiConnector)) {
            throw new Error("LLMService requires an instance of ApiConnector.");
        }
        this.apiConnector = apiConnector;
        this.jsonRetryMax = 3;
        this.debugCallback = (msg) => logger.info(msg); // Default debug callback
        this.apiConnector.setDebugCallback(this.debugCallback); // Pass down
    }

    setDebugCallback(callback) {
        this.debugCallback = callback;
        this.apiConnector.setDebugCallback(callback); // Ensure connector also uses it
    }

    async callLlmWithThinking(prompt, taskType, maxTokens = null, usePlanningModel = false) {
        if (maxTokens === null) {
            maxTokens = PromptManager.getTokenLimit(taskType);
        }
        const systemPrompt = PromptManager.createSystemPrompt(taskType);
        const messages = [
            { role: "system", content: systemPrompt },
            { role: "user", content: prompt }
        ];

        this.debugCallback(\`\n=== \${taskType.toUpperCase()} TASK START ===\`);
        this.debugCallback(\`Using token limit: \${maxTokens}\`);

        for (let jsonAttempt = 0; jsonAttempt < this.jsonRetryMax; jsonAttempt++) {
            try {
                this.debugCallback(\`📤 Calling API... (JSON parse attempt \${jsonAttempt + 1}/\${this.jsonRetryMax})\`);

                const result = await this.apiConnector.callApi(messages, maxTokens, undefined /* temperature */, usePlanningModel);
                const rawContent = result.content;

                this.debugCallback(\`✅ API call successful. Response length: \${rawContent.length} chars\`);
                // this.debugCallback(\`📝 API Full Response:\n\${rawContent.substring(0, 500)}...\`); // Be careful logging full response

                const jsonData = JSONParser.extractJsonFromContent(rawContent);

                if (jsonData) {
                    this.debugCallback("✅ JSON parsing successful.");
                    // this.debugCallback(\`📋 Parsed Data: \${JSON.stringify(jsonData, null, 2).substring(0,500)}...\`);
                    return jsonData;
                } else {
                    this.debugCallback(\`❌ JSON parsing failed (Attempt \${jsonAttempt + 1}/\${this.jsonRetryMax})\`);
                    if (jsonAttempt < this.jsonRetryMax - 1) {
                        this.debugCallback("🔄 Retrying with modified prompt for JSON emphasis...");
                        // Modify user prompt to emphasize JSON for retry
                        messages[messages.length - 1].content = \`\${prompt}\n\nIMPORTANT: Your response MUST be in valid JSON format, enclosed in a single triple-backtick block (e.g., \\`\\`\\`json ... \\`\\`\\`). Ensure all strings are double-quoted and there are no trailing commas.\`;
                        continue;
                    } else {
                        this.debugCallback("❌ Max JSON parsing retries reached.");
                        throw new JSONParseException("Failed to parse JSON from LLM response after multiple retries.");
                    }
                }
            } catch (error) {
                this.debugCallback(\`❌ LLM call or JSON parsing failed: \${error.message}\`);
                if (error instanceof APIException && jsonAttempt === this.jsonRetryMax -1) {
                    // If API error and last attempt, rethrow
                    throw error;
                }
                 if (error instanceof JSONParseException && jsonAttempt === this.jsonRetryMax -1) {
                    throw error;
                 }
                // For other errors or if not last attempt, it will loop or eventually throw after loop.
                 if (jsonAttempt === this.jsonRetryMax - 1) throw error; // Catch all for last attempt
            }
        }
        // Fallback, should ideally be caught by the loop's final throw
        throw new JSONParseException("LLMService.callLlmWithThinking failed after all retries.");
    }
}

module.exports = { LLMService, APIException, JSONParseException };
