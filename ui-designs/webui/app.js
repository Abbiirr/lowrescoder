'use strict';
/* AutoCode WebUI — views + actions (classic script), ported from AutoCode.html
   (which implements the Claude Design source AutoCode.dc.html). Behaviour and visuals
   are identical to the standalone prototype when running in demo mode.

   LIVE-MODE SEAM: a later task (T3) builds window.Live from window.RPC + window.Reducer
   (rpc.js + events.js). Where a surface should talk to a real backend, this file routes
   through live() and falls back to the demo behavior when live() is null. Every such
   point is tagged with a `/* LIVE SEAM: ... *​/` comment describing the contract. */

/* LIVE SEAM: demo/live switch — live() returns the active live adapter, or null.
   Null ⇒ demo mode, so every seam below falls back to DEMO. window.Live is created and
   enabled by T3; index.html disables it for ?demo=1 (see applyDemoFlag/init). */
function live(){ return window.Live && window.Live.enabled ? window.Live : null; }

/* ---------- demo data (sourced from demo.js / window.DEMO) ---------- */
var DEMO = window.DEMO || {};
var THREADS = DEMO.THREADS, BASE_ROWS = DEMO.BASE_ROWS, COMPL = DEMO.COMPL,
    SKILLS_POP = DEMO.SKILLS_POP, MODES = DEMO.MODES, MODELS = DEMO.MODELS,
    QUICK_CHIPS = DEMO.QUICK_CHIPS, REVIEW_FILES = DEMO.REVIEW_FILES, DIFFS = DEMO.DIFFS,
    AUTOMATIONS = DEMO.AUTOMATIONS, SKILL_CARDS = DEMO.SKILL_CARDS, PERM_CARDS = DEMO.PERM_CARDS,
    PERM_TOGGLES = DEMO.PERM_TOGGLES, FILE_TREE = DEMO.FILE_TREE;

/* ---------- palettes ---------- */
var PAL = {
  glass: {
    dark: { desk:'#05060a', deskimg:'radial-gradient(1100px 700px at 75% -10%,rgba(64,96,192,.5),transparent 60%),radial-gradient(900px 650px at 8% 108%,rgba(120,64,160,.38),transparent 55%)', win:'rgba(13,16,24,.82)', panel:'rgba(255,255,255,.035)', panel2:'rgba(255,255,255,.055)', glass:'rgba(20,24,36,.85)', hov:'rgba(255,255,255,.06)', sel:'rgba(101,141,255,.13)', line:'rgba(255,255,255,.075)', line2:'rgba(255,255,255,.14)', t1:'#edf0f7', t2:'#9aa3b8', t3:'#5f6880', acc:'#658dff', accInk:'#070b16', accSoft:'rgba(101,141,255,.16)', ok:'#42d392', okSoft:'rgba(66,211,146,.12)', warn:'#f0b34e', warnSoft:'rgba(240,179,78,.13)', err:'#f26d78', errSoft:'rgba(242,109,120,.12)', blur:'20px', r:'10px', rlg:'16px', shadow:'0 32px 90px rgba(0,0,0,.6)' },
    light: { desk:'#e7eaf3', deskimg:'radial-gradient(1000px 650px at 78% -8%,rgba(99,132,255,.28),transparent 60%),radial-gradient(850px 600px at 5% 106%,rgba(190,120,255,.22),transparent 55%)', win:'rgba(252,253,255,.86)', panel:'rgba(255,255,255,.55)', panel2:'rgba(255,255,255,.85)', glass:'rgba(255,255,255,.94)', hov:'rgba(23,32,60,.05)', sel:'rgba(59,111,232,.1)', line:'rgba(23,32,60,.09)', line2:'rgba(23,32,60,.17)', t1:'#181d2a', t2:'#59637b', t3:'#9aa2b6', acc:'#3b6fe8', accInk:'#ffffff', accSoft:'rgba(59,111,232,.12)', ok:'#149457', okSoft:'rgba(20,148,87,.1)', warn:'#b26205', warnSoft:'rgba(178,98,5,.1)', err:'#d7263d', errSoft:'rgba(215,38,61,.08)', blur:'20px', r:'10px', rlg:'16px', shadow:'0 28px 80px rgba(30,40,80,.28)' }
  },
  mono: {
    dark: { desk:'#000000', deskimg:'none', win:'#0d0d0d', panel:'rgba(255,255,255,.028)', panel2:'rgba(255,255,255,.05)', glass:'#161616', hov:'rgba(255,255,255,.055)', sel:'rgba(255,255,255,.09)', line:'#202020', line2:'#303030', t1:'#f1f1f1', t2:'#8f8f8f', t3:'#575757', acc:'#f5f5f5', accInk:'#0b0b0b', accSoft:'rgba(255,255,255,.1)', ok:'#3ecf8e', okSoft:'rgba(62,207,142,.1)', warn:'#d9a13c', warnSoft:'rgba(217,161,60,.12)', err:'#e5484d', errSoft:'rgba(229,72,77,.12)', blur:'0px', r:'7px', rlg:'10px', shadow:'0 24px 60px rgba(0,0,0,.7)' },
    light: { desk:'#e9e9e9', deskimg:'none', win:'#fcfcfc', panel:'rgba(0,0,0,.026)', panel2:'rgba(0,0,0,.045)', glass:'#ffffff', hov:'rgba(0,0,0,.05)', sel:'rgba(0,0,0,.07)', line:'#e4e4e4', line2:'#cfcfcf', t1:'#141414', t2:'#6e6e6e', t3:'#a3a3a3', acc:'#141414', accInk:'#ffffff', accSoft:'rgba(0,0,0,.07)', ok:'#17853f', okSoft:'rgba(23,133,63,.09)', warn:'#9a6700', warnSoft:'rgba(154,103,0,.1)', err:'#d13438', errSoft:'rgba(209,52,56,.08)', blur:'0px', r:'7px', rlg:'10px', shadow:'0 20px 50px rgba(0,0,0,.18)' }
  },
  warm: {
    dark: { desk:'#0d0906', deskimg:'radial-gradient(1000px 650px at 80% -10%,rgba(214,140,50,.24),transparent 60%),radial-gradient(800px 600px at 5% 108%,rgba(150,80,45,.2),transparent 55%)', win:'rgba(26,19,12,.88)', panel:'rgba(255,214,160,.05)', panel2:'rgba(255,214,160,.08)', glass:'rgba(34,25,16,.9)', hov:'rgba(255,214,160,.08)', sel:'rgba(231,154,60,.15)', line:'rgba(255,214,160,.1)', line2:'rgba(255,214,160,.19)', t1:'#f5eddf', t2:'#ab9d88', t3:'#6f6353', acc:'#e79a3c', accInk:'#1c1206', accSoft:'rgba(231,154,60,.16)', ok:'#85ca8f', okSoft:'rgba(133,202,143,.12)', warn:'#e7c34c', warnSoft:'rgba(231,195,76,.13)', err:'#e4685f', errSoft:'rgba(228,104,95,.13)', blur:'16px', r:'10px', rlg:'14px', shadow:'0 30px 80px rgba(0,0,0,.55)' },
    light: { desk:'#ece4d6', deskimg:'radial-gradient(950px 600px at 80% -8%,rgba(230,170,90,.3),transparent 60%),radial-gradient(800px 560px at 4% 106%,rgba(200,140,80,.18),transparent 55%)', win:'rgba(253,250,244,.92)', panel:'rgba(255,252,246,.65)', panel2:'rgba(255,254,250,.92)', glass:'rgba(255,253,248,.96)', hov:'rgba(90,70,40,.06)', sel:'rgba(176,106,26,.12)', line:'rgba(90,70,40,.13)', line2:'rgba(90,70,40,.24)', t1:'#271e12', t2:'#6f6250', t3:'#a3947e', acc:'#b06a1a', accInk:'#ffffff', accSoft:'rgba(176,106,26,.12)', ok:'#3f7d47', okSoft:'rgba(63,125,71,.1)', warn:'#8f6400', warnSoft:'rgba(143,100,0,.1)', err:'#bf3a30', errSoft:'rgba(191,58,48,.09)', blur:'16px', r:'10px', rlg:'14px', shadow:'0 24px 60px rgba(80,60,30,.22)' }
  }
};
var CODE_PAL = {
  light: { kw:'#7c3aed', ty:'#0f7490', fn:'#1d4fd8', st:'#237a3b', nu:'#a15c07', cm:'#97a1b5', pn:'#2a3345', gh:'#9aa4b8' },
  dark:  { kw:'#b990ff', ty:'#6fd4e8', fn:'#82aaff', st:'#9ad98f', nu:'#f2b46d', cm:'#5c6579', pn:'#ccd5e8', gh:'#67718a' }
};

/* ---------- state ---------- */
var state = {
  dir:'glass', theme:'dark', view:'home', threadId:'t1', tab:'chat', editorOpen:false, reviewOpen:false,
  search:'', composerHome:'', composerThread:'',
  popSkills:false, popMode:false, popModel:false,
  mode:'Worktree', model:'AC-1 High', reasoning:'High',
  exp:{}, approval:'pending', showApprovalOut:false,
  ghostDone:false, l22:'error', complIdx:0, hoverOn:false, sigOn:false, peekOn:false, hintsOn:true,
  staged:{f1:true,f2:true,f3:false}, diffFile:'f1',
  commitMsg:'fix: clamp chargeable time at venue close', prState:null,
  autos:{a1:true,a2:true,a3:false},
  permPolicy:'balanced', permNet:false, permTests:true,
  mcpStripe:'error', mcpGithub:true, mcpPg:true,
  toasts:[], extras:{}, thinking:{}, newThreads:[]
};
var hoverT = null, toastSeq = 0;

function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function set(patch){ Object.assign(state, patch); render(); }

/* ---------- derived data (with live seams) ---------- */
function baseRows(id){
  if (BASE_ROWS[id]) return BASE_ROWS[id];
  for (var i=0;i<state.newThreads.length;i++) if (state.newThreads[i].id===id) return state.newThreads[i].rows;
  return [];
}
function allThreads(){
  var q = (state.search||'').toLowerCase();
  /* LIVE SEAM: sessions data source — in live mode the thread list is the reducer's
     session model (session.list + on_status), not DEMO.THREADS. openThread → session.resume,
     newThread → session.new, onSearch filters the same list. T3 supplies live().sessions(). */
  var L = live();
  var base;
  if (L && L.sessions) {
    base = L.sessions();
  } else {
    var nts = state.newThreads.map(function(t){ return Object.assign({}, t, { badge:null }); });
    base = nts.concat(THREADS);
  }
  return base.filter(function(t){ return !q || t.title.toLowerCase().indexOf(q) !== -1; });
}
function costMeter(){
  /* LIVE SEAM: cost meter — live().cost() supplies usage % from on_cost_update
     (Plan & usage). Demo returns the prototype's fixed 62%. */
  var L = live();
  if (L && L.cost) return L.cost();
  return { pct: 62 };
}
function skillsPop(){
  /* LIVE SEAM: skills list — command.list drives skills in live mode; demo uses
     DEMO.SKILLS_POP (composer popover) and DEMO.SKILL_CARDS (skills page). */
  var L = live();
  return (L && L.skillsPop) ? L.skillsPop() : SKILLS_POP;
}
function skillCards(){
  var L = live();
  return (L && L.skillCards) ? L.skillCards() : SKILL_CARDS;
}

