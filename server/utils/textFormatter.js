// Basic logger
const logger = { info: console.log, warn: console.warn, error: console.error };

const TextFormatter = {
    formatNovelContent: (content, useTraditionalQuotes = true) => {
        if (!content || typeof content !== 'string') {
            return content;
        }

        let formatted = content;

        // Normalize line endings
        formatted = formatted.replace(/\r\n|\r/g, '\n');

        // Unify quotes
        if (useTraditionalQuotes) {
            // Convert English quotes to Chinese quotes
            // This needs to be careful not to mess up already formatted quotes or nested quotes.
            // A simple regex might be too naive for complex cases.
            // Python version: content = re.sub(r'"([^"]*)"', r'「\1」', content) (multiple times)
            // JS equivalent is trickier due to lack of lookbehinds in all engines, but modern JS supports them.
            // For simplicity, let's do a basic replacement.
            formatted = formatted.replace(/"([^"]*?)"/g, '「$1」');
             // Python version did it 3 times, perhaps for overlapping matches or specific cases.
            formatted = formatted.replace(/"([^"]*?)"/g, '「$1」');
            formatted = formatted.replace(/"([^"]*?)"/g, '「$1」');
        } else {
            // Convert Chinese quotes to English quotes
            formatted = formatted.replace(/「([^」]*?)」/g, '"$1"');
        }

        // Paragraph formatting (Python version was complex)
        // Simplified version: ensure double newlines after sentences ending with specific punctuation.
        // formatted = formatted.replace(/([。！？])([^」\n])/g, '$1\n\n$2'); // Python: ([。！？])([^」
])
        // formatted = formatted.replace(/([」])([。！？])([^」\n])/g, '$1$2\n\n$3'); // Python: ([」])([。！？])([^」
])

        // A simpler approach for JS: Split by lines, process, then join.
        const lines = formatted.split('\n');
        let processedLines = [];
        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();
            if (line) {
                 // Ensure sentences end with appropriate punctuation (very basic)
                if (/[a-zA-Z0-9\u4e00-\u9fff]$/.test(line) && !/[。！？？」]$/.test(line)) {
                    line += '。';
                }
                processedLines.push(line);
            } else if (processedLines.length > 0 && processedLines[processedLines.length -1] !== '') {
                // Keep single empty lines between paragraphs, but not multiple
                processedLines.push('');
            }
        }

        // Remove leading/trailing empty lines and ensure max one empty line between content lines
        formatted = processedLines.filter((line, index, arr) => {
            return line !== '' || (index > 0 && arr[index-1] !== '');
        }).join('\n');

        // Clean up multiple newlines that might have been introduced or were already there
        formatted = formatted.replace(/\n{3,}/g, '\n\n');

        return formatted.trim();
    }
    // _formatParagraphs, _formatDialogue, _fixPunctuation from Python could be translated here if needed
    // For now, keeping it simpler.
};

module.exports = { TextFormatter };
