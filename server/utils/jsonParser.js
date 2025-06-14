const logger = { // Basic logger, replace with a proper one if needed
    info: (msg) => console.log(\`[JSONParser INFO] \${msg}\`),
    warn: (msg) => console.warn(\`[JSONParser WARN] \${msg}\`),
    error: (msg) => console.error(\`[JSONParser ERROR] \${msg}\`)
};

class JSONParseException extends Error {
    constructor(message) {
        super(message);
        this.name = "JSONParseException";
    }
}

const JSONParser = {
    extractJsonFromContent: (content) => {
        if (!content || typeof content !== 'string') {
            logger.warn('Invalid content provided for JSON extraction.');
            return null;
        }

        const strategies = [
            // Standard markdown code block
            /```json\s*([\s\S]*?)\s*```/g,
            // Code block without 'json' tag but with braces (more lenient)
            /```\s*(\{[\s\S]*?\})\s*```/g,
            // Attempt to find a valid JSON object directly if not in code blocks
            // This regex is simplified and might need refinement for complex cases.
            // It tries to match balanced braces.
            /(\{(?:[^{}]|\{[^{}]*\})*\})/g
        ];

        for (const regex of strategies) {
            let match;
            // Reset lastIndex for global regexes if they are reused (though here we create new ones)
            // regex.lastIndex = 0;
            while ((match = regex.exec(content)) !== null) {
                let jsonStr = match[1].trim();
                jsonStr = JSONParser._cleanJsonString(jsonStr);
                try {
                    const result = JSON.parse(jsonStr);
                    if (typeof result === 'object' && result !== null) {
                        logger.info('Successfully parsed JSON from content.');
                        return result;
                    }
                } catch (e) {
                    logger.warn(\`Attempted to parse: \${jsonStr.substring(0,100)}... but failed: \${e.message}\`);
                    // Continue to try other matches or strategies
                }
            }
        }

        logger.warn('Could not find valid JSON in content using standard strategies. Attempting repair...');
        return JSONParser._attemptJsonRepair(content);
    },

    _cleanJsonString: (jsonStr) => {
        // Remove BOM if present (though less common in JS contexts from APIs)
        if (jsonStr.startsWith('\ufeff')) {
            jsonStr = jsonStr.substring(1);
        }
        // Some LLMs might add comments, try to remove them (very basic)
        jsonStr = jsonStr.split('\n').filter(line => !line.trim().startsWith('//')).join('\n');

        // Remove trailing commas (common issue)
        jsonStr = jsonStr.replace(/,\s*([}\]])/g, '$1');

        return jsonStr.trim();
    },

    _attemptJsonRepair: (content) => {
        logger.info('Attempting JSON repair...');
        let jsonPart = content;
        let startBrace = jsonPart.indexOf('{');
        if (startBrace === -1) {
            logger.warn('No opening brace found for JSON repair.');
            return null;
        }
        jsonPart = jsonPart.substring(startBrace);

        let braceCount = 0;
        let validEnd = -1;

        for (let i = 0; i < jsonPart.length; i++) {
            if (jsonPart[i] === '{') {
                braceCount++;
            } else if (jsonPart[i] === '}') {
                braceCount--;
                if (braceCount === 0) {
                    validEnd = i + 1;
                    break;
                }
            }
        }

        if (validEnd > 0) {
            const repairedJson = jsonPart.substring(0, validEnd);
            try {
                const result = JSON.parse(repairedJson);
                logger.info('Successfully repaired and parsed JSON.');
                return result;
            } catch (e) {
                logger.error(\`JSON repair failed: \${e.message}. Repaired string: \${repairedJson.substring(0,100)}...\`);
            }
        } else {
            logger.warn('Could not determine a valid end for JSON repair.');
        }
        return null;
    }
};

module.exports = { JSONParser, JSONParseException };