/* ---------- icons ---------- */
function svg(w, stroke, body, extra){
  return '<svg width="'+w+'" height="'+w+'" viewBox="0 0 24 24" fill="none" stroke="'+stroke+'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'+(extra||'')+'>'+body+'</svg>';
}
var I = {
  folder: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>',
  branch: '<line x1="6" x2="6" y1="3" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"></path>',
  sun: '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path>',
  plus: '<path d="M12 5v14M5 12h14"></path>',
  search: '<circle cx="11" cy="11" r="7"></circle><path d="m21 21-4.3-4.3"></path>',
  spinner: '<path d="M21 12a9 9 0 1 1-9-9" stroke-linecap="round"></path>',
  chevR: '<path d="m9 18 6-6-6-6"></path>',
  chevD: '<path d="m6 9 6 6 6-6"></path>',
  chevL: '<path d="m15 18-6-6 6-6"></path>',
  check: '<path d="M20 6 9 17l-5-5"></path>',
  clock: '<circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 3"></path>',
  plan: '<path d="M9 11H4a2 2 0 0 0-2 2v7h20v-7a2 2 0 0 0-2-2h-5"></path><path d="M9 3h6v8H9z"></path>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"></path><circle cx="12" cy="12" r="3"></circle>',
  term: '<path d="m4 17 6-6-6-6"></path><path d="M12 19h8"></path>',
  pencil: '<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"></path>',
  warnTri: '<path d="M12 9v4"></path><path d="M12 17h.01"></path><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"></path>',
  expand: '<path d="M16 3h5v5"></path><path d="M8 3H3v5"></path><path d="M21 3l-7 7"></path><path d="M3 3l7 7"></path><path d="M16 21h5v-5"></path><path d="M8 21H3v-5"></path><path d="M21 21l-7-7"></path><path d="M3 21l7-7"></path>',
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"></path>',
  reset: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path>',
  x: '<path d="M18 6 6 18M6 6l12 12"></path>',
  pr: '<circle cx="18" cy="18" r="3"></circle><circle cx="6" cy="6" r="3"></circle><path d="M13 6h3a2 2 0 0 1 2 2v7"></path><line x1="6" x2="6" y1="9" y2="21"></line>',
  cube: '<path d="M12.89 1.45l8 4A2 2 0 0 1 22 7.24v9.53a2 2 0 0 1-1.11 1.79l-8 4a2 2 0 0 1-1.78 0l-8-4a2 2 0 0 1-1.11-1.8V7.24a2 2 0 0 1 1.11-1.79l8-4a2 2 0 0 1 1.78 0z"></path>',
  probs: '<circle cx="12" cy="12" r="9"></circle><path d="m15 9-6 6M9 9l6 6"></path>',
  bell: '<path d="M12 3a6 6 0 0 0-6 6v4.5l-1.5 3h15L18 13.5V9a6 6 0 0 0-6-6z"></path><path d="M9.5 20a2.5 2.5 0 0 0 5 0"></path>',
  upArrow: '<path d="M12 19V5M5 12l7-7 7 7"></path>'
};
function spinnerIcon(w, color){ return '<svg width="'+w+'" height="'+w+'" viewBox="0 0 24 24" fill="none" stroke="'+color+'" stroke-width="2.5" style="animation:spin .9s linear infinite;flex:none">'+I.spinner+'</svg>'; }
function badgeStyles(k){ return k==='warn' ? {cl:'var(--warn)',bg:'var(--warn-soft)'} : k==='ok' ? {cl:'var(--ok)',bg:'var(--ok-soft)'} : {cl:'var(--t3)',bg:'var(--panel2)'}; }

/* ---------- titlebar ---------- */
function titlebar(c){
  var dirs = [['glass','Glass'],['mono','Mono'],['warm','Warm']].map(function(d){
    var on = c.dir===d[0];
    return '<button onclick="event.stopPropagation();A.setDir(\''+d[0]+'\')" class="hvc" style="padding:3px 14px;border-radius:999px;font-size:11.5px;font-weight:600;color:'+(on?'var(--t1)':'var(--t3)')+';background:'+(on?'var(--sel)':'transparent')+';transition:background .15s,color .15s">'+d[1]+'</button>';
  }).join('');
  return '<div style="position:relative;height:46px;flex:none;display:flex;align-items:center;gap:14px;padding:0 16px;border-bottom:1px solid var(--line);user-select:none">'
    + '<div style="display:flex;gap:8px;align-items:center">'
    +   '<span style="width:12px;height:12px;border-radius:50%;background:#ff5f57;display:inline-block"></span>'
    +   '<span style="width:12px;height:12px;border-radius:50%;background:#febc2e;display:inline-block"></span>'
    +   '<span style="width:12px;height:12px;border-radius:50%;background:#28c840;display:inline-block"></span>'
    + '</div>'
    + '<div style="display:flex;align-items:center;gap:8px">'
    +   '<span style="font-weight:700;font-size:13px;letter-spacing:-.2px">AutoCode</span>'
    +   '<button class="hvt" style="display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--t2);font-size:11.5px;transition:background .15s">'
    +     svg(12,'currentColor',I.folder) + 'cyberstation-spa <span style="color:var(--t3)">·</span> ' + svg(11,'currentColor',I.branch) + ' main'
    +   '</button>'
    + '</div>'
    + '<div style="position:absolute;left:50%;transform:translateX(-50%);display:flex;background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:3px;gap:2px">'+dirs+'</div>'
    + '<div style="margin-left:auto;display:flex;align-items:center;gap:10px">'
    +   '<button onclick="A.toggleTheme()" title="Toggle theme" class="hvt a93" style="width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;border-radius:var(--r);color:var(--t2);transition:background .15s">'
    +     svg(15,'currentColor', c.theme==='dark' ? I.moon : I.sun)
    +   '</button>'
    +   '<span style="width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,var(--acc),#b17ae8);border:1px solid var(--line2);display:inline-block"></span>'
    + '</div>'
    + '</div>';
}

/* ---------- sidebar ---------- */
function sideThreadItem(t, c, inActive){
  var b = badgeStyles(t.badgeKind);
  var dot = t.running ? 'var(--acc)' : t.done ? 'var(--ok)' : 'var(--t3)';
  var anim = (inActive && t.running) ? 'pulse 1.6s ease infinite' : 'none';
  var bg = (c.view==='thread' && c.threadId===t.id) ? 'var(--sel)' : 'transparent';
  return '<button onclick="A.openThread(\''+t.id+'\')" class="hv a99" style="display:flex;align-items:center;gap:9px;padding:7px 9px;border-radius:var(--r);background:'+bg+';transition:background .12s">'
    + '<span style="width:7px;height:7px;flex:none;border-radius:50%;background:'+dot+';animation:'+anim+'"></span>'
    + '<span style="flex:1;min-width:0">'
    +   '<span style="display:block;font-size:12.5px;font-weight:550;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+esc(t.title)+'</span>'
    +   '<span style="display:block;font-size:10.5px;color:var(--t3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px">'+esc(t.meta)+'</span>'
    + '</span>'
    + (t.badge ? '<span style="flex:none;font-size:10px;font-weight:650;color:'+b.cl+';background:'+b.bg+';padding:2px 7px;border-radius:999px">'+esc(t.badge)+'</span>' : '')
    + '</button>';
}
function sidebar(c){
  var threads = allThreads();
  var cm = costMeter();
  var nav = [
    { label:'Threads', v:'home', meta:'5' },
    { label:'Automations', v:'automations', meta:'2 on' },
    { label:'Skills', v:'skills', meta:'6' },
    { label:'Settings', v:'settings', meta:'' }
  ].map(function(n){
    var on = c.view===n.v;
    return '<button onclick="A.setView(\''+n.v+'\')" class="hvt a99" style="display:flex;align-items:center;gap:9px;height:30px;padding:0 9px;border-radius:var(--r);font-size:12.5px;font-weight:550;color:'+(on?'var(--t1)':'var(--t2)')+';background:'+(on?'var(--sel)':'transparent')+';transition:background .12s,color .12s">'
      + n.label + '<span style="margin-left:auto;font-size:10.5px;color:var(--t3)">'+n.meta+'</span></button>';
  }).join('');
  var act = threads.filter(function(t){return t.group==='active';}).map(function(t){return sideThreadItem(t,c,true);}).join('');
  var rec = threads.filter(function(t){return t.group==='recent';}).map(function(t){return sideThreadItem(t,c,false);}).join('');
  return '<div style="width:242px;flex:none;display:flex;flex-direction:column;border-right:1px solid var(--line);background:var(--panel);backdrop-filter:blur(var(--blur))">'
    + '<div style="padding:12px 12px 8px;display:flex;flex-direction:column;gap:8px">'
    +   '<button onclick="A.newThread()" class="hvb a98" style="display:flex;align-items:center;justify-content:center;gap:7px;height:34px;border-radius:var(--r);background:var(--acc);color:var(--acc-ink);font-size:12.5px;font-weight:650;transition:filter .15s">'
    +     '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">'+I.plus+'</svg>'
    +     'New thread <span style="margin-left:auto;padding-right:2px;font-size:10.5px;font-weight:500;opacity:.65">⌘N</span>'
    +   '</button>'
    +   '<div style="display:flex;align-items:center;gap:7px;height:30px;padding:0 9px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel2)">'
    +     '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" stroke-width="2" stroke-linecap="round">'+I.search+'</svg>'
    +     '<input id="i-search" value="'+esc(state.search)+'" oninput="A.onSearch(event)" placeholder="Search threads" style="flex:1;background:transparent;border:none;font-size:12px;min-width:0">'
    +   '</div>'
    +   '<div style="display:flex;flex-direction:column;gap:1px">'+nav+'</div>'
    + '</div>'
    + '<div data-scroll="sb" style="flex:1;overflow-y:auto;padding:4px 12px 8px;display:flex;flex-direction:column;gap:2px">'
    +   '<div style="font-size:10px;font-weight:700;letter-spacing:.12em;color:var(--t3);padding:8px 9px 4px">ACTIVE</div>' + act
    +   '<div style="font-size:10px;font-weight:700;letter-spacing:.12em;color:var(--t3);padding:12px 9px 4px">RECENT</div>' + rec
    + '</div>'
    + '<div style="flex:none;padding:12px;border-top:1px solid var(--line)">'
    +   '<div style="display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--t2)">'
    +     '<span style="font-weight:650;color:var(--t1)">Pro</span> '+cm.pct+'% of weekly compute'
    +     '<span style="margin-left:auto;font-size:10.5px;color:var(--t3)">Resets Mon</span>'
    +   '</div>'
    +   '<div style="height:4px;border-radius:999px;background:var(--line);margin-top:8px;overflow:hidden"><div style="width:'+cm.pct+'%;height:100%;border-radius:999px;background:var(--acc)"></div></div>'
    + '</div>'
    + '</div>';
}

