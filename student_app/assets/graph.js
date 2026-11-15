/* Offline, bounded force layout. Work happens in the student's browser once;
   there is no idle animation loop and no graph library to load on the board. */
class KnowledgeMap {
  constructor(svg, onSelect) {
    this.svg = svg; this.onSelect = onSelect; this.positions = new Map();
    this.transform = {x:0,y:0,k:1}; this.selected = null; this.query = ''; this.focused = false;
    this.skills = []; this.edges = []; this.pathIds = new Set(); this.signature = '';
    this.svg.setAttribute('viewBox','0 0 600 520');
    this.svg.addEventListener('pointerdown', event => this.begin(event));
    this.svg.addEventListener('pointermove', event => this.move(event));
    this.svg.addEventListener('pointerup', event => this.end(event));
    this.svg.addEventListener('pointercancel', event => this.end(event));
    this.svg.addEventListener('wheel', event => {
      if (!event.ctrlKey && !event.metaKey) return; // Ordinary scrolling still moves the page.
      event.preventDefault(); this.zoom(event.deltaY < 0 ? 1.12 : 1/1.12, this.point(event));
    }, {passive:false});
    this.svg.addEventListener('keydown', event => {
      if (event.target !== this.svg) return;
      if (event.key === '+' || event.key === '=') this.zoom(1.2);
      else if (event.key === '-') this.zoom(1/1.2);
      else if (event.key === '0') this.reset();
      else if (['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)) {
        const shifts={ArrowLeft:[35,0],ArrowRight:[-35,0],ArrowUp:[0,35],ArrowDown:[0,-35]};
        this.transform.x+=shifts[event.key][0]; this.transform.y+=shifts[event.key][1]; this.paintTransform();
      } else return;
      event.preventDefault();
    });
  }
  element(tag, attrs={}) {
    const node=document.createElementNS('http://www.w3.org/2000/svg',tag);
    Object.entries(attrs).forEach(([key,value])=>node.setAttribute(key,value)); return node;
  }
  point(event) {
    const point=this.svg.createSVGPoint(); point.x=event.clientX; point.y=event.clientY;
    return point.matrixTransform(this.svg.getScreenCTM().inverse());
  }
  setData(profile, selected) {
    this.skills=[...profile.skills].sort((a,b)=>a.id.localeCompare(b.id));
    const ids=new Set(this.skills.map(skill=>skill.id));
    this.edges=[...(profile.related_edges || []),...(profile.edges || [])].filter(e=>ids.has(e.source)&&ids.has(e.target));
    this.selected=selected; this.pathIds=new Set((profile.learning_path?.steps || []).map(step=>step.id));
    const signature=JSON.stringify([this.skills.map(s=>s.id),this.edges.map(e=>[e.source,e.target,e.kind,e.weight])]);
    if (this.signature!==signature) {this.signature=signature; this.layout();}
    this.draw();
  }
  layout() {
    const n=this.skills.length;
    this.skills.forEach((skill,i)=>this.positions.set(skill.id,{x:300+180*Math.cos(i*2*Math.PI/n-.5),y:260+180*Math.sin(i*2*Math.PI/n-.5)}));
    // Stable initial ordering and a fixed iteration budget make layout repeatable.
    for(let iteration=0;iteration<240;iteration++) {
      const forces=new Map(this.skills.map(skill=>[skill.id,{x:0,y:0}]));
      for(let i=0;i<n;i++) for(let j=i+1;j<n;j++) {
        const a=this.positions.get(this.skills[i].id), b=this.positions.get(this.skills[j].id);
        const dx=a.x-b.x,dy=a.y-b.y,d=Math.max(1,Math.hypot(dx,dy));
        const force=4300/(d*d)+(d<125 ? (125-d)*.05 : 0);
        const f=forces.get(this.skills[i].id),g=forces.get(this.skills[j].id);
        f.x+=dx/d*force; f.y+=dy/d*force; g.x-=dx/d*force; g.y-=dy/d*force;
      }
      for(const edge of this.edges) {
        const a=this.positions.get(edge.source),b=this.positions.get(edge.target);
        const dx=b.x-a.x,dy=b.y-a.y,d=Math.max(1,Math.hypot(dx,dy));
        const semantic=edge.kind==='semantic',weight=Math.max(0,Math.min(1,edge.weight ?? .5));
        const desired=semantic ? 185-weight*55 : 180;
        const force=(d-desired)*(semantic ? .012+weight*.012 : .015);
        const f=forces.get(edge.source),g=forces.get(edge.target);
        f.x+=dx/d*force;f.y+=dy/d*force;g.x-=dx/d*force;g.y-=dy/d*force;
      }
      const cooling=1-iteration/300;
      for(const skill of this.skills) {
        const p=this.positions.get(skill.id),f=forces.get(skill.id);
        p.x+=Math.max(-8,Math.min(8,f.x+(300-p.x)*.004))*cooling;
        p.y+=Math.max(-8,Math.min(8,f.y+(245-p.y)*.004))*cooling;
      }
    }
    const points=[...this.positions.values()];
    const minX=Math.min(...points.map(p=>p.x)),maxX=Math.max(...points.map(p=>p.x));
    const minY=Math.min(...points.map(p=>p.y)),maxY=Math.max(...points.map(p=>p.y));
    points.forEach(p=>{p.x=85+(p.x-minX)/Math.max(1,maxX-minX)*430;p.y=55+(p.y-minY)/Math.max(1,maxY-minY)*365;});
  }
  draw() {
    this.svg.replaceChildren();
    const defs=this.element('defs'), marker=this.element('marker',{id:'map-arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:5,markerHeight:5,orient:'auto'});
    marker.append(this.element('path',{d:'M0 0L10 5L0 10Z',fill:'#7c8a83'}));defs.append(marker);this.svg.append(defs);
    this.world=this.element('g',{'class':'graph-world'});this.svg.append(this.world);
    this.edgeNodes=[];this.nodeElements=new Map();
    for(const edge of this.edges) {
      const semantic=edge.kind==='semantic';
      const path=this.element('path',{'class':`map-edge ${semantic?'related-edge':'prerequisite-edge'}${!semantic&&this.pathIds.has(edge.source)&&this.pathIds.has(edge.target)?' path-edge':''}`});
      if(!semantic)path.setAttribute('marker-end','url(#map-arrow)');
      const title=this.element('title');title.textContent=semantic?'Related subject matter; not a prerequisite':'Supports learning';path.append(title);
      this.world.append(path);this.edgeNodes.push({edge,path});
    }
    for(const skill of this.skills) {
      const group=this.element('g',{tabindex:0,role:'button','class':'map-node','data-state':skill.display_state,'data-skill':skill.id,'aria-label':`${skill.name}: ${KnowledgeMap.stateLabel(skill.display_state)}`});
      const halo=this.element('circle',{r:28,class:'node-halo'});
      const circle=this.element('circle',{r:19,class:`node-dot ${skill.display_state}`});
      const symbol=this.element('text',{y:6,'text-anchor':'middle',class:'node-symbol','aria-hidden':'true'});
      symbol.textContent={not_assessed:'○',developing:'↗',demonstrated:'✓',due:'◷'}[skill.display_state]||'○';
      const label=this.element('text',{y:41,'text-anchor':'middle',class:'node-name'});
      let lines=[''];
      for(const word of skill.name.split(' ')){const last=lines.length-1;if((lines[last]+' '+word).trim().length>18)lines.push(word);else lines[last]=(lines[last]+' '+word).trim();}
      lines.forEach((line,i)=>{const span=this.element('tspan',{x:0,dy:i?16:0});span.textContent=line;label.append(span);});
      group.append(halo,circle,symbol,label);
      group.onclick=()=>{if(!this.suppressClick)this.select(skill.id);};
      group.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();this.select(skill.id);}};
      this.world.append(group);this.nodeElements.set(skill.id,group);
    }
    this.paintPositions();this.paintTransform();this.highlight();
  }
  paintPositions() {
    for(const {edge,path} of this.edgeNodes) {
      const a=this.positions.get(edge.source),b=this.positions.get(edge.target),dx=b.x-a.x,dy=b.y-a.y,d=Math.max(1,Math.hypot(dx,dy));
      path.setAttribute('d',`M${a.x+dx/d*23} ${a.y+dy/d*23} L${b.x-dx/d*26} ${b.y-dy/d*26}`);
    }
    this.nodeElements.forEach((group,id)=>{const p=this.positions.get(id);group.setAttribute('transform',`translate(${p.x} ${p.y})`);});
  }
  paintTransform() {if(this.world)this.world.setAttribute('transform',`translate(${this.transform.x} ${this.transform.y}) scale(${this.transform.k})`);}
  select(id,center=false) {
    this.selected=id;this.highlight();
    if(center){const p=this.positions.get(id);this.transform={x:300-p.x*1.5,y:240-p.y*1.5,k:1.5};this.paintTransform();}
    this.onSelect(this.skills.find(s=>s.id===id));
  }
  highlight() {
    const neighbors=new Set([this.selected]);
    this.edges.forEach(e=>{if(e.source===this.selected)neighbors.add(e.target);if(e.target===this.selected)neighbors.add(e.source);});
    const matching=new Set(this.skills.filter(s=>s.name.toLowerCase().includes(this.query.toLowerCase())).map(s=>s.id));
    const visible=id=>(!this.focused||!this.selected||neighbors.has(id))&&(!this.query||matching.has(id));
    this.nodeElements?.forEach((group,id)=>{
      group.setAttribute('aria-pressed',String(id===this.selected));
      group.classList.toggle('dimmed',!visible(id));
      group.classList.toggle('on-path',this.pathIds.has(id));
    });
    this.edgeNodes?.forEach(({edge,path})=>path.classList.toggle('dimmed',!visible(edge.source)||!visible(edge.target)));
  }
  zoom(factor,point={x:300,y:260}) {
    const next=Math.min(3,Math.max(.6,this.transform.k*factor)),ratio=next/this.transform.k;
    this.transform.x=point.x-(point.x-this.transform.x)*ratio;this.transform.y=point.y-(point.y-this.transform.y)*ratio;this.transform.k=next;this.paintTransform();
  }
  reset() {this.transform={x:0,y:0,k:1};this.paintTransform();}
  begin(event) {
    if(this.drag||event.button!==0)return;
    const point=this.point(event),node=event.target.closest('[data-skill]');
    this.drag={pointer:event.pointerId,id:node?.dataset.skill,point,start:point,moved:false};this.suppressClick=false;
    this.svg.setPointerCapture(event.pointerId);
  }
  move(event) {
    if(!this.drag||event.pointerId!==this.drag.pointer)return;
    const point=this.point(event),dx=point.x-this.drag.point.x,dy=point.y-this.drag.point.y;
    if(Math.hypot(point.x-this.drag.start.x,point.y-this.drag.start.y)>5)this.drag.moved=true;
    if(this.drag.moved){
      if(this.drag.id){const p=this.positions.get(this.drag.id);p.x+=dx/this.transform.k;p.y+=dy/this.transform.k;this.paintPositions();}
      else{this.transform.x+=dx;this.transform.y+=dy;this.paintTransform();}
    }
    this.drag.point=point;
  }
  end(event) {
    if(!this.drag||event.pointerId!==this.drag.pointer)return;
    const {id,moved}=this.drag;this.suppressClick=moved;this.drag=null;
    if(this.svg.hasPointerCapture(event.pointerId))this.svg.releasePointerCapture(event.pointerId);
    // Pointer capture retargets clicks to the SVG, so select on release as well.
    if(id&&!moved)this.select(id);
    setTimeout(()=>{this.suppressClick=false;},0);
  }
  // Child-facing labels; the server sends localised ones in profile.state_labels.
  static stateLabel(value) {return (KnowledgeMap.labels||{})[value]||{not_assessed:'Not tried yet',developing:'Getting there',demonstrated:'Got it',due:'Time to review'}[value]||value;}
}
window.KnowledgeMap=KnowledgeMap;
