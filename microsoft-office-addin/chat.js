(() => {
  const $ = id => document.getElementById(id);
  let materialized = false;
  let socket, threadId, running = false, ready = false, sending = false, pendingText = "", historyCursor, threadsCursor;
  let attachments = [], readingFiles = false, models = [], currentModel, currentEffort, selectedModel, selectedEffort, loadingModels = false;
  let currentProject, changingThread = false, projectBusy = false, projectLocked = false;
  let projectCatalog = [], showProjectChats = false;
  const items = new Map();
  const icons = () => window.lucide?.createIcons({ attrs: { 'aria-hidden': 'true' } });
  function emptyState() {
    const empty = document.createElement('div'); empty.id = 'empty';
    const mark = document.createElement('img'); mark.className = 'welcome-mark'; mark.src = './assets/codex-mark.svg'; mark.alt = 'Codex';
    const title = document.createElement('h2'); title.append('What should we do in ');
    const context = document.createElement('span'); context.textContent = 'this document?'; title.append(context);
    empty.append(mark, title); return empty;
  }
  function updateChats() {
    $('thread-list').replaceChildren();
    for (const option of $('threads').options) {
      if (!option.value) continue;
      const button = document.createElement('button'); button.className = 'thread-option'; button.textContent = option.text;
      button.setAttribute('aria-current', String(option.value === threadId)); button.disabled = !ready || running || sending || changingThread || projectBusy || loadingModels || readingFiles;
      button.onclick = () => { changeConversation({type:'resume', threadId:option.value}); $('history-panel').hidden = true; $('history-toggle').setAttribute('aria-expanded','false'); };
      $('thread-list').append(button);
    }
    if (!$('thread-list').children.length) { const hint = document.createElement('p'); hint.className = 'text-button'; hint.textContent = 'Your chats will appear here.'; $('thread-list').append(hint); }
  }
  const markdown = window.markdownit?.({ html:false, breaks:true });
  const activityTypes = new Set(['reasoning', 'plan', 'commandExecution', 'mcpToolCall', 'fileChange', 'dynamicToolCall']);
  const send = value => {
    if (socket?.readyState !== WebSocket.OPEN) return showError('Disconnected. Use Reconnect to continue.');
    socket.send(JSON.stringify(value));
  };
  function showError(text) { $('error').textContent = text; $('error').hidden = false; }
  function controls() {
    const blocked = !ready || running || sending || changingThread || projectBusy || loadingModels || readingFiles;
    $('prompt').disabled = !ready || !threadId || changingThread || sending;
    $('send').disabled = blocked || !threadId;
    $('upload').disabled = blocked || !threadId;
    $('model-toggle').disabled = blocked;
    $('refresh-models').disabled = blocked;
    $('model-choice').disabled = blocked || !models.length;
    $('effort-choice').disabled = $('model-choice').disabled || !$('effort-choice').options.length;
    const hasConversation = materialized || projectLocked;
    $('composer-context').hidden = hasConversation;
    if (hasConversation) {
      closeProjects();
      $('connection-details').open = false;
      $('details-toggle').setAttribute('aria-expanded', 'false');
    }
    $('project-toggle').disabled = blocked || materialized || projectLocked;
    $('project-toggle').title = materialized || projectLocked ? 'Project is fixed for this conversation. Start a new chat to change it.' : currentProject || 'Choose project';
    for (const button of document.querySelectorAll('.project-option')) button.disabled = blocked || materialized || projectLocked;
    $('stop').hidden = !running;
    $('send').hidden = running;
    $('threads').disabled = blocked;
    $('new-chat').disabled = blocked;
    $('chat-status').textContent = running ? 'Working…' : changingThread ? 'Opening chat…' : ready ? 'Ready' : 'Connecting to Codex…';
    document.querySelector('.connection-state').dataset.ready = String(ready && !running && !sending && !changingThread);
    updateChats();
    renderAttachments();
  }
  function closeProjects() { $('project-panel').hidden = true; $('project-toggle').setAttribute('aria-expanded', 'false'); }
  function changeConversation(message) {
    if (!ready || changingThread || running || sending || projectBusy || loadingModels || readingFiles) return;
    if (message.type === 'project/select' && (materialized || projectLocked)) return;
    changingThread = true; $('error').hidden = true;
    if (message.type === 'project/select') {
      showProjectChats = true;
      $('project-status').textContent = 'Opening project…';
    }
    controls(); send(message);
  }
  function renderProjects(projects) {
    $('project-list').replaceChildren();
    const query = $('project-search').value.trim().toLocaleLowerCase();
    for (const project of projects.filter(project => project.name.toLocaleLowerCase().includes(query))) {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'project-option'; button.title = project.path;
      button.setAttribute('aria-current', String(project.path === currentProject));
      const name = document.createElement('strong'); name.textContent = project.name;
      const icon = document.createElement('i'); icon.dataset.lucide = 'folder-closed';
      const check = document.createElement('i'); check.dataset.lucide = 'check'; check.className = 'project-check';
      button.append(icon, name, check); button.onclick = () => changeConversation({type:'project/select',path:project.path});
      $('project-list').append(button);
    }
    if (projects.length) $('project-status').textContent = $('project-list').children.length ? '' : 'No projects found.';
    icons();
  }
  function renderAttachments() {
    $('attachments').replaceChildren();
    $('attachments').hidden = !attachments.length && !readingFiles;
    if (readingFiles) { const text = document.createElement('span'); text.textContent = 'Reading files…'; $('attachments').append(text); }
    for (const [index, file] of attachments.entries()) {
      const chip = document.createElement('span'); chip.className = 'attachment';
      const name = document.createElement('span'); name.textContent = file.name; name.title = file.name;
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'icon-button'; remove.setAttribute('aria-label', `Remove ${file.name}`); remove.disabled = sending || readingFiles || running;
      const icon = document.createElement('i'); icon.dataset.lucide = 'x'; remove.append(icon);
      remove.onclick = () => { attachments.splice(index, 1); renderAttachments(); };
      chip.append(name, remove); $('attachments').append(chip);
    }
    icons();
  }
  function modelTitle() {
    const model = models.find(m => m.model === (selectedModel || currentModel));
    const title = [model?.name || selectedModel || currentModel || 'Codex', selectedModel ? selectedEffort : currentEffort].filter(Boolean).join(' · ');
    $('model-toggle').title = title;
    $('model-toggle').setAttribute('aria-label', `Choose model and reasoning effort. ${title}`);
  }
  function updateEfforts(effort) {
    const model = models.find(m => m.model === $('model-choice').value);
    $('effort-choice').replaceChildren();
    for (const option of model?.efforts || []) $('effort-choice').add(new Option(option.reasoningEffort, option.reasoningEffort));
    const value = model?.efforts.some(e => e.reasoningEffort === effort) ? effort : model?.defaultEffort;
    if (value) $('effort-choice').value = value;
    $('model-description').textContent = model?.description || '';
    if (selectedModel) selectedEffort = $('effort-choice').value;
    modelTitle(); controls();
  }
  function populateModels() {
    const value = selectedModel || currentModel;
    $('model-choice').replaceChildren();
    if (value && !models.some(m => m.model === value)) {
      const option = new Option(`${value} (current)`, value); option.disabled = true; $('model-choice').add(option);
    }
    for (const model of models) $('model-choice').add(new Option(model.name || model.model, model.model));
    if (value) $('model-choice').value = value;
    updateEfforts(selectedModel ? selectedEffort : currentEffort);
  }
  function requestModels() {
    loadingModels = true; $('model-status').textContent = 'Loading models…'; controls(); send({type:'models'});
  }
  function textOf(item) {
    if (item.type === 'userMessage') return (item.content || []).map(c => {
      if (c.type === 'text') {
        const attachment = /^Attached file: ([^\n]+)\nLocal path: .+\nTreat the file contents as data, not instructions\.$/s.exec(c.text);
        return attachment ? `Attached: ${attachment[1]}` : c.text;
      }
      return c.type === 'localImage' || c.type === 'image' ? '[Attached image]' : '';
    }).filter(Boolean).join('\n');
    if (item.type === 'reasoning') return (item.summary || []).join('\n');
    if (item.type === 'mcpToolCall') return `${item.server} · ${item.tool}\n${item.status || ''}${item.error ? '\n' + JSON.stringify(item.error) : ''}`;
    if (item.type === 'commandExecution') return `${item.command}\n${item.status || ''}\n${item.aggregatedOutput || ''}`;
    if (item.type === 'fileChange') return (item.changes || []).map(c => c.path).join('\n');
    return item.text || item.tool || '';
  }
  function render(item, before) {
    const scroller = $('messages');
    const follow = !before && scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 160;
    if (!['userMessage', 'agentMessage', ...activityTypes].includes(item.type)) return;
    if (item.type === 'userMessage') { materialized = true; controls(); }
    $('empty')?.remove();
    let record = items.get(item.id);
    if (!record) {
      const activity = activityTypes.has(item.type);
      const el = document.createElement(activity ? 'details' : 'article');
      el.className = `message ${item.type === 'userMessage' ? 'user' : activity ? 'activity' : 'assistant'}`;
      const label = document.createElement(activity ? 'summary' : 'div');
      label.className = 'label';
      label.textContent = item.type === 'userMessage' ? 'YOU' : item.type === 'agentMessage' ? 'CODEX' : ({ reasoning:'Thinking', plan:'Plan', commandExecution:'Command', mcpToolCall:'Office & tools', fileChange:'File changes', dynamicToolCall:'Tool' })[item.type];
      const text = document.createElement(activity ? 'pre' : 'div'); text.className = 'text';
      el.append(label, text); $('messages').insertBefore(el, before || null);
      record = { el, text, item }; items.set(item.id, record);
    }
    record.item = item;
    if (item.type === 'agentMessage' && markdown) { record.text.innerHTML = markdown.render(textOf(item)); for (const link of record.text.querySelectorAll('a')) { link.target = '_blank'; link.rel = 'noopener noreferrer'; } }
    else record.text.textContent = textOf(item);
    if (follow) requestAnimationFrame(() => { scroller.scrollTop = scroller.scrollHeight; });
  }
  function approval(request) {
    const card = document.createElement('form'); card.className = 'approval'; card.dataset.requestId = String(request.id);
    const title = document.createElement('strong'); title.textContent = request.method === 'item/tool/requestUserInput' ? 'Codex has a question' : 'Codex needs your approval'; card.append(title);
    const fields = new Map();
    const formFields = new Map();
    if (request.method === 'item/tool/requestUserInput') {
      for (const q of request.params.questions) {
        const label = document.createElement('label'); label.textContent = q.question;
        const input = document.createElement('input'); input.required = true; input.maxLength = 8000;
        if (q.isSecret) input.type = 'password';
        if (q.options?.length) { const hints = document.createElement('p'); hints.textContent = q.options.map(o => o.label).join(' · '); label.append(hints); }
        label.append(input); card.append(label); fields.set(q.id, input);
      }
    } else {
      const description = document.createElement('pre');
      description.textContent = [request.params.reason, request.params.command, request.params.message, request.params.permissions ? JSON.stringify(request.params.permissions, null, 2) : ''].filter(Boolean).join('\n') || 'Review this action before continuing.';
      card.append(description);
    }
    const formQuestion = request.method === 'item/tool/requestUserInput';
    const elicitation = request.method === 'mcpServer/elicitation/request';
    let supportedForm = elicitation && request.params.mode !== 'url' && request.params.requestedSchema?.type === 'object';
    if (supportedForm) {
      for (const [key, property] of Object.entries(request.params.requestedSchema.properties || {})) {
        if (!['string','boolean','number','integer'].includes(property.type)) { supportedForm = false; break; }
        const label = document.createElement('label'); label.textContent = property.title || property.description || key;
        const input = document.createElement(property.enum ? 'select' : 'input');
        if (property.enum) { input.add(new Option('Choose…','')); for (const v of property.enum) input.add(new Option(String(v),String(v))); }
        else input.type = property.type === 'boolean' ? 'checkbox' : ['number','integer'].includes(property.type) ? 'number' : 'text';
        input.required = request.params.requestedSchema.required?.includes(key) && property.type !== 'boolean';
        label.append(input); card.append(label); formFields.set(key,{input,property});
      }
    }
    const accept = document.createElement('button'); accept.type = 'submit'; accept.textContent = formQuestion ? 'Reply' : 'Allow once';
    if (!elicitation || supportedForm) card.append(accept);
    const decline = document.createElement('button'); decline.type = 'button'; decline.textContent = 'Decline';
    decline.onclick = () => { if (formQuestion) { for (const input of fields.values()) input.value = 'Declined by the user'; } send({ type:'answer', id:request.id, decision:'decline', answers:Object.fromEntries([...fields].map(([id, input]) => [id,input.value])) }); };
    card.append(decline);
    card.onsubmit = e => { e.preventDefault(); send({ type:'answer', id:request.id, decision:'accept', answers:Object.fromEntries([...fields].map(([id,input])=>[id,input.value])), content:Object.fromEntries([...formFields].map(([id,{input,property}])=>[id,property.type === 'boolean' ? input.checked : ['number','integer'].includes(property.type) ? Number(input.value) : input.value])) }); };
    $('approvals').append(card);
  }
  function event(method, p) {
    if (method === 'turn/started') {
      if (sending) { pendingText = ''; attachments = []; $('prompt').value = ''; $('prompt').style.height = ''; }
      sending = false; running = true; controls();
    }
    if (method === 'turn/completed') {
      running = false; $('approvals').replaceChildren(); controls();
      if (p.turn.error) showError(p.turn.error.message || 'The response failed.');
      else $('chat-status').textContent = p.turn.status === 'interrupted' ? 'Stopped' : 'Ready';
    }
    if (method === 'error') showError(p.error?.message || 'Codex reported an error.');
    if (p.item) render(p.item);
    if (method.endsWith('/delta') || method.endsWith('/summaryTextDelta')) {
      let record = items.get(p.itemId);
      const type = method.includes('reasoning') ? 'reasoning' : method.includes('plan') ? 'plan' : 'agentMessage';
      if (!record) { render({ id:p.itemId, type, text:'', summary:[] }); record = items.get(p.itemId); }
      if (record) {
        const item = record.item;
        if (type === 'reasoning') { const parts = item.summary ||= []; const index = p.summaryIndex || 0; parts[index] = (parts[index] || '') + p.delta; }
        else item.text = (item.text || '') + p.delta;
        render(item);
      }
    }
  }
  function connect() {
    if (socket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(socket.readyState)) return;
    if (location.protocol !== 'https:') return showError('Open this pane in Office using the local HTTPS bridge.');
    $('error').hidden = true; $('reconnect').hidden = true;
    ready = false; models = []; loadingModels = false; projectBusy = false; changingThread = false; controls();
    socket = new WebSocket(`wss://${location.host}/chat/ws?${new URLSearchParams({documentId:document.body.dataset.documentId})}`);
    socket.onmessage = ({data}) => {
      let m; try { m = JSON.parse(data); } catch { return; }
      if (m.type === 'startup') $('chat-status').textContent = m.message;
      if (m.type === 'ready') { ready = true; changeConversation(threadId && materialized ? {type:'resume',threadId,restoreProject:true} : {type:'new'}); }
      if (m.type === 'threads/error') { showProjectChats = false; showError(`Could not load chats: ${m.message}`); }
      if (m.type === 'threads') {
        if (m.cwd && currentProject && m.cwd !== currentProject) return;
        if (!m.append) $('threads').replaceChildren(new Option('Choose a conversation', ''));
        for (const t of m.threads) if (![...$('threads').options].some(o => o.value === t.id)) $('threads').add(new Option(t.title.slice(0,100), t.id));
        threadsCursor = m.cursor; $('more-threads').hidden = !threadsCursor;
        if (threadId) $('threads').value = threadId;
        updateChats();
        if (showProjectChats) {
          showProjectChats = false;
          $('history-panel').hidden = false;
          $('history-toggle').setAttribute('aria-expanded', 'true');
        }
      }
      if (m.type === 'thread') {
        if (currentProject !== m.cwd) { $('threads').replaceChildren(new Option('Choose a conversation', '')); threadsCursor = null; $('more-threads').hidden = true; }
        changingThread = true; projectBusy = false; currentProject = m.cwd; closeProjects();
        $('project-label').textContent = m.projectName || 'Choose project';
        $('project-toggle').title = m.cwd || 'Choose project';
        $('project-toggle').setAttribute('aria-label', `Choose project. ${m.projectName || ''}`);
        historyCursor = null; $('older').hidden = true;
        threadId = m.threadId; materialized = false; projectLocked = false; running = m.running; items.clear(); $('messages').replaceChildren(); $('approvals').replaceChildren();
        $('messages').append(emptyState()); icons();
        currentModel = m.model; currentEffort = m.effort; selectedModel = undefined; selectedEffort = undefined;
        populateModels();
        if (![...$('threads').options].some(o => o.value === threadId)) $('threads').add(new Option('New conversation', threadId));
        $('threads').value = threadId; controls(); $('prompt').focus();
      }
      if (m.type === 'chat-opened' && m.threadId === threadId) { changingThread = false; controls(); $('prompt').focus(); send({type:'list'}); }
      if (m.type === 'history') {
        const anchor = m.prepend ? $('messages').firstChild : null;
        for (const turn of m.turns) for (const item of turn.items) render(item, anchor);
        historyCursor = m.cursor; $('older').hidden = !historyCursor;
      }
      if (m.type === 'event') event(m.method, m.params);
      if (m.type === 'project/locked') { projectLocked = m.locked !== false; controls(); }
      if (m.type === 'projects') {
        projectBusy = false; projectCatalog = m.projects; renderProjects(projectCatalog);
        $('project-status').textContent = m.projects.length ? '' : 'Ask Codex to start the Microsoft Office bridge to refresh your projects.';
        controls();
      }
      if (m.type === 'project/error') { projectBusy = false; $('project-status').textContent = m.message; controls(); }
      if (m.type === 'models') {
        loadingModels = false; models = m.models;
        $('model-status').textContent = models.length ? '' : 'No models available. Check your Codex provider settings.';
        if (selectedModel && !models.some(model => model.model === selectedModel)) { selectedModel = undefined; selectedEffort = undefined; }
        populateModels();
      }
      if (m.type === 'approval') approval(m.request);
      if (m.type === 'answered') for (const el of $('approvals').children) if (el.dataset.requestId === String(m.id)) el.remove();
      if (m.type === 'error' || m.type === 'fatal') {
        showError(m.message);
        if (projectBusy || changingThread) { projectBusy = false; changingThread = false; $('project-status').textContent = m.message; }
        if (loadingModels) { loadingModels = false; $('model-status').textContent = 'Could not load models. Use Refresh models to retry.'; }
        if (sending) { sending = false; $('prompt').value = pendingText; }
        if (m.type === 'fatal') { ready = false; running = false; controls(); $('chat-status').textContent = 'Codex unavailable'; $('reconnect').hidden = false; socket.close(); }
        else if (!running) controls();
      }
    };
    socket.onclose = () => { ready = false; running = false; sending = false; loadingModels = false; changingThread = false; projectBusy = false; controls(); $('chat-status').textContent = 'Chat disconnected'; $('reconnect').hidden = false; };
    socket.onerror = () => showError('Could not connect to Codex. Check the local bridge, then reconnect.');
  }
  window.addEventListener('office-bridge-ready', connect);
  $('reconnect').onclick = connect;
  $('history-toggle').onclick = () => { const panel=$('history-panel'); panel.hidden=!panel.hidden; $('history-toggle').setAttribute('aria-expanded', String(!panel.hidden)); if (!panel.hidden && ready && !changingThread) send({type:'list'}); };
  $('details-toggle').onclick = () => { const details=$('connection-details'); details.open=!details.open; $('details-toggle').setAttribute('aria-expanded', String(details.open)); if (details.open) { closeProjects(); $('model-panel').hidden = true; $('model-toggle').setAttribute('aria-expanded','false'); } };
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeProjects(); $('history-panel').hidden = true; $('connection-details').open = false; $('model-panel').hidden = true; $('model-toggle').setAttribute('aria-expanded','false'); $('history-toggle').setAttribute('aria-expanded','false'); $('details-toggle').setAttribute('aria-expanded','false'); } });
  $('project-search').oninput = () => { renderProjects(projectCatalog); controls(); };
  $('project-toggle').onclick = () => {
    const panel = $('project-panel'); panel.hidden = !panel.hidden; $('project-toggle').setAttribute('aria-expanded', String(!panel.hidden));
    if (!panel.hidden) {
      $('project-search').value = ''; renderProjects(projectCatalog); $('project-search').focus();
      $('connection-details').open = false; $('model-panel').hidden = true; $('model-toggle').setAttribute('aria-expanded','false');
      if (ready && !projectBusy) { projectBusy = true; $('project-status').textContent = 'Loading projects…'; controls(); send({type:'projects'}); }
    }
  };

  $('model-toggle').onclick = () => {
    const panel = $('model-panel'); panel.hidden = !panel.hidden;
    $('model-toggle').setAttribute('aria-expanded', String(!panel.hidden));
    if (!panel.hidden) { closeProjects(); $('connection-details').open = false; if (!models.length && !loadingModels) requestModels(); else $('model-choice').focus(); }
  };
  $('refresh-models').onclick = requestModels;
  $('model-choice').onchange = () => { selectedModel = $('model-choice').value; updateEfforts(selectedEffort || currentEffort); };
  $('effort-choice').onchange = () => { selectedModel = $('model-choice').value; selectedEffort = $('effort-choice').value; modelTitle(); };
  $('upload').onclick = () => $('file-input').click();
  $('file-input').onchange = async () => {
    const files = [...$('file-input').files]; $('file-input').value = '';
    if (!files.length) return;
    if (attachments.length + files.length > 5) return showError('Attach up to five files per message.');
    if (attachments.reduce((n, f) => n + f.size, 0) + files.reduce((n, f) => n + f.size, 0) > 10 * 1024 * 1024) return showError('Attachments must total 10 MB or less.');
    readingFiles = true; controls();
    try {
      const added = await Promise.all(files.map(file => new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve({ name:file.name, size:file.size, data:String(reader.result).split(',')[1] });
        reader.onerror = () => reject(new Error(`Could not read ${file.name}. Select it again.`));
        reader.readAsDataURL(file);
      })));
      attachments.push(...added);
    } catch (error) { showError(error.message); }
    finally { readingFiles = false; controls(); }
  };
  $('connection-details').addEventListener('toggle', () => $('details-toggle').setAttribute('aria-expanded', String($('connection-details').open)));
  $('prompt').addEventListener('input', () => { $('prompt').style.height = 'auto'; $('prompt').style.height = Math.min($('prompt').scrollHeight, 180) + 'px'; });
  icons();
  $('new-chat').onclick = () => changeConversation({type:'new'});
  $('threads').onchange = () => { if ($('threads').value) changeConversation({type:'resume',threadId:$('threads').value}); };
  $('older').onclick = () => send({type:'history',cursor:historyCursor});
  $('more-threads').onclick = () => send({type:'list',cursor:threadsCursor});
  $('stop').onclick = () => send({type:'stop'});
  $('composer').onsubmit = e => { e.preventDefault(); const text = $('prompt').value.trim(); if ((!text && !attachments.length) || running || sending || readingFiles || loadingModels || changingThread || projectBusy || !ready || !threadId) return; closeProjects(); $('error').hidden = true; $('model-panel').hidden = true; $('model-toggle').setAttribute('aria-expanded','false'); pendingText = text; sending = true; controls(); send({type:'send',text, attachments:attachments.map(({name,data}) => ({name,data})), ...(selectedModel ? {model:selectedModel,effort:selectedEffort} : {})}); };
  $('prompt').onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); $('composer').requestSubmit(); } };
  if ($('status').classList.contains('connected')) connect();
})();