/* ---------- popovers ---------- */
function skillsPopover(withFooter){
  var items = skillsPop().map(function(s,i){
    return '<button onclick="event.stopPropagation();A.skillInsert('+i+')" class="hv" style="display:flex;align-items:baseline;gap:10px;width:100%;padding:7px 9px;border-radius:7px;transition:background .12s">'
      + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:12px;color:var(--acc);font-weight:600;flex:none">'+s.cmd+'</span>'
      + '<span style="font-size:11.5px;color:var(--t2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+s.desc+'</span>'
      + '</button>';
  }).join('');
  var footer = withFooter
    ? '<div style="border-top:1px solid var(--line);margin:5px 4px 2px;padding:6px 5px 2px"><button onclick="A.openSkillsPage()" class="hva" style="font-size:11.5px;color:var(--t3);transition:color .12s">Manage skills →</button></div>'
    : '';
  return '<div style="position:absolute;bottom:calc(100% + 8px);left:0;width:340px;background:var(--glass);backdrop-filter:blur(var(--blur));border:1px solid var(--line2);border-radius:var(--r);box-shadow:0 16px 50px rgba(0,0,0,.3);padding:5px;z-index:40;animation:fadeUp .14s ease">'+items+footer+'</div>';
}
function reasoningSegs(){
  return ['Low','Med','High'].map(function(r){
    var on = state.reasoning===r;
    return '<button onclick="event.stopPropagation();A.pickReasoning(\''+r+'\')" class="hvc" style="padding:2px 9px;border-radius:999px;font-size:10.5px;font-weight:600;color:'+(on?'var(--t1)':'var(--t3)')+';background:'+(on?'var(--sel)':'transparent')+'">'+r+'</button>';
  }).join('');
}
function modePopover(){
  var items = MODES.map(function(m,i){
    return '<button onclick="event.stopPropagation();A.pickMode('+i+')" class="hv" style="display:flex;align-items:center;gap:9px;width:100%;padding:7px 9px;border-radius:7px;transition:background .12s">'
      + '<span style="flex:1"><span style="display:block;font-size:12.5px;font-weight:550;color:var(--t1)">'+m.label+'</span><span style="display:block;font-size:11px;color:var(--t3)">'+m.desc+'</span></span>'
      + (state.mode===m.label ? '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--acc)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+I.check+'</svg>' : '')
      + '</button>';
  }).join('');
  return '<div style="position:absolute;bottom:calc(100% + 8px);right:76px;width:250px;background:var(--glass);backdrop-filter:blur(var(--blur));border:1px solid var(--line2);border-radius:var(--r);box-shadow:0 16px 50px rgba(0,0,0,.3);padding:5px;z-index:40;animation:fadeUp .14s ease">'+items+'</div>';
}
function modelPopover(){
  var items = MODELS.map(function(m,i){
    return '<button onclick="event.stopPropagation();A.pickModel('+i+')" class="hv" style="display:flex;align-items:center;gap:9px;width:100%;padding:7px 9px;border-radius:7px;transition:background .12s">'
      + '<span style="flex:1"><span style="display:block;font-size:12.5px;font-weight:550;color:var(--t1)">'+m.label+'</span><span style="display:block;font-size:11px;color:var(--t3)">'+m.desc+'</span></span>'
      + (state.model===m.label ? '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--acc)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+I.check+'</svg>' : '')
      + '</button>';
  }).join('');
  return '<div style="position:absolute;bottom:calc(100% + 8px);right:38px;width:260px;background:var(--glass);backdrop-filter:blur(var(--blur));border:1px solid var(--line2);border-radius:var(--r);box-shadow:0 16px 50px rgba(0,0,0,.3);padding:5px;z-index:40;animation:fadeUp .14s ease">'
    + items
    + '<div style="border-top:1px solid var(--line);margin:5px 4px 2px;padding:7px 9px 3px;display:flex;align-items:center;gap:8px">'
    +   '<span style="font-size:11px;color:var(--t3)">Reasoning</span>'
    +   '<div style="margin-left:auto;display:flex;background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:2px;gap:1px">'+reasoningSegs()+'</div>'
    + '</div>'
    + '</div>';
}

/* ---------- home ---------- */
function homeCard(t, inActive){
  var b = badgeStyles(t.badgeKind);
  var dot = t.running ? 'var(--acc)' : t.done ? 'var(--ok)' : 'var(--t3)';
  var lead = (inActive && t.running)
    ? spinnerIcon(15,'var(--acc)')
    : '<span style="width:8px;height:8px;flex:none;border-radius:50%;background:'+dot+'"></span>';
  return '<button onclick="A.openThread(\''+t.id+'\')" class="hvcb a995" style="display:flex;align-items:center;gap:12px;padding:12px 14px;border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur));transition:background .15s,border-color .15s">'
    + lead
    + '<span style="flex:1;min-width:0;text-align:left">'
    +   '<span style="display:block;font-size:13.5px;font-weight:600;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+esc(t.title)+'</span>'
    +   '<span style="display:block;font-size:11.5px;color:var(--t3);margin-top:2px">'+esc(t.meta)+'</span>'
    + '</span>'
    + (t.badge ? '<span style="flex:none;font-size:11px;font-weight:650;color:'+b.cl+';background:'+b.bg+';padding:3px 10px;border-radius:999px">'+esc(t.badge)+'</span>' : '')
    + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex:none">'+I.chevR+'</svg>'
    + '</button>';
}
function home(c){
  var threads = allThreads();
  var chips = QUICK_CHIPS.map(function(q,i){
    return '<button onclick="A.chip('+i+')" class="hvtb a97" style="padding:5px 12px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--t2);font-size:12px;transition:background .15s,color .15s,border-color .15s">'+esc(q)+'</button>';
  }).join('');
  var act = threads.filter(function(t){return t.group==='active';}).map(function(t){return homeCard(t,true);}).join('');
  var rec = threads.filter(function(t){return t.group==='recent';}).map(function(t){return homeCard(t,false);}).join('');
  return '<div data-scroll="home" style="flex:1;overflow-y:auto;min-height:0">'
    + '<div style="max-width:820px;margin:0 auto;padding:56px 32px 40px;display:flex;flex-direction:column;gap:24px">'
    +   '<div style="text-align:left">'
    +     '<div style="font-size:22px;font-weight:700;letter-spacing:-.3px">What are we coding next?</div>'
    +     '<div style="font-size:13px;color:var(--t2);margin-top:4px">Threads run in parallel — local, in a worktree, or in the cloud.</div>'
    +   '</div>'
    +   '<div onclick="event.stopPropagation()" style="position:relative;border:1px solid var(--line2);background:var(--glass);backdrop-filter:blur(var(--blur));border-radius:var(--r-lg);padding:14px 14px 10px;box-shadow:0 12px 40px rgba(0,0,0,.14)">'
    +     '<textarea id="i-home" oninput="A.onComposerHome(event)" onkeydown="A.homeKey(event)" rows="3" placeholder="Describe a task — fix a bug, build a feature, refactor a module…" style="width:100%;background:transparent;border:none;resize:none;font-size:14px;line-height:1.55;color:var(--t1)">'+esc(state.composerHome)+'</textarea>'
    +     '<div style="display:flex;align-items:center;gap:6px;margin-top:8px">'
    +       '<button title="Attach context" class="hvt" style="width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;border-radius:var(--r);border:1px solid var(--line);color:var(--t2);transition:background .15s"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'+I.plus+'</svg></button>'
    +       '<button onclick="A.togglePopSkills(event)" class="hvt" style="height:28px;display:inline-flex;align-items:center;gap:6px;padding:0 10px;border-radius:var(--r);border:1px solid var(--line);color:var(--t2);font-size:12px;font-weight:550;transition:background .15s"><span style="font-family:\'JetBrains Mono\',monospace;font-size:12px">/</span> Skills</button>'
    +       '<div style="flex:1"></div>'
    +       '<button onclick="A.togglePopMode(event)" class="hvt" style="height:28px;display:inline-flex;align-items:center;gap:6px;padding:0 10px;border-radius:var(--r);border:1px solid var(--line);color:var(--t2);font-size:12px;font-weight:550;transition:background .15s">'
    +         svg(12,'currentColor',I.branch) + esc(state.mode)
    +         '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">'+I.chevD+'</svg>'
    +       '</button>'
    +       '<button onclick="A.togglePopModel(event)" class="hvt" style="height:28px;display:inline-flex;align-items:center;gap:6px;padding:0 10px;border-radius:var(--r);border:1px solid var(--line);color:var(--t2);font-size:12px;font-weight:550;transition:background .15s">'
    +         esc(state.model)
    +         '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">'+I.chevD+'</svg>'
    +       '</button>'
    +       '<button onclick="A.sendHome()" title="Send" class="hvb a92" style="width:30px;height:30px;display:inline-flex;align-items:center;justify-content:center;border-radius:999px;background:var(--acc);color:var(--acc-ink);transition:filter .15s"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+I.upArrow+'</svg></button>'
    +     '</div>'
    +     (state.popSkills ? skillsPopover(true) : '')
    +     (state.popMode ? modePopover() : '')
    +     (state.popModel ? modelPopover() : '')
    +   '</div>'
    +   '<div style="display:flex;gap:8px;flex-wrap:wrap">'+chips+'</div>'
    +   '<div style="display:flex;flex-direction:column;gap:6px">'
    +     '<div style="font-size:11px;font-weight:700;letter-spacing:.1em;color:var(--t3);padding:6px 2px 2px">ACTIVE NOW</div>' + act
    +     '<div style="font-size:11px;font-weight:700;letter-spacing:.1em;color:var(--t3);padding:14px 2px 2px">RECENT</div>' + rec
    +   '</div>'
    + '</div>'
    + '</div>';
}

/* ---------- chat rows ---------- */
function diffLinesHtml(diff, padLeft, fs){
  return diff.map(function(d){
    var bg = d.t==='a' ? 'var(--ok-soft)' : d.t==='d' ? 'var(--err-soft)' : 'transparent';
    var cl = d.t==='a' ? 'var(--ok)' : d.t==='d' ? 'var(--err)' : 'var(--t3)';
    var pre = d.t==='a' ? '+' : d.t==='d' ? '−' : ' ';
    return '<div style="display:flex;gap:'+(padLeft?'10px':'9px')+';padding:'+(padLeft?'1px 12px 1px 18px':'1.5px 12px')+';background:'+bg+'">'
      + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:'+fs+';color:'+cl+';width:8px;flex:none">'+pre+'</span>'
      + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:'+fs+';color:var(--t2);white-space:pre">'+esc(d.s)+'</span>'
      + '</div>';
  }).join('');
}
function rowUser(r){
  return '<div style="align-self:flex-end;max-width:82%;background:var(--acc-soft);border:1px solid var(--line);border-radius:var(--r-lg);border-bottom-right-radius:4px;padding:10px 14px;font-size:13.5px;line-height:1.55;color:var(--t1)">'+esc(r.text)+'</div>';
}
function rowTrigger(r){
  return '<div style="align-self:center;display:flex;align-items:center;gap:7px;font-size:11.5px;color:var(--t3);padding:2px 0">'
    + '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'+I.clock+'</svg>'
    + esc(r.text) + '</div>';
}
function rowPlan(r){
  var done = r.steps.filter(function(s){return s.s==='done';}).length;
  var steps = r.steps.map(function(st){
    if (st.s==='done') return '<div style="display:flex;align-items:center;gap:9px"><span style="width:15px;height:15px;flex:none;border-radius:50%;background:var(--ok-soft);display:inline-flex;align-items:center;justify-content:center"><svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">'+I.check+'</svg></span><span style="font-size:12.5px;color:var(--t3);text-decoration:line-through;text-decoration-color:var(--line2)">'+esc(st.t)+'</span></div>';
    if (st.s==='now') return '<div style="display:flex;align-items:center;gap:9px">'+spinnerIcon(15,'var(--acc)')+'<span style="font-size:12.5px;color:var(--t1);font-weight:600">'+esc(st.t)+'</span></div>';
    return '<div style="display:flex;align-items:center;gap:9px"><span style="width:15px;height:15px;flex:none;border-radius:50%;border:1.5px solid var(--line2);display:inline-block"></span><span style="font-size:12.5px;color:var(--t2)">'+esc(st.t)+'</span></div>';
  }).join('');
  return '<div style="border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur));padding:12px 14px">'
    + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:9px">'
    +   '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--acc)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'+I.plan+'</svg>'
    +   '<span style="font-size:12px;font-weight:700">'+esc(r.title)+'</span>'
    +   '<span style="margin-left:auto;font-size:11px;color:var(--t3)">'+done+'/'+r.steps.length+'</span>'
    + '</div>'
    + '<div style="display:flex;flex-direction:column;gap:6px">'+steps+'</div>'
    + '</div>';
}
function rowAct(r){
  var open = !!state.exp[r.id];
  var icon = r.icon==='read' ? I.eye : r.icon==='term' ? I.term : I.pencil;
  var body = '';
  if (open && r.files) body = '<div style="border-top:1px solid var(--line);padding:8px 12px 9px 31px;display:flex;flex-direction:column;gap:4px">'
    + r.files.map(function(f){return '<span style="font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--t2)">'+esc(f)+'</span>';}).join('') + '</div>';
  if (open && r.term) body = '<pre style="border-top:1px solid var(--line);margin:0;padding:10px 12px 11px 31px;font-family:\'JetBrains Mono\',monospace;font-size:11px;line-height:1.65;color:var(--t2);white-space:pre-wrap;background:rgba(0,0,0,.14)">'+esc(r.term)+'</pre>';
  if (open && r.diff) body = '<div style="border-top:1px solid var(--line);padding:6px 0;background:rgba(0,0,0,.14)">'+diffLinesHtml(r.diff,true,'11px')+'</div>';
  return '<div style="border:1px solid var(--line);border-radius:var(--r);background:var(--panel);overflow:hidden">'
    + '<button onclick="A.toggleAct(\''+r.id+'\')" class="hv" style="display:flex;align-items:center;gap:9px;width:100%;padding:8px 11px;transition:background .12s">'
    +   '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="transition:transform .16s;transform:'+(open?'rotate(90deg)':'rotate(0deg)')+';flex:none">'+I.chevR+'</svg>'
    +   '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--t2)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex:none">'+icon+'</svg>'
    +   '<span style="font-weight:550;color:var(--t1);font-family:\'JetBrains Mono\',monospace;font-size:11.5px">'+esc(r.label)+'</span>'
    +   '<span style="margin-left:auto;font-size:11px;color:'+(r.bad?'var(--err)':'var(--t3)')+';font-weight:600">'+esc(r.meta)+'</span>'
    + '</button>'
    + body
    + '</div>';
}
function rowApproval(c){
  var st = state.approval;
  var P = PAL[c.dir][c.theme];
  var border = st==='pending' ? P.warn+'66' : 'var(--line)';
  var badge = st==='pending'
    ? '<span style="font-size:10.5px;font-weight:650;color:var(--warn);background:var(--warn-soft);padding:3px 9px;border-radius:999px;flex:none">Waiting</span>'
    : st==='ok'
    ? '<span style="font-size:10.5px;font-weight:650;color:var(--ok);background:var(--ok-soft);padding:3px 9px;border-radius:999px;flex:none">Approved</span>'
    : '<span style="font-size:10.5px;font-weight:650;color:var(--err);background:var(--err-soft);padding:3px 9px;border-radius:999px;flex:none">Denied</span>';
  var tail = '';
  if (st==='pending') tail = '<div style="display:flex;gap:8px;margin-top:10px">'
    + '<button onclick="A.approve()" class="hvb a97" style="height:28px;padding:0 14px;border-radius:var(--r);background:var(--acc);color:var(--acc-ink);font-size:12px;font-weight:650;transition:filter .15s">Allow once</button>'
    + '<button onclick="A.deny()" class="hvt a97" style="height:28px;padding:0 14px;border-radius:var(--r);border:1px solid var(--line);color:var(--t2);font-size:12px;font-weight:600;transition:background .15s">Deny</button>'
    + '<span style="margin-left:auto;align-self:center;font-size:11px;color:var(--t3)">⏎ approve · ⎋ deny</span>'
    + '</div>';
  if (st==='ok') {
    tail = '<button onclick="A.toggleApprovalOut()" class="hvc" style="display:flex;align-items:center;gap:7px;margin-top:10px;font-size:11.5px;color:var(--t3);transition:color .12s">'
      + '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="transition:transform .16s;transform:'+(state.showApprovalOut?'rotate(90deg)':'rotate(0deg)')+'">'+I.chevR+'</svg>'
      + 'e2e output · 4 passed</button>';
    if (state.showApprovalOut) tail += '<pre style="margin:8px 0 0;padding:9px 11px;border:1px solid var(--line);border-radius:8px;background:rgba(0,0,0,.16);font-family:\'JetBrains Mono\',monospace;font-size:11px;line-height:1.65;color:var(--t2);white-space:pre-wrap">✓ books across close without double charge\n✓ credits overlap exactly once\n✓ member discount applies post-clamp\n✓ receipt shows single line item\n\n4 passed (4)  ·  11.2s</pre>';
  }
  return '<div style="border:1px solid '+border+';border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur));overflow:hidden">'
    + '<div style="padding:12px 14px">'
    +   '<div style="display:flex;align-items:center;gap:9px">'
    +     '<span style="width:26px;height:26px;flex:none;border-radius:8px;background:var(--warn-soft);display:inline-flex;align-items:center;justify-content:center"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--warn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'+I.warnTri+'</svg></span>'
    +     '<span style="flex:1"><span style="display:block;font-size:12.5px;font-weight:700">Approval needed</span><span style="display:block;font-size:11.5px;color:var(--t3);margin-top:1px">Command runs outside the sandbox — needs network for the payment fixture</span></span>'
    +     badge
    +   '</div>'
    +   '<div style="margin-top:10px;border:1px solid var(--line);border-radius:8px;background:rgba(0,0,0,.16);padding:8px 11px;font-family:\'JetBrains Mono\',monospace;font-size:11.5px;color:var(--t1)">pnpm test:e2e --grep &quot;booking overlap&quot;</div>'
    +   tail
    + '</div>'
    + '</div>';
}
function rowAnswer(r){
  var paras = (r.paras||[]).map(function(p){ return '<div style="font-size:13.5px;line-height:1.62;color:var(--t1)">'+esc(p)+'</div>'; }).join('');
  var actions = (r.actions||[]).map(function(a){
    return '<button onclick="A.answerAct(\''+a.act+'\')" class="hvcb a97" style="height:27px;display:inline-flex;align-items:center;gap:6px;padding:0 12px;border-radius:var(--r);border:1px solid var(--line);background:var(--panel);color:var(--t1);font-size:12px;font-weight:600;transition:background .15s,border-color .15s">'+esc(a.label)+'</button>';
  }).join('');
  return '<div style="display:flex;flex-direction:column;gap:10px;padding:2px 2px 0">'
    + paras
    + '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'+actions+'<span style="font-size:11px;color:var(--t3)">'+esc(r.meta||'')+'</span></div>'
    + '</div>';
}
function rowThinking(){
  return '<div style="display:flex;align-items:center;gap:9px;padding:4px 2px">'
    + '<span style="display:inline-flex;gap:3px">'
    +   '<span style="width:5px;height:5px;border-radius:50%;background:var(--acc);animation:dots 1.2s ease infinite"></span>'
    +   '<span style="width:5px;height:5px;border-radius:50%;background:var(--acc);animation:dots 1.2s ease .15s infinite"></span>'
    +   '<span style="width:5px;height:5px;border-radius:50%;background:var(--acc);animation:dots 1.2s ease .3s infinite"></span>'
    + '</span>'
    + '<span style="font-size:12px;color:var(--t3)">Working — porting slices to Zustand…</span>'
    + '</div>';
}

/* ---------- thread ---------- */
function chatColumn(c){
  var rows = baseRows(c.threadId).concat(state.extras[c.threadId]||[]);
  if (state.thinking[c.threadId]) rows = rows.concat([{kind:'thinking'}]);
  var html = rows.map(function(r){
    var inner = r.kind==='user' ? rowUser(r)
      : r.kind==='trigger' ? rowTrigger(r)
      : r.kind==='plan' ? rowPlan(r)
      : r.kind==='act' ? rowAct(r)
      : r.kind==='approval' ? rowApproval(c)
      : r.kind==='answer' ? rowAnswer(r)
      : r.kind==='thinking' ? rowThinking()
      : '';
    return '<div style="display:flex;flex-direction:column">'+inner+'</div>';
  }).join('');
  return '<div style="flex:1;display:flex;flex-direction:column;min-width:0;min-height:0">'
    + '<div data-scroll="chat" style="flex:1;overflow-y:auto;min-height:0">'
    +   '<div style="max-width:760px;margin:0 auto;padding:24px 28px 16px;display:flex;flex-direction:column;gap:14px">'+html+'</div>'
    + '</div>'
    + '<div style="flex:none;padding:10px 28px 16px">'
    +   '<div onclick="event.stopPropagation()" style="max-width:760px;margin:0 auto;position:relative;border:1px solid var(--line2);background:var(--glass);backdrop-filter:blur(var(--blur));border-radius:var(--r-lg);padding:10px 12px 8px;box-shadow:0 10px 34px rgba(0,0,0,.12)">'
    +     '<textarea id="i-thread" oninput="A.onComposerThread(event)" onkeydown="A.threadKey(event)" rows="1" placeholder="Reply — or / for skills" style="width:100%;background:transparent;border:none;resize:none;font-size:13px;line-height:1.5;color:var(--t1)">'+esc(state.composerThread)+'</textarea>'
    +     '<div style="display:flex;align-items:center;gap:6px;margin-top:6px">'
    +       '<button onclick="A.togglePopSkills(event)" class="hvt" style="height:24px;display:inline-flex;align-items:center;gap:5px;padding:0 8px;border-radius:7px;border:1px solid var(--line);color:var(--t3);font-size:11px;font-weight:550;transition:background .15s"><span style="font-family:\'JetBrains Mono\',monospace">/</span> Skills</button>'
    +       '<div style="flex:1"></div>'
    +       '<span style="font-size:10.5px;color:var(--t3)">'+esc(state.mode)+' · '+esc(state.model)+'</span>'
    +       '<button onclick="A.sendThread()" title="Send" class="hvb a92" style="width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;border-radius:999px;background:var(--acc);color:var(--acc-ink);transition:filter .15s"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+I.upArrow+'</svg></button>'
    +     '</div>'
    +     (state.popSkills ? skillsPopover(false) : '')
    +   '</div>'
    + '</div>'
    + '</div>';
}
function thread(c){
  var t = null;
  var all = allThreads();
  for (var i=0;i<all.length;i++) if (all[i].id===c.threadId) t = all[i];
  if (!t) t = { title:'Thread', meta:'' };
  return '<div style="flex:1;display:flex;flex-direction:column;min-height:0">'
    + '<div style="flex:none;display:flex;align-items:center;gap:10px;padding:0 16px;height:44px;border-bottom:1px solid var(--line)">'
    +   '<button onclick="A.backHome()" title="Back" class="hvt a92" style="width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;border-radius:var(--r);color:var(--t2);transition:background .15s"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'+I.chevL+'</svg></button>'
    +   '<span style="font-size:13px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:380px">'+esc(t.title)+'</span>'
    +   '<span style="font-size:11px;color:var(--t3);white-space:nowrap">'+esc(t.meta)+'</span>'
    +   '<div style="flex:1"></div>'
    +   '<div style="display:flex;background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:2px;gap:1px">'
    +     '<button onclick="A.selChat()" class="hvc" style="padding:3px 13px;border-radius:999px;font-size:11.5px;font-weight:600;color:'+(c.tab==='chat'?'var(--t1)':'var(--t3)')+'">Chat</button>'
    +     '<button onclick="A.selEditor()" class="hvc" style="padding:3px 13px;border-radius:999px;font-size:11.5px;font-weight:600;color:'+(c.tab==='editor'?'var(--t1)':'var(--t3)')+'">Editor</button>'
    +   '</div>'
    +   '<button onclick="A.toggleReview()" class="hvt a97" style="display:inline-flex;align-items:center;gap:6px;height:28px;padding:0 11px;border-radius:var(--r);border:1px solid var(--line);background:var(--panel);color:var(--t2);font-size:11.5px;font-weight:600;transition:background .15s">'
    +     svg(12,'currentColor',I.expand) + 'Review <span style="font-size:10px;font-weight:650;color:var(--ok)">+68 −8</span>'
    +   '</button>'
    + '</div>'
    + '<div style="flex:1;display:flex;min-height:0">'
    +   (c.tab==='chat' ? chatColumn(c) : editorView(c))
    +   (c.reviewOpen ? reviewRail(c) : '')
    + '</div>'
    + '</div>';
}

/* ---------- editor ---------- */
function kw(s){ return '<span style="color:var(--c-kw)">'+s+'</span>'; }
function ty(s){ return '<span style="color:var(--c-ty)">'+s+'</span>'; }
function fnc(s){ return '<span style="color:var(--c-fn)">'+s+'</span>'; }
function stc(s){ return '<span style="color:var(--c-st)">'+s+'</span>'; }
function nu(s){ return '<span style="color:var(--c-nu)">'+s+'</span>'; }
function gutter(n){ return '<span style="width:46px;flex:none;text-align:right;padding-right:18px;color:var(--t3);user-select:none">'+n+'</span>'; }
function ln(n, inner, lineStyle){
  return '<div style="display:flex'+(lineStyle||'')+'">'+gutter(n)+'<span style="white-space:pre">'+inner+'</span></div>';
}
function inlay(label){ return state.hintsOn ? '<span style="font-size:10px;color:var(--t3);background:var(--panel2);border-radius:4px;padding:1px 4px;margin-right:3px">'+label+'</span>' : ''; }

function hoverCard(){
  return '<div onmouseenter="A.hoverStay()" onmouseleave="A.hoverOut()" style="position:absolute;top:calc(100% + 2px);left:150px;width:390px;background:var(--glass);backdrop-filter:blur(var(--blur));border:1px solid var(--line2);border-radius:var(--r);box-shadow:0 18px 50px rgba(0,0,0,.35);z-index:30;animation:fadeUp .12s ease;overflow:hidden">'
    + '<div style="padding:9px 12px;border-bottom:1px solid var(--line);font-size:11.5px;white-space:pre-wrap">'+kw('function')+' '+fnc('venueCloseFor')+'(at: '+ty('Date')+'): '+ty('Date')+'</div>'
    + '<div style="padding:9px 12px;font-family:-apple-system,system-ui,sans-serif;font-size:11.5px;line-height:1.55;color:var(--t2)">Returns the venue’s closing time for the calendar day of <span style="font-family:\'JetBrains Mono\',monospace;font-size:10.5px;color:var(--t1);background:var(--panel2);padding:1px 4px;border-radius:4px">at</span>. Reads hours from VenueConfig and handles overnight venues that close past midnight.</div>'
    + '<div style="display:flex;gap:12px;padding:7px 12px;border-top:1px solid var(--line);font-family:-apple-system,system-ui,sans-serif">'
    +   '<button onclick="A.openPeek()" class="hvo" style="font-size:11px;font-weight:600;color:var(--acc);transition:opacity .12s">Peek definition ⌥F12</button>'
    +   '<button onclick="A.goSessions()" class="hvc" style="font-size:11px;font-weight:600;color:var(--t3);transition:color .12s">Go to sessions.ts</button>'
    +   '<span style="margin-left:auto;font-size:11px;color:var(--t3)">3 references</span>'
    + '</div>'
    + '</div>';
}
function peekWindow(){
  function pln(n, inner, sel){
    return '<div style="display:flex'+(sel?';background:var(--sel)':'')+'"><span style="width:44px;flex:none;text-align:right;padding-right:14px;color:var(--t3);user-select:none">'+n+'</span><span style="white-space:pre">'+inner+'</span></div>';
  }
  return '<div style="margin:4px 16px 6px 46px;border:1px solid var(--line2);border-left:3px solid var(--acc);border-radius:8px;overflow:hidden;background:var(--panel);animation:fadeUp .14s ease">'
    + '<div style="display:flex;align-items:center;gap:8px;padding:6px 11px;border-bottom:1px solid var(--line);background:var(--panel2)">'
    +   '<span style="font-size:11px;font-weight:650;color:var(--t1)">venueCloseFor</span>'
    +   '<span style="font-family:\'JetBrains Mono\',monospace;font-size:10.5px;color:var(--t3)">src/lib/sessions.ts · 82:17</span>'
    +   '<div style="flex:1"></div>'
    +   '<button onclick="A.closePeek()" class="hvt" style="width:20px;height:20px;display:inline-flex;align-items:center;justify-content:center;border-radius:5px;color:var(--t3);transition:background .12s"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">'+I.x+'</svg></button>'
    + '</div>'
    + '<div style="padding:6px 0;font-size:11.5px;line-height:1.8">'
    +   pln(82, kw('export function')+' '+fnc('venueCloseFor')+'(at: '+ty('Date')+'): '+ty('Date')+' {')
    +   pln(83, '  '+kw('const')+' cfg = '+fnc('venueConfigFor')+'(at);')
    +   pln(84, '  '+kw('const')+' close = '+fnc('setTime')+'(at, cfg.closeHour, cfg.closeMinute);', true)
    +   pln(85, '  '+kw('return')+' cfg.overnight ? '+fnc('addDays')+'(close, '+nu('1')+') : close;')
    +   pln(86, '}')
    + '</div>'
    + '</div>';
}
function sigCard(){
  return '<div style="position:absolute;bottom:calc(100% + 2px);left:120px;width:400px;background:var(--glass);backdrop-filter:blur(var(--blur));border:1px solid var(--line2);border-radius:var(--r);box-shadow:0 18px 50px rgba(0,0,0,.35);z-index:30;animation:fadeUp .12s ease;overflow:hidden">'
    + '<div style="padding:8px 12px;font-size:11.5px;white-space:pre-wrap">'+fnc('applyDiscount')+'(<span style="background:var(--acc-soft);color:var(--acc);border-radius:4px;padding:1px 4px;font-weight:700">amount: number</span>, tier: '+ty('MemberTier')+'): '+ty('number')+'</div>'
    + '<div style="padding:7px 12px;border-top:1px solid var(--line);font-family:-apple-system,system-ui,sans-serif;font-size:11px;line-height:1.5;color:var(--t2)"><span style="font-weight:650;color:var(--t1)">amount</span> — the post-clamp total in cents, before member discounts.</div>'
    + '<div style="padding:5px 12px 7px;font-family:-apple-system,system-ui,sans-serif;font-size:10.5px;color:var(--t3)">Param 1 of 2 · ⌘⇧Space to toggle</div>'
    + '</div>';
}
function complPopup(){
  var items = COMPL.map(function(it, i){
    var on = i===state.complIdx;
    return '<button onclick="A.complPick(event,'+i+')" class="hv" style="display:flex;align-items:center;gap:8px;width:100%;padding:4.5px 8px;border-radius:6px;background:'+(on?'var(--sel)':'transparent')+';border-left:'+(on?'2px solid var(--acc)':'2px solid transparent')+';transition:background .1s">'
      + '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--c-ty)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex:none">'+I.cube+'</svg>'
      + '<span style="flex:1;font-family:\'JetBrains Mono\',monospace;font-size:11.5px;color:var(--t1);text-align:left">'+it.n+'</span>'
      + '<span style="flex:none;font-family:\'JetBrains Mono\',monospace;font-size:10px;color:var(--t3)">'+esc(it.t)+'</span>'
      + '</button>';
  }).join('');
  var sel = COMPL[state.complIdx];
  return '<div style="position:absolute;top:calc(100% + 2px);left:230px;display:flex;background:var(--glass);backdrop-filter:blur(var(--blur));border:1px solid var(--line2);border-radius:var(--r);box-shadow:0 22px 60px rgba(0,0,0,.4);z-index:35;animation:fadeUp .12s ease;overflow:hidden">'
    + '<div style="width:238px;padding:4px;border-right:1px solid var(--line);max-height:228px;overflow-y:auto">'+items+'</div>'
    + '<div style="width:250px;padding:10px 12px;display:flex;flex-direction:column;gap:6px">'
    +   '<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px"><span style="color:var(--t1)">'+sel.n+'</span><span style="color:var(--t3)">: </span><span style="color:var(--c-ty)">'+esc(sel.t)+'</span></div>'
    +   '<div style="font-family:-apple-system,system-ui,sans-serif;font-size:11px;line-height:1.55;color:var(--t2)">'+esc(sel.d)+'</div>'
    +   '<div style="margin-top:auto;font-family:-apple-system,system-ui,sans-serif;font-size:10px;color:var(--t3);border-top:1px solid var(--line);padding-top:6px">↑↓ navigate · ⏎ / Tab accept · esc dismiss</div>'
    + '</div>'
    + '</div>';
}
function editorView(c){
  var tree = FILE_TREE.map(function(f, i){
    var lead = f.dir
      ? '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex:none;opacity:.7">'+I.chevD+'</svg>'
      : '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex:none;opacity:.55;margin-left:2px">'+I.file+'</svg>';
    return '<button onclick="A.fileClick('+i+')" class="hv" style="display:flex;align-items:center;gap:6px;width:100%;height:24px;padding-left:'+(10+f.ind*13)+'px;padding-right:8px;border-radius:6px;background:'+(f.active?'var(--sel)':'transparent')+';color:'+(f.active?'var(--t1)':'var(--t2)')+';transition:background .12s">'
      + lead
      + '<span style="flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:left;font-family:\'JetBrains Mono\',monospace;font-size:10.5px">'+f.n+'</span>'
      + (f.badge ? '<span style="flex:none;font-size:9.5px;font-weight:700;color:'+(f.badge==='M'?'var(--warn)':'var(--ok)')+'">'+f.badge+'</span>' : '')
      + '</button>';
  }).join('');

  var chipDefs = [
    { label:'Ghost text', kbd:'Tab', on: !state.ghostDone },
    { label:'Completions', kbd:'⌃Space', on: state.l22==='typing' },
    { label:'Hover docs', kbd:'', on: state.hoverOn },
    { label:'Signature help', kbd:'⌘⇧Space', on: state.sigOn },
    { label:'Peek definition', kbd:'⌥F12', on: state.peekOn },
    { label:'Inlay hints', kbd:'', on: state.hintsOn }
  ];
  var chips = chipDefs.map(function(ch, i){
    return '<button onclick="A.chipTry('+i+')" class="hvc a96" style="flex:none;display:inline-flex;align-items:center;gap:6px;height:24px;padding:0 10px;border-radius:999px;border:1px solid '+(ch.on?'transparent':'var(--line)')+';background:'+(ch.on?'var(--acc-soft)':'var(--panel)')+';color:'+(ch.on?'var(--acc)':'var(--t2)')+';font-size:11px;font-weight:600;transition:background .15s,color .15s">'
      + ch.label + (ch.kbd ? '<span style="font-size:9.5px;opacity:.7;font-family:\'JetBrains Mono\',monospace">'+ch.kbd+'</span>' : '')
      + '</button>';
  }).join('');

  var crumbSep = '<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+I.chevR+'</svg>';

  /* line 8 — hover + peek anchor */
  var l8 = '<div style="display:flex;position:relative">'
    + gutter(8)
    + '<span style="white-space:pre">  '+kw('const')+' <span>closeTime</span> = <span onmouseenter="A.hoverIn()" onmouseleave="A.hoverOut()" onclick="A.openPeek()" style="color:var(--c-fn);cursor:pointer;border-bottom:1px dotted '+(state.hoverOn?'var(--t3)':'transparent')+'">venueCloseFor</span>('+inlay('at:')+'session.startsAt);</span>'
    + (state.hoverOn ? hoverCard() : '')
    + '</div>';

  /* line 13 — ghost text */
  var l13inner = state.ghostDone
    ? '<span style="white-space:pre">    total -= '+fnc('overlapCredit')+'(session, rate);</span>'
    : '<span style="white-space:pre">    <span style="color:var(--c-gh);font-style:italic">total -= overlapCredit(session, rate);</span>  <button onclick="event.stopPropagation();A.acceptGhost()" class="hvt a95" style="display:inline-flex;align-items:center;gap:5px;padding:1px 8px;border-radius:6px;border:1px solid var(--line2);background:var(--panel2);color:var(--t2);font-size:10px;font-weight:650;font-family:-apple-system,system-ui,sans-serif;vertical-align:1px;transition:background .12s,color .12s"><span style="font-family:\'JetBrains Mono\',monospace">Tab ↹</span> accept</button></span>';
  var l13 = '<div style="display:flex;background:'+(state.ghostDone?'transparent':'var(--acc-soft)')+'">'+gutter(13)+l13inner+'</div>';

  /* line 15 — signature help anchor */
  var l15 = '<div style="display:flex;position:relative">'
    + gutter(15)
    + '<span style="white-space:pre">  '+kw('return')+' <span onclick="A.toggleSig()" style="color:var(--c-fn);cursor:pointer">applyDiscount</span>('+inlay('amount:')+'total, '+inlay('tier:')+'session.memberTier);</span>'
    + (state.sigOn ? sigCard() : '')
    + '</div>';

  /* line 20 — diagnostics / completion */
  var l20inner;
  if (state.l22==='error') {
    l20inner = '<span style="white-space:pre">  '+kw('const')+' mins = (session.<span onclick="A.startCompletion()" title="Click to fix" style="cursor:pointer;text-decoration:underline wavy var(--err) 1.5px;text-underline-offset:4px">endAt</span> - session.startsAt) / '+nu('60_000')+';  <button onclick="A.startCompletion()" class="hverr" style="font-size:10.5px;font-style:italic;color:var(--err);opacity:.9;font-family:\'JetBrains Mono\',monospace;transition:opacity .12s">✕ Property \'endAt\' does not exist on type \'Session\'. Did you mean \'endsAt\'? · click to fix</button></span>';
  } else if (state.l22==='typing') {
    l20inner = '<span style="white-space:pre">  '+kw('const')+' mins = (session.<span style="display:inline-block;width:1.5px;height:14px;background:var(--acc);vertical-align:-2px;animation:blink 1.1s steps(1) infinite"></span></span>';
  } else {
    l20inner = '<span style="white-space:pre">  '+kw('const')+' mins = (session.<span style="background:var(--ok-soft);border-radius:3px">endsAt</span> - session.startsAt) / '+nu('60_000')+';</span>';
  }
  var l20 = '<div style="display:flex;position:relative;background:var(--panel2)">'+gutter(20)+l20inner+(state.l22==='typing' ? complPopup() : '')+'</div>';

  var code = ''
    + ln(1, kw('import')+' { MS_PER_HOUR } '+kw('from')+' '+stc('"./constants"')+';')
    + ln(2, kw('import')+' { venueCloseFor } '+kw('from')+' '+stc('"./sessions"')+';')
    + ln(3, kw('import')+' { applyDiscount } '+kw('from')+' '+stc('"./discounts"')+';')
    + ln(4, kw('import type')+' { Session, MemberTier } '+kw('from')+' '+stc('"./types"')+';')
    + ln(5, ' ')
    + '<div style="display:flex">'+gutter(6)+'<span style="white-space:pre;color:var(--c-cm)">/** Total for one session, clamped at venue close. */</span></div>'
    + ln(7, kw('export function')+' '+fnc('calcTotal')+'(session: '+ty('Session')+', rate: '+ty('Rate')+') {')
    + l8
    + (state.peekOn ? peekWindow() : '')
    + ln(9, '  '+kw('const')+' chargeable = Math.'+fnc('min')+'(session.endsAt, closeTime) - session.startsAt;')
    + ln(10, '  '+kw('const')+' hours = Math.'+fnc('ceil')+'(chargeable / MS_PER_HOUR);')
    + ln(11, '  '+kw('let')+' total = hours * rate.hourly;')
    + ln(12, '  '+kw('if')+' (session.spansClose) {')
    + l13
    + ln(14, '  }')
    + l15
    + ln(16, '}')
    + ln(17, ' ')
    + '<div style="display:flex">'+gutter(18)+'<span style="white-space:pre;color:var(--c-cm)">/** One receipt row for the invoice. */</span></div>'
    + ln(19, kw('export function')+' '+fnc('receiptLine')+'(session: '+ty('Session')+') {')
    + l20
    + ln(21, '  '+kw('return')+' '+stc('`&#36;{')+fnc('formatRange')+'(session)'+stc('} · &#36;{')+'mins'+stc('} min`')+';')
    + ln(22, '}');

  return '<div style="flex:1;display:flex;min-width:0;min-height:0">'
    + '<div style="width:196px;flex:none;display:flex;flex-direction:column;border-right:1px solid var(--line);background:var(--panel);min-height:0">'
    +   '<div style="flex:none;display:flex;align-items:center;height:34px;padding:0 12px;font-size:10px;font-weight:700;letter-spacing:.12em;color:var(--t3)">EXPLORER</div>'
    +   '<div data-scroll="filerail" style="flex:1;overflow-y:auto;padding:0 6px 8px">'+tree+'</div>'
    + '</div>'
    + '<div style="flex:1;display:flex;flex-direction:column;min-width:0;min-height:0">'
    +   '<div style="flex:none;display:flex;align-items:center;height:36px;border-bottom:1px solid var(--line);padding:0 8px;gap:2px">'
    +     '<div style="display:flex;align-items:center;gap:7px;height:28px;padding:0 12px;border-radius:8px;background:var(--sel);font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--t1)">pricing.ts <span style="width:7px;height:7px;border-radius:50%;background:var(--warn);display:inline-block"></span></div>'
    +     '<button class="hvt" style="display:flex;align-items:center;gap:7px;height:28px;padding:0 12px;border-radius:8px;font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--t3);transition:background .12s">sessions.ts</button>'
    +     '<button class="hvt" style="display:flex;align-items:center;gap:7px;height:28px;padding:0 12px;border-radius:8px;font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--t3);transition:background .12s">bookingStore.ts <span style="width:7px;height:7px;border-radius:50%;background:var(--warn);display:inline-block"></span></button>'
    +     '<div style="flex:1"></div>'
    +     '<button onclick="A.resetDemo()" title="Reset IntelliSense demo" class="hvt arot" style="width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;border-radius:7px;color:var(--t3);transition:background .12s">'+svg(13,'currentColor',I.reset)+'</button>'
    +     '<button onclick="A.closeEditor()" title="Close editor" class="hvt" style="width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;border-radius:7px;color:var(--t3);transition:background .12s"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">'+I.x+'</svg></button>'
    +   '</div>'
    +   '<div style="flex:none;display:flex;align-items:center;gap:6px;padding:7px 12px;border-bottom:1px solid var(--line);overflow-x:auto">'
    +     '<span style="font-size:10px;font-weight:700;letter-spacing:.1em;color:var(--t3);flex:none;margin-right:2px">TRY</span>' + chips
    +   '</div>'
    +   '<div style="flex:none;display:flex;align-items:center;gap:6px;height:26px;padding:0 16px;font-size:11px;color:var(--t3)">src '+crumbSep+' lib '+crumbSep+' pricing.ts '+crumbSep+' <span style="color:var(--t2)">calcTotal</span></div>'
    +   '<div data-scroll="code" style="flex:1;overflow:auto;min-height:0;padding:6px 0 24px;font-family:\'JetBrains Mono\',monospace;font-size:12.5px;line-height:1.85;color:var(--c-pn)">'+code+'</div>'
    +   '<div style="flex:none;display:flex;align-items:center;gap:14px;height:27px;padding:0 14px;border-top:1px solid var(--line);font-size:11px;color:var(--t3)">'
    +     '<span style="display:inline-flex;align-items:center;gap:5px">'+svg(11,'currentColor',I.branch)+'fix/booking-overlap</span>'
    +     '<span style="display:inline-flex;align-items:center;gap:5px;color:'+(state.l22==='fixed'?'var(--t3)':'var(--err)')+';font-weight:600"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'+I.probs+'</svg>'+(state.l22==='fixed'?'0 errors':'1 error')+'</span>'
    +     '<div style="flex:1"></div>'
    +     '<span>Ln 20, Col 24</span><span>Spaces: 2</span><span>UTF-8</span><span>TypeScript 5.5</span>'
    +     '<span style="display:inline-flex;align-items:center;gap:5px;color:var(--acc);font-weight:600">'+svg(11,'currentColor',I.bell)+'Suggestions on</span>'
    +   '</div>'
    + '</div>'
    + '</div>';
}

/* ---------- review rail ---------- */
function reviewRail(c){
  var stagedCount = REVIEW_FILES.filter(function(f){return state.staged[f.id];}).length;
  var files = REVIEW_FILES.map(function(f){
    var on = state.diffFile===f.id;
    var stg = state.staged[f.id];
    return '<div onclick="A.selDiff(\''+f.id+'\')" class="hv" style="display:flex;align-items:center;gap:9px;padding:7px 9px;border-radius:var(--r);background:'+(on?'var(--sel)':'transparent')+';cursor:pointer;transition:background .12s">'
      + '<button onclick="event.stopPropagation();A.stageFile(\''+f.id+'\')" title="Stage file" style="width:15px;height:15px;flex:none;border-radius:4.5px;border:1.5px solid '+(stg?'var(--acc)':'var(--line2)')+';background:'+(stg?'var(--acc)':'transparent')+';display:inline-flex;align-items:center;justify-content:center;transition:background .12s,border-color .12s">'
      +   (stg ? '<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="var(--acc-ink)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">'+I.check+'</svg>' : '')
      + '</button>'
      + '<span style="flex:1;min-width:0;font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+f.name+'</span>'
      + '<span style="flex:none;font-size:10.5px;font-weight:650;color:var(--ok)">+'+f.add+'</span>'
      + '<span style="flex:none;font-size:10.5px;font-weight:650;color:var(--err)">−'+f.del+'</span>'
      + '</div>';
  }).join('');
  var fname = '';
  for (var i=0;i<REVIEW_FILES.length;i++) if (REVIEW_FILES[i].id===state.diffFile) fname = REVIEW_FILES[i].name;
  var prBtn;
  if (state.prState==='creating') {
    prBtn = '<button style="height:32px;display:flex;align-items:center;justify-content:center;gap:8px;border-radius:var(--r);background:var(--panel2);border:1px solid var(--line);color:var(--t2);font-size:12px;font-weight:600;cursor:default">'+spinnerIcon(12,'currentColor')+' Opening PR…</button>';
  } else if (state.prState==='open') {
    prBtn = '<button onclick="A.viewPR()" class="hvb" style="height:32px;display:flex;align-items:center;justify-content:center;gap:7px;border-radius:var(--r);border:1px solid var(--line);background:var(--ok-soft);color:var(--ok);font-size:12px;font-weight:650;transition:filter .15s">'+svg(12,'currentColor',I.pr)+' PR #131 open · checks running</button>';
  } else {
    prBtn = '<button onclick="A.createPR()" class="hvb a98" style="height:32px;display:flex;align-items:center;justify-content:center;gap:7px;border-radius:var(--r);background:var(--acc);color:var(--acc-ink);font-size:12px;font-weight:650;transition:filter .15s">'+svg(12,'currentColor',I.pr)+' Commit staged &amp; open PR</button>';
  }
  return '<div style="width:340px;flex:none;display:flex;flex-direction:column;border-left:1px solid var(--line);background:var(--panel);backdrop-filter:blur(var(--blur));min-height:0">'
    + '<div style="flex:none;display:flex;align-items:center;gap:8px;height:40px;padding:0 12px;border-bottom:1px solid var(--line)">'
    +   '<span style="font-size:12px;font-weight:700">Review</span>'
    +   '<span style="font-size:11px;color:var(--t3)">'+stagedCount+' of 3 staged</span>'
    +   '<div style="flex:1"></div>'
    +   '<button onclick="A.stageAll()" class="hvo" style="font-size:11px;font-weight:600;color:var(--acc);transition:opacity .12s">Stage all</button>'
    +   '<button onclick="A.toggleReview()" title="Close" class="hvt" style="width:22px;height:22px;display:inline-flex;align-items:center;justify-content:center;border-radius:6px;color:var(--t3);transition:background .12s"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">'+I.x+'</svg></button>'
    + '</div>'
    + '<div style="flex:none;padding:8px;display:flex;flex-direction:column;gap:2px;border-bottom:1px solid var(--line)">'+files+'</div>'
    + '<div data-scroll="rvdiff" style="flex:1;overflow-y:auto;min-height:0">'
    +   '<div style="padding:9px 12px 4px;font-family:\'JetBrains Mono\',monospace;font-size:10.5px;color:var(--t3)">'+fname+'</div>'
    +   '<div style="padding:2px 0 10px">'+diffLinesHtml(DIFFS[state.diffFile]||[], false, '10.5px')+'</div>'
    + '</div>'
    + '<div style="flex:none;padding:12px;border-top:1px solid var(--line);display:flex;flex-direction:column;gap:8px">'
    +   '<input id="i-commit" value="'+esc(state.commitMsg)+'" oninput="A.onCommit(event)" style="height:30px;padding:0 10px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel2);font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--t1)">'
    +   prBtn
    + '</div>'
    + '</div>';
}

/* ---------- automations ---------- */
function toggleBtn(on, onclick){
  return '<button onclick="'+onclick+'" title="Toggle" style="width:32px;height:18px;flex:none;border-radius:999px;background:'+(on?'var(--acc)':'var(--line2)')+';position:relative;transition:background .18s">'
    + '<span style="position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.3);transition:transform .18s;transform:'+(on?'translateX(14px)':'translateX(0)')+'"></span>'
    + '</button>';
}
function automations(c){
  var rows = AUTOMATIONS.map(function(a){
    return '<div style="display:flex;align-items:center;gap:14px;padding:14px 16px;border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur))">'
      + toggleBtn(state.autos[a.id], 'event.stopPropagation();A.autoToggle(\''+a.id+'\')')
      + '<span style="flex:1;min-width:0">'
      +   '<span style="display:flex;align-items:center;gap:8px">'
      +     '<span style="font-size:13.5px;font-weight:650;color:var(--t1)">'+a.name+'</span>'
      +     '<span style="font-size:10.5px;font-weight:600;color:var(--t3);background:var(--panel2);border:1px solid var(--line);padding:1px 8px;border-radius:999px;font-family:\'JetBrains Mono\',monospace">'+a.sched+'</span>'
      +   '</span>'
      +   '<span style="display:block;font-size:12px;color:var(--t2);margin-top:3px">'+a.desc+'</span>'
      +   '<span style="display:block;font-size:11px;color:var(--t3);margin-top:3px">'+a.last+'</span>'
      + '</span>'
      + (a.view ? '<button onclick="A.openThread(\''+a.view+'\')" class="hvt a97" style="flex:none;height:27px;padding:0 12px;border-radius:var(--r);border:1px solid var(--line);color:var(--t2);font-size:11.5px;font-weight:600;transition:background .15s">Last run</button>' : '')
      + '</div>';
  }).join('');
  return '<div data-scroll="auto" style="flex:1;overflow-y:auto;min-height:0">'
    + '<div style="max-width:820px;margin:0 auto;padding:44px 32px 40px;display:flex;flex-direction:column;gap:18px">'
    +   '<div style="display:flex;align-items:flex-end;gap:12px">'
    +     '<div><div style="font-size:20px;font-weight:700;letter-spacing:-.3px">Automations</div><div style="font-size:12.5px;color:var(--t2);margin-top:3px">Scheduled and event-driven agent runs on this repo.</div></div>'
    +     '<button onclick="A.newAutomation()" class="hvb a97" style="margin-left:auto;height:30px;display:inline-flex;align-items:center;gap:6px;padding:0 13px;border-radius:var(--r);background:var(--acc);color:var(--acc-ink);font-size:12px;font-weight:650;transition:filter .15s"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">'+I.plus+'</svg> New automation</button>'
    +   '</div>'
    +   '<div style="display:flex;flex-direction:column;gap:10px">'+rows+'</div>'
    + '</div>'
    + '</div>';
}

/* ---------- skills ---------- */
function skillsView(c){
  var cards = skillCards().map(function(s, i){
    return '<div class="hvbd" style="display:flex;flex-direction:column;gap:7px;padding:14px 16px;border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur));transition:border-color .15s">'
      + '<div style="display:flex;align-items:center;gap:8px">'
      +   '<span style="font-family:\'JetBrains Mono\',monospace;font-size:13px;font-weight:650;color:var(--acc)">'+s.cmd+'</span>'
      +   '<button onclick="A.runSkill('+i+')" class="hvt a96" style="margin-left:auto;height:24px;padding:0 11px;border-radius:7px;border:1px solid var(--line);color:var(--t2);font-size:11px;font-weight:600;transition:background .15s">Run</button>'
      + '</div>'
      + '<div style="font-size:12px;line-height:1.5;color:var(--t2)">'+s.desc+'</div>'
      + '<div style="font-size:10.5px;color:var(--t3)">'+s.meta+'</div>'
      + '</div>';
  }).join('');
  return '<div data-scroll="skills" style="flex:1;overflow-y:auto;min-height:0">'
    + '<div style="max-width:820px;margin:0 auto;padding:44px 32px 40px;display:flex;flex-direction:column;gap:18px">'
    +   '<div style="display:flex;align-items:flex-end;gap:12px">'
    +     '<div><div style="font-size:20px;font-weight:700;letter-spacing:-.3px">Skills</div><div style="font-size:12.5px;color:var(--t2);margin-top:3px">Reusable slash-commands the agent can run in any thread.</div></div>'
    +     '<button onclick="A.newSkill()" class="hvb a97" style="margin-left:auto;height:30px;display:inline-flex;align-items:center;gap:6px;padding:0 13px;border-radius:var(--r);background:var(--acc);color:var(--acc-ink);font-size:12px;font-weight:650;transition:filter .15s"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">'+I.plus+'</svg> New skill</button>'
    +   '</div>'
    +   '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'+cards+'</div>'
    + '</div>'
    + '</div>';
}

/* ---------- settings ---------- */
function settingsView(c){
  var cm = costMeter();
  var themeSegs = ['dark','light'].map(function(t){
    var on = c.theme===t;
    return '<button onclick="A.setTheme(\''+t+'\')" class="hvc" style="padding:3px 14px;border-radius:999px;font-size:11.5px;font-weight:600;color:'+(on?'var(--t1)':'var(--t3)')+';background:'+(on?'var(--sel)':'transparent')+'">'+(t==='dark'?'Dark':'Light')+'</button>';
  }).join('');
  var dirSegs = [['glass','Glass'],['mono','Mono'],['warm','Warm']].map(function(d){
    var on = c.dir===d[0];
    return '<button onclick="A.setDir(\''+d[0]+'\')" class="hvc" style="padding:3px 14px;border-radius:999px;font-size:11.5px;font-weight:600;color:'+(on?'var(--t1)':'var(--t3)')+';background:'+(on?'var(--sel)':'transparent')+'">'+d[1]+'</button>';
  }).join('');
  var models = MODELS.map(function(m, i){
    return '<button onclick="A.pickModel('+i+')" class="hv" style="display:flex;align-items:center;gap:10px;width:100%;padding:11px 16px;border-bottom:1px solid var(--line);transition:background .12s">'
      + '<span style="flex:1;text-align:left"><span style="display:block;font-size:13px;font-weight:550;color:var(--t1)">'+m.label+'</span><span style="display:block;font-size:11.5px;color:var(--t3);margin-top:1px">'+m.desc+'</span></span>'
      + (state.model===m.label ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--acc)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+I.check+'</svg>' : '')
      + '</button>';
  }).join('');
  var reason2 = ['Low','Med','High'].map(function(r){
    var on = state.reasoning===r;
    return '<button onclick="A.pickReasoning(\''+r+'\')" class="hvc" style="padding:3px 12px;border-radius:999px;font-size:11px;font-weight:600;color:'+(on?'var(--t1)':'var(--t3)')+';background:'+(on?'var(--sel)':'transparent')+'">'+r+'</button>';
  }).join('');
  var perms = PERM_CARDS.map(function(p){
    var on = state.permPolicy===p.id;
    return '<button onclick="A.pickPerm(\''+p.id+'\')" class="hv a985" style="display:flex;flex-direction:column;gap:5px;padding:12px 13px;border:1px solid '+(on?'var(--acc)':'var(--line)')+';border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur));transition:border-color .15s,background .15s">'
      + '<span style="display:flex;align-items:center;gap:7px;width:100%">'
      +   '<span style="width:13px;height:13px;border-radius:50%;border:1.5px solid '+(on?'var(--acc)':'var(--line)')+';display:inline-flex;align-items:center;justify-content:center"><span style="width:6px;height:6px;border-radius:50%;background:'+(on?'var(--acc)':'transparent')+'"></span></span>'
      +   '<span style="font-size:12.5px;font-weight:650;color:var(--t1)">'+p.name+'</span>'
      +   (p.rec ? '<span style="margin-left:auto;font-size:9.5px;font-weight:700;color:var(--acc);background:var(--acc-soft);padding:1px 6px;border-radius:999px">DEFAULT</span>' : '')
      + '</span>'
      + '<span style="font-size:11px;line-height:1.45;color:var(--t3);text-align:left">'+p.desc+'</span>'
      + '</button>';
  }).join('');
  var permTgls = PERM_TOGGLES.map(function(t){
    return '<div style="display:flex;align-items:center;gap:12px;padding:11px 16px;border-bottom:1px solid var(--line)">'
      + '<span style="flex:1"><span style="display:block;font-size:13px;font-weight:550;color:var(--t1)">'+t.label+'</span><span style="display:block;font-size:11.5px;color:var(--t3);margin-top:1px">'+t.desc+'</span></span>'
      + toggleBtn(state[t.id], 'A.togglePerm(\''+t.id+'\')')
      + '</div>';
  }).join('');
  var mcpDefs = [
    { id:'github', name:'github', desc:'Issues, PRs, checks', st: state.mcpGithub ? 'ok' : 'off' },
    { id:'pg', name:'postgres-local', desc:'Read-only schema + explain', st: state.mcpPg ? 'ok' : 'off' },
    { id:'stripe', name:'stripe-fixtures', desc:'Test-mode payment fixtures', st: state.mcpStripe }
  ];
  var mcps = mcpDefs.map(function(m){
    var on = m.st==='ok';
    var dot = on ? 'var(--ok)' : m.st==='error' ? 'var(--err)' : 'var(--t3)';
    var right = '';
    if (m.st==='error') right = '<span style="font-size:10.5px;font-weight:650;color:var(--err);background:var(--err-soft);padding:2px 8px;border-radius:999px">Auth expired</span>'
      + '<button onclick="A.mcpReconnect()" class="hv a96" style="height:25px;padding:0 11px;border-radius:7px;border:1px solid var(--line);color:var(--t1);font-size:11px;font-weight:600;transition:background .15s">Reconnect</button>';
    else if (m.st==='connecting') right = spinnerIcon(13,'var(--acc)');
    else if (m.id!=='stripe' || on) right = toggleBtn(on, 'A.mcpToggle(\''+m.id+'\')');
    return '<div style="display:flex;align-items:center;gap:11px;padding:11px 16px;border-bottom:1px solid var(--line)">'
      + '<span style="width:8px;height:8px;flex:none;border-radius:50%;background:'+dot+'"></span>'
      + '<span style="flex:1;min-width:0"><span style="display:block;font-family:\'JetBrains Mono\',monospace;font-size:12px;font-weight:600;color:var(--t1)">'+m.name+'</span><span style="display:block;font-size:11.5px;color:var(--t3);margin-top:1px">'+m.desc+'</span></span>'
      + right
      + '</div>';
  }).join('');
  return '<div data-scroll="settings" style="flex:1;overflow-y:auto;min-height:0">'
    + '<div style="max-width:720px;margin:0 auto;padding:44px 32px 48px;display:flex;flex-direction:column;gap:26px">'
    +   '<div><div style="font-size:20px;font-weight:700;letter-spacing:-.3px">Settings</div><div style="font-size:12.5px;color:var(--t2);margin-top:3px">Workspace defaults for cyberstation-spa.</div></div>'
    +   '<div style="display:flex;flex-direction:column;gap:10px">'
    +     '<div style="font-size:11px;font-weight:700;letter-spacing:.1em;color:var(--t3)">APPEARANCE</div>'
    +     '<div style="border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur))">'
    +       '<div style="display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid var(--line)"><span style="flex:1;font-size:13px;font-weight:550">Theme</span><div style="display:flex;background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:2px;gap:1px">'+themeSegs+'</div></div>'
    +       '<div style="display:flex;align-items:center;gap:12px;padding:12px 16px"><span style="flex:1;font-size:13px;font-weight:550">Direction</span><div style="display:flex;background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:2px;gap:1px">'+dirSegs+'</div></div>'
    +     '</div>'
    +   '</div>'
    +   '<div style="display:flex;flex-direction:column;gap:10px">'
    +     '<div style="font-size:11px;font-weight:700;letter-spacing:.1em;color:var(--t3)">MODEL &amp; HARNESS</div>'
    +     '<div style="border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur))">'
    +       models
    +       '<div style="display:flex;align-items:center;gap:12px;padding:11px 16px"><span style="flex:1;font-size:13px;font-weight:550">Reasoning effort</span><div style="display:flex;background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:2px;gap:1px">'+reason2+'</div></div>'
    +     '</div>'
    +   '</div>'
    +   '<div style="display:flex;flex-direction:column;gap:10px">'
    +     '<div style="font-size:11px;font-weight:700;letter-spacing:.1em;color:var(--t3)">PERMISSIONS</div>'
    +     '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">'+perms+'</div>'
    +     '<div style="border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur))">'+permTgls+'</div>'
    +   '</div>'
    +   '<div style="display:flex;flex-direction:column;gap:10px">'
    +     '<div style="display:flex;align-items:center"><span style="font-size:11px;font-weight:700;letter-spacing:.1em;color:var(--t3)">MCP SERVERS</span><button onclick="A.addServer()" class="hvo" style="margin-left:auto;font-size:11.5px;font-weight:600;color:var(--acc);transition:opacity .12s">+ Add server</button></div>'
    +     '<div style="border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur))">'+mcps+'</div>'
    +   '</div>'
    +   '<div style="display:flex;flex-direction:column;gap:10px">'
    +     '<div style="font-size:11px;font-weight:700;letter-spacing:.1em;color:var(--t3)">PLAN &amp; USAGE</div>'
    +     '<div style="display:flex;align-items:center;gap:14px;padding:14px 16px;border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel);backdrop-filter:blur(var(--blur))">'
    +       '<span style="flex:1"><span style="display:block;font-size:13px;font-weight:650">AutoCode Pro</span><span style="display:block;font-size:11.5px;color:var(--t3);margin-top:2px">'+cm.pct+'% of weekly compute used · resets Monday</span>'
    +         '<span style="display:block;height:4px;border-radius:999px;background:var(--line);margin-top:9px;overflow:hidden;max-width:300px"><span style="display:block;width:'+cm.pct+'%;height:100%;border-radius:999px;background:var(--acc)"></span></span>'
    +       '</span>'
    +       '<button onclick="A.billing()" class="hvt" style="flex:none;height:28px;padding:0 13px;border-radius:var(--r);border:1px solid var(--line);color:var(--t2);font-size:11.5px;font-weight:600;transition:background .15s">Manage billing</button>'
    +     '</div>'
    +   '</div>'
    + '</div>'
    + '</div>';
}

/* ---------- toasts ---------- */
function toastsHtml(){
  var items = state.toasts.map(function(t){
    return '<div style="display:flex;align-items:center;gap:8px;padding:8px 13px;background:var(--glass);backdrop-filter:blur(var(--blur));border:1px solid var(--line2);border-radius:var(--r);box-shadow:0 10px 30px rgba(0,0,0,.25);font-size:12.5px;color:var(--t1);animation:fadeUp .18s ease">'
      + '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+I.check+'</svg>'
      + esc(t.msg) + '</div>';
  }).join('');
  return '<div style="position:absolute;right:18px;bottom:18px;display:flex;flex-direction:column;gap:8px;z-index:60;pointer-events:none">'+items+'</div>';
}

/* ---------- root view ---------- */
function cur(){ return { dir:state.dir, theme:state.theme, view:state.view, threadId:state.threadId, tab:state.tab, editorOpen:state.editorOpen, reviewOpen:state.reviewOpen }; }
function themeVars(c){
  var P = PAL[c.dir][c.theme];
  var C = CODE_PAL[c.theme==='light'?'light':'dark'];
  return '--desk:'+P.desk+';--deskimg:'+P.deskimg+';--win:'+P.win+';--panel:'+P.panel+';--panel2:'+P.panel2+';--glass:'+P.glass+';--hov:'+P.hov+';--sel:'+P.sel+';--line:'+P.line+';--line2:'+P.line2+';--t1:'+P.t1+';--t2:'+P.t2+';--t3:'+P.t3+';--acc:'+P.acc+';--acc-ink:'+P.accInk+';--acc-soft:'+P.accSoft+';--ok:'+P.ok+';--ok-soft:'+P.okSoft+';--warn:'+P.warn+';--warn-soft:'+P.warnSoft+';--err:'+P.err+';--err-soft:'+P.errSoft+';--blur:'+P.blur+';--r:'+P.r+';--r-lg:'+P.rlg+';--shadow:'+P.shadow
    + ';--c-kw:'+C.kw+';--c-ty:'+C.ty+';--c-fn:'+C.fn+';--c-st:'+C.st+';--c-nu:'+C.nu+';--c-cm:'+C.cm+';--c-pn:'+C.pn+';--c-gh:'+C.gh;
}
function view(){
  var c = cur();
  var main = c.view==='home' ? home(c)
    : c.view==='thread' ? thread(c)
    : c.view==='automations' ? automations(c)
    : c.view==='skills' ? skillsView(c)
    : settingsView(c);
  return '<div onclick="A.closePops()" style="position:fixed;inset:0;background:var(--desk);overflow:hidden;font-size:13px;'+themeVars(c)+'">'
    + '<div style="position:absolute;inset:0;background:var(--deskimg);pointer-events:none;transition:opacity .4s"></div>'
    + '<div style="position:absolute;inset:20px;display:flex;flex-direction:column;background:var(--win);backdrop-filter:blur(28px) saturate(1.25);border:1px solid var(--line2);border-radius:16px;box-shadow:var(--shadow);overflow:hidden;color:var(--t1)">'
    +   titlebar(c)
    +   '<div style="flex:1;display:flex;min-height:0">'
    +     sidebar(c)
    +     '<div style="flex:1;display:flex;flex-direction:column;min-width:0;position:relative">'+main+toastsHtml()+'</div>'
    +   '</div>'
    + '</div>'
    + '</div>';
}

/* ---------- render with focus/scroll preservation ---------- */
function render(){
  var appEl = document.getElementById('app');
  var act = document.activeElement;
  var focusId = (act && act.id) ? act.id : null;
  var selS = null, selE = null;
  if (focusId && (act.tagName==='INPUT' || act.tagName==='TEXTAREA')) { selS = act.selectionStart; selE = act.selectionEnd; }
  var scrolls = {};
  var nodes = appEl.querySelectorAll('[data-scroll]');
  for (var i=0;i<nodes.length;i++) scrolls[nodes[i].getAttribute('data-scroll')] = { t:nodes[i].scrollTop, l:nodes[i].scrollLeft };
  appEl.innerHTML = view();
  nodes = appEl.querySelectorAll('[data-scroll]');
  for (var j=0;j<nodes.length;j++) {
    var s = scrolls[nodes[j].getAttribute('data-scroll')];
    if (s) { nodes[j].scrollTop = s.t; nodes[j].scrollLeft = s.l; }
  }
  if (focusId) {
    var el = document.getElementById(focusId);
    if (el) { el.focus(); if (selS !== null && el.setSelectionRange) { try { el.setSelectionRange(selS, selE); } catch(e){} } }
  }
}
function scrollChatBottom(){
  var el = document.querySelector('[data-scroll="chat"]');
  if (el) el.scrollTop = el.scrollHeight;
}

/* ---------- behaviors ---------- */
function toast(msg){
  var id = ++toastSeq;
  state.toasts = state.toasts.concat([{ id:id, msg:msg }]);
  render();
  /* Toast lifetime is a demo-simulated async behavior (lives in demo.js). */
  DEMO.dismissToastLater(id);
}
function focusHome(){ var el = document.getElementById('i-home'); if (el) el.focus(); }
function acceptGhost(){ if (state.ghostDone) return; state.ghostDone = true; render(); toast('Inline suggestion accepted · Tab'); }
function acceptCompl(){
  var it = COMPL[state.complIdx];
  if (it.n==='endsAt') { state.l22 = 'fixed'; render(); toast('Quick fix applied — 0 problems'); }
  else { state.l22 = 'error'; render(); toast('Inserted .' + it.n); }
}
function send(which){
  var key = which==='home' ? 'composerHome' : 'composerThread';
  var text = (state[key]||'').trim();
  if (!text) return;
  if (which==='home') {
    var id = 'nt' + Date.now();
    var th = { id:id, title: text.length>44 ? text.slice(0,44)+'…' : text, rows:[{kind:'user',text:text}], meta:'worktree · '+state.model+' · just now', running:true, group:'active' };
    state.newThreads = [th].concat(state.newThreads);
    state.composerHome = '';
    state.view = 'thread'; state.threadId = id; state.tab = 'chat'; state.editorOpen = false; state.reviewOpen = false;
    state.thinking[id] = true;
    render(); scrollChatBottom();
    /* LIVE SEAM: chat send (home) — the optimistic user row above renders in both modes.
       Live: live().sendHome(id, text) issues a `chat` request; on_token/on_thinking/on_done
       drive the new thread's transcript through the reducer. Demo: DEMO.simSendHome appends
       a canned plan after a beat. */
    var L = live();
    if (L && L.sendHome) L.sendHome(id, text);
    else DEMO.simSendHome(id);
  } else {
    var tid = state.threadId;
    state.composerThread = '';
    state.extras[tid] = (state.extras[tid]||[]).concat([{kind:'user',text:text}]);
    state.thinking[tid] = true;
    render(); scrollChatBottom();
    /* LIVE SEAM: chat send (thread reply) — live().sendThread(tid, text) issues `chat`;
       streamed events append the answer. Demo: DEMO.simSendThread appends a canned reply. */
    var L2 = live();
    if (L2 && L2.sendThread) L2.sendThread(tid, text);
    else DEMO.simSendThread(tid);
  }
}

/* ---------- actions ---------- */
var A = {
  closePops: function(){ if (state.popSkills||state.popMode||state.popModel) set({popSkills:false,popMode:false,popModel:false}); },
  setDir: function(d){ set({dir:d}); },
  setTheme: function(t){ set({theme:t}); },
  toggleTheme: function(){ set({theme: state.theme==='dark' ? 'light' : 'dark'}); },
  setView: function(v){ set({view:v}); },
  openThread: function(id){
    /* LIVE SEAM: sessions — live().openThread(id) issues session.resume and the reducer
       loads that thread's transcript. Demo just switches local view state. */
    var L = live(); if (L && L.openThread) L.openThread(id);
    set({view:'thread', threadId:id, tab:'chat', editorOpen:false, reviewOpen: id==='t1' ? state.reviewOpen : false});
  },
  backHome: function(){ set({view:'home'}); },
  newThread: function(){
    /* LIVE SEAM: sessions — live().newThread() issues session.new; demo opens the home composer. */
    var L = live(); if (L && L.newThread) L.newThread();
    set({view:'home'}); setTimeout(focusHome, 50);
  },
  onSearch: function(e){
    /* LIVE SEAM: sessions — search filters the live session list (see allThreads);
       demo filters DEMO.THREADS. */
    state.search = e.target.value;
    var L = live(); if (L && L.onSearch) L.onSearch(state.search);
    render();
  },
  onComposerHome: function(e){ state.composerHome = e.target.value; },
  onComposerThread: function(e){ state.composerThread = e.target.value; },
  homeKey: function(e){ if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); send('home'); } },
  threadKey: function(e){ if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); send('thread'); } },
  sendHome: function(){ send('home'); },
  sendThread: function(){ send('thread'); },
  togglePopSkills: function(e){ e.stopPropagation(); set({popSkills:!state.popSkills, popMode:false, popModel:false}); },
  togglePopMode: function(e){ e.stopPropagation(); set({popMode:!state.popMode, popSkills:false, popModel:false}); },
  togglePopModel: function(e){ e.stopPropagation(); set({popModel:!state.popModel, popSkills:false, popMode:false}); },
  skillInsert: function(i){
    var key = state.view==='thread' ? 'composerThread' : 'composerHome';
    var patch = {popSkills:false}; patch[key] = skillsPop()[i].cmd + ' ';
    set(patch);
    var el = document.getElementById(state.view==='thread' ? 'i-thread' : 'i-home'); if (el) el.focus();
  },
  openSkillsPage: function(){ set({view:'skills', popSkills:false}); },
  pickMode: function(i){
    /* LIVE SEAM: config — live().setMode/setModel/setReasoning persist the choice via
       config.set (mirrored by on_status). Demo just updates local state. */
    var L = live(); if (L && L.setMode) L.setMode(MODES[i].label);
    set({mode:MODES[i].label, popMode:false});
  },
  pickModel: function(i){
    var L = live(); if (L && L.setModel) L.setModel(MODELS[i].label);
    set({model:MODELS[i].label, popModel:false});
  },
  pickReasoning: function(r){
    var L = live(); if (L && L.setReasoning) L.setReasoning(r);
    set({reasoning:r});
  },
  cancelTurn: function(){
    /* LIVE SEAM: cancel turn — live().cancel() sends the `cancel` request (Esc → steer
       per §4); the reducer resolves the active turn via on_done(cancelled). Demo: no-op. */
    var L = live(); if (L && L.cancel) L.cancel();
  },
  chip: function(i){ set({composerHome:QUICK_CHIPS[i]}); focusHome(); },
  selChat: function(){ set({tab:'chat'}); },
  selEditor: function(){ set({tab:'editor', editorOpen:true}); },
  closeEditor: function(e){ if (e) e.stopPropagation(); set({editorOpen:false, tab:'chat'}); },
  toggleReview: function(){ set({reviewOpen:!state.reviewOpen}); },
  toggleAct: function(id){ state.exp[id] = !state.exp[id]; render(); },
  approve: function(){
    /* LIVE SEAM: approval decision — live().approve() replies "allow" to the pending
       on_tool_request/on_ask_user server request; the reducer advances on on_done.
       Demo flips local approval state + toast. */
    var L = live(); if (L && L.approve) { L.approve(); return; }
    set({approval:'ok'}); toast('Approved — running pnpm test:e2e');
  },
  deny: function(){
    /* LIVE SEAM: approval decision — live().deny() replies "deny". Demo flips state + toast. */
    var L = live(); if (L && L.deny) { L.deny(); return; }
    set({approval:'no'}); toast('Denied — e2e run skipped');
  },
  toggleApprovalOut: function(){ set({showApprovalOut:!state.showApprovalOut}); },
  answerAct: function(kind){
    if (kind==='editor') set({editorOpen:true, tab:'editor'});
    else if (kind==='review') set({reviewOpen:true});
    else toast('Opening github.com/cyberstation/spa (demo)');
  },
  /* editor */
  chipTry: function(i){
    if (i===0) { set({ghostDone:false, peekOn:false, sigOn:false, l22: state.l22==='typing' ? 'error' : state.l22}); toast('Ghost suggestion restored — press Tab'); }
    else if (i===1) set({l22:'typing', complIdx:0, peekOn:false, sigOn:false, hoverOn:false});
    else if (i===2) set({hoverOn:!state.hoverOn, sigOn:false, peekOn:false});
    else if (i===3) set({sigOn:!state.sigOn, hoverOn:false, peekOn:false});
    else if (i===4) set({peekOn:!state.peekOn, hoverOn:false, sigOn:false});
    else set({hintsOn:!state.hintsOn});
  },
  hoverIn: function(){ clearTimeout(hoverT); if (!state.hoverOn) set({hoverOn:true}); },
  hoverOut: function(){ clearTimeout(hoverT); hoverT = setTimeout(function(){ if (state.hoverOn) set({hoverOn:false}); }, 260); },
  hoverStay: function(){ clearTimeout(hoverT); },
  openPeek: function(){ set({peekOn:true, hoverOn:false, sigOn:false}); },
  closePeek: function(){ set({peekOn:false}); },
  toggleSig: function(){ set({sigOn:!state.sigOn, hoverOn:false, peekOn:false}); },
  goSessions: function(){ toast('Opening sessions.ts (demo)'); },
  startCompletion: function(){ set({l22:'typing', complIdx:0, peekOn:false, sigOn:false, hoverOn:false}); },
  complPick: function(e, i){ e.stopPropagation(); if (i===state.complIdx) acceptCompl(); else set({complIdx:i}); },
  acceptGhost: function(){ acceptGhost(); },
  resetDemo: function(){ set({ghostDone:false, l22:'error', complIdx:0, hoverOn:false, sigOn:false, peekOn:false, hintsOn:true}); toast('IntelliSense demo reset'); },
  fileClick: function(i){ if (!FILE_TREE[i].active) toast('Demo focuses on pricing.ts'); },
  /* review */
  selDiff: function(id){ set({diffFile:id}); },
  stageFile: function(id){ state.staged[id] = !state.staged[id]; render(); },
  stageAll: function(){ set({staged:{f1:true,f2:true,f3:true}}); },
  onCommit: function(e){ state.commitMsg = e.target.value; },
  createPR: function(){ set({prState:'creating'}); DEMO.simCreatePR(); },
  viewPR: function(){ toast('Opening github.com/cyberstation/spa/pull/131 (demo)'); },
  /* automations / skills / settings */
  autoToggle: function(id){
    var on = !state.autos[id]; state.autos[id] = on; render();
    var name = ''; for (var i=0;i<AUTOMATIONS.length;i++) if (AUTOMATIONS[i].id===id) name = AUTOMATIONS[i].name;
    toast(name + (on ? ' enabled' : ' paused'));
  },
  newAutomation: function(){ toast('Automation builder (demo)'); },
  runSkill: function(i){ set({view:'home', composerHome:skillCards()[i].cmd+' '}); setTimeout(focusHome, 50); },
  newSkill: function(){ toast('Skill editor (demo)'); },
  pickPerm: function(id){
    set({permPolicy:id});
    var name = ''; for (var i=0;i<PERM_CARDS.length;i++) if (PERM_CARDS[i].id===id) name = PERM_CARDS[i].name;
    toast('Approval policy: ' + name);
  },
  togglePerm: function(key){ state[key] = !state[key]; render(); },
  mcpToggle: function(id){
    if (id==='github') state.mcpGithub = !state.mcpGithub;
    else if (id==='pg') state.mcpPg = !state.mcpPg;
    else state.mcpStripe = 'error';
    render();
  },
  mcpReconnect: function(){ set({mcpStripe:'connecting'}); DEMO.simMcpReconnect(); },
  billing: function(){ toast('Billing portal (demo)'); },
  addServer: function(){ toast('MCP server wizard (demo)'); }
};

