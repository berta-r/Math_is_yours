const $ = id => document.getElementById(id);
let student = '', session = '', selected = '', busy = false;
let solved = false;
let current = null, listing = [], hasHints = false, hasSolution = false;
let recommendation = null, selectedSkill = null, profileData = null;
let feedbackVersion = 0;
let reflected = false, savedReflection = '', canReveal = false, learningGoal = null;
const knowledgeMap = new KnowledgeMap($('graph'), skill => {
  if (!skill) return;
  selectedSkill = skill.id; showSkill(skill); syncControls();
});
function syncControls() {
  document.querySelectorAll('button:not(#close-image)').forEach(b => b.disabled = busy);
  $('submit').disabled = busy || !reflected || !selected || solved || !current?.gradable;
  $('hint').disabled = busy || !hasHints;
  $('solution').disabled = busy || !hasSolution || !canReveal || !reflected;
  $('reveal').disabled = busy || !current?.gradable || !canReveal || !reflected;
  $('reflection').disabled = busy || !current?.gradable;
  $('save-reflection').disabled = busy || !current?.gradable || $('reflection').value.trim().length < 5 || $('reflection').value.trim() === savedReflection;
  $('answer-stage').hidden = !reflected;
  $('save-reflection').textContent = reflected ? 'Save revised idea' : 'Explore answer choices →';
  $('solution-gate').textContent = canReveal ? 'You can now review the answer and any available explanation.' : hasHints ? 'Review opens after two attempts and at least one hint. You can take another learning step at any time.' : 'Review opens after two attempts. You can choose a short skill check whenever you need one.';
  $('problem-select').disabled = busy;
  $('student').disabled = busy;
  $('language-filter').disabled = busy;
  const currentRecommendation = current?.id === recommendation?.id;
  $('start-recommended').disabled = busy || !recommendation?.problem || currentRecommendation;
  $('start-recommended').textContent = currentRecommendation ? 'Current exercise' : 'Start next step';
  $('practice-skill').disabled = busy || !selectedSkill;
  $('set-goal').disabled = busy || !selectedSkill;
  $('graph-focus').disabled = busy || !selectedSkill;
  $('learning-goal').disabled = busy;
  $('workspace').setAttribute('aria-busy', String(busy));
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
async function openProblem(key = null, returnTo = null) {
  feedbackVersion++;
  const chosen = key || $('problem-select').value;
  if (![...$('problem-select').options].some(o => o.value === chosen)) {
    const p = listing.find(p => p.key === chosen);
    $('problem-select').append(new Option(p ? problemLabel(p) : chosen, chosen));
  }
  $('problem-select').value = chosen;
  const data = await api('start', {problem:chosen, return_to:returnTo});
  current = data.problem; hasHints = data.has_hints; hasSolution = data.has_solution;
  reflected = !data.reflection_required; savedReflection = ''; canReveal = !!data.can_reveal;
  $('reflection').value = '';
  $('reflection-prompt').textContent = data.reflection_prompt || 'What do you notice, and what could you try first?';
  $('reflection-note').textContent = 'A rough idea is enough. You can ask for a hint before choosing.';
  session = data.session; selected = ''; solved = false;
  $('feedback').dataset.state = 'neutral';
  $('skill').textContent = data.skill;
  $('practice-title').textContent = data.kind === 'diagnostic' ? 'A short skill check' : 'A fresh challenge';
  $('hint-source').textContent = '';
  renderMedia();
  $('question').lang = data.problem.language === 'cat' ? 'ca' : 'en';
  $('options').replaceChildren();
  for (const letter of 'ABCDE') {
    const value = data.problem.options[letter] || (data.problem.image_url ? 'See original image' : 'Option text unavailable');
    const button = document.createElement('button');
    const key = document.createElement('span'); key.className = 'option-letter'; key.textContent = letter;
    const label = document.createElement('span');
    if (data.problem.option_images?.[letter] && !data.problem.options[letter]) {
      const preview = document.createElement('img'); preview.src = data.problem.option_images[letter]; preview.alt = `Choice ${letter}, extracted from the original image`; preview.className = 'option-image';
      preview.onerror = () => { label.textContent = 'View choice in original image'; };
      label.append(preview);
    } else { label.textContent = value; }
    const check = document.createElement('span'); check.className = 'option-check'; check.textContent = '✓'; check.setAttribute('aria-hidden', 'true');
    button.append(key, label, check);
    button.setAttribute('aria-pressed', 'false');
    button.onclick = () => {
      selected = letter;
      [...$('options').children].forEach(b => { b.classList.toggle('selected', b === button); b.setAttribute('aria-pressed', String(b === button)); });
      syncControls();
    };
    $('options').append(button);
  }
  $('feedback').textContent = !current.gradable ? 'View-only problem: no answer key is loaded.' : 'Take a moment to notice the information you have. Write a first step, then explore the choices.';
}
function renderMedia() {
  if (!current) return;
  const mode = $('display-mode').value;
  $('question').textContent = current.text || `Problem ${current.id}`;
  $('question').hidden = mode === 'image' && !!current.image_url;
  $('problem-figure').hidden = mode === 'text' || !current.image_url;
  const image = $('problem-image');
  if (current.image_url) {
    image.src = current.image_url;
  } else { image.removeAttribute('src'); }
  const notes = [];
  if (current.options_source === 'ocr') notes.push('Answer text was read from the image. Check symbols against the original if something looks unusual.');
  if (Object.keys(current.option_images || {}).length) notes.push('Choice previews were extracted from the original. Use the full image if a preview looks incomplete.');
  if (current.requires_image && !current.image_url) notes.push('This problem needs an image, but the local file is missing. Prepare data with --save-images.');
  if (mode === 'image' && !current.image_url) notes.push('No local image is available; showing text instead.');
  if (mode === 'text' && !current.text) notes.push('This problem has no question text. Switch to image or combined display.');
  if (mode === 'text' && (current.requires_image || Object.keys(current.options).length < 5)) notes.push('Text alone may omit diagrams or answer choices. Switch to text + image for the original.');
  $('media-note').textContent = notes.join(' ');
}
$('problem-image').onerror = () => { $('media-note').textContent = 'The image could not be loaded. Check the local image folder and reopen this problem.'; };
$('display-mode').onchange = renderMedia;
const imageViewer = $('image-viewer');
$('image-link').onclick = () => {
  if (!current?.image_url || imageViewer.open) return;
  $('viewer-error').textContent = '';
  $('image-viewer-title').textContent = `Problem ${current.id} · ${current.language}`;
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
$('enlarged-image').onerror = () => { $('viewer-error').textContent = 'The image could not be loaded. Close this viewer and try opening the problem again.'; };
function problemLabel(p) {
  return p.kind === 'diagnostic' ? `Quick check: ${p.skill} · ${p.id.split('-').pop()} · ${p.language}` : `${p.id} · ${p.language} · ${p.format}`;
}
function populateProblems() {
  $('problem-select').replaceChildren();
  listing.filter(p => !$('language-filter').value || p.language === $('language-filter').value).forEach(p => {
    const option = document.createElement('option'); option.value=p.key; option.textContent=problemLabel(p); $('problem-select').append(option);
  });
}
$('language-filter').onchange = () => run(async () => { populateProblems(); await openProblem(); await refreshRecommendation(); });
async function refreshGraph() {
  const profile = await api('profile', {goal:learningGoal,focus:session});
  profileData = profile;
  $('stat-evidence').textContent = profile.skills.reduce((sum,s) => sum + s.evidence, 0);
  $('stat-demonstrated').textContent = profile.skills.filter(s => s.state === 'demonstrated').length;
  $('stat-due').textContent = profile.skills.filter(s => s.due).length;
  knowledgeMap.setData(profile, selectedSkill);
  if (selectedSkill) showSkill(profile.skills.find(s => s.id === selectedSkill));
  $('graph-method').textContent = profile.graph_method === 'embeddings' ? 'Related links use prepared skill embeddings. Nearer dots tend to share connections.' : profile.graph_method === 'keyword-tfidf' ? 'Related links currently use shared topic vocabulary. Semantic embeddings can replace this initial map.' : 'This map currently shows authored learning connections.';
  const goalSelect=$('learning-goal');
  goalSelect.replaceChildren(new Option('Guide me from my progress',''));
  profile.skills.forEach(skill=>goalSelect.append(new Option(skill.name,skill.id)));
  goalSelect.value=learningGoal || '';
  renderPath(profile.learning_path);
  $('total').textContent = `${profile.attempts} attempts saved · ${profile.coverage.tagged}/${profile.coverage.exercises} exercises tagged.`;
  $('history').replaceChildren();
  for (const event of profile.history) {
    const item = document.createElement('li');
    const name = profile.skills.find(s => s.id === event.skill_id)?.name;
    const title = document.createElement('strong'); title.textContent = `${event.kind === 'diagnostic' ? `Skill check: ${name || 'Practice'}` : event.problem_id} · ${event.correct ? 'Correct' : 'Keep exploring'}`;
    const detail = document.createElement('span');
    const attribution = event.eligible ? 'Independent evidence recorded' : event.reason === 'multi_skill_requires_diagnostic' ? 'Multiple skills: diagnostic recommended' : event.reason === 'unclassified' ? 'No skill attribution yet' : 'Assisted or repeat practice';
    detail.textContent = `${attribution} · ${new Date(event.created).toLocaleString()}`;
    item.append(title,detail); $('history').append(item);
  }
  if (!profile.history.length) { const item=document.createElement('li'); item.textContent='Your first attempt will appear here.'; $('history').append(item); }
  $('history-section').hidden=false;
}
function stateLabel(state) { return KnowledgeMap.stateLabel(state); }
function renderPath(path) {
  $('learning-path').replaceChildren();
  $('path-reason').textContent=path?.reason || 'Your next steps will adapt as you build independent evidence.';
  $('path-title').textContent=path?.goal_name ? `Towards ${path.goal_name.toLowerCase()}` : 'Your learning path';
  for(const step of path?.steps || []) {
    const li=document.createElement('li');
    const button=document.createElement('button');button.className='path-step';
    const title=document.createElement('strong');title.textContent=step.name;
    const detail=document.createElement('span');detail.textContent=step.reason || stateLabel(step.state);
    button.append(title,detail);
    button.onclick=()=>{knowledgeMap.select(step.id,true);$('skill-detail').focus({preventScroll:true});};
    if(step.id===path.next_skill){li.className='next-step';button.setAttribute('aria-label',`${step.name}: suggested next step. ${step.reason || ''}`);}
    li.append(button);$('learning-path').append(li);
  }
  $('path-strengths').textContent=path?.strengths?.length ? `You can draw on: ${path.strengths.map(s=>s.name).join(', ')}.` : 'Your strengths will appear as you demonstrate skills independently.';
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
  if(!matches.length){const li=document.createElement('li');li.textContent='No matching skill. Try another word.';results.append(li);}
};
$('graph-search').onkeydown=event=>{if(event.key==='Escape'){$('graph-search').value='';$('graph-search').oninput();}if(event.key==='Enter'){document.querySelector('#graph-results button')?.click();}};
$('learning-goal').onchange=()=>run(async()=>{learningGoal=$('learning-goal').value||null;await refreshGraph();await refreshRecommendation();});
$('set-goal').onclick=()=>run(async()=>{learningGoal=selectedSkill;await refreshGraph();await refreshRecommendation();});
$('reflection').oninput=()=>{reflected=$('reflection').value.trim()===savedReflection && !!savedReflection;syncControls();};
$('save-reflection').onclick=()=>run(async()=>{
  feedbackVersion++; $('hint-source').textContent='';
  const reflection=$('reflection').value.trim();
  const result=await api('reflect',{session,reflection});
  reflected=!!result.reflection_saved;savedReflection=reflection;
  $('reflection-note').textContent='Your approach is saved. It is a thinking note, not a graded explanation.';
  $('feedback').textContent=result.message || 'Now compare your approach with the choices.';
  $('feedback').dataset.state='neutral';
  if(reflected){$('answer-stage').hidden=false;document.querySelector('#options button')?.focus();}
});
function showSkill(skill) {
  if (!skill) return;
  const probability = skill.probability === null ? 'No independent evidence yet.' : `Provisional estimate: ${Math.round(skill.probability*100)}%. ${skill.evidence} independent checks, ${skill.successes} successful.`;
  $('skill-detail').textContent = `${skill.name} · ${stateLabel(skill.state)}. ${skill.description} ${probability}`;
  $('skill-review').textContent = skill.next_review ? `${skill.due ? 'Review due' : 'Next review'}: ${new Date(skill.next_review).toLocaleDateString()}.` : 'A review will be scheduled after independent practice.';
}
async function refreshRecommendation(skill = null) {
  recommendation = await api('recommendation', {focus:session,language:$('language-filter').value || current?.language || 'eng',skill,goal:learningGoal});
  $('recommendation-title').textContent = recommendation.skill || 'Choose your next challenge';
  $('recommendation-kind').textContent = (recommendation.kind || 'next step').toUpperCase();
  $('recommendation-reason').textContent = recommendation.reason + (recommendation.language_fallback ? ' This check is available in English.' : '');
  syncControls();
}
$('start-recommended').onclick = () => run(async () => { if(recommendation?.problem) { await openProblem(recommendation.problem,recommendation.return_to); $('question').focus(); } });
$('practice-skill').onclick = () => run(async () => { await refreshRecommendation(selectedSkill); if(recommendation?.problem) { await openProblem(recommendation.problem); $('question').focus(); } });
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
    $('dataset-info').textContent = `${listing.filter(p => p.kind !== 'diagnostic').length} exercises · ${listing.filter(p => p.kind === 'diagnostic').length} short skill checks. Choose freely or follow your next step.`;
    $('language-filter').replaceChildren(new Option('All languages', ''));
    [...new Set(listing.map(p => p.language))].sort().forEach(lang => $('language-filter').append(new Option(lang, lang)));
    populateProblems();
    selectedSkill=null; session=''; current=null; learningGoal=null; feedbackVersion++;
    knowledgeMap.selected=null; knowledgeMap.query=''; knowledgeMap.focused=false; knowledgeMap.reset();
    $('graph-search').value=''; $('graph-results').hidden=true; $('graph-focus').setAttribute('aria-pressed','false');
    await refreshGraph(); await refreshRecommendation();
    await openProblem(recommendation.problem || $('problem-select').value, recommendation.return_to); $('workspace').hidden=false;
    $('skill-detail').textContent = 'Select a skill to see the evidence behind its state.';
    $('skill-review').textContent = '';
    $('question').focus();
  });
};
$('open-problem').onclick = () => run(async () => { await openProblem(); await refreshRecommendation(); $('question').focus(); });
$('submit').onclick = () => run(async () => {
  feedbackVersion++; $('hint-source').textContent='';
  if (!selected) throw new Error('Choose A, B, C, D or E first.');
  const result = await api('answer',{session,answer:selected});
  canReveal = !!result.can_reveal;
  $('feedback').textContent=result.message;
  $('feedback').dataset.state = result.correct ? 'correct' : 'retry';
  solved = result.correct;
  await refreshGraph();
  await refreshRecommendation();
});
for (const action of ['hint','solution']) $(''+action).onclick = () => run(async () => {
  const version = ++feedbackVersion;
  const result = await api(action,{session}); $('feedback').textContent=result.message; $('feedback').dataset.state = 'neutral';
  if ('can_reveal' in result) canReveal=!!result.can_reveal;
  $('hint-source').textContent = action === 'hint' ? `Hint ${result.rung || 1} · ${result.scope === 'skill' ? 'General skill guidance in English' : 'Authored problem guidance'}` : 'Authored explanation';
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
      if(result.status === 'done') { $('feedback').textContent=result.message; $('hint-source').textContent += result.source === 'local_model_selected' ? ' · Selected by the local tutor' : ' · Stored hint'; return; }
    } catch { return; }
  }
}
$('reveal').onclick = () => run(async () => {
  feedbackVersion++; $('hint-source').textContent='';
  const result = await api('reveal', {session});
  $('feedback').textContent = result.message;
  $('feedback').dataset.state = 'correct';
  [...$('options').children].forEach((button, index) => button.classList.toggle('correct-answer', 'ABCDE'[index] === result.answer));
  await refreshRecommendation();
});
syncControls();
