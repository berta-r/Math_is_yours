/* Child-facing state labels, shared by the tree and app.js. The server sends
   localised ones in profile.state_labels; these are the English fallbacks. */
class KnowledgeMap {
  static stateLabel(value) {return (KnowledgeMap.labels||{})[value]||{not_assessed:'Not tried yet',developing:'Getting there',demonstrated:'Got it',due:'Time to review'}[value]||value;}
}
window.KnowledgeMap=KnowledgeMap;

/* Layered, left-to-right skill tree. Prerequisites sit to the left of what they
   unlock; the layout is computed once per data change, with no pan, zoom or physics. */
const SVG_NS='http://www.w3.org/2000/svg';
const TREE={nodeW:220,laneH:16,lineH:22,padTop:14,padX:14,stateH:22,padBottom:12,colGap:110,rowGap:28,margin:14,glyphW:28};
class SkillTree {
  constructor(svg,onSelect) {
    this.svg=svg;this.onSelect=onSelect;this.skills=[];this.edges=[];this.selected=null;
    this.path=null;this.goal=null;this.nextSkill=null;this.measure=document.createElement('canvas').getContext('2d');
    // Labels are measured with the bundled font; redraw once it has loaded.
    document.fonts?.ready?.then(()=>{if(this.skills.length)this.draw();});
  }
  element(tag,attrs={}) {
    const node=document.createElementNS(SVG_NS,tag);
    Object.entries(attrs).forEach(([key,value])=>node.setAttribute(key,value));return node;
  }
  // goal: the goal the student chose (null = "Guide me"); the server always proposes a route.
  setData(profile,selected=null,goal=null) {
    this.skills=profile.skills||[];
    const ids=new Set(this.skills.map(s=>s.id));
    this.edges=(profile.edges||[]).filter(e=>ids.has(e.source)&&ids.has(e.target)&&e.source!==e.target);
    this.selected=selected;this.goal=goal&&ids.has(goal)?goal:null;
    this.path=profile.learning_path||null;this.nextSkill=this.path?.next_skill||null;
    this.draw();
  }
  state(skill) {return skill.display_state||skill.state||'not_assessed';}
  // Greedy word wrap against the real text width; a single long word keeps its own line.
  wrap(text) {
    const font=getComputedStyle(this.svg).getPropertyValue('--tree-font').trim()||'Archivo, Arial, sans-serif';
    this.measure.font=`700 18px ${font}`;
    const fits=document.fonts?.check?.(`700 18px ${font}`)!==false;
    const max=TREE.nodeW-2*TREE.padX-TREE.glyphW,width=s=>this.measure.measureText(s).width*(fits?1:1.12);
    const lines=[];
    for(const word of text.split(/\s+/).filter(Boolean)) {
      const last=lines.length-1;
      if(last>=0&&width(lines[last]+' '+word)<=max)lines[last]+=' '+word;else lines.push(word);
    }
    return lines.length?lines:[''];
  }
  layout() {
    const byId=new Map(this.skills.map(s=>[s.id,s])),prereqs=new Map(),children=new Map();
    this.skills.forEach(s=>{prereqs.set(s.id,[]);children.set(s.id,[]);});
    this.edges.forEach(e=>{prereqs.get(e.target).push(e.source);children.get(e.source).push(e.target);});
    // Layer = longest path from a root (memoised; a cycle, if any, is cut where found).
    const layer=new Map(),visiting=new Set();
    const depth=id=>{
      if(layer.has(id))return layer.get(id);
      if(visiting.has(id))return 0;
      visiting.add(id);const value=Math.max(-1,...prereqs.get(id).map(depth))+1;visiting.delete(id);
      layer.set(id,value);return value;
    };
    this.skills.forEach(s=>depth(s.id));
    const count=Math.max(0,...layer.values())+1;
    const columns=Array.from({length:count},()=>[]);
    this.skills.forEach(s=>columns[layer.get(s.id)].push(s.id));
    // An edge that skips a column gets a waypoint in each column it crosses, so it runs
    // through a gap between boxes instead of disappearing behind one.
    const up=new Map(prereqs),down=new Map(children),label=new Map(this.skills.map(s=>[s.id,s.name]));
    this.routes=new Map();
    this.edges.forEach((e,i)=>{
      const from=layer.get(e.source),to=layer.get(e.target);
      if(to<=from+1){this.routes.set(e,[]);return;}
      const points=[];let previous=e.source;
      for(let c=from+1;c<to;c++){
        const id=`~${i}~${c}`;points.push(id);columns[c].push(id);label.set(id,label.get(e.target)+label.get(e.source));
        up.set(id,[previous]);down.set(id,[]);down.get(previous)?.push(id);previous=id;
      }
      down.set(previous,[e.target]);up.set(e.target,up.get(e.target).map(x=>x===e.source?previous:x));
      down.set(e.source,down.get(e.source).filter(x=>x!==e.target));
      this.routes.set(e,points);
    });
    const name=id=>label.get(id);
    columns.forEach(col=>col.sort((a,b)=>name(a).localeCompare(name(b))));
    // Node height fits the longest wrapped name: every box in the tree has the same size.
    this.lines=new Map(this.skills.map(s=>[s.id,this.wrap(s.name)]));
    const maxLines=Math.max(1,...[...this.lines.values()].map(l=>l.length));
    this.nodeH=TREE.padTop+maxLines*TREE.lineH+TREE.stateH+TREE.padBottom;
    const size=id=>id.startsWith('~')?TREE.laneH:this.nodeH;
    const span=col=>col.reduce((sum,id)=>sum+size(id),0)+Math.max(0,col.length-1)*TREE.rowGap;
    this.width=2*TREE.margin+count*TREE.nodeW+(count-1)*TREE.colGap;
    this.height=2*TREE.margin+Math.max(...columns.map(span));
    const place=()=>{
      this.pos=new Map();
      columns.forEach((col,c)=>{
        let y=(this.height-span(col))/2;
        col.forEach(id=>{this.pos.set(id,{x:TREE.margin+c*(TREE.nodeW+TREE.colGap),y,h:size(id)});y+=size(id)+TREE.rowGap;});
      });
    };
    // Barycentre sweeps reduce crossings: forward on prerequisites, backward on what they unlock.
    const centre=id=>{const p=this.pos.get(id);return p.y+p.h/2;};
    const sortBy=(col,neighbours)=>{
      const value=new Map(col.map(id=>{const n=neighbours.get(id)||[];return [id,n.length?n.reduce((s,x)=>s+centre(x),0)/n.length:centre(id)];}));
      col.sort((a,b)=>value.get(a)-value.get(b)||name(a).localeCompare(name(b)));
    };
    place();
    for(let sweep=0;sweep<3;sweep++) {
      for(let c=1;c<count;c++){sortBy(columns[c],up);place();}
      for(let c=count-2;c>=0;c--){sortBy(columns[c],down);place();}
    }
    for(let c=1;c<count;c++){sortBy(columns[c],up);place();}
    this.order=columns.flat().filter(id=>!id.startsWith('~'));
  }
  draw() {
    if(!this.skills.length){this.svg.replaceChildren();return;}
    this.layout();
    const W=TREE.nodeW,H=this.nodeH;
    this.svg.replaceChildren();
    this.svg.setAttribute('viewBox',`0 0 ${this.width} ${this.height}`);
    this.svg.setAttribute('preserveAspectRatio','xMidYMid meet');
    this.svg.style.setProperty('--tree-width',`${this.width}px`);
    const defs=this.element('defs');
    for(const [id,cls] of [['tree-arrow','arrow'],['tree-arrow-path','arrow arrow-path']]) {
      const marker=this.element('marker',{id,viewBox:'0 0 10 10',refX:10,refY:5,markerWidth:11,markerHeight:11,markerUnits:'userSpaceOnUse',orient:'auto'});
      marker.append(this.element('path',{d:'M0 0L10 5L0 10Z','class':cls}));defs.append(marker);
    }
    this.svg.append(defs);
    // Path membership: a chosen goal colours its whole route; "Guide me" marks only the next skill.
    const steps=this.goal?(this.path?.steps||[]).map(s=>s.id):[];
    const pathSet=new Set(this.goal?[...steps,this.goal]:[]);
    const rank=new Map(steps.map((id,i)=>[id,i]));
    const onPath=e=>pathSet.has(e.source)&&pathSet.has(e.target)&&(e.target===this.goal||(rank.has(e.source)&&rank.has(e.target)&&rank.get(e.source)<rank.get(e.target)));
    // Spread the ports so arrows into one box do not land on top of each other.
    const outgoing=new Map(),incoming=new Map();
    for(const e of this.edges){(outgoing.get(e.source)||outgoing.set(e.source,[]).get(e.source)).push(e);(incoming.get(e.target)||incoming.set(e.target,[]).get(e.target)).push(e);}
    const hop=(edge,key)=>{const w=this.routes.get(edge)||[];return key==='target'?(w[0]||edge.target):(w[w.length-1]||edge.source);};
    const port=(list,e,key)=>{
      const sorted=[...list].sort((a,b)=>this.pos.get(hop(a,key)).y-this.pos.get(hop(b,key)).y);
      const step=Math.min(14,(H-24)/Math.max(1,sorted.length-1));
      return (sorted.indexOf(e)-(sorted.length-1)/2)*step;
    };
    const edgeLayer=this.element('g',{'class':'tree-edges','aria-hidden':'true'}),pathLayer=this.element('g',{'class':'tree-path-edges','aria-hidden':'true'});
    for(const e of this.edges) {
      const a=this.pos.get(e.source),b=this.pos.get(e.target),waypoints=this.routes.get(e)||[];
      // Ports are ordered by where the edge goes next, so neighbouring arrows do not cross.
      let x=a.x+W,y=a.y+H/2+port(outgoing.get(e.source),e,'target');
      const x2=b.x-2,y2=b.y+H/2+port(incoming.get(e.target),e,'source');
      const curve=(tx,ty)=>{const bend=Math.max(40,(tx-x)*.5);const d=`C${x+bend} ${y} ${tx-bend} ${ty} ${tx} ${ty}`;x=tx;y=ty;return d;};
      let d=`M${x} ${y}`;
      for(const id of waypoints){const p=this.pos.get(id),cy=p.y+p.h/2;d+=curve(p.x,cy)+`L${p.x+W} ${cy}`;x=p.x+W;}
      d+=curve(x2,y2);
      const highlighted=onPath(e);
      const edge=this.element('path',{d,'class':`tree-edge${highlighted?' path-edge':''}`,'marker-end':`url(#${highlighted?'tree-arrow-path':'tree-arrow'})`,'data-source':e.source,'data-target':e.target});
      (highlighted?pathLayer:edgeLayer).append(edge);
    }
    this.svg.append(edgeLayer,pathLayer);
    this.nodes=new Map();
    for(const id of this.order) {
      const skill=this.skills.find(s=>s.id===id),state=this.state(skill),p=this.pos.get(id);
      const isGoal=id===this.goal,isNext=!this.goal&&id===this.nextSkill,inPath=pathSet.has(id);
      const classes=['tree-node',`state-${state}`];
      if(isGoal)classes.push('is-goal');else if(inPath&&skill.state!=='demonstrated')classes.push('on-path');
      if(isNext&&skill.state!=='demonstrated')classes.push('on-path','is-next');
      const label=`${skill.name}: ${KnowledgeMap.stateLabel(state)}`;
      const group=this.element('g',{'class':classes.join(' '),role:'button',tabindex:0,'data-id':id,'data-state':state,'aria-pressed':String(id===this.selected),'aria-label':label,transform:`translate(${p.x} ${p.y})`});
      group.append(this.element('rect',{'class':'focus-ring',x:-10,y:-10,width:W+20,height:H+20}));
      group.append(this.element('rect',{'class':'select-ring',x:-6,y:-6,width:W+12,height:H+12}));
      group.append(this.element('rect',{'class':'box',x:0,y:0,width:W,height:H}));
      const name=this.element('text',{'class':'node-name',x:TREE.padX,y:TREE.padTop});
      this.lines.get(id).forEach((line,i)=>{const span=this.element('tspan',{x:TREE.padX,dy:i?TREE.lineH:16});span.textContent=line;name.append(span);});
      const status=this.element('text',{'class':'node-state',x:TREE.padX,y:H-TREE.padBottom-4});status.textContent=KnowledgeMap.stateLabel(state);
      group.append(name,status);
      if(isGoal) group.append(this.element('rect',{'class':'goal-mark',x:W-26,y:12,width:14,height:14}));
      else {
        const glyph={demonstrated:'✓',developing:'↗',due:'◷'}[state];
        if(glyph){const g=this.element('text',{'class':'node-glyph',x:W-12,y:30,'text-anchor':'end','aria-hidden':'true'});g.textContent=glyph;group.append(g);}
      }
      const title=this.element('title');title.textContent=label;group.append(title);
      group.addEventListener('click',()=>this.select(id));
      group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();this.select(id);}});
      this.svg.append(group);this.nodes.set(id,group);
    }
  }
  // When the tree scrolls sideways (phones), bring a skill to the left edge of the window.
  reveal(id) {
    const group=this.nodes?.get(id),box=this.svg.parentElement;
    if(!group||!box||box.scrollWidth<=box.clientWidth)return;
    box.scrollLeft+=group.getBoundingClientRect().left-box.getBoundingClientRect().left-24;
  }
  select(id) {
    this.selected=id;
    this.nodes?.forEach((group,key)=>group.setAttribute('aria-pressed',String(key===id)));
    this.onSelect(this.skills.find(s=>s.id===id));
  }
}
window.SkillTree=SkillTree;
