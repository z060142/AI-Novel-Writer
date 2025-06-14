# Novel Writer Web Application

This is a web-based application designed to assist users in writing novels using a hierarchical approach, with AI-powered content generation capabilities. It is a Node.js conversion of the original Python Tkinter application.

## Core Functionalities

-   **Hierarchical Writing**: Follows a structured process: Overall Outline -> Chapters -> Chapter Outlines -> Paragraphs.
-   **LLM Integration**: Utilizes Large Language Models (configurable for OpenAI, Anthropic, Ollama, other custom OpenAI-compatible APIs) for:
    -   Generating novel outlines.
    -   Dividing outlines into chapters.
    -   Generating detailed chapter outlines.
    -   Planning paragraph purposes.
    -   Writing paragraph content.
    -   Extracting world-building elements.
-   **Project Management**: Create, save, load, and export novel projects. Project data is stored locally on the server.
-   **Configuration**:
    -   Global API settings (API key, model, endpoint).
    -   Global Writing Configuration (writing style, pacing, tone, themes, target word counts).
    -   (Planned) Stage-specific configurations for fine-tuning generation at each step.
-   **World Building**: Manage characters, settings, terminology. These elements can be automatically extracted from generated content.
-   **Interactive UI**: Web interface for managing projects, configurations, novel structure, and content.
-   **Advanced Features**:
    -   Use selected text as reference context for paragraph generation.
    -   Automatic writing mode to generate content for entire chapters.

## Prerequisites

-   **Node.js**: Version 16.x or higher is recommended.
-   **npm**: Node Package Manager (usually installed with Node.js).

## Setup and Installation

1.  **Get the Code**:
    Download or clone the project files to your local machine.

2.  **Navigate to Project Directory**:
    Open a terminal or command prompt and change to the project's root directory.
    \`\`\`bash
    cd path/to/novel-writer-web
    \`\`\`

3.  **Install Dependencies**:
    Run the following command to install the necessary Node.js packages defined in `package.json` (like Express, Axios, etc.):
    \`\`\`bash
    npm install
    \`\`\`

4.  **API Configuration**:
    The application requires API credentials to connect to Large Language Models.
    -   On the first run, or if `server/data/api_config.json` is missing, the application will create it with default values.
    -   **You MUST edit this file or use the UI to set your API key and preferred model.**
    -   The key fields in `server/data/api_config.json` (or configurable via the UI) are:
        -   `api_key`: Your secret API key for the LLM provider.
        -   `model`: The specific model you want to use (e.g., "gpt-4", "claude-3-opus-20240229", your local model name for Ollama).
        -   `base_url`: The base endpoint for the API (e.g., "https://api.openai.com/v1", "http://localhost:11434/v1" for Ollama).
        -   `provider`: The LLM provider type (e.g., "openai", "anthropic", "custom" for Ollama or other OpenAI-compatible APIs).
        -   It also supports separate configuration for a "planning model" used for outlining and structuring tasks.

## Running the Application

1.  **Start the Server**:
    Once dependencies are installed and API configuration is reviewed, run the following command from the project's root directory:
    \`\`\`bash
    npm start
    \`\`\`
    This uses the `start` script defined in `package.json` (which executes `node server/server.js`).

2.  **Access the Application**:
    Open your web browser and navigate to:
    [http://localhost:3000](http://localhost:3000) (or the port specified in `server/server.js` or console output).

## Using the Application (Web Interface)

The web interface is divided into several key areas:

-   **Project Management**:
    -   Enter a "Project Title" and "Project Theme".
    -   Click "New Project" to start.
    -   "Save Project" saves your current work to the server.
    -   "Load Project": Enter a project name (from the "Available Projects" list) and click to load.
    -   "Refresh Project List": Updates the list of saved projects.
    -   "Export Project TXT": Downloads the current novel as a plain text file.

-   **Configuration**:
    -   **API Config**: Click "API Config" to view current settings. Input your API key, model, and base URL, then click "Save API Config".
    -   **Global Writing Config**: Click "Global Writing Config" to open a modal where you can define overall writing style, tone, themes, target word counts, etc. Click "Apply Global Config to Project" in the modal (and then save the project to persist these).

-   **Novel Structure Tree**:
    -   Displays the hierarchical structure: Novel Title -> Overall Outline -> Chapters -> Chapter Outlines -> Paragraphs.
    -   Click on items to view their content or details in the "Content Editor".

-   **Content Editor / Details**:
    -   Shows the content of the selected item from the novel tree.
    -   Allows direct editing of the overall outline, chapter outlines (as JSON), and paragraph content.
    -   **Remember to click "Save Project" to persist your edits.**

-   **Generation Controls**:
    -   "Generate Outline": Generates the main plot and structure for your novel.
    -   "Divide Chapters": Splits the overall outline into distinct chapters.
    -   (After selecting a chapter/paragraph in the tree) Further controls will appear or be enabled for generating chapter outlines, dividing paragraphs, and writing individual paragraphs.
    -   "Write/Rewrite Selected Paragraph": Writes or re-writes the content for the currently selected paragraph in the tree.

-   **Advanced Features**:
    -   **Reference Context**: Select text in the "Content Editor" and click "Use Selected Text as Reference". This text will be used as additional context for the next paragraph writing task. Click "Clear Reference" to remove it.
    -   **Automatic Writing**:
        -   "Auto Write Current Chapter": Sequentially generates content for all uncompleted paragraphs in the currently selected (or first) chapter.
        -   "Delay (sec)": Sets the pause between automatic paragraph generations.
        -   "Stop Auto Writing": Halts the current auto-writing process.

-   **Frontend Log**: Displays messages about frontend operations and API call statuses.

### Basic Workflow Example

1.  Configure your API settings via the "API Config" button.
2.  Enter a "Project Title" and "Theme", then click "New Project".
3.  (Optional) Adjust "Global Writing Config".
4.  Click "Generate Outline". Review/edit the outline in the Content Editor.
5.  Click "Divide Chapters".
6.  Select a chapter in the Novel Structure tree. (The system might auto-generate its chapter outline and paragraph divisions, or you'll have buttons to trigger these).
7.  Select a paragraph. Click "Write/Rewrite Selected Paragraph". Review/edit.
8.  Use "Auto Write Current Chapter" to complete a chapter more quickly.
9.  **Save your project frequently!**

## Project Data

-   All novel project data is stored as individual `.json` files in the `server/data/` directory within the application folder.
-   The global API configuration is stored in `server/data/api_config.json`.

## Troubleshooting

-   **Server Not Starting**:
    -   Ensure Node.js and npm are installed correctly.
    -   Run `npm install` to get all dependencies.
    -   Check if the port (default 3000) is already in use by another application.
-   **API Errors / No Content Generated**:
    -   Verify your API key, model name, and base URL in the "API Config" section of the UI (or in `server/data/api_config.json`).
    -   Check your LLM provider account for any issues (e.g., billing, rate limits).
    -   Look at the messages in the "Frontend Log" and the server console output for error details.
-   **Project Not Saving/Loading**:
    -   Ensure the `server/data/` directory is writable by the Node.js process.
    -   Check for any errors in the server console.
