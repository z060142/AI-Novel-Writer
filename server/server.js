const express = require('express');
const path = require('path');
const fs = require('fs').promises;
const sanitize = require('sanitize-filename');

// Models
const NovelProject = require('./models/NovelProject');
const Chapter = require('./models/Chapter');
const Paragraph = require('./models/Paragraph');
const APIConfig = require('./models/APIConfig');
const GlobalWritingConfig = require('./models/GlobalWritingConfig');
const WorldBuilding = require('./models/WorldBuilding');
const StageSpecificConfig = require('./models/StageSpecificConfig'); // Added
const { CreationStatus, TaskType } = require('./models/enums');

// Services
const { ApiConnector, APIException: ServiceAPIException } = require('./services/apiConnector'); // Renamed to avoid conflict
const { LLMService, JSONParseException: ServiceJSONParseException } = require('./services/llmService'); // Renamed
const NovelWriterCoreService = require('./services/novelWriterCoreService');

const app = express();
const PORT = process.env.PORT || 3000;
const DATA_DIR = path.join(__dirname, 'data');
const API_CONFIG_PATH = path.join(DATA_DIR, 'api_config.json');

// --- Global Service Instances ---
let globalApiConfig = new APIConfig(); // To hold the global API config
let llmServiceInstance; // To be initialized after globalApiConfig is loaded

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

// Helper function to load a project
async function loadProject(projectName) {
    const safeFileName = sanitize(projectName);
    const filePath = path.join(DATA_DIR, `${safeFileName}.json`);
    try {
        const data = await fs.readFile(filePath, 'utf8');
        return new NovelProject(JSON.parse(data));
    } catch (error) {
        if (error.code === 'ENOENT') throw new Error('Project not found');
        throw error;
    }
}

// Helper function to save a project
async function saveProject(project) {
    const safeFileName = sanitize(project.title);
    const filePath = path.join(DATA_DIR, `${safeFileName}.json`);
    await fs.writeFile(filePath, JSON.stringify(project, null, 2), 'utf8');
}


// Initialize App (Load Global API Config, Init Services)
const initializeApp = async () => {
    try {
        await fs.mkdir(DATA_DIR, { recursive: true });
        try {
            await fs.access(API_CONFIG_PATH);
            const configData = await fs.readFile(API_CONFIG_PATH, 'utf8');
            globalApiConfig = new APIConfig(JSON.parse(configData));
            console.log('Global API config loaded.');
        } catch (error) {
            if (error.code === 'ENOENT') {
                console.log('api_config.json not found. Creating with default values.');
                globalApiConfig = new APIConfig();
                await fs.writeFile(API_CONFIG_PATH, JSON.stringify(globalApiConfig, null, 2), 'utf8');
            } else {
                throw error;
            }
        }
        const apiConnector = new ApiConnector(globalApiConfig);
        llmServiceInstance = new LLMService(apiConnector);
        // Setup debug logging for llmService if needed (e.g., from a config or environment variable)
        // llmServiceInstance.setDebugCallback(console.log);
        console.log('LLM Service Initialized.');

    } catch (error) {
        console.error('Error during app initialization:', error);
        process.exit(1); // Exit if core services can't initialize
    }
};

// --- API Configuration APIs ---
app.get('/api/config/api', (req, res) => {
    res.json(globalApiConfig); // Return the loaded global config
});

app.post('/api/config/api', async (req, res) => {
    try {
        const configData = req.body;
        if (!configData) return res.status(400).json({ message: 'API configuration data is required.' });

        globalApiConfig = new APIConfig(configData); // Update global instance
        await fs.writeFile(API_CONFIG_PATH, JSON.stringify(globalApiConfig, null, 2), 'utf8');

        // Re-initialize services that depend on apiConfig
        const newApiConnector = new ApiConnector(globalApiConfig);
        llmServiceInstance = new LLMService(newApiConnector);
        // llmServiceInstance.setDebugCallback(console.log);
        console.log('API config updated and LLM Service re-initialized.');

        res.json({ message: 'API configuration saved successfully.', config: globalApiConfig });
    } catch (error) {
        console.error('Error saving API config:', error);
        res.status(500).json({ message: 'Error saving API configuration', error: error.message });
    }
});

