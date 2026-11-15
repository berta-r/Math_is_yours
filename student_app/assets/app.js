// Child-facing copy. The interface follows the language of the open problem (T-101).
const STRINGS = {
  en: {
    skip:'Skip to content', nav_solve:'Solve', nav_path:'My path', nav_work:'My work', profile_switch:'Switch profile',
    change_problem:'Change problem', dataset_info:'Pick any problem you like, or follow your next step in My path.',
    language:'Language', all_languages:'All languages', display:'Display', display_combined:'Text + picture', display_text:'Text only', display_image:'Picture only',
    choose_problem:'Choose a problem', open:'Open', quick_check:'Quick check', problem:'Problem',
    steps_aria:'Thinking steps', understand:'Understand', plan:'Plan', check:'Check',
    heading_steps:'Think it through, one step at a time', heading_idea:'Start with an idea',
    steps_problem:'Steps for this problem', steps_skill:'General steps for {skill}, in English',
    note_toggle:'Add a note (optional)', reflection_prompt:'What do you notice, and what could you try first?',
    reflection_placeholder:'I notice… My first step could be…', save_note:'Save my note', save_revised:'Save my new idea', see_choices:'Explore answer choices →',
    note_steps:'Optional. Your note is saved with your work. It is not marked.', note_free:'A rough idea is enough. You can ask for a hint before choosing.',
    note_saved:'Your idea is saved. It is a thinking note, not a test.',
    choose_answer:'Choose your answer', answer_choices:'Answer choices', check_answer:'Check my answer →', check_again:'Check again →',
    pick_first:'Pick an answer first.', pick_other:'Pick a different answer to check again.', next_problem:'Next problem →',
    hint:'Get a hint', see_answer:'See answer', see_explanation:'See explanation',
    gate_open:'You can now look at the answer and the explanation.', gate_hints:'The answer opens after two tries and one hint.', gate_plain:'The answer opens after two tries.',
    label_hint:'Hint', label_answer:'Answer', label_explanation:'Explanation', general_tip:'A general tip for this skill, in English', tutor_chose:'Chosen by your tutor',
    view_only:'This problem has no answer key, so you can read it but not check an answer.',
    correct_title:'That’s right!', wrong_title:'Try a different answer',
    yes:'Yes.', not_yet:'Not yet.',
    your_path:'Your path', learning_path:'Learning path', where_go:'Where would you like to go?', guide_me:'Guide me from my progress',
    kind_diagnostic:'Quick check', kind_prerequisite:'Let’s practise', kind_repair:'Let’s practise', kind_practice:'Let’s practise', kind_review:'Review time',
    kind_transfer:'Try something new', kind_stretch:'A challenge', kind_path:'Towards your goal', kind_chosen:'Your choice', kind_complete:'All done', kind_default:'Your next step',
    choose_next:'Choose your next challenge', start_next:'Start next step →', current_exercise:'Current problem',
    path_empty:'Your next steps will grow as you practise.',
    explore_skills:'Explore all skills', skills_aria:'Skills you can explore', explore_connections:'Explore skill connections', problem_map:'Problem map',
    find_area:'Find a skill', search_placeholder:'Try multiplication…', matching_skills:'Matching skills', no_match:'No skill found. Try another word.',
    map_controls:'Map controls', zoom_in:'Zoom in', zoom_out:'Zoom out', fit_map:'Fit map', focus:'Focus connections',
    graph_aria:'Connected skill map. Drag to move it. Use plus and minus to zoom.', graph_help:'Drag the map or a dot · Use + / − to zoom · Pick a skill to explore',
    key_supports:'Helps you learn →', key_related:'Related ideas', key_path:'Your path',
    practice_notes:'Your practice notes', select_skill:'Pick a skill to see how you are doing.', practise_skill:'Practise this skill →', build_path:'Build a path here',
    skill_none:'You have not tried this skill on your own yet.', skill_some:'You have answered {n} on your own and got {k} right.',
    review_due:'Review today', review_next:'Next review: {date}.', review_later:'A review date appears after you practise on your own.', answers_saved:'{n} answers saved.',
    about_estimates:'About these learning estimates',
    method_text:'These estimates are provisional. “Not tried yet” means we do not know yet. A review date never lowers your estimate. Related ideas do not become requirements.',
    practice_so_far:'Practice so far', progress_aria:'Learning progress', stat_solo:'problems solved on your own', stat_shown:'skills you’ve shown', stat_review:'skills to review',
    download:'Download my work ↓', recent:'Recent practice', empty_history:'Your first answer will appear here.',
    history_correct:'Correct', history_wrong:'Keep exploring', history_solo:'Solved on your own', history_first:'First try on your own', history_help:'With help or seen before',
    history_mixed:'Mixed skills: a quick check comes next', history_untagged:'Not linked to a skill yet',
    problem_image:'Problem picture', close:'Close ×', viewer_help:'Press Escape or tap outside the picture to go back to your problem.', enlarge_image:'Make the problem picture bigger',
    working:'Working on it…', strengths:'You can build on: {list}.', strengths_none:'Your strengths will appear as you show skills on your own.',
    media_ocr:'The answer text was read from the picture. If a symbol looks odd, check the picture.', media_choices:'The answer pictures were cut from the original. Open the full picture if one looks incomplete.',
    media_missing:'This problem needs a picture, but the picture file is missing.', media_noimage:'There is no picture for this problem, so you see the text.',
    media_notext:'This problem has no text. Choose “Text + picture” or “Picture only”.', media_partial:'The text may miss a diagram or some answers. Choose “Text + picture” to see everything.',
    media_error:'The picture could not be loaded. Open the problem again.', choice_alt:'Answer {letter}, cut from the original picture', choice_unavailable:'See the picture', choice_view:'See this answer in the picture',
    choose_letter:'Choose A, B, C, D or E first.',
  },
  ca: {
    skip:'Ves al contingut', nav_solve:'Resol', nav_path:'El meu camí', nav_work:'La meva feina', profile_switch:'Canvia de perfil',
    change_problem:'Canvia de problema', dataset_info:'Tria el problema que vulguis o segueix el teu pas següent a El meu camí.',
    language:'Llengua', all_languages:'Totes les llengües', display:'Com es veu', display_combined:'Text + imatge', display_text:'Només text', display_image:'Només imatge',
    choose_problem:'Tria un problema', open:'Obre', quick_check:'Prova ràpida', problem:'Problema',
    steps_aria:'Passos per pensar', understand:'Entén', plan:'Planifica', check:'Comprova',
    heading_steps:'Pensa-ho pas a pas', heading_idea:'Comença amb una idea',
    steps_problem:'Passos per a aquest problema', steps_skill:'Passos generals de {skill}, en anglès',
    note_toggle:'Afegeix una nota (opcional)', reflection_prompt:'Què hi veus i què podries provar primer?',
    reflection_placeholder:'Hi veig… El meu primer pas podria ser…', save_note:'Desa la nota', save_revised:'Desa la nova idea', see_choices:'Mira les opcions de resposta →',
    note_steps:'Opcional. La nota es desa amb la teva feina. No es puntua.', note_free:'N’hi ha prou amb una idea aproximada. Pots demanar una pista abans de triar.',
    note_saved:'La teva idea està desada. És una nota per pensar, no un examen.',
    choose_answer:'Tria la teva resposta', answer_choices:'Opcions de resposta', check_answer:'Comprova la resposta →', check_again:'Torna a comprovar →',
    pick_first:'Primer tria una resposta.', pick_other:'Tria una altra resposta per tornar a comprovar.', next_problem:'Problema següent →',
    hint:'Demana una pista', see_answer:'Mira la resposta', see_explanation:'Mira l’explicació',
    gate_open:'Ja pots mirar la resposta i l’explicació.', gate_hints:'La resposta s’obre després de dos intents i una pista.', gate_plain:'La resposta s’obre després de dos intents.',
    label_hint:'Pista', label_answer:'Resposta', label_explanation:'Explicació', general_tip:'Un consell general d’aquesta habilitat, en anglès', tutor_chose:'L’ha triat el teu tutor',
    view_only:'Aquest problema no té clau de respostes: el pots llegir, però no comprovar.',
    correct_title:'Ben fet!', wrong_title:'Prova una altra resposta',
    yes:'Sí.', not_yet:'Encara no.',
    your_path:'El teu camí', learning_path:'Camí d’aprenentatge', where_go:'On vols arribar?', guide_me:'Guia’m segons el que he fet',
    kind_diagnostic:'Prova ràpida', kind_prerequisite:'Practiquem', kind_repair:'Practiquem', kind_practice:'Practiquem', kind_review:'Hora de repassar',
    kind_transfer:'Prova una cosa nova', kind_stretch:'Un repte', kind_path:'Cap al teu objectiu', kind_chosen:'La teva tria', kind_complete:'Tot fet', kind_default:'El teu pas següent',
    choose_next:'Tria el teu proper repte', start_next:'Comença el pas següent →', current_exercise:'Problema actual',
    path_empty:'Els teus passos següents creixeran a mesura que practiquis.',
    explore_skills:'Explora totes les habilitats', skills_aria:'Habilitats que pots explorar', explore_connections:'Explora com es connecten les habilitats', problem_map:'Mapa de problemes',
    find_area:'Busca una habilitat', search_placeholder:'Prova «multiplication»…', matching_skills:'Habilitats trobades', no_match:'No l’he trobada. Prova una altra paraula.',
    map_controls:'Controls del mapa', zoom_in:'Amplia', zoom_out:'Redueix', fit_map:'Ajusta el mapa', focus:'Mostra les connexions',
    graph_aria:'Mapa d’habilitats connectades. Arrossega’l per moure’l. Fes servir més i menys per ampliar.', graph_help:'Arrossega el mapa o un punt · Fes servir + / − per ampliar · Tria una habilitat',
    key_supports:'T’ajuda a aprendre →', key_related:'Idees relacionades', key_path:'El teu camí',
    practice_notes:'Les teves notes de pràctica', select_skill:'Tria una habilitat per veure com vas.', practise_skill:'Practica aquesta habilitat →', build_path:'Fes un camí fins aquí',
    skill_none:'Encara no has provat aquesta habilitat pel teu compte.', skill_some:'N’has respost {n} pel teu compte i n’has encertat {k}.',
    review_due:'Repassa-la avui', review_next:'Proper repàs: {date}.', review_later:'Quan practiquis pel teu compte, apareixerà una data de repàs.', answers_saved:'{n} respostes desades.',
    about_estimates:'Sobre aquestes estimacions',
    method_text:'Aquestes estimacions són provisionals. «Encara no l’has provat» vol dir que encara no ho sabem. Una data de repàs no baixa mai la teva estimació. Les idees relacionades no es converteixen en requisits.',
    practice_so_far:'La feina feta', progress_aria:'El teu progrés', stat_solo:'problemes resolts pel teu compte', stat_shown:'habilitats que ja domines', stat_review:'habilitats per repassar',
    download:'Descarrega la meva feina ↓', recent:'Pràctica recent', empty_history:'La teva primera resposta apareixerà aquí.',
    history_correct:'Correcte', history_wrong:'Continua explorant', history_solo:'Resolt pel teu compte', history_first:'Primer intent pel teu compte', history_help:'Amb ajuda o ja vist',
    history_mixed:'Diverses habilitats: ara toca una prova ràpida', history_untagged:'Encara no està lligat a cap habilitat',
    problem_image:'Imatge del problema', close:'Tanca ×', viewer_help:'Prem Escape o toca fora de la imatge per tornar al problema.', enlarge_image:'Amplia la imatge del problema',
    working:'Hi estic treballant…', strengths:'Pots aprofitar: {list}.', strengths_none:'Els teus punts forts apareixeran quan demostris habilitats pel teu compte.',
    media_ocr:'El text de les respostes s’ha llegit de la imatge. Si un símbol sembla estrany, mira la imatge.', media_choices:'Les imatges de les respostes s’han retallat de l’original. Obre la imatge sencera si en falta un tros.',
    media_missing:'Aquest problema necessita una imatge, però no hi és.', media_noimage:'Aquest problema no té imatge, així que en veus el text.',
    media_notext:'Aquest problema no té text. Tria «Text + imatge» o «Només imatge».', media_partial:'Pot ser que el text no inclogui un dibuix o algunes respostes. Tria «Text + imatge» per veure-ho tot.',
    media_error:'No s’ha pogut carregar la imatge. Torna a obrir el problema.', choice_alt:'Resposta {letter}, retallada de la imatge original', choice_unavailable:'Mira la imatge', choice_view:'Mira aquesta resposta a la imatge',
    choose_letter:'Primer tria A, B, C, D o E.',
  },
};
const LANGUAGE_NAMES = {cat:'Català', eng:'English'};
let uiLang = 'en';
function t(key, values = {}) {
  const text = STRINGS[uiLang][key] ?? STRINGS.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => values[name] ?? '');
}
const apiLanguage = () => uiLang === 'ca' ? 'cat' : 'eng';
const languageName = code => LANGUAGE_NAMES[code] || code;
// Static copy lives in the HTML as data-i18n keys and is re-rendered on every language change.
function applyStrings() {
  document.documentElement.lang = uiLang;
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  document.querySelectorAll('[data-i18n-aria]').forEach(el => { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
  // View titles end with the brand's blue square.
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const period = document.createElement('span'); period.className = 'hero-period'; period.textContent = '.';
    el.replaceChildren(document.createTextNode(t(el.dataset.i18nTitle)), period);
  });
  document.querySelectorAll('[data-state-label]').forEach(el => { el.textContent = KnowledgeMap.stateLabel(el.dataset.stateLabel); });
}
function setLanguage(problemLanguage) {
  const next = problemLanguage === 'cat' ? 'ca' : 'en';
  if (next === uiLang) return false;
  uiLang = next; applyStrings(); return true;
}
const $ = id => document.getElementById(id);
let student = '', session = '', selected = '', busy = false;
let solved = false, lastWrong = '';
let current = null, listing = [], hasHints = false, hasSolution = false;
let recommendation = null, selectedSkill = null, profileData = null;
let feedbackVersion = 0;
let reflected = false, savedReflection = '', canReveal = false, learningGoal = null;
let mediaError = false, openData = null;
// A problem key in the URL (from the problem map) opens directly; it is consumed once.
let pendingProblem = new URLSearchParams(location.search).get('problem');
if (pendingProblem !== null) history.replaceState(null, '', '/');
const NICKNAME_KEY = 'kangaroo-student';
function storedNickname() { try { return localStorage.getItem(NICKNAME_KEY) || ''; } catch { return ''; } }
function storeNickname(name) { try { localStorage.setItem(NICKNAME_KEY, name); } catch { /* private mode: nothing to remember */ } }
// Thinking steps: answers stay on the server; the page only knows questions and options.
let thinkingSteps = [], stepIndex = 0;
const stepsComplete = () => thinkingSteps.length > 0 && stepIndex >= thinkingSteps.length;
const knowledgeMap = new KnowledgeMap($('graph'), skill => {
  if (!skill) return;
  selectedSkill = skill.id; showSkill(skill); syncControls();
});
function syncControls() {
  document.querySelectorAll('button:not(#close-image)').forEach(b => b.disabled = busy);
  $('submit').disabled = busy || !reflected || !selected || selected === lastWrong || solved || !current?.gradable;
  $('submit').hidden = solved;
  $('submit').textContent = lastWrong ? t('check_again') : t('check_answer');
  // A disabled primary action always says why.
  const helper = !busy && !solved && current?.gradable && reflected ? (!selected ? t('pick_first') : selected === lastWrong ? t('pick_other') : '') : '';
  $('submit-helper').textContent = helper; $('submit-helper').hidden = !helper;
  $('next-problem').hidden = !solved;
  $('next-problem').textContent = t('next_problem');
  $('hint').disabled = busy || !hasHints;
  $('solution').disabled = busy || !hasSolution || !canReveal || !reflected;
  $('reveal').disabled = busy || !current?.gradable || !canReveal || !reflected;
  $('reflection').disabled = busy || !current?.gradable;
  $('save-reflection').disabled = busy || !current?.gradable || $('reflection').value.trim().length < 5 || $('reflection').value.trim() === savedReflection;
  $('answer-stage').hidden = !reflected;
  $('step-options').querySelectorAll('button').forEach(b => b.disabled = busy || stepsComplete() || !current?.gradable);
  $('save-reflection').textContent = thinkingSteps.length ? t('save_note') : reflected ? t('save_revised') : t('see_choices');
  $('solution-gate').textContent = canReveal ? t('gate_open') : hasHints ? t('gate_hints') : t('gate_plain');
  $('problem-select').disabled = busy;
  $('student').disabled = busy;
  $('language-filter').disabled = busy;
  const currentRecommendation = current?.key === recommendation?.problem;
  $('start-recommended').disabled = busy || !recommendation?.problem || currentRecommendation;
  $('start-recommended').hidden = currentRecommendation;
  document.querySelector('.recommendation').hidden = currentRecommendation;
  $('start-recommended').textContent = currentRecommendation ? t('current_exercise') : t('start_next');
  $('practice-skill').textContent = t('practise_skill');
  $('practice-skill').disabled = busy || !selectedSkill;
  $('set-goal').disabled = busy || !selectedSkill;
  $('graph-focus').disabled = busy || !selectedSkill;
  $('learning-goal').disabled = busy;
  $('workspace').setAttribute('aria-busy', String(busy));
  $('activity-status').textContent = busy ? t('working') : '';
}
document.addEventListener('pointerdown', event => {
  const button = event.target.closest('button');
  if (button && !button.disabled) button.classList.add('pointer-press');
});
const releasePress = () => document.querySelectorAll('.pointer-press').forEach(b => b.classList.remove('pointer-press'));
document.addEventListener('pointerup', releasePress);
document.addEventListener('pointercancel', releasePress);
window.addEventListener('blur', releasePress);
async function api(path, data = {}) {
  const response = await fetch('/api/' + path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({student, ...data})});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed');
  return result;
}
async function run(action) {
  if (busy) return;
  busy = true; $('error').textContent = '';
  syncControls();
  try { await action(); } catch(error) { $('error').textContent = error.message; }
  finally { busy = false; syncControls(); }
}
// Hints, revealed answers and explanations share one labelled line under the hint button.
function showFeedback(kind, text) {
  const label = document.createElement('strong'); label.textContent = t('label_' + kind) + ':';
  $('feedback').replaceChildren(label, document.createTextNode(' ' + text));
  $('feedback').dataset.kind = kind;
  $('feedback').dataset.state = kind === 'answer' ? 'correct' : 'neutral';
}
function clearFeedback() { $('feedback').replaceChildren(); delete $('feedback').dataset.kind; $('feedback').dataset.state = 'neutral'; $('hint-source').textContent = ''; }
async function openProblem(key = null, returnTo = null) {
  feedbackVersion++;
  const chosen = key || $('problem-select').value;
  if (![...$('problem-select').options].some(o => o.value === chosen)) {
    const p = listing.find(p => p.key === chosen);
    $('problem-select').append(new Option(p ? problemLabel(p) : chosen, chosen));
  }
  $('problem-select').value = chosen;
  const data = await api('start', {problem:chosen, return_to:returnTo});
  openData = data;
  current = data.problem; hasHints = data.has_hints; hasSolution = data.has_solution;
  const languageChanged = setLanguage(current.language);
  thinkingSteps = data.thinking_steps || []; stepIndex = 0;
  // With steps, completing them unlocks the choices; without steps, a saved thought does.
  reflected = !thinkingSteps.length && !data.reflection_required; savedReflection = ''; canReveal = !!data.can_reveal;
  $('reflection').value = '';
  session = data.session; selected = ''; solved = false; lastWrong = '';
  renderProblemText();
  renderThinking(data);
  clearFeedback();
  $('answer-moment').hidden = true;
  $('skill').textContent = data.skill;
  $('question').lang = current.language === 'cat' ? 'ca' : 'en';
  renderOptions();
  if (languageChanged) { populateProblems(); if (student) await refreshGraph(); }
}
// Copy that depends on the open problem; re-run when the language changes.
function renderProblemText() {
  if (!openData) return;
  $('reflection-prompt').textContent = uiLang === 'en' && openData.reflection_prompt ? openData.reflection_prompt : t('reflection_prompt');
  $('reflection-note').textContent = savedReflection ? t('note_saved') : thinkingSteps.length ? t('note_steps') : t('note_free');
  $('practice-title').textContent = openData.kind === 'diagnostic' ? t('quick_check') : t('problem');
  $('reflection-heading').textContent = thinkingSteps.length ? t('heading_steps') : t('heading_idea');
  $('step-scope').textContent = openData.steps_scope === 'problem' ? t('steps_problem') : t('steps_skill', {skill:(openData.steps_skill || '').toLowerCase()});
  renderMedia();
}
function renderOptions() {
  $('options').replaceChildren();
  for (const letter of 'ABCDE') {
    const value = current.options[letter] || (current.image_url ? t('choice_unavailable') : '—');
    const button = document.createElement('button');
    button.type = 'button';
    const key = document.createElement('span'); key.className = 'option-letter'; key.textContent = letter;
    const label = document.createElement('span'); label.className = 'option-text';
    if (current.option_images?.[letter] && !current.options[letter]) {
      const preview = document.createElement('img'); preview.src = current.option_images[letter]; preview.alt = t('choice_alt', {letter}); preview.className = 'option-image';
      preview.onerror = () => { label.textContent = t('choice_view'); };
      label.append(preview);
    } else { label.textContent = value; }
    // The mark is set only by a checked result: ✓ for correct, ✗ for wrong.
    const check = document.createElement('span'); check.className = 'option-check'; check.setAttribute('aria-hidden', 'true');
    button.append(key, label, check);
    button.dataset.letter = letter;
    button.setAttribute('aria-pressed', 'false');
    button.onclick = () => {
      if (solved) return;
      selected = letter;
      [...$('options').children].forEach(b => { b.classList.toggle('selected', b === button); b.setAttribute('aria-pressed', String(b === button)); });
      syncControls();
    };
    $('options').append(button);
  }
}
function markOption(letter, state) {
  const button = $('options').querySelector(`[data-letter="${letter}"]`);
  if (!button) return;
  button.classList.remove('selected');
  button.classList.add(state);
  button.querySelector('.option-check').textContent = state === 'wrong' ? '✗' : '✓';
}
function renderThinking(data) {
  const hasSteps = thinkingSteps.length > 0;
  $('thinking').hidden = !hasSteps;
  $('note-toggle').hidden = !hasSteps;
  $('note-area').hidden = hasSteps;
  $('note-toggle').setAttribute('aria-expanded', 'false');
  $('step-feedback').hidden = true; $('step-feedback').textContent = '';
  $('step-options').classList.remove('resolved');
  if (!hasSteps) return;
  $('thinking').lang = data.steps_language === 'cat' ? 'ca' : 'en';
  renderStep();
}
function renderStep() {
  const done = stepsComplete();
  const shown = Math.min(stepIndex, thinkingSteps.length - 1);
  [...$('step-rail').children].forEach((item, index) => {
    item.classList.toggle('done', index < stepIndex);
    if (index === stepIndex && !done) item.setAttribute('aria-current', 'step'); else item.removeAttribute('aria-current');
  });
  if (done) return;  // Keep the last question and its resolved options visible.
  const step = thinkingSteps[shown];
  $('step-question').textContent = step.question;
  $('step-options').replaceChildren();
  $('step-options').classList.remove('resolved');
  step.options.forEach((text, choice) => {
    const button = document.createElement('button');
    button.type = 'button';
    const label = document.createElement('span'); label.textContent = text;
    const mark = document.createElement('span'); mark.className = 'option-check'; mark.setAttribute('aria-hidden', 'true');
    button.append(label, mark);
    button.onclick = () => answerStep(choice, button);
    $('step-options').append(button);
  });
}
function answerStep(choice, button) {
  run(async () => {
    const result = await api('step', {session, index:stepIndex, choice});
    // One channel during the steps: the server's message and the reason, under the options.
    const feedback = $('step-feedback');
    feedback.hidden = false; feedback.dataset.state = result.correct ? 'correct' : 'retry';
    const label = document.createElement('strong'); label.textContent = (result.correct ? '✓ ' : '') + (result.message || (result.correct ? t('yes') : t('not_yet')));
    feedback.replaceChildren(label, document.createTextNode(' ' + result.why));
    if (!result.correct) { button.classList.add('tried'); button.querySelector('.option-check').textContent = '✗'; return; }
    stepIndex = result.next_index;
    if (result.completed) {
      button.classList.add('chosen'); button.querySelector('.option-check').textContent = '✓';
      $('step-options').classList.add('resolved');
      reflected = true;
    }
    renderStep();
  }).then(() => {
    if (stepsComplete() && reflected) { $('answer-stage').hidden = false; document.querySelector('#options button')?.focus({preventScroll:true}); }
    else if (!stepsComplete()) $('step-options').querySelector('button')?.focus({preventScroll:true});
  });
}
$('note-toggle').onclick = () => {
  const open = $('note-area').hidden;
  $('note-area').hidden = !open; $('note-toggle').setAttribute('aria-expanded', String(open));
  if (open) $('reflection').focus();
};
function renderMedia() {
  if (!current) return;
  const mode = $('display-mode').value;
  $('question').textContent = current.text || `${t('problem')} ${current.id}`;
  $('question').hidden = mode === 'image' && !!current.image_url;
  $('problem-figure').hidden = mode === 'text' || !current.image_url;
  const image = $('problem-image');
  if (current.image_url) { if (image.getAttribute('src') !== current.image_url) { mediaError = false; image.src = current.image_url; } }
  else { image.removeAttribute('src'); }
  const notes = [];
  if (!current.gradable) notes.push(t('view_only'));
  if (mediaError) notes.push(t('media_error'));
  if (current.options_source === 'ocr') notes.push(t('media_ocr'));
  if (Object.keys(current.option_images || {}).length) notes.push(t('media_choices'));
  if (current.requires_image && !current.image_url) notes.push(t('media_missing'));
  if (mode === 'image' && !current.image_url) notes.push(t('media_noimage'));
  if (mode === 'text' && !current.text) notes.push(t('media_notext'));
  if (mode === 'text' && (current.requires_image || Object.keys(current.options).length < 5)) notes.push(t('media_partial'));
  $('media-note').textContent = notes.join(' ');
}
$('problem-image').onerror = () => { mediaError = true; renderMedia(); };
$('display-mode').onchange = renderMedia;
const imageViewer = $('image-viewer');
$('image-link').onclick = () => {
  if (!current?.image_url || imageViewer.open) return;
  $('viewer-error').textContent = '';
  $('enlarged-image').src = current.image_url;
  imageViewer.showModal();
  document.body.classList.add('viewer-open');
};
$('close-image').onclick = () => imageViewer.close();
imageViewer.addEventListener('close', () => {
  document.body.classList.remove('viewer-open');
  $('enlarged-image').removeAttribute('src');
  $('image-link').focus({preventScroll:true});
});
// Native dialog handles Escape and traps focus. Backdrop clicks also dismiss it.
imageViewer.addEventListener('click', event => {
  if (event.target !== imageViewer) return;
  const bounds = imageViewer.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) imageViewer.close();
});
$('enlarged-image').onerror = () => { $('viewer-error').textContent = t('media_error'); };
// Child-readable picker labels: never raw ids.
function problemLabel(p) {
  if (p.kind === 'diagnostic') return `${t('quick_check')}: ${p.skill} · ${p.id.split('-').pop()} · ${languageName(p.language)}`;
  const text = p.preview || p.skill || p.id;
  return `${text.length > 50 ? text.slice(0, 50).replace(/[\s.,;:!?]+$/, '') + '…' : text} · ${languageName(p.language)}`;
}
function populateProblems() {
  const value = $('problem-select').value;
  $('problem-select').replaceChildren();
  listing.filter(p => !$('language-filter').value || p.language === $('language-filter').value).forEach(p => {
    const option = document.createElement('option'); option.value=p.key; option.textContent=problemLabel(p); $('problem-select').append(option);
  });
  if ([...$('problem-select').options].some(o => o.value === value)) $('problem-select').value = value;
  const filter = $('language-filter'), chosen = filter.value;
  filter.replaceChildren(new Option(t('all_languages'), ''));
  [...new Set(listing.map(p => p.language))].sort().forEach(lang => filter.append(new Option(languageName(lang), lang)));
  filter.value = chosen;
}
$('language-filter').onchange = () => run(async () => { populateProblems(); await openProblem(); await refreshRecommendation(); });
async function refreshGraph() {
  const profile = await api('profile', {goal:learningGoal,focus:session,language:apiLanguage()});
  profileData = profile;
  KnowledgeMap.labels = profile.state_labels || null;
  document.querySelectorAll('[data-state-label]').forEach(el => { el.textContent = KnowledgeMap.stateLabel(el.dataset.stateLabel); });
  $('stat-evidence').textContent = profile.skills.reduce((sum,s) => sum + (s.successes || 0), 0);
  $('stat-demonstrated').textContent = profile.skills.filter(s => s.state === 'demonstrated').length;
  $('stat-due').textContent = profile.skills.filter(s => s.due).length;
  knowledgeMap.setData(profile, selectedSkill);
  const skillList = $('skill-list'); skillList.replaceChildren();
  profile.skills.forEach(skill => {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'skill-tile';
    const name = document.createElement('strong'); name.textContent = skill.name;
    const state = document.createElement('span'); state.textContent = stateLabel(skill.state);
    button.append(name, state);
    button.onclick = () => { document.querySelector('.connection-map').open = true; knowledgeMap.select(skill.id, true); $('skill-detail').focus({preventScroll:true}); $('skill-detail').scrollIntoView({block:'center'}); };
    skillList.append(button);
  });
  if (selectedSkill) showSkill(profile.skills.find(s => s.id === selectedSkill));
  else $('skill-detail').textContent = t('select_skill');
  $('graph-method').textContent = profile.graph_method === 'embeddings' ? 'Related links use prepared skill embeddings. Nearer dots tend to share connections.' : profile.graph_method === 'keyword-tfidf' ? 'Related links currently use shared topic vocabulary. Semantic embeddings can replace this initial map.' : 'This map currently shows authored learning connections.';
  const goalSelect=$('learning-goal');
  goalSelect.replaceChildren(new Option(t('guide_me'),''));
  profile.skills.forEach(skill=>goalSelect.append(new Option(skill.name,skill.id)));
  goalSelect.value=learningGoal || '';
  renderPath(profile.learning_path);
  $('total').textContent = t('answers_saved', {n:profile.attempts});
  $('history').replaceChildren();
  for (const event of profile.history) {
    const item = document.createElement('li');
    const name = profile.skills.find(s => s.id === event.skill_id)?.name;
    const problem = listing.find(p => p.id === event.problem_id && p.language === event.language) || listing.find(p => p.id === event.problem_id);
    const what = event.kind === 'diagnostic' ? `${t('quick_check')}: ${name || ''}` : problem ? problemLabel(problem) : event.problem_id;
    const title = document.createElement('strong'); title.textContent = `${what} · ${event.correct ? t('history_correct') : t('history_wrong')}`;
    const detail = document.createElement('span');
    const attribution = event.eligible ? t(event.correct ? 'history_solo' : 'history_first') : event.reason === 'multi_skill_requires_diagnostic' ? t('history_mixed') : event.reason === 'unclassified' ? t('history_untagged') : t('history_help');
    detail.textContent = `${attribution} · ${new Date(event.created).toLocaleString(uiLang === 'ca' ? 'ca' : 'en')}`;
    item.append(title,detail); $('history').append(item);
  }
  if (!profile.history.length) { const item=document.createElement('li'); item.textContent=t('empty_history'); $('history').append(item); }
  $('history-section').hidden=false;
}
function stateLabel(state) { return KnowledgeMap.stateLabel(state); }
function renderPath(path) {
  $('learning-path').replaceChildren();
  $('path-reason').textContent=path?.reason || t('path_empty');
  $('path-title').textContent=t('learning_path');
  for(const step of path?.steps || []) {
    const li=document.createElement('li');
    const button=document.createElement('button');button.type='button';button.className='path-step';
    const title=document.createElement('strong');title.textContent=step.name;
    const detail=document.createElement('span');detail.textContent=step.child_reason || stateLabel(step.state);
    button.append(title,detail);
    button.onclick=()=>{document.querySelector('.connection-map').open=true;knowledgeMap.select(step.id,true);$('skill-detail').focus({preventScroll:true});$('skill-detail').scrollIntoView({block:'center'});};
    if(step.id===path.next_skill){li.className='next-step';button.setAttribute('aria-label',`${step.name}: ${step.child_reason || ''}`);}
    li.append(button);$('learning-path').append(li);
  }
  $('path-strengths').textContent=path?.strengths?.length ? t('strengths', {list:path.strengths.map(s=>s.name).join(', ')}) : t('strengths_none');
}
$('graph-zoom-in').onclick=()=>knowledgeMap.zoom(1.25);
$('graph-zoom-out').onclick=()=>knowledgeMap.zoom(1/1.25);
$('graph-reset').onclick=()=>knowledgeMap.reset();
$('graph-focus').onclick=()=>{knowledgeMap.focused=!knowledgeMap.focused;knowledgeMap.highlight();$('graph-focus').setAttribute('aria-pressed',String(knowledgeMap.focused));};
$('graph-search').oninput=()=>{
  const query=$('graph-search').value.trim();knowledgeMap.query=query;knowledgeMap.highlight();
  const results=$('graph-results');results.replaceChildren();results.hidden=!query;
  if(!query)return;
  const matches=(profileData?.skills || []).filter(skill=>skill.name.toLowerCase().includes(query.toLowerCase()));
  for(const skill of matches){
    const item=document.createElement('li'),button=document.createElement('button');button.className='text-button';button.textContent=skill.name;
    button.onclick=()=>{knowledgeMap.select(skill.id,true);};item.append(button);results.append(item);
  }
  if(!matches.length){const li=document.createElement('li');li.textContent=t('no_match');results.append(li);}
};
$('graph-search').onkeydown=event=>{if(event.key==='Escape'){$('graph-search').value='';$('graph-search').oninput();}if(event.key==='Enter'){document.querySelector('#graph-results button')?.click();}};
$('learning-goal').onchange=()=>run(async()=>{learningGoal=$('learning-goal').value||null;await refreshGraph();await refreshRecommendation();});
$('set-goal').onclick=()=>run(async()=>{learningGoal=selectedSkill;await refreshGraph();await refreshRecommendation();});
$('reflection').oninput=()=>{if(!thinkingSteps.length)reflected=$('reflection').value.trim()===savedReflection && !!savedReflection;syncControls();};
$('save-reflection').onclick=()=>run(async()=>{
  feedbackVersion++; clearFeedback();
  const reflection=$('reflection').value.trim();
  const result=await api('reflect',{session,reflection});
  savedReflection=reflection;
  $('reflection-note').textContent=thinkingSteps.length ? t('note_saved') : result.message || t('note_saved');
  if(thinkingSteps.length) return;  // With steps, the note is optional and does not unlock the choices.
  reflected=!!result.reflection_saved;
  if(reflected){$('answer-stage').hidden=false;document.querySelector('#options button')?.focus();}
});
function showSkill(skill) {
  if (!skill) return;
  const evidence = skill.probability === null ? t('skill_none') : t('skill_some', {n:skill.evidence, k:skill.successes});
  $('skill-detail').textContent = `${skill.name} · ${stateLabel(skill.state)}. ${skill.description} ${evidence}`;
  $('skill-review').textContent = skill.next_review ? (skill.due ? t('review_due') + '.' : t('review_next', {date:new Date(skill.next_review).toLocaleDateString(uiLang === 'ca' ? 'ca' : 'en')})) : t('review_later');
}
async function refreshRecommendation(skill = null) {
  recommendation = await api('recommendation', {focus:session,language:$('language-filter').value || current?.language || 'eng',skill,goal:learningGoal});
  renderRecommendation();
  syncControls();
}
function renderRecommendation() {
  if (!recommendation) return;
  $('recommendation-title').textContent = recommendation.skill || t('choose_next');
  $('recommendation-kind').textContent = t('kind_' + (recommendation.kind || 'default'));
  $('recommendation-reason').textContent = (recommendation.summary || '') + (recommendation.language_note ? ' ' + recommendation.language_note : '');
  // The technical reason stays available to adults in the method note.
  $('method-reason').textContent = recommendation.reason || '';
}
$('start-recommended').onclick = () => run(async () => { if(recommendation?.problem) { await openProblem(recommendation.problem,recommendation.return_to); setStudioView('practice'); $('question').focus(); } });
$('practice-skill').onclick = () => run(async () => { await refreshRecommendation(selectedSkill); if(recommendation?.problem) { await openProblem(recommendation.problem); setStudioView('practice'); $('question').focus(); } });
$('next-problem').onclick = () => run(async () => {
  await refreshRecommendation();
  if (recommendation?.problem && recommendation.problem !== current?.key) await openProblem(recommendation.problem, recommendation.return_to);
  else {
    const keys = [...$('problem-select').options].map(o => o.value);
    const next = keys[(keys.indexOf(current?.key) + 1) % keys.length];
    await openProblem(next);
  }
  await refreshRecommendation();
  window.scrollTo(0, 0); $('question').focus({preventScroll:true});
});
$('download-report').onclick = () => run(async () => {
  const result = await api('report'); const url = URL.createObjectURL(new Blob([result.markdown],{type:'text/markdown;charset=utf-8'}));
  const link=document.createElement('a'); link.href=url; link.download='learning-notebook.md'; link.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
});
$('profile-form').onsubmit = event => {
  event.preventDefault();
  run(async () => {
    student = $('student').value.trim();
    const data = await api('problems');
    listing = data.problems;
    populateProblems();
    selectedSkill=null; session=''; current=null; learningGoal=null; feedbackVersion++;
    knowledgeMap.selected=null; knowledgeMap.query=''; knowledgeMap.focused=false; knowledgeMap.reset();
    $('graph-search').value=''; $('graph-results').hidden=true; $('graph-focus').setAttribute('aria-pressed','false');
    await refreshGraph(); await refreshRecommendation();
    const requested = pendingProblem && listing.some(p => p.key === pendingProblem) ? pendingProblem : null;
    pendingProblem = null;
    if (requested) await openProblem(requested);
    else await openProblem(recommendation.problem || $('problem-select').value, recommendation.return_to);
    await refreshRecommendation();
    $('workspace').hidden=false;
    storeNickname(student);
    $('problem-map-link').href = '/map?student=' + encodeURIComponent(student); $('problem-map-link').hidden = false;
    $('welcome').hidden = true; $('studio-nav').hidden = false; $('profile-switch').hidden = false;
    document.body.classList.remove('landing');
    $('profile-name').textContent = student;
    setStudioView('practice', false);
    $('skill-review').textContent = '';
    $('question').focus();
  });
};
$('open-problem').onclick = () => run(async () => { await openProblem(); await refreshRecommendation(); $('question').focus(); });
function showAnswerMoment(correct, message) {
  const panel = $('answer-moment');
  const symbol = panel.querySelector('.answer-moment-symbol');
  panel.dataset.state = correct ? 'correct' : 'retry';
  symbol.textContent = correct ? '✓' : '✗';
  panel.querySelector('.answer-moment-title').textContent = correct ? t('correct_title') : t('wrong_title');
  panel.querySelector('.answer-moment-message').textContent = message || '';
  panel.hidden = false;
  panel.getAnimations().forEach(animation => animation.cancel());
  symbol.getAnimations().forEach(animation => animation.cancel());
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
    panel.animate([{opacity:0, transform:'translateY(18px)'},{opacity:1, transform:'translateY(0)'}],
      {duration:380, easing:'cubic-bezier(0.23, 1, 0.32, 1)'});
    symbol.animate([{opacity:0, transform:'scale(.55)'},{opacity:1, transform:'scale(1.13)', offset:.6},{opacity:1, transform:'scale(1)'}],
      {duration:480, easing:'cubic-bezier(0.23, 1, 0.32, 1)'});
  }
  panel.scrollIntoView({block:'center', behavior:'instant'});
}
$('submit').onclick = () => run(async () => {
  feedbackVersion++; clearFeedback();
  if (!selected) throw new Error(t('choose_letter'));
  const answer = selected;
  const result = await api('answer',{session,answer});
  canReveal = !!result.can_reveal;
  solved = result.correct;
  markOption(answer, result.correct ? 'correct' : 'wrong');
  if (result.correct) selected = ''; else lastWrong = answer;
  showAnswerMoment(result.correct, result.message);
  await refreshGraph();
  await refreshRecommendation();
});
for (const action of ['hint','solution']) $(''+action).onclick = () => run(async () => {
  const version = ++feedbackVersion;
  const result = await api(action,{session});
  showFeedback(action === 'hint' ? 'hint' : 'explanation', result.message);
  if ('can_reveal' in result) canReveal=!!result.can_reveal;
  $('hint-source').textContent = action === 'hint' && result.scope === 'skill' ? t('general_tip') : '';
  if (result.job) pollHint(result.job, session, student, version);
  await refreshRecommendation();
});
async function pollHint(job, requestedSession, requestedStudent, version) {
  for (let count=0; count<35 && version === feedbackVersion && requestedSession === session && requestedStudent === student; count++) {
    await new Promise(resolve => setTimeout(resolve,1000));
    if(version !== feedbackVersion || requestedSession !== session || requestedStudent !== student) return;
    try {
      const result=await api('hint-job',{job});
      if(version !== feedbackVersion || requestedSession !== session || requestedStudent !== student) return;
      if(result.status === 'done') {
        showFeedback('hint', result.message);
        if (result.source === 'local_model_selected') $('hint-source').textContent = [$('hint-source').textContent, t('tutor_chose')].filter(Boolean).join(' · ');
        return;
      }
    } catch { return; }
  }
}
$('reveal').onclick = () => run(async () => {
  feedbackVersion++; clearFeedback();
  const result = await api('reveal', {session});
  showFeedback('answer', result.message);
  markOption(result.answer, 'correct-answer');
  await refreshRecommendation();
});
syncControls();

