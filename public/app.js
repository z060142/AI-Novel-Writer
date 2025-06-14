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
    const writeCurrentParagraphBtn = document.getElementById('writeCurrentParagraphBtn');

    const novelTreeViewDiv = document.getElementById('novelTreeView');
    const generalStatusDiv = document.getElementById('generalStatus'); // Added
    const contentDisplayTextArea = document.getElementById('contentDisplay');

    const apiConfigBtn = document.getElementById('apiConfigBtn');
    const globalConfigBtn = document.getElementById('globalConfigBtn');

    const apiKeyInput = document.getElementById('apiKey');
    const apiModelInput = document.getElementById('apiModel');
    const apiBaseUrlInput = document.getElementById('apiBaseUrl');
    const saveApiConfigBtn = document.getElementById('saveApiConfigBtn');
    const logAreaDiv = document.getElementById('logArea');

    const globalConfigModal = document.getElementById('globalConfigModal');
    const gcWritingStyleSelect = document.getElementById('gcWritingStyle');
    const gcPacingStyleSelect = document.getElementById('gcPacingStyle');
    const gcToneInput = document.getElementById('gcTone');
    const gcTargetChapterWordsInput = document.getElementById('gcTargetChapterWords');
    const gcTargetParagraphWordsInput = document.getElementById('gcTargetParagraphWords');
    const gcDialogueStyleInput = document.getElementById('gcDialogueStyle');
    const gcDescriptionDensitySelect = document.getElementById('gcDescriptionDensity');
    const gcEmotionalIntensitySelect = document.getElementById('gcEmotionalIntensity');
    const gcContinuousThemesTextarea = document.getElementById('gcContinuousThemes');
    const gcMustIncludeElementsTextarea = document.getElementById('gcMustIncludeElements');
    const gcAvoidElementsTextarea = document.getElementById('gcAvoidElements');
    const gcGlobalInstructionsTextarea = document.getElementById('gcGlobalInstructions');
    const saveGlobalConfigModalBtn = document.getElementById('saveGlobalConfigBtn');
    const closeGlobalConfigBtn = document.getElementById('closeGlobalConfigBtn');

    const useSelectedAsRefBtn = document.getElementById('useSelectedAsRefBtn');
    const clearRefBtn = document.getElementById('clearRefBtn');
    const currentReferenceContextP = document.getElementById('currentReferenceContext');

    const autoWriteChapterBtn = document.getElementById('autoWriteChapterBtn');
    const autoWriteAllBtn = document.getElementById('autoWriteAllBtn');
    const autoWriteDelayInput = document.getElementById('autoWriteDelay');
    const stopAutoWriteBtn = document.getElementById('stopAutoWriteBtn');
    const autoWriteProgressDiv = document.getElementById('autoWriteProgress');

    // --- Application State ---
    let currentProject = null;
    let currentDisplayContext = { type: null, chapterIndex: null, paragraphIndex: null };
    let selectedReferenceContext = '';
    let isAutoWriting = false;

    // --- Utility Functions ---
    function setGeneralStatus(message, isError = false) {
        if(generalStatusDiv) {
            generalStatusDiv.textContent = message;
            generalStatusDiv.style.color = isError ? 'red' : 'inherit';
        }
    }

    function logMessage(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.textContent = \`[\${timestamp}] \${message}\`;
        if (type === 'error') logEntry.style.color = 'red';
        else if (type === 'success') logEntry.style.color = 'green';
        logAreaDiv.appendChild(logEntry);
        logAreaDiv.scrollTop = logAreaDiv.scrollHeight;
    }

    async function apiCall(endpoint, method = 'GET', body = null) {
        logMessage(\`API Call: \${method} \${endpoint}\`);
        setGeneralStatus(\`Sending request to \${endpoint}...\`);
        try {
            const options = { method, headers: { 'Content-Type': 'application/json' } };
            if (body) options.body = JSON.stringify(body);
            const response = await fetch(endpoint, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: response.statusText }));
                throw new Error(\`HTTP error \${response.status}: \${errorData.message}\`);
            }
            setGeneralStatus(\`Request to \${endpoint} successful.\`);
            if (response.headers.get('Content-Type')?.includes('text/plain')) return await response.text();
            return await response.json();
        } catch (error) {
            logMessage(\`API Error (\${method} \${endpoint}): \${error.message}\`, 'error');
            setGeneralStatus(\`API Error: \${error.message}\`, true);
            throw error;
        }
    }

    function updateCurrentProjectInfo() {
        if (!currentProject) {
            renderNovelTree(null);
            contentDisplayTextArea.value = 'No project loaded. Select or create a project.';
            contentDisplayTextArea.readOnly = true;
            currentDisplayContext = { type: null, chapterIndex: null, paragraphIndex: null };
        }

        if (currentProject && currentProject.title) {
            currentProjectInfoDiv.textContent = \`Current Project: \${currentProject.title}\`;
            projectTitleInput.value = currentProject.title;
            projectThemeInput.value = currentProject.theme;
            saveProjectBtn.disabled = false;
            exportProjectBtn.disabled = false;
            generateOutlineBtn.disabled = !!currentProject.outline;
            divideChaptersBtn.disabled = !currentProject.outline || !!currentProject.chapters?.length;
            globalConfigBtn.disabled = false;
             // Update default display if context is null (e.g. after load)
            if (currentDisplayContext.type === null) {
                if (currentProject.outline) displayContentForItem('overall_outline');
                else displayContentForItem('novel_title');
            }
        } else {
            currentProjectInfoDiv.textContent = 'Current Project: None';
            projectTitleInput.value = '';
            projectThemeInput.value = '';
            saveProjectBtn.disabled = true;
            exportProjectBtn.disabled = true;
            generateOutlineBtn.disabled = true;
            divideChaptersBtn.disabled = true;
            globalConfigBtn.disabled = true;
        }
        // This button's state depends on the specific item selected in the tree
        writeCurrentParagraphBtn.disabled = !(currentDisplayContext.type === 'paragraph' && currentProject?.chapters[currentDisplayContext.chapterIndex]?.paragraphs[currentDisplayContext.paragraphIndex]);
        autoWriteChapterBtn.disabled = !currentProject?.chapters?.length > 0 || isAutoWriting;
        autoWriteAllBtn.disabled = !currentProject?.chapters?.length > 0 || isAutoWriting; // Conceptual
    }

    function displayContentForItem(itemType, chapterIndex = null, paragraphIndex = null) {
        logMessage(\`Displaying content for: \${itemType} \${chapterIndex !== null ? 'Ch:' + (chapterIndex+1) : ''} \${paragraphIndex !== null ? 'P:' + (paragraphIndex+1) : ''}\`);
        currentDisplayContext = { type: itemType, chapterIndex, paragraphIndex };
        let contentToDisplay = '';
        let currentSelectionPath = itemType;
        contentDisplayTextArea.readOnly = false;

        if (!currentProject) {
            contentDisplayTextArea.value = "No project loaded.";
            currentDisplayContext = { type: null, chapterIndex: null, paragraphIndex: null };
            updateCurrentProjectInfo(); return;
        }

        switch (itemType) {
            case 'novel_title':
                contentToDisplay = \`Title: \${currentProject.title}\nTheme: \${currentProject.theme}\`;
                contentDisplayTextArea.readOnly = true; break;
            case 'overall_outline':
                contentToDisplay = currentProject.outline || "No overall outline yet."; break;
            case 'chapter':
                if (chapterIndex !== null && currentProject.chapters[chapterIndex]) {
                    const ch = currentProject.chapters[chapterIndex];
                    contentToDisplay = \`Chapter \${ch.number || (chapterIndex + 1)}: \${ch.title}\nSummary: \${ch.summary}\nStatus: \${ch.status}\nEst. Words: \${ch.estimated_words}\`;
                    currentSelectionPath += \`_\${chapterIndex}\`;
                    contentDisplayTextArea.readOnly = true;
                } else { contentToDisplay = "Chapter data not found."; } break;
            case 'chapter_outline':
                if (chapterIndex !== null && currentProject.chapters[chapterIndex]) {
                    const ch = currentProject.chapters[chapterIndex];
                    contentToDisplay = ch.outline ? JSON.stringify(ch.outline, null, 2) : "No chapter outline yet.";
                    currentSelectionPath += \`_\${chapterIndex}\`;
                } else { contentToDisplay = "Chapter outline data not found."; } break;
            case 'paragraph':
                if (chapterIndex !== null && paragraphIndex !== null && currentProject.chapters[chapterIndex]?.paragraphs[paragraphIndex]) {
                    contentToDisplay = currentProject.chapters[chapterIndex].paragraphs[paragraphIndex].content || "";
                    currentSelectionPath += \`_\${chapterIndex}_\${paragraphIndex}\`;
                } else { contentToDisplay = "Paragraph data not found."; } break;
            default:
                contentToDisplay = "Select an item from the novel structure to view/edit.";
                contentDisplayTextArea.readOnly = true;
                currentDisplayContext = { type: null, chapterIndex: null, paragraphIndex: null };
        }
        contentDisplayTextArea.value = contentToDisplay;
        updateCurrentProjectInfo();

        document.querySelectorAll('#novelTreeView .tree-item').forEach(item => item.classList.remove('selected'));
        const selectedElement = document.querySelector(\`#novelTreeView .tree-item[data-path="\${currentSelectionPath}"]\`);
        if (selectedElement) selectedElement.classList.add('selected');
    }

    function renderNovelTree(project) {
        novelTreeViewDiv.innerHTML = '';
        if (!project) { novelTreeViewDiv.innerHTML = '<p>No project loaded.</p>'; return; }
        const ulRoot = document.createElement('ul'); ulRoot.classList.add('tree-root');
        const liNovel = document.createElement('li');
        liNovel.textContent = \`📖 \${project.title || 'Untitled Novel'}\`;
        liNovel.classList.add('tree-item', 'novel-title-item');
        liNovel.dataset.path = 'novel_title';
        liNovel.addEventListener('click', () => displayContentForItem('novel_title'));
        ulRoot.appendChild(liNovel);

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

        if (project.chapters && project.chapters.length > 0) {
            const ulChapters = document.createElement('ul');
            project.chapters.forEach((chapter, chIndex) => {
                const liChapter = document.createElement('li');
                const totalWords = chapter.paragraphs?.reduce((sum, p) => sum + (p.word_count || 0), 0) || 0;
                liChapter.textContent = \`📚 Chapter \${chapter.number || (chIndex + 1)}: \${chapter.title} (\${chapter.status}, \${totalWords} words)\`;
                liChapter.classList.add('tree-item', 'chapter-item');
                liChapter.dataset.path = \`chapter_\${chIndex}\`;
                liChapter.addEventListener('click', (e) => { e.stopPropagation(); displayContentForItem('chapter', chIndex); });
                const ulChapterDetails = document.createElement('ul');
                if (chapter.outline && Object.keys(chapter.outline).length > 0) {
                    const liChapterOutline = document.createElement('li');
                    liChapterOutline.textContent = \`📝 Chapter Outline (\${JSON.stringify(chapter.outline).length} chars)\`;
                    liChapterOutline.classList.add('tree-item', 'chapter-outline-item');
                    liChapterOutline.dataset.path = \`chapter_outline_\${chIndex}\`;
                    liChapterOutline.addEventListener('click', (e) => { e.stopPropagation(); displayContentForItem('chapter_outline', chIndex); });
                    ulChapterDetails.appendChild(liChapterOutline);
                } else { /* Placeholder for chapter outline */ }
                if (chapter.paragraphs && chapter.paragraphs.length > 0) {
                    const ulParagraphs = document.createElement('ul');
                    chapter.paragraphs.forEach((para, pIndex) => {
                        const liPara = document.createElement('li');
                        liPara.textContent = \`📄 P\${para.order !== undefined ? para.order + 1 : pIndex + 1}: \${(para.purpose || 'Untitled').substring(0, 30)}... (\${para.status}, \${para.word_count || 0} words)\`;
                        liPara.classList.add('tree-item', 'paragraph-item');
                        liPara.dataset.path = \`paragraph_\${chIndex}_\${pIndex}\`;
                        liPara.addEventListener('click', (e) => { e.stopPropagation(); displayContentForItem('paragraph', chIndex, pIndex); });
                        ulParagraphs.appendChild(liPara);
                    });
                    ulChapterDetails.appendChild(ulParagraphs);
                } else { /* Placeholder for paragraphs */ }
                liChapter.appendChild(ulChapterDetails);
                ulChapters.appendChild(liChapter);
            });
            ulRoot.appendChild(ulChapters);
        } else if (project.title) { /* Placeholder for chapters */ }
        novelTreeViewDiv.appendChild(ulRoot);
        logMessage("Novel structure tree rendered.");
    }

    function updateReferenceContextDisplay() {
        if (currentReferenceContextP) {
            if (selectedReferenceContext) currentReferenceContextP.textContent = \`Ref: \${selectedReferenceContext.substring(0, 70)}...\`;
            else currentReferenceContextP.textContent = 'No reference context set.';
        }
    }
    if(useSelectedAsRefBtn) useSelectedAsRefBtn.addEventListener('click', () => { /* ... (same as provided) ... */ });
    if(clearRefBtn) clearRefBtn.addEventListener('click', () => { /* ... (same as provided) ... */ });

    async function listProjects() { /* ... (same) ... */ }
    async function createNewProject() {
        const title = projectTitleInput.value.trim();
        const theme = projectThemeInput.value.trim();
        if (!title || !theme) { logMessage('Project title and theme are required.', 'error'); return; }
        try {
            currentProject = await apiCall('/api/projects/new', 'POST', { title, theme });
            renderNovelTree(currentProject);
            logMessage(\`New project '\${currentProject.title}' created!\`, 'success');
            setGeneralStatus(\`Project '\${currentProject.title}' created!\`);
            updateCurrentProjectInfo();
            listProjects();
            displayContentForItem('novel_title');
        } catch (error) {}
    }
    async function saveProjectToServer() { /* ... (same as provided, ensure renderNovelTree is called if paragraph status/wordcount changes) ... */ }
    async function loadProjectFromServer() {
        contentDisplayTextArea.value = 'Loading project...'; contentDisplayTextArea.readOnly = true;
        const projectName = loadProjectNameInput.value.trim();
        if (!projectName) { logMessage('Enter project name to load.', 'error'); return; }
        try {
            currentProject = await apiCall(\`/api/projects/load/\${projectName}\`);
            renderNovelTree(currentProject);
            logMessage(\`Project '\${currentProject.title}' loaded!\`, 'success');
            setGeneralStatus(\`Project '\${currentProject.title}' loaded.\`);
            updateCurrentProjectInfo(); // Will call displayContentForItem via logic within
        } catch (error) { currentProject = null; updateCurrentProjectInfo(); }
    }
    async function exportProjectAsText() { /* ... (same) ... */ }

    async function handleGenerateOutline() {
        if (generateOutlineBtn.disabled) return;
        if (!currentProject) { logMessage("No project loaded.", "error"); return; }
        logMessage(\`Generating outline for \${currentProject.title}...\`);
        generateOutlineBtn.textContent = 'Generating...'; generateOutlineBtn.disabled = true;
        try {
            const response = await apiCall(\`/api/novel/\${currentProject.title}/generate-outline\`, 'POST', { stageConfig: {} });
            currentProject = response.project;
            renderNovelTree(currentProject);
            logMessage("Outline generated!", "success");
            updateCurrentProjectInfo(); // Re-evaluates button states
            displayContentForItem('overall_outline');
        } catch (error) { logMessage(\`Outline generation failed: \${error.message}\`, "error");
        } finally { generateOutlineBtn.textContent = '1. Generate Outline'; generateOutlineBtn.disabled = !!currentProject?.outline; }
    }
    async function handleDivideChapters() {
        if (divideChaptersBtn.disabled) return;
        if (!currentProject?.outline) { logMessage("Project outline must exist.", "error"); return; }
        logMessage(\`Dividing chapters for \${currentProject.title}...\`);
        divideChaptersBtn.textContent = 'Dividing...'; divideChaptersBtn.disabled = true;
        try {
            const response = await apiCall(\`/api/novel/\${currentProject.title}/divide-chapters\`, 'POST', { stageConfig: {} });
            currentProject = response.project;
            renderNovelTree(currentProject);
            logMessage("Chapters divided!", "success");
        } catch (error) { logMessage(\`Chapter division failed: \${error.message}\`, "error");
        } finally {
            divideChaptersBtn.textContent = '2. Divide Chapters';
            updateCurrentProjectInfo(); // Re-evaluates button states
        }
    }
    async function handleWriteParagraph() {
        const btn = document.getElementById('writeCurrentParagraphBtn');
        if(btn && btn.disabled) return;

        const { type, chapterIndex, paragraphIndex } = currentDisplayContext;
        if (type !== 'paragraph' || chapterIndex === null || paragraphIndex === null || !currentProject) {
            logMessage("Select a specific paragraph in the tree to write.", "error"); return;
        }
        const paragraph = currentProject.chapters[chapterIndex].paragraphs[paragraphIndex];
        if (paragraph.status === '已完成' && paragraph.content.trim() !== '') {
            if (!confirm("This paragraph seems completed. Overwrite?")) return;
        }
        logMessage(\`Requesting to write Ch:\${chapterIndex+1}, P:\${paragraphIndex+1}...\`);
        if(btn) { btn.textContent = 'Writing...'; btn.disabled = true; }
        try {
            const body = { stageConfig: {}, selectedContext: selectedReferenceContext };
            const response = await apiCall(\`/api/novel/\${currentProject.title}/chapters/\${chapterIndex}/paragraphs/\${paragraphIndex}/write\`, 'POST', body);
            currentProject = response.project;
            logMessage(\`Paragraph Ch:\${chapterIndex+1}, P:\${paragraphIndex+1} written successfully!\`, "success");
            renderNovelTree(currentProject);
            displayContentForItem('paragraph', chapterIndex, paragraphIndex);
        } catch (error) {
            logMessage(\`Paragraph writing failed: \${error.message}\`, "error");
            if(currentProject.chapters[chapterIndex]?.paragraphs[paragraphIndex]){
                currentProject.chapters[chapterIndex].paragraphs[paragraphIndex].status = "錯誤";
                renderNovelTree(currentProject);
            }
        } finally {
            if(btn) { btn.textContent = 'Write/Rewrite Selected Paragraph'; btn.disabled = false; }
            updateCurrentProjectInfo(); // Re-evaluates button states
        }
    }

    async function loadAndDisplayApiConfig() { /* ... (same) ... */ }
    async function saveApiConfiguration() { /* ... (same) ... */ }
    function openGlobalConfigModal() { /* ... (same) ... */ }
    function applyGlobalConfigToProject() { /* ... (same) ... */ }

    async function autoWriteParagraphs(chapterIndex, startParagraphIndex = 0) {
        if (!currentProject || chapterIndex < 0 || chapterIndex >= currentProject.chapters.length) {
            logMessage("Invalid chapter for auto-writing.", "error"); isAutoWriting = false; return;
        }
        const chapter = currentProject.chapters[chapterIndex];
        const delayMs = (parseInt(autoWriteDelayInput.value) || 2) * 1000;
        autoWriteChapterBtn.textContent = 'Auto-Writing...';

        for (let pIndex = startParagraphIndex; pIndex < chapter.paragraphs.length; pIndex++) {
            if (!isAutoWriting) {
                logMessage("Auto-writing stopped by user.", "warn"); autoWriteProgressDiv.textContent = "Stopped.";
                autoWriteChapterBtn.textContent = 'Auto Write Current Chapter'; return;
            }
            const paragraph = chapter.paragraphs[pIndex];
            if (paragraph.status === '已完成' && paragraph.content.trim() !== '') {
                autoWriteProgressDiv.textContent = \`Ch:\${chapterIndex+1}, P:\${pIndex+1} - Skipped.\`;
                logMessage(\`Skipping Ch:\${chapterIndex+1}, P:\${pIndex+1} (completed).\`, "info"); continue;
            }
            autoWriteProgressDiv.textContent = \`Writing Ch:\${chapterIndex+1}, P:\${pIndex+1}...\`;
            currentDisplayContext = { type: 'paragraph', chapterIndex, paragraphIndex: pIndex };
            try {
                const body = { stageConfig: {}, selectedContext: selectedReferenceContext };
                const response = await apiCall(\`/api/novel/\${currentProject.title}/chapters/\${chapterIndex}/paragraphs/\${pIndex}/write\`, 'POST', body);
                currentProject = response.project;
                logMessage(\`Auto-wrote Ch:\${chapterIndex+1}, P:\${pIndex+1}.\`, "success");
                renderNovelTree(currentProject); displayContentForItem('paragraph', chapterIndex, pIndex); // updateCurrentProjectInfo is called by displayContentForItem
            } catch (error) {
                logMessage(\`Auto-writing Ch:\${chapterIndex+1}, P:\${pIndex+1} failed: \${error.message}\`, "error");
                autoWriteProgressDiv.textContent = \`Error Ch:\${chapterIndex+1}, P:\${pIndex+1}. Stopping.\`;
                if(currentProject.chapters[chapterIndex]?.paragraphs[pIndex]){ currentProject.chapters[chapterIndex].paragraphs[pIndex].status = "錯誤"; renderNovelTree(currentProject); }
                isAutoWriting = false; autoWriteChapterBtn.textContent = 'Auto Write Current Chapter'; return;
            }
            if (pIndex < chapter.paragraphs.length - 1 && isAutoWriting) {
                autoWriteProgressDiv.textContent = \`Finished Ch:\${chapterIndex+1}, P:\${pIndex+1}. Waiting \${delayMs/1000}s...\`;
                await new Promise(resolve => setTimeout(resolve, delayMs));
            }
        }
        autoWriteProgressDiv.textContent = \`Chapter \${chapterIndex+1} auto-writing finished.\`;
        logMessage(\`Chapter \${chapterIndex+1} auto-writing finished.\`, 'success');
        isAutoWriting = false; autoWriteChapterBtn.textContent = 'Auto Write Current Chapter';
        if(stopAutoWriteBtn) stopAutoWriteBtn.disabled = true;
        updateCurrentProjectInfo();
    }

    // Initialize event listeners
    listProjectsBtn.addEventListener('click', listProjects);
    newProjectBtn.addEventListener('click', createNewProject);
    saveProjectBtn.addEventListener('click', saveProjectToServer);
    loadProjectBtn.addEventListener('click', loadProjectFromServer);
    exportProjectBtn.addEventListener('click', exportProjectAsText);
    generateOutlineBtn.addEventListener('click', handleGenerateOutline);
    divideChaptersBtn.addEventListener('click', handleDivideChapters);
    apiConfigBtn.addEventListener('click', loadAndDisplayApiConfig);
    saveApiConfigBtn.addEventListener('click', saveApiConfiguration);
    globalConfigBtn.addEventListener('click', openGlobalConfigModal);
    saveGlobalConfigModalBtn.addEventListener('click', applyGlobalConfigToProject);
    closeGlobalConfigBtn.addEventListener('click', () => { globalConfigModal.style.display = 'none'; });
    if(writeCurrentParagraphBtn) writeCurrentParagraphBtn.addEventListener('click', handleWriteParagraph);

    autoWriteChapterBtn.addEventListener('click', async () => { /* ... (same as provided, ensure button state updates) ... */ });
    autoWriteAllBtn.addEventListener('click', () => { logMessage("Auto Write All - Not fully implemented.", "warn"); });
    stopAutoWriteBtn.addEventListener('click', () => { /* ... (same as provided, ensure button state updates) ... */ });

    updateCurrentProjectInfo();
    listProjects();
    updateReferenceContextDisplay();
    if(stopAutoWriteBtn) stopAutoWriteBtn.disabled = true;
});