// --- Project Management APIs ---
app.get('/api/projects', async (req, res) => { /* ... existing code ... */
    try {
        const files = await fs.readdir(DATA_DIR);
        const projectFiles = files.filter(file => file.endsWith('.json') && file !== 'api_config.json');
        const projectNames = projectFiles.map(file => file.replace('.json', ''));
        res.json(projectNames);
    } catch (error) {
        console.error('Error listing projects:', error);
        res.status(500).json({ message: 'Error listing projects', error: error.message });
    }
});
app.post('/api/projects/new', async (req, res) => { /* ... existing code, ensure new NovelProject uses globalApiConfig or a copy ... */
    try {
        const { title, theme } = req.body;
        if (!title || !theme) return res.status(400).json({ message: 'Title and theme are required.' });
        const safeFileName = sanitize(title) || 'Untitled Project';
        if (safeFileName === 'api_config') return res.status(400).json({ message: 'Project title cannot be "api_config".' });
        const filePath = path.join(DATA_DIR, `${safeFileName}.json`);
        try { await fs.access(filePath); return res.status(409).json({ message: `Project '\${title}' already exists.` }); } catch (err) {}

        const newProject = new NovelProject({ title, theme });
        newProject.api_config = new APIConfig(globalApiConfig); // Project gets a copy of current global API config
        await saveProject(newProject);
        res.status(201).json(newProject);
    } catch (error) { res.status(500).json({ message: 'Error creating new project', error: error.message }); }
});
app.post('/api/projects/save', async (req, res) => { /* ... existing code ... */
    try {
        const projectData = req.body;
        if (!projectData || !projectData.title) return res.status(400).json({ message: 'Project data with a title is required.' });
        const safeFileName = sanitize(projectData.title) || 'Untitled Project';
        if (safeFileName === 'api_config') return res.status(400).json({ message: 'Project title cannot be "api_config".' });

        // Ensure projectData is a full NovelProject instance before saving
        const projectToSave = new NovelProject(projectData);
        await saveProject(projectToSave);
        res.json({ message: `Project '\${projectData.title}' saved successfully.` });
    } catch (error) { res.status(500).json({ message: 'Error saving project', error: error.message }); }
});
app.get('/api/projects/load/:projectName', async (req, res) => { /* ... existing code ... */
    try {
        const project = await loadProject(req.params.projectName);
        res.json(project);
    } catch (error) {
        if (error.message === 'Project not found') return res.status(404).json({ message: error.message });
        res.status(500).json({ message: 'Error loading project', error: error.message });
    }
});
app.get('/api/projects/export/:projectName', async (req, res) => {
    try {
        const project = await loadProject(req.params.projectName);
        let content = [];
        content.push('《' + project.title + '》'); // Line 164 equivalent
        content.push("=".repeat(50));
        content.push("");
        project.chapters.forEach((chapterData, i) => {
            const chap = new Chapter(chapterData); // Ensure Chapter is correctly instantiated
            content.push('第' + (i + 1) + '章 ' + chap.title);
            content.push("-".repeat(30));
            content.push("");
            if (chap.paragraphs) { // Add null check for paragraphs
                chap.paragraphs.forEach(paraData => {
                    const para = new Paragraph(paraData); // Ensure Paragraph is correctly instantiated
                    if (para.content) {
                        content.push(para.content);
                        content.push("");
                    }
                });
            }
            content.push("");
        });
        res.setHeader('Content-Disposition', \`attachment; filename="\${sanitize(project.title)}.txt"\`);
        res.setHeader('Content-Type', 'text/plain; charset=utf-8');
        res.send(content.join('\n'));
    } catch (error) {
        console.error('Error exporting novel:', error); // Log the error on server
        if (error.message === 'Project not found') return res.status(404).json({ message: error.message });
        res.status(500).json({ message: 'Error exporting novel', error: error.message });
    }
});

// --- Novel Writing Core APIs ---
const coreServiceRouter = express.Router(); // Use a router for these specific APIs

// Middleware to load project for these routes
coreServiceRouter.use('/:projectName', async (req, res, next) => {
    try {
        req.project = await loadProject(req.params.projectName);
        // Initialize core service with the project-specific LLM service (or global one)
        // For now, assume coreService uses the global llmServiceInstance
        req.novelWriterCoreService = new NovelWriterCoreService(llmServiceInstance);
        next();
    } catch (error) {
        if (error.message === 'Project not found') return res.status(404).json({ message: error.message });
        return res.status(500).json({ message: 'Error loading project for core operation', error: error.message });
    }
});

coreServiceRouter.post('/:projectName/generate-outline', async (req, res) => {
    try {
        const { stageConfig: stageConfigData } = req.body;
        const stageConfig = new StageSpecificConfig(stageConfigData);
        const outlineResult = await req.novelWriterCoreService.generateOutline(req.project, stageConfig);
        if (outlineResult) {
            await saveProject(req.project);
            res.json({ message: "Outline generated successfully", outline: outlineResult, project: req.project });
        } else {
            res.status(500).json({ message: "Failed to generate outline" });
        }
    } catch (e) { res.status(500).json({ message: e.message, stack: e.stack }); }
});

coreServiceRouter.post('/:projectName/divide-chapters', async (req, res) => {
    try {
        const { stageConfig: stageConfigData } = req.body;
        const stageConfig = new StageSpecificConfig(stageConfigData);
        const chapters = await req.novelWriterCoreService.divideChapters(req.project, stageConfig);
        if (chapters) {
            await saveProject(req.project);
            res.json({ message: "Chapters divided successfully", chapters: chapters, project: req.project });
        } else {
            res.status(500).json({ message: "Failed to divide chapters" });
        }
    } catch (e) { res.status(500).json({ message: e.message, stack: e.stack }); }
});

coreServiceRouter.post('/:projectName/chapters/:chapterIndex/generate-outline', async (req, res) => {
    try {
        const chapterIndex = parseInt(req.params.chapterIndex);
        const { stageConfig: stageConfigData } = req.body;
        const stageConfig = new StageSpecificConfig(stageConfigData);
        const chapterOutline = await req.novelWriterCoreService.generateChapterOutline(req.project, chapterIndex, stageConfig);
        if (chapterOutline) {
            await saveProject(req.project);
            res.json({ message: "Chapter outline generated", chapterOutline: chapterOutline, project: req.project });
        } else {
             res.status(500).json({ message: "Failed to generate chapter outline" });
        }
    } catch (e) { res.status(500).json({ message: e.message, stack: e.stack }); }
});

coreServiceRouter.post('/:projectName/chapters/:chapterIndex/divide-paragraphs', async (req, res) => {
    try {
        const chapterIndex = parseInt(req.params.chapterIndex);
        const { stageConfig: stageConfigData } = req.body;
        const stageConfig = new StageSpecificConfig(stageConfigData);
        const paragraphs = await req.novelWriterCoreService.divideParagraphs(req.project, chapterIndex, stageConfig);
        if (paragraphs) {
            await saveProject(req.project);
            res.json({ message: "Paragraphs divided", paragraphs: paragraphs, project: req.project });
        } else {
            res.status(500).json({ message: "Failed to divide paragraphs" });
        }
    } catch (e) { res.status(500).json({ message: e.message, stack: e.stack }); }
});

coreServiceRouter.post('/:projectName/chapters/:chapterIndex/paragraphs/:paragraphIndex/write', async (req, res) => {
    try {
        const chapterIndex = parseInt(req.params.chapterIndex);
        const paragraphIndex = parseInt(req.params.paragraphIndex);
        const { stageConfig: stageConfigData, selectedContext } = req.body;
        const stageConfig = new StageSpecificConfig(stageConfigData);

        const content = await req.novelWriterCoreService.writeParagraph(req.project, chapterIndex, paragraphIndex, stageConfig, selectedContext);
        // writeParagraph now also calls updateWorldBuilding and saves it internally to req.project
        await saveProject(req.project); // Save the project after world building might have been updated
        res.json({ message: "Paragraph written", content: content, project: req.project });
    } catch (e) {
        // Ensure project is saved even if paragraph writing fails, to save status=ERROR
        if (req.project) await saveProject(req.project).catch(err => console.error("Failed to save project on error:", err));
        res.status(500).json({ message: e.message, stack: e.stack });
    }
});

app.use('/api/novel', coreServiceRouter);


// Root route
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

// Start server after initialization
initializeApp().then(() => {
    app.listen(PORT, () => {
      console.log(\`Server is running on http://localhost:\${PORT}\`);
      console.log(\`Data directory is \${DATA_DIR}\`);
    });
}).catch(error => {
    console.error("Failed to initialize application. Exiting.", error);
    process.exit(1);
});