// Workspace navigation only changes presentation; every exercise remains in memory.
const viewKeys = {practice:'nav_solve', map:'nav_path', notebook:'nav_work'};
function setStudioView(view, focus = true) {
  if (!viewKeys[view] || $('workspace').hidden) return;
  for (const name of Object.keys(viewKeys)) $(''+name+'-view').hidden = name !== view;
  document.querySelectorAll('#studio-nav button').forEach(button => {
    if (button.dataset.view === view) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  document.body.dataset.view = view;
  $('view-title').textContent = t(viewKeys[view]);
  if (focus) { $('view-title').focus({preventScroll:true}); window.scrollTo(0,0); }
}
document.querySelectorAll('#studio-nav [data-view]').forEach(button => button.addEventListener('click', () => setStudioView(button.dataset.view)));
$('profile-switch').onclick = () => {
  $('workspace').hidden = true; $('studio-nav').hidden = true; $('profile-switch').hidden = true; $('welcome').hidden = false;
  $('problem-map-link').hidden = true;
  document.body.classList.add('landing');
  $('student').focus(); window.scrollTo(0,0);
};
// Re-render language-dependent dynamic copy whenever the problem language changes.
const originalSetLanguage = setLanguage;
setLanguage = problemLanguage => {
  const changed = originalSetLanguage(problemLanguage);
  if (changed) {
    renderProblemText(); renderRecommendation();
    $('view-title').textContent = t(viewKeys[document.body.dataset.view] || 'nav_solve');
    if (!selectedSkill) $('skill-detail').textContent = t('select_skill');
  }
  return changed;
};
const originalOpenProblem = openProblem;
openProblem = async (...args) => {
  await originalOpenProblem(...args);
  $('exercise-settings').open = false;
};
applyStrings();
// Returning visitors: remember the nickname; a ?problem= link skips the landing.
{
  const known = storedNickname();
  if (known) $('student').value = known;
  if (known && pendingProblem) $('profile-form').requestSubmit();
}