/* ---------- global keyboard (editor IntelliSense demo + thread cancel) ---------- */
window.addEventListener('keydown', function(e){
  /* LIVE SEAM: cancel turn — Escape in the thread chat view cancels the active turn
     (live: `cancel`/`steer`; demo: no-op). */
  if (state.view==='thread' && state.tab==='chat' && e.key==='Escape') { A.cancelTurn(); return; }
  if (state.view!=='thread' || state.tab!=='editor') return;
  var tag = e.target && e.target.tagName;
  if (tag==='INPUT' || tag==='TEXTAREA') return;
  if (state.l22==='typing') {
    if (e.key==='ArrowDown') { e.preventDefault(); state.complIdx = Math.min(5, state.complIdx+1); render(); }
    else if (e.key==='ArrowUp') { e.preventDefault(); state.complIdx = Math.max(0, state.complIdx-1); render(); }
    else if (e.key==='Enter' || e.key==='Tab') { e.preventDefault(); acceptCompl(); }
    else if (e.key==='Escape') { set({l22:'error'}); }
    return;
  }
  if (e.key==='Tab' && !state.ghostDone) { e.preventDefault(); acceptGhost(); }
  else if (e.key==='Escape') { set({peekOn:false, sigOn:false, hoverOn:false}); }
});

/* ---------- init ---------- */
function applyDemoFlag(){
  /* LIVE SEAM: demo/live switch — index.html sets window.__demo=true for ?demo=1. When
     demo is forced, live mode is turned off so live() returns null and every seam falls
     back to DEMO. T3 constructs window.Live (from rpc.js + events.js) and leaves it
     enabled only when window.__demo is not set. Default today: demo mode. */
  if (window.__demo === true && window.Live) window.Live.enabled = false;
}

/* Public store handle for the live wiring (T3) and tests. */
window.A = A;
window.Store = { state: state, set: set, render: render };

function init(){
  applyDemoFlag();
  /* Guarded so headless tests can load app.js without an #app node and drive render() themselves. */
  if (document.getElementById('app')) render();
}
init();
