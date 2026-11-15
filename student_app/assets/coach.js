/* Local coach presentation. All durable state and all arithmetic live on the server.
   This file shares app.js's classic-script bindings; it has no external dependencies. */
(() => {
  'use strict';
  const contexts = new Map();
  let active = null, timer = null, finishToken = '', shuttingDown = false;
  const panel = document.createElement('section');
  panel.className = 'coach-content'; panel.setAttribute('aria-label', t('coach_title'));
  panel.innerHTML = '<p class="coach-intro" id="coach-intro"></p>' +
    '<p id="coach-notice" class="coach-notice"></p>' +
    '<ol id="coach-history" class="coach-history" aria-label="Conversation"></ol>' +
    '<div id="coach-empty" class="coach-empty"><p></p><div class="coach-examples"></div></div>' +
    '<div id="coach-pending" class="coach-pending" role="status" hidden><span class="coach-pending-mark" aria-hidden="true">…</span><div><strong></strong><p></p></div></div>' +
    '<form id="coach-form"><label for="coach-input" id="coach-input-label"></label><textarea id="coach-input" rows="3" maxlength="1200" aria-describedby="coach-save-status"></textarea>' +
    '<div class="coach-compose-footer"><span id="coach-save-status" role="status"></span><button id="coach-send" type="submit" class="primary"></button></div></form>' +
    '<div id="coach-error" class="coach-error" role="alert" hidden><p></p><button id="coach-reload" type="button" class="text-button"></button></div>' +
    '<p id="coach-announcement" class="sr-only" role="status" aria-live="polite"></p>';
  $('exercise-coach-slot').append(panel);

  const input = $('coach-input');
  const identityFor = mode => ({student, mode, language:apiLanguage(), ...(session ? {session} : {})});
  const keyFor = identity => JSON.stringify([identity.student, identity.mode, identity.session || '', identity.language]);
  const shown = () => !$('workspace').hidden && (document.body.dataset.view === 'numbers' ||
    document.body.dataset.view === 'practice' && $('coach-panel').open);
  const element = (tag, className, text) => { const node=document.createElement(tag); node.className=className; if (text !== undefined) node.textContent=text; return node; };
  const errorMessage = (state, key) => { state.error=key; if (active === state) renderStatus(); };

  async function request(path, identity, extra = {}) {
    const abort = new AbortController(), timeout = setTimeout(() => abort.abort(), 12000);
    try {
      const response = await fetch('/api/' + path, {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({...identity, ...extra}), signal:abort.signal});
      const data = await response.json();
      if (!response.ok) { const error=new Error(data.error || 'Request failed'); error.apiMessage=data.error; throw error; }
      return data;
    } finally { clearTimeout(timeout); }
  }

  function schedulePoll() {
    clearTimeout(timer);
    if ((active?.pending || active?.modelBusy) && shown() && !document.hidden) {
      const state=active;
      timer=setTimeout(() => load(state, true), 1500);
    }
  }

  function accept(state, data, useDraft = false) {
    state.turns = data.turns || []; state.pending=!!data.pending; state.modelBusy=!!data.busy; state.storage=data.storage;
    state.revision=Math.max(state.revision, data.draft_revision || data.revision || 0);
    if (useDraft && !state.dirty) state.draft=data.draft || '';
    state.loaded=true; state.error='';
    if (data.assistance?.session === session && student === state.identity.student) {
      canReveal=!!data.assistance.can_reveal;
      if (openData) openData.hints=data.assistance.hints;
      syncControls();
    }
    if (active === state) { renderConversation(); renderStatus(); schedulePoll(); }
  }

  async function load(state, polling = false) {
    if (!state || state.loading || shuttingDown) return;
    state.loading=true; renderStatus();
    try {
      const data=await request('coach-history', state.identity);
      const wasLoaded=state.loaded;
      accept(state, data, !wasLoaded);
      if (active === state && !wasLoaded) input.value=state.draft;
    } catch {
      errorMessage(state, 'coach_load_failed');
    } finally {
      state.loading=false;
      if (active === state) { renderStatus(); if (!state.error || polling) schedulePoll(); }
    }
  }

  function switchContext(mode) {
    clearTimeout(timer);
    if (!student) return;
    const identity=identityFor(mode), key=keyFor(identity);
    if (active?.key === key) { renderCopy(); schedulePoll(); return; }
    if (active) void flushDraft(active).catch(() => {});
    if (!contexts.has(key)) contexts.set(key, {key,identity,turns:[],pending:false,loaded:false,loading:false,
      draft:'',revision:0,dirty:false,saveState:'',error:'',request:null,sending:false,saveChain:Promise.resolve()});
    active=contexts.get(key);
    input.value=active.draft;
    $('coach-announcement').textContent='';
    renderCopy(); renderConversation(); renderStatus();
    void load(active);
  }

  function changeDraft() {
    if (!active) return;
    active.draft=input.value; active.dirty=true; active.saveState='saving';
    active.revision=Math.max(Date.now(), active.revision + 1);
    clearTimeout(active.saveTimer);
    const state=active;
    state.saveTimer=setTimeout(() => flushDraft(state).catch(() => {}), 500);
    renderStatus();
  }

  function flushDraft(state = active) {
    if (!state) return Promise.resolve();
    clearTimeout(state.saveTimer);
    if (!state.dirty) return state.saveChain;
    const draft=state.draft, revision=state.revision;
    state.saveChain=state.saveChain.catch(() => {}).then(async () => {
      // A more recent save may already have acknowledged this revision.
      if (revision < (state.savedRevision || 0)) return;
      try {
        const data=await request('coach-draft', state.identity, {draft, revision});
        state.savedRevision=revision; state.storage=data.storage;
        if (state.revision === revision) { state.dirty=false; state.saveState='saved'; }
      } catch (error) {
        state.saveState='failed';
        throw error;
      } finally { if (active === state) renderStatus(); }
    });
    return state.saveChain;
  }

  function sourceLabel(turn) {
    return t(turn.calculation_status === 'invalid' ? 'coach_source_invalid' : turn.source === 'verified_arithmetic' ? 'coach_source_math' : turn.source === 'local_model_generated' ? 'coach_source_model' : 'coach_source_prepared');
  }

  function renderConversation() {
    if (!active) return;
    const list=$('coach-history'), oldSignature=list.dataset.signature;
    const signature=JSON.stringify([active.key, uiLang, active.turns]);
    if (oldSignature === signature) return;
    const wasNearBottom=list.scrollHeight-list.scrollTop-list.clientHeight < 90;
    const fragment=document.createDocumentFragment();
    active.turns.forEach(turn => {
      const item=element('li','coach-turn'); item.dataset.turnId=turn.id;
      const thought=element('div','coach-student');
      thought.append(element('strong','coach-speaker',t('coach_you')), element('p','coach-message',turn.student_message));
      item.append(thought);
      if (turn.tutor_message && turn.status !== 'pending') {
        const reply=element('div','coach-reply'); reply.dataset.source=turn.source || ''; reply.dataset.calculationStatus=turn.calculation_status || '';
        const glyph=element('span','coach-reply-glyph',turn.source === 'verified_arithmetic' && turn.calculation_status !== 'invalid' ? '=' : '?'); glyph.setAttribute('aria-hidden','true');
        const body=element('div','coach-reply-body');
        body.append(element('h3','coach-speaker',t('coach_tutor')), element('p','coach-message',turn.tutor_message),
          element('span','coach-source',sourceLabel(turn)));
        const reason=turn.reason || turn.fallback_reason;
        if (reason && turn.source !== 'verified_arithmetic' && turn.source !== 'local_model_generated') {
          const note=element('details','coach-reason');
          note.append(element('summary','',t('coach_reason')), element('p','',t('coach_fallback')), element('code','',reason));
          body.append(note);
        }
        reply.append(glyph,body); item.append(reply);
      }
      fragment.append(item);
    });
    list.replaceChildren(fragment); list.dataset.signature=signature;
    $('coach-empty').hidden=active.turns.length > 0;
    if (wasNearBottom) list.scrollTop=list.scrollHeight;
    const last=active.turns[active.turns.length-1];
    if (last?.tutor_message && last.status !== 'pending') $('coach-announcement').textContent=t('coach_tutor') + ': ' + last.tutor_message;
  }

  function renderCopy() {
    const practice=active?.identity.mode === 'practice';
    panel.setAttribute('aria-label', t(practice ? 'numbers_title' : 'coach_title'));
    $('coach-intro').textContent=t(practice ? 'numbers_intro' : 'coach_intro');
    $('coach-intro').hidden=!!practice;
    $('coach-notice').textContent=t(practice ? (session ? 'coach_practice_attached' : 'coach_practice_notice') : 'coach_help_notice');
    $('coach-input-label').textContent=t('coach_label'); input.placeholder=t('coach_placeholder');
    $('coach-history').setAttribute('aria-label',t('coach_title'));
    $('coach-pending').querySelector('strong').textContent=t('coach_wait_title');
    $('coach-pending').querySelector('p').textContent=t('coach_wait');
    $('coach-empty').querySelector('p').textContent=t('coach_empty');
    const examples=$('coach-empty').querySelector('.coach-examples'); examples.replaceChildren();
    for (const key of ['coach_example_math','coach_example_check','coach_example_why']) {
      const button=element('button','coach-example',t(key)); button.type='button';
      button.onclick=() => { input.value=t(key); changeDraft(); input.focus(); };
      examples.append(button);
    }
    $('coach-reload').textContent=t('coach_reload');
    $('numbers-language').value=apiLanguage();
    renderConversation(); renderStatus();
  }

  function renderStatus() {
    const state=active;
    $('coach-send').textContent=t(state?.request ? 'coach_retry' : 'coach_send');
    $('coach-pending').hidden=!(state?.pending || state?.modelBusy);
    $('coach-pending').querySelector('p').textContent=t(state?.modelBusy && !state?.pending ? 'coach_wait_other' : 'coach_wait');
    $('coach-history').setAttribute('aria-busy', String(!!state?.pending));
    const place=t(state?.storage === 'Arduino' ? 'coach_board' : 'coach_computer');
    $('coach-save-status').textContent=state?.saveState === 'failed' ? t('coach_unsaved') :
      state?.dirty || state?.sending ? t('coach_saving') : state?.loaded ? t('coach_saved',{place}) : '';
    $('coach-save-status').dataset.state=state?.saveState || '';
    $('coach-error').hidden=!state?.error;
    $('coach-error').querySelector('p').textContent=state?.error ? t(state.error) : '';
    $('coach-reload').hidden=state?.error === 'coach_send_failed';
    syncCoachControls();
  }

  function syncCoachControls() {
    const state=active;
    input.disabled=!!(shuttingDown || !state?.loaded || state?.sending);
    $('coach-send').disabled=!!(busy || shuttingDown || !state?.loaded || state?.sending || state?.pending || state?.modelBusy || !input.value.trim());
    panel.querySelectorAll('.coach-example').forEach(button => button.disabled=!!(busy || shuttingDown || !state?.loaded || state?.sending));
    $('coach-reload').disabled=!!state?.loading;
    $('finish-session').disabled=!!(busy || shuttingDown);
    $('poweroff').disabled=!!(shuttingDown || !finishToken);
  }

  $('coach-form').onsubmit=async event => {
    event.preventDefault();
    const state=active, message=input.value.trim();
    if (!state?.loaded || state.pending || state.modelBusy || state.sending || !message || busy || shuttingDown) return;
    state.sending=true; state.error='';
    if (!state.request || state.request.message !== message) {
      const bytes=new Uint8Array(16); crypto.getRandomValues(bytes);
      state.request={message,request_id:Array.from(bytes, value => value.toString(16).padStart(2,'0')).join('')};
    }
    renderStatus();
    try {
      await flushDraft(state);
      const data=await request('coach',state.identity,state.request);
      state.request=null; state.draft=''; state.dirty=true; state.saveState='saving';
      state.revision=Math.max(Date.now(),state.revision+1);
      if (active === state) input.value='';
      accept(state,data);
      await flushDraft(state).catch(() => {});
    } catch (error) { errorMessage(state,error.apiMessage ? 'coach_request_failed' : 'coach_send_failed'); }
    finally { state.sending=false; if(active === state) { renderStatus(); input.focus({preventScroll:true}); } }
  };
  input.addEventListener('input',changeDraft);
  input.addEventListener('keydown',event => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); $('coach-form').requestSubmit(); }
  });
  $('coach-reload').onclick=() => void load(active);
  $('coach-panel').addEventListener('toggle',() => { if ($('coach-panel').open) { switchContext('exercise'); void load(active); } else clearTimeout(timer); });
  $('open-number-practice').onclick=() => setStudioView('numbers');
  $('numbers-back').onclick=() => setStudioView('practice');
  $('numbers-language').onchange=() => run(async () => {
    setLanguage($('numbers-language').value); switchContext('practice');
    await refreshGraph(); await refreshRecommendation();
  });

  $('finish-session').onclick=async () => {
    finishToken=''; $('poweroff').hidden=true; $('finish-message').textContent=t('finish_saving');
    $('finish-dialog').showModal();
    try {
      await Promise.all([...contexts.values()].map(state => flushDraft(state)));
      if ([...contexts.values()].some(state => state.identity.student === student && state.sending)) {
        $('finish-message').textContent=t('finish_wait'); return;
      }
      const result=await request('finish',{student,...(session?{session}:{})});
      finishToken=result.finish_token || '';
      $('poweroff').hidden=!result.safe_shutdown;
      $('finish-message').textContent=t(result.safe_shutdown ? 'finish_saved' : 'finish_local');
      syncCoachControls();
    } catch (error) { $('finish-message').textContent=t(error.apiMessage?.includes('reply') ? 'finish_wait' : 'finish_error'); }
  };
  $('finish-cancel').onclick=() => $('finish-dialog').close();
  $('poweroff').onclick=async () => {
    if (!finishToken || shuttingDown) return;
    $('poweroff').disabled=true;
    try {
      await request('poweroff',{student},{finish_token:finishToken,confirm:'poweroff'});
      shuttingDown=true; clearTimeout(timer); finishToken='';
      $('poweroff').hidden=true; $('finish-cancel').hidden=true;
      $('finish-message').textContent=t('poweroff_wait');
      $('finish-dialog').addEventListener('cancel',event => event.preventDefault(),{once:true});
      syncCoachControls();
    } catch { $('finish-message').textContent=t('finish_error'); syncCoachControls(); }
  };
  $('finish-dialog').addEventListener('click',event => { if (event.target === $('finish-dialog') && !shuttingDown) $('finish-dialog').close(); });
  document.addEventListener('visibilitychange',() => {
    if (document.hidden) { clearTimeout(timer); void flushDraft().catch(() => {}); }
    else if (shown()) void load(active);
  });
  window.addEventListener('beforeunload',event => {
    if ([...contexts.values()].some(state => state.dirty || state.sending)) { event.preventDefault(); event.returnValue=''; }
  });
  window.MathCoach = {
    syncControls:syncCoachControls,
    contextChanged() { switchContext(document.body.dataset.view === 'numbers' ? 'practice' : 'exercise'); },
    languageChanged() { renderCopy(); },
    setView(view) {
      if (view === 'numbers') { $('practice-coach-slot').append(panel); switchContext('practice'); }
      else if (view === 'practice') { $('exercise-coach-slot').append(panel); switchContext('exercise'); }
      else clearTimeout(timer);
    },
    leaveProfile() { clearTimeout(timer); if (active) void flushDraft(active).catch(() => {}); active=null; },
    flushDraft,
  };
  renderCopy();
})();
