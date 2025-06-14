document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const projectTitleInput = document.getElementById('projectTitle');
    const projectThemeInput = document.getElementById('projectTheme');
    const newProjectBtn = document.getElementById('newProjectBtn');
    const saveProjectBtn = document.getElementById('saveProjectBtn');
    const loadProjectBtn = document.getElementById('loadProjectBtn');
    const loadProjectNameInput = document.getElementById('loadProjectName');
    const exportProjectBtn = document.getElementById('exportProjectBtn');
    const projectListUl = document.getElementById('projectList');
    const listProjectsBtn = document.getElementById('listProjectsBtn');

    const currentProjectInfoDiv = document.getElementById('currentProjectInfo');
    const generateOutlineBtn = document.getElementById('generateOutlineBtn');
    const divideChaptersBtn = document.getElementById('divideChaptersBtn');

    const novelTreeViewDiv = document.getElementById('novelTreeView');
    const contentDisplayTextArea = document.getElementById('contentDisplay');

    const apiConfigBtn = document.getElementById('apiConfigBtn');
    const globalConfigBtn = document.getElementById('globalConfigBtn');

    const apiKeyInput = document.getElementById('apiKey');
    const apiModelInput = document.getElementById('apiModel');
    const apiBaseUrlInput = document.getElementById('apiBaseUrl');
    const saveApiConfigBtn = document.getElementById('saveApiConfigBtn');
    const logAreaDiv = document.getElementById('logArea');

    // --- Application State ---
    let currentProject = null; // Will hold the loaded NovelProject object

    // --- Utility Functions ---
    function logMessage(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.textContent = \`[\${timestamp}] \${message}\`;
        if (type === 'error') {
            logEntry.style.color = 'red';
        } else if (type === 'success') {
            logEntry.style.color = 'green';
        }
        logAreaDiv.appendChild(logEntry);
        logAreaDiv.scrollTop = logAreaDiv.scrollHeight; // Auto-scroll
    }

    async function apiCall(endpoint, method = 'GET', body = null) {
        logMessage(\`API Call: \${method} \${endpoint}\`);
        try {
            const options = {
                method,
                headers: { 'Content-Type': 'application/json' },
            };
            if (body) {
                options.body = JSON.stringify(body);
            }
            const response = await fetch(endpoint, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: response.statusText }));
                throw new Error(\`HTTP error \${response.status}: \${errorData.message}\`);
            }
            // For export, response might be text, not JSON
            if (response.headers.get('Content-Type')?.includes('text/plain')) {
                return await response.text();
            }
            return await response.json();
        } catch (error) {
            logMessage(\`API Error (\${method} \${endpoint}): \${error.message}\`, 'error');
            throw error;
        }
    }

    function updateCurrentProjectInfo() {
        if (!currentProject) renderNovelTree(null);
        if (currentProject && currentProject.title) {
            currentProjectInfoDiv.textContent = \`Current Project: \${currentProject.title}\`;
            projectTitleInput.value = currentProject.title;
            projectThemeInput.value = currentProject.theme;
            contentDisplayTextArea.value = currentProject.outline || ''; // Display outline by default
            // Enable/disable buttons based on project state
            saveProjectBtn.disabled = false;
            exportProjectBtn.disabled = false;
            generateOutlineBtn.disabled = !!currentProject.outline; // Disable if outline exists
            divideChaptersBtn.disabled = !currentProject.outline || !!currentProject.chapters?.length;
        } else {
            currentProjectInfoDiv.textContent = 'Current Project: None';
            projectTitleInput.value = '';
            projectThemeInput.value = '';
            contentDisplayTextArea.value = '';
            saveProjectBtn.disabled = true;
            exportProjectBtn.disabled = true;
            generateOutlineBtn.disabled = true;
            divideChaptersBtn.disabled = true;
        }
    }

    // --- Hierarchical Display Functions ---
    // const novelTreeViewDiv = document.getElementById('novelTreeView'); // Ensure this is defined with other DOM elements - Already defined

    function displayContentForItem(itemType, chapterIndex = null, paragraphIndex = null) {
        logMessage(\`Displaying content for: \${itemType} \${chapterIndex !== null ? 'Ch:' + (chapterIndex+1) : ''} \${paragraphIndex !== null ? 'P:' + (paragraphIndex+1) : ''}\`);
        let contentToDisplay = '';
        let currentSelectionPath = itemType;

        if (!currentProject) {
            contentDisplayTextArea.value = "No project loaded.";
            return;
        }

        switch (itemType) {
            case 'novel_title':
                contentToDisplay = \`Title: \${currentProject.title}\nTheme: \${currentProject.theme}\`;
                break;
            case 'overall_outline':
                contentToDisplay = currentProject.outline || "No overall outline yet.";
                break;
            case 'chapter':
                if (chapterIndex !== null && currentProject.chapters[chapterIndex]) {
                    const ch = currentProject.chapters[chapterIndex];
                    contentToDisplay = \`Chapter \${ch.number || (chapterIndex + 1)}: \${ch.title}\nSummary: \${ch.summary}\nStatus: \${ch.status}\nEst. Words: \${ch.estimated_words}\`;
                    contentToDisplay += "\n\nParagraphs:\n";
                    ch.paragraphs.forEach((p, idx) => {
                        contentToDisplay += \`  P\${idx+1}: \${p.purpose.substring(0,50)}... (\${p.status})\n\`;
                    });
                    currentSelectionPath += \`_\${chapterIndex}\`;
                } else {
                    contentToDisplay = "Chapter data not found.";
                }
                break;
            case 'chapter_outline':
                if (chapterIndex !== null && currentProject.chapters[chapterIndex] && currentProject.chapters[chapterIndex].outline) {
                    contentToDisplay = JSON.stringify(currentProject.chapters[chapterIndex].outline, null, 2);
                     currentSelectionPath += \`_\${chapterIndex}\`;
                } else {
                    contentToDisplay = "No chapter outline yet or chapter data not found.";
                }
                break;
            case 'paragraph':
                if (chapterIndex !== null && paragraphIndex !== null &&
                    currentProject.chapters[chapterIndex] && currentProject.chapters[chapterIndex].paragraphs[paragraphIndex]) {
                    contentToDisplay = currentProject.chapters[chapterIndex].paragraphs[paragraphIndex].content || "No content for this paragraph yet.";
                    currentSelectionPath += \`_\${chapterIndex}_\${paragraphIndex}\`;
                } else {
                    contentToDisplay = "Paragraph data not found.";
                }
                break;
            default:
                contentToDisplay = "Select an item from the novel structure.";
        }
        contentDisplayTextArea.value = contentToDisplay;

        // Highlight selected item in tree (basic)
        document.querySelectorAll('#novelTreeView .tree-item').forEach(item => item.classList.remove('selected'));
        const selectedElement = document.querySelector(\`#novelTreeView .tree-item[data-path="\${currentSelectionPath}"]\`);
        if (selectedElement) {
            selectedElement.classList.add('selected');
        }
    }

    function renderNovelTree(project) {
        novelTreeViewDiv.innerHTML = ''; // Clear previous tree
        if (!project) {
            novelTreeViewDiv.innerHTML = '<p>No project loaded.</p>';
            return;
        }

        const ulRoot = document.createElement('ul');
        ulRoot.classList.add('tree-root');

        // Novel Title (Root Item)
        const liNovel = document.createElement('li');
        liNovel.textContent = \`📖 \${project.title || 'Untitled Novel'}\`;
        liNovel.classList.add('tree-item', 'novel-title-item');
        liNovel.dataset.path = 'novel_title';
        liNovel.addEventListener('click', () => displayContentForItem('novel_title'));
        ulRoot.appendChild(liNovel);

        // Overall Outline
        if (project.outline) {
            const liOverallOutline = document.createElement('li');
            liOverallOutline.textContent = \`📋 Overall Outline (\${project.outline.length} chars)\`;
            liOverallOutline.classList.add('tree-item', 'outline-item');
            liOverallOutline.dataset.path = 'overall_outline';
            liOverallOutline.addEventListener('click', () => displayContentForItem('overall_outline'));
            ulRoot.appendChild(liOverallOutline);
        } else {
             const liOverallOutlinePlaceholder = document.createElement('li');
            liOverallOutlinePlaceholder.textContent = \`📋 Overall Outline (Not generated)\`;
            liOverallOutlinePlaceholder.classList.add('tree-item', 'placeholder-item');
            ulRoot.appendChild(liOverallOutlinePlaceholder);
        }


        // Chapters
        if (project.chapters && project.chapters.length > 0) {
            const ulChapters = document.createElement('ul');
            project.chapters.forEach((chapter, chIndex) => {
                const liChapter = document.createElement('li');
                const totalWords = chapter.paragraphs.reduce((sum, p) => sum + (p.word_count || 0), 0);
                liChapter.textContent = \`📚 Chapter \${chapter.number || (chIndex + 1)}: \${chapter.title} (\${chapter.status}, \${totalWords} words)\`;
                liChapter.classList.add('tree-item', 'chapter-item');
                liChapter.dataset.path = \`chapter_\${chIndex}\`;
                liChapter.addEventListener('click', (e) => {
                    e.stopPropagation(); // Prevent parent clicks if nested
                    displayContentForItem('chapter', chIndex);
                });

                const ulChapterDetails = document.createElement('ul');

                // Chapter Outline
                if (chapter.outline && Object.keys(chapter.outline).length > 0) {
                    const liChapterOutline = document.createElement('li');
                    liChapterOutline.textContent = \`📝 Chapter Outline (\${JSON.stringify(chapter.outline).length} chars)\`;
                    liChapterOutline.classList.add('tree-item', 'chapter-outline-item');
                    liChapterOutline.dataset.path = \`chapter_outline_\${chIndex}\`;
                    liChapterOutline.addEventListener('click', (e) => {
                        e.stopPropagation();
                        displayContentForItem('chapter_outline', chIndex);
                    });
                    ulChapterDetails.appendChild(liChapterOutline);
                } else {
                    const liChapterOutlinePlaceholder = document.createElement('li');
                    liChapterOutlinePlaceholder.textContent = \`📝 Chapter Outline (Not generated)\`;
                    liChapterOutlinePlaceholder.classList.add('tree-item', 'placeholder-item');
                    ulChapterDetails.appendChild(liChapterOutlinePlaceholder);
                }

                // Paragraphs
                if (chapter.paragraphs && chapter.paragraphs.length > 0) {
                    const ulParagraphs = document.createElement('ul');
                    chapter.paragraphs.forEach((para, pIndex) => {
                        const liPara = document.createElement('li');
                        liPara.textContent = \`📄 P\${para.order !== undefined ? para.order + 1 : pIndex + 1}: \${(para.purpose || 'Untitled').substring(0, 30)}... (\${para.status}, \${para.word_count || 0} words)\`;
                        liPara.classList.add('tree-item', 'paragraph-item');
                        liPara.dataset.path = \`paragraph_\${chIndex}_\${pIndex}\`;
                        liPara.addEventListener('click', (e) => {
                            e.stopPropagation();
                            displayContentForItem('paragraph', chIndex, pIndex);
                        });
                        ulParagraphs.appendChild(liPara);
                    });
                    ulChapterDetails.appendChild(ulParagraphs);
                } else {
                     const liParagraphsPlaceholder = document.createElement('li');
                    liParagraphsPlaceholder.textContent = \`📄 Paragraphs (Not generated)\`;
                    liParagraphsPlaceholder.classList.add('tree-item', 'placeholder-item');
                    ulChapterDetails.appendChild(liParagraphsPlaceholder);
                }
                liChapter.appendChild(ulChapterDetails);
                ulChapters.appendChild(liChapter);
            });
            ulRoot.appendChild(ulChapters);
        } else if (project.title) { // Only show placeholder if project exists but no chapters
            const liChapterPlaceholder = document.createElement('li');
            liChapterPlaceholder.textContent = \`📚 Chapters (Not generated)\`;
            liChapterPlaceholder.classList.add('tree-item', 'placeholder-item');
            ulRoot.appendChild(liChapterPlaceholder);
        }
        novelTreeViewDiv.appendChild(ulRoot);
        logMessage("Novel structure tree rendered.");
    }

    // --- Event Handlers ---
    async function listProjects() {
        try {
            const projectNames = await apiCall('/api/projects');
            projectListUl.innerHTML = ''; // Clear existing list
            if (projectNames.length === 0) {
                projectListUl.innerHTML = '<li>No projects found.</li>';
            } else {
                projectNames.forEach(name => {
                    const li = document.createElement('li');
                    li.textContent = name;
                    li.addEventListener('click', () => {
                        loadProjectNameInput.value = name;
                        loadProjectFromServer(); // Optionally auto-load on click
                    });
                    projectListUl.appendChild(li);
                });
            }
            logMessage('Project list refreshed.', 'success');
        } catch (error) {
            // Error already logged by apiCall
        }
    }

    async function createNewProject() {
        const title = projectTitleInput.value.trim();
        const theme = projectThemeInput.value.trim();
        if (!title || !theme) {
            logMessage('Project title and theme are required to create a new project.', 'error');
            return;
        }
        try {
            const newProjectData = await apiCall('/api/projects/new', 'POST', { title, theme });
            currentProject = newProjectData;
            renderNovelTree(currentProject);
            logMessage(\`New project '\${currentProject.title}' created successfully!\`, 'success');
            updateCurrentProjectInfo();
            listProjects(); // Refresh project list
        } catch (error) {
            // Error already logged
        }
    }

    async function saveProjectToServer() {
        if (!currentProject) {
            logMessage('No active project to save.', 'error');
            return;
        }
        // Update currentProject from UI before saving (if needed, e.g. outline directly edited)
        currentProject.title = projectTitleInput.value.trim(); // Ensure title is up-to-date
        currentProject.theme = projectThemeInput.value.trim();
        // For now, assuming contentDisplay might hold the outline if that's what's being shown
        // More complex state management needed if other parts are editable directly in this textarea
        if(contentDisplayTextArea.value && !currentProject.chapters?.length) { // crude check if it's outline
            currentProject.outline = contentDisplayTextArea.value;
        }

        try {
            await apiCall('/api/projects/save', 'POST', currentProject);
            logMessage(\`Project '\${currentProject.title}' saved successfully!\`, 'success');
        } catch (error) {
            // Error already logged
        }
    }

    async function loadProjectFromServer() {
        const projectName = loadProjectNameInput.value.trim();
        if (!projectName) {
            logMessage('Please enter a project name to load.', 'error');
            return;
        }
        try {
            const projectData = await apiCall(\`/api/projects/load/\${projectName}\`);
            currentProject = projectData;
            renderNovelTree(currentProject);
            logMessage(\`Project '\${currentProject.title}' loaded successfully!\`, 'success');
            updateCurrentProjectInfo();
            // TODO: Populate novelTreeView with project structure
            // novelTreeViewDiv.textContent = JSON.stringify(currentProject, null, 2).substring(0, 500) + "... (raw data)"; // Replaced by renderNovelTree
        } catch (error) {
            currentProject = null;
            updateCurrentProjectInfo();
        }
    }

    async function exportProjectAsText() {
        if (!currentProject || !currentProject.title) {
            logMessage('No active project to export or project title is missing.', 'error');
            return;
        }
        try {
            const textContent = await apiCall(\`/api/projects/export/\${currentProject.title}\`, 'GET');
            // Create a blob and trigger download
            const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = \`\${currentProject.title}.txt\`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            logMessage(\`Project '\${currentProject.title}' exported.\`, 'success');
        } catch (error) {
            logMessage(\`Failed to export project: \${error.message}\`, 'error');
        }
    }


    async function handleGenerateOutline() {
        if (!currentProject) {
            logMessage("No project loaded to generate outline for.", "error");
            return;
        }
        logMessage(\`Generating outline for \${currentProject.title}...\`);
        generateOutlineBtn.disabled = true;
        try {
            // StageConfig can be collected from UI later. For now, sending empty.
            const response = await apiCall(\`/api/novel/\${currentProject.title}/generate-outline\`, 'POST', { stageConfig: {} });
            currentProject = response.project; // Update project with backend changes
            renderNovelTree(currentProject);
            logMessage("Outline generated successfully!", "success");
            updateCurrentProjectInfo();
        } catch (error) {
            logMessage(\`Outline generation failed: \${error.message}\`, "error");
        } finally {
            generateOutlineBtn.disabled = !!currentProject?.outline; // Re-evaluate based on new state
        }
    }

    async function handleDivideChapters() {
        if (!currentProject || !currentProject.outline) {
            logMessage("Project outline must exist to divide chapters.", "error");
            return;
        }
        logMessage(\`Dividing chapters for \${currentProject.title}...\`);
        divideChaptersBtn.disabled = true;
        try {
            const response = await apiCall(\`/api/novel/\${currentProject.title}/divide-chapters\`, 'POST', { stageConfig: {} });
            currentProject = response.project;
            renderNovelTree(currentProject);
            logMessage("Chapters divided successfully!", "success");
            updateCurrentProjectInfo();
            // TODO: Update tree view
             // novelTreeViewDiv.textContent = JSON.stringify(currentProject, null, 2).substring(0, 500) + "... (raw data)"; // Replaced by renderNovelTree
        } catch (error) {
             logMessage(\`Chapter division failed: \${error.message}\`, "error");
        } finally {
            divideChaptersBtn.disabled = !currentProject?.outline || !!currentProject?.chapters?.length;
        }
    }


    async function loadAndDisplayApiConfig() {
        logMessage("Loading API configuration...");
        try {
            const config = await apiCall('/api/config/api', 'GET');
            if (config) {
                apiKeyInput.value = config.api_key || '';
                apiModelInput.value = config.model || '';
                apiBaseUrlInput.value = config.base_url || '';
                // Display more config fields if added to HTML
                contentDisplayTextArea.value = JSON.stringify(config, null, 2);
                logMessage("API configuration loaded and displayed.", "success");
            }
        } catch (error) {
            logMessage(\`Failed to load API config: \${error.message}\`, "error");
            contentDisplayTextArea.value = "Failed to load API configuration.";
        }
    }

    async function saveApiConfiguration() {
        logMessage("Saving API configuration...");
        // Best practice: fetch current config, update specific fields, then save the whole object
        // This ensures other settings not in the UI are preserved.
        try {
            const currentFullConfig = await apiCall('/api/config/api', 'GET') || {};
            const updatedConfig = {
                ...currentFullConfig, // Spread existing config
                api_key: apiKeyInput.value.trim() || currentFullConfig.api_key, // Keep existing if input empty
                model: apiModelInput.value.trim() || currentFullConfig.model,
                base_url: apiBaseUrlInput.value.trim() || currentFullConfig.base_url,
                // Preserve other fields not directly editable in this simple UI
                provider: currentFullConfig.provider,
                max_retries: currentFullConfig.max_retries,
                timeout: currentFullConfig.timeout,
                language: currentFullConfig.language,
                use_traditional_quotes: currentFullConfig.use_traditional_quotes,
                disable_thinking: currentFullConfig.disable_thinking,
                use_planning_model: currentFullConfig.use_planning_model,
                planning_base_url: currentFullConfig.planning_base_url,
                planning_model: currentFullConfig.planning_model,
                planning_provider: currentFullConfig.planning_provider,
                planning_api_key: currentFullConfig.planning_api_key
            };


            const response = await apiCall('/api/config/api', 'POST', updatedConfig);
            logMessage("API configuration saved successfully!", "success");
            // Optionally, display the full saved config
            contentDisplayTextArea.value = JSON.stringify(response.config, null, 2);
        } catch (error) {
            logMessage(\`Failed to save API config: \${error.message}\`, "error");
        }
    }
    // --- Initialize ---
    logMessage("Frontend application initialized.");
    listProjectsBtn.addEventListener('click', listProjects);
    newProjectBtn.addEventListener('click', createNewProject);
    saveProjectBtn.addEventListener('click', saveProjectToServer);
    loadProjectBtn.addEventListener('click', loadProjectFromServer);
    exportProjectBtn.addEventListener('click', exportProjectAsText);

    generateOutlineBtn.addEventListener('click', handleGenerateOutline);
    divideChaptersBtn.addEventListener('click', handleDivideChapters);

    apiConfigBtn.addEventListener('click', loadAndDisplayApiConfig);
    saveApiConfigBtn.addEventListener('click', saveApiConfiguration);
    globalConfigBtn.addEventListener('click', () => logMessage('Global Config button clicked (not implemented yet).'));

    // Initial setup
    updateCurrentProjectInfo(); // Set initial button states
    listProjects(); // Load project list on start
});
