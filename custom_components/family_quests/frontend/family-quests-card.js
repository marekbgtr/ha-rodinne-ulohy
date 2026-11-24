/* Rodinné úlohy 0.5.0 — dependency-free Lovelace card. */
(function () {
  "use strict";
  var esc = function (v) { return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); };
  var modes = {independent:"Každý samostatne", first:"Kto prvý", together:"Spoločne", rotation:"Na striedačku"};
  var days = ["Po", "Ut", "St", "Št", "Pi", "So", "Ne"];
  var button = function (label, action, attrs, cls) { return '<button type="button" class="' + (cls || '') + '" data-action="' + action + '" ' + (attrs || '') + '>' + label + '</button>'; };
  var attr = function (key, val) { return 'data-' + key + '="' + esc(val) + '"'; };
  var field = function (label, name, value, type, extra) { return '<label>' + esc(label) + '<input name="' + name + '" type="' + (type || 'text') + '" value="' + esc(value) + '" ' + (extra || '') + '></label>'; };
  var check = function (label, name, checked, value) { return '<label class="check"><input type="checkbox" name="' + name + '" value="' + esc(value == null ? 'yes' : value) + '" ' + (checked ? 'checked' : '') + '>' + esc(label) + '</label>'; };
  var select = function (label, name, value, choices) { return '<label>' + esc(label) + '<select name="' + name + '">' + Object.keys(choices).map(function (key) { return '<option value="' + esc(key) + '" ' + (key === value ? 'selected' : '') + '>' + esc(choices[key]) + '</option>'; }).join('') + '</select></label>'; };

  // Inline paths work without Android emoji/icon fonts or external downloads.
  var svg = function (body, filled) { return '<svg class="fq-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="'+(filled?'currentColor':'none')+'" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'+body+'</svg>'; };
  var stateIcon = function (state) {
    if(state==='exempt')return svg('<path d="M5 12h14"/>');
    if(state==='missed')return svg('<circle cx="12" cy="12" r="9"/><path d="m8 8 8 8m0-8-8 8"/>');
    return svg('<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>');
  };
  var tokenIcon = function (symbol, filled) {
    var shape;
    if(/[❤♥💗💖💕💙💚💛💜🧡🤍🖤🤎]/u.test(symbol))shape='<path d="M12 21 3.5 12.5C-2 6 6 0 12 6c6-6 14 0 8.5 6.5Z"/>';
    else if(/[🐴🐎♞♘]/u.test(symbol))shape='<path d="m8 21 1-5 5-4-4-1-3 3-4-2 5-7V2l4 3c7 0 8 8 7 16Z"/><path d="M7 21h13M10 7h.1"/>';
    else if(/[💎♦]/u.test(symbol))shape='<path d="m3 8 4-5h10l4 5-9 13ZM3 8h18M7 3l5 18 5-18"/>';
    else if(/[🦖🦕]/u.test(symbol))shape='<path d="M4 21v-5l-2-5 5 3h5V7l3-4h6v6h-5v6l-3 3v3h-3v-3H7v3Z"/><path d="M17 6h.1M16 12h3"/>';
    else if(/[⭐🌟★☆]/u.test(symbol))shape='<path d="m12 2 3 6 7 1-5 5 1 8-6-4-6 4 1-8-5-5 7-1Z"/>';
    else return '<span class="custom-token">'+esc(symbol)+'</span>'+(filled?'<span class="token-check">'+svg('<path d="m5 12 4 4 10-10"/>')+'</span>':'');
    return svg(shape,filled);
  };

  class FamilyQuestsCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({mode:"open"});
      this._tab = "today";
      this._week = 0;
      this._person = "";
      this._busy = false;
      this._loading = false;
      this._error = "";
      this._editor = null;
      this.shadowRoot.addEventListener("click", (ev) => this.click(ev));
      this.shadowRoot.addEventListener("submit", (ev) => this.submit(ev));
    }
    setConfig(config) {
      if (config.mode && ["child", "admin", "stats"].indexOf(config.mode) < 0) throw new Error("mode musí byť child, admin alebo stats");
      this._config = config;
      this._person = config.person || "";
      this.render();
    }
    set hass(hass) {
      this._hass = hass;
      if (!this._config) return;
      var board = Object.keys(hass.states).map(k => hass.states[k]).find(s => s.attributes.family_quests_board);
      var revision = board ? board.state : "missing";
      if ((!this._data || revision !== this._revision) && !this._loading && !this._busy && !this._editor) {
        this._revision = revision;
        this.refresh();
      }
    }
    connectedCallback() {
      if (!this._timer) this._timer = setInterval(() => {
        if (this._hass && !this._editor && !this._busy) this.refresh();
      }, 30000);
      if (this._hass) this.refresh();
    }
    disconnectedCallback() { clearInterval(this._timer); this._timer = null; }
    getCardSize() { return 8; }
    static getStubConfig() { return {mode:"child"}; }
    async refresh() {
      if (!this._hass || this._loading) return;
      this._loading = true;
      try { this._data = await this._hass.callWS({type:"family_quests/get"}); }
      catch (e) { this._error = e.message || String(e); }
      finally { this._loading = false; this.render(); }
    }
    async act(action, data) {
      if (this._busy) return;
      this._busy = true; this._error = "";
      this.shadowRoot.querySelectorAll("button").forEach(b => { b.disabled = true; });
      try {
        this._data = await this._hass.callWS({type:"family_quests/action", action:action, data:data,
          request_id: Date.now().toString(36) + "-" + Math.random().toString(36).slice(2), expected_version:this._data.version});
        this._editor = null;
      } catch (e) {
        this._error = e.message || String(e);
        // Reload the server state on stale version or an uncertain network response.
        try { this._data = await this._hass.callWS({type:"family_quests/get"}); } catch (_) { /* keep error */ }
      } finally { this._busy = false; this.render(); }
    }
    person(pid) { return this._data.people.find(p => p.id === pid); }
    chosen() {
      return this._data.people.find(p => p.id === this._person || p.name === this._person) || this._data.people.find(p => p.active) || this._data.people[0];
    }
    header(p, admin) {
      if (!p) return '<div class="empty">Pridaj prvého účastníka v rodičovskej karte.</div>';
      return '<div class="hero"><div class="avatar">' + (p.avatar ? '<img src="' + esc(p.avatar) + '" alt="' + esc(p.name) + '">' : esc(p.name.slice(0,1))) + '</div><div class="grow"><h2>' + esc(p.name) + '</h2><div class="muted">' + (admin ? 'Rodičovský prehľad' : this._config.mode === 'stats' ? 'Týždenný prehľad' : 'Tvoje dnešné úlohy') + '</div></div><div class="balance"><b>' + p.balance + ' <span>' + esc(p.symbol) + '</span></b><small>' + esc(p.unit) + '</small></div></div>';
    }
    status(occ, pid) {
      var m = occ.members[pid];
      if (m.exempt) return "exempt";
      if (m.award) return "done";
      if (m.submitted) return m.confirmed ? "waiting" : "approval";
      if (occ.winner && occ.winner !== pid) return "other";
      if (Date.now() >= Date.parse(occ.cutoff)) return "missed";
      return "open";
    }
    taskRow(occ, pid, admin) {
      if (occ.task.frequency === "repeat") return this.repeatRow(occ,pid,admin);
      var p = this.person(pid), status = this.status(occ, pid), m = occ.members[pid];
      if (!p || (!admin && status === "other")) return '';
      var labels = {done:"Hotovo", approval:"Čaká na rodiča", waiting:"Čaká na ostatných", exempt:"Ospravedlnené", other:"Splnil niekto iný", missed:"Čas vypršal"};
      var late = Date.now() > Date.parse(occ.due), points = late ? occ.task.late_points : occ.task.points;
      var data = attr("oid", occ.id) + ' ' + attr("pid", pid);
      var shownPoints = m.full_points ? occ.task.points : m.submitted ? ((!occ.due || Date.parse(m.submitted) <= Date.parse(occ.due)) ? occ.task.points : occ.task.late_points) : points;
      if (m.award && occ.task.mode === 'together' && occ.task.split) {
        var eligible = Object.keys(occ.members).filter(id => !occ.members[id].exempt);
        var pool = Math.min.apply(null, eligible.map(id => (occ.members[id].full_points || !occ.due || Date.parse(occ.members[id].submitted) <= Date.parse(occ.due)) ? occ.task.points : occ.task.late_points));
        shownPoints = Math.floor(pool / eligible.length) + (eligible.indexOf(pid) < pool % eligible.length ? 1 : 0);
      }
      var deadline = occ.task.frequency === 'weekly' ? 'Tento týždeň · do nedele' : occ.task.frequency === 'ongoing' ? 'Bez termínu' : (occ.task.frequency === 'once' ? 'Do ' + occ.task.date + ' · ' : 'do ') + occ.task.due;
      var details = esc(deadline) + ' · ' + shownPoints + ' ' + esc(p.symbol);
      if (status !== "open") details = labels[status] + ' · ' + details;
      if (m.full_points) details += ' · Plné body uznal rodič';
      if (admin) details = esc(p.name) + ' · ' + occ.day + ' · ' + details;
      var controls = '';
      if (admin) {
        if (m.exempt) controls += button('Zrušiť ospravedlnenie','unexempt',data,'quiet');
        if (!m.exempt && status !== 'other' && !m.full_points && (late || status === 'missed')) controls += button('Uznať za plné body','approve_full',data,'positive');
        if (status === "approval") controls += button('Schváliť', 'approve', data, 'positive');
        if (m.submitted) controls += button('↶ Vrátiť', 'undo', data, 'quiet');
        else if (!m.exempt && status !== "other") controls += button('Ospravedlniť', 'exempt', data, 'quiet');
      } else if (status === "open") controls = button(tokenIcon(p.symbol,false), 'complete', data + ' aria-label="' + esc('Splniť: ' + occ.task.name) + '"', 'star');
      else controls = '<span class="status-icon" aria-label="' + esc(labels[status]) + '">' + (status === "done" ? tokenIcon(p.symbol,true) : stateIcon(status)) + '</span>';
      return '<div class="task ' + status + '"><span class="task-icon">' + esc(occ.task.icon) + '</span><div class="grow"><h3>' + esc(occ.task.name) + '</h3><div class="muted">' + details + '</div>' + (admin && m.exempt ? '<small>' + esc(m.exempt_reason) + '</small>' : '') + '</div><div class="actions">' + controls + '</div></div>';
    }
    repeatRow(occ,pid,admin) {
      var p=this.person(pid), m=occ.members[pid]; if(!p)return '';
      var records=(m.attempts||[]).filter(r=>!r.voided), done=records.filter(r=>r.award).length;
      var ended=Date.now()>=Date.parse(occ.cutoff), limit=occ.task.repeat_limit, goal=occ.task.repeat_goal;
      var capped=!!limit&&records.length>=limit;
      var ready=!m.exempt&&!ended&&!capped;
      var data=attr('oid',occ.id)+' '+attr('pid',pid), controls='';
      var details='Dnes splnené '+done+'× · získané '+(done*occ.task.points)+' '+esc(p.symbol);
      details+=' · '+occ.task.points+' '+esc(p.symbol)+' za splnenie';
      if(goal)details+=' · cieľ '+goal+'×';
      if(limit)details+=' · limit '+limit+'×';
      if(records.length>done)details+=' · čaká na rodiča '+(records.length-done)+'×';
      if(m.exempt)details+=' · Ospravedlnené';
      else if(ended)details+=' · Deň uzavretý';
      else if(capped)details+=' · Limit dosiahnutý';
      if(admin) {
        details=esc(p.name)+' · '+esc(occ.day)+' · '+details;
        controls=button(m.exempt?'Zrušiť ospravedlnenie':'Ospravedlniť',m.exempt?'unexempt':'exempt',data,'quiet');
      } else if(ready)controls=button(tokenIcon(p.symbol,false),'complete',data+' aria-label="Zaznamenať ďalšie splnenie: '+esc(occ.task.name)+'"','star');
      else controls='<span class="status-icon">'+(m.exempt?stateIcon('exempt'):done?tokenIcon(p.symbol,true):stateIcon('missed'))+'</span>';
      var history='';
      if(admin&&records.length)history='<details><summary>Jednotlivé splnenia ('+records.length+')</summary>'+records.map(r=>{
        var attrs=data+' '+attr('attempt',r.id);
        return '<div class="attempt"><span>'+esc(new Date(r.submitted).toLocaleTimeString('sk-SK',{hour:'2-digit',minute:'2-digit',timeZone:this._data.timezone||'Europe/Bratislava'}))+' · '+(r.award?'Schválené':'Čaká na rodiča')+'</span><div class="actions">'+(!r.award&&!m.exempt?button('Schváliť','approve',attrs,'positive'):'')+button('Vrátiť','undo',attrs,'quiet')+'</div></div>';
      }).join('')+'</details>';
      return '<div class="task '+(m.exempt?'exempt':ended&&goal&&done<goal?'missed':'')+'"><span class="task-icon">'+esc(occ.task.icon)+'</span><div class="grow"><h3>'+esc(occ.task.name)+'</h3><div class="muted">'+details+'</div>'+history+'</div><div class="actions">'+controls+'</div></div>';
    }
    child(p) {
      if (!p) return '';
      var today = this._data.occurrences.filter(o => (o.current == null ? o.day === this._data.today : o.current) && o.members[p.id] && (!o.winner || o.winner === p.id));
      var goal = this._data.rewards.find(r => r.id === p.goal && r.active);
      var goalPool=goal&&goal.shared?this.sharedRequest(goal.id):null;
      var goalSaved=goal&&goal.shared?(goalPool?goalPool.funded:0):p.balance;
      var result = p.show_statistics ? '<div class="pills"><span>✓ ' + p.week_completed + ' tento týždeň</span><span>' + (p.week_net >= 0 ? '+' : '') + p.week_net + ' ' + esc(p.symbol) + ' čistá zmena</span></div>' : '';
      if (goal) result += '<div class="goal"><div>' + esc(goal.icon) + ' <b>' + esc(goal.name) + '</b><span class="right">Ešte ' + Math.max(0,goal.cost-goalSaved) + ' ' + esc(p.symbol) + '</span></div><progress max="' + Math.max(1,goal.cost) + '" value="' + Math.max(0, Math.min(goal.cost,goalSaved)) + '"></progress></div>';
      result += '<nav>' + button('Úlohy', 'tab', attr('tab','today'), this._tab === 'today' ? 'selected' : '') + button('Odmeny', 'tab', attr('tab','rewards'), this._tab === 'rewards' ? 'selected' : '') + (p.show_statistics ? button('Môj týždeň', 'tab', attr('tab','stats'), this._tab === 'stats' ? 'selected' : '') : '') + button('Môj symbol', 'symbols', attr('pid',p.id), '') + '</nav>';
      if (this._tab === 'rewards') return result + this.rewardList(p, false);
      if (this._tab === 'stats' && p.show_statistics) return result + this.statistics(p);
      if (!today.length) return result + '<div class="empty">Dnes tu nemáš žiadne úlohy. 🌿</div>';
      var groups = Object.create(null);
      today.forEach(o => { var g = o.task.group || "Úlohy"; (groups[g] || (groups[g]=[])).push(o); });
      var groupOrder = this._data.group_order || [];
      var groupNames = groupOrder.filter(g => Object.prototype.hasOwnProperty.call(groups,g));
      Object.keys(groups).forEach(g => { if(groupNames.indexOf(g)<0)groupNames.push(g); });
      groupNames.forEach(g => {
        var list = groups[g], done = list.filter(o => o.task.frequency === "repeat" ? (o.members[p.id].attempts||[]).filter(r=>!r.voided&&r.award).length >= Math.max(1,o.task.repeat_goal||0) : !!o.members[p.id].award).length;
        result += '<h4>' + esc(g) + '<span>' + done + ' / ' + list.length + '</span></h4>' + list.sort((a,b) => (a.due || '9999').localeCompare(b.due || '9999')).map(o => this.taskRow(o,p.id,false)).join('');
      });
      return result;
    }
    sharedRequest(rid) {
      return this._data.requests.find(q=>q.shared&&q.reward.id===rid&&['funding','pending'].indexOf(q.status)>=0);
    }
    contributorNames(q) {
      return Object.keys(q.contributors||{}).map(pid=>{
        var p=this.person(pid)||{name:'Účastník',symbol:''};
        return p.name+': '+q.contributors[pid]+' '+p.symbol;
      }).join(' · ');
    }
    sharedReward(r,p,admin) {
      var q=this.sharedRequest(r.id), reward=q?q.reward:r, funded=q?q.funded:0;
      var pending=q&&q.status==='pending', remaining=reward.cost-funded;
      var own=q&&q.contributors?q.contributors[p.id]||0:0;
      var attrs=attr('id',r.id)+' '+attr('pid',p.id), controls='';
      if(admin) {
        controls=button('Upraviť','edit-reward',attr('id',r.id));
        if(q)controls+=button('Zrušiť zbieranie a vrátiť body','cancel-pool',attr('id',q.id),'negative');
      } else {
        controls=button(pending?'Čaká na rodiča':!r.active?'Pozastavené':p.balance<=0?'Chýbajú body':'Prispieť','contribute',attrs+(pending||!r.active||p.balance<=0?' disabled':''),'positive');
        if(own&&!pending)controls+=button('Vrátiť môj príspevok','withdraw',attr('id',q.id)+' '+attr('pid',p.id),'quiet');
        if(r.active)controls+=button(p.goal===r.id?'Môj cieľ':'Dať ako cieľ','goal',attrs,'quiet');
      }
      return '<div class="task reward shared-reward"><span class="task-icon">'+esc(reward.icon)+'</span><div class="grow"><h3>'+esc(reward.name)+'</h3><div class="muted">Spoločná odmena · '+funded+' / '+reward.cost+' bodov · zostáva '+remaining+'</div><progress max="'+reward.cost+'" value="'+funded+'"></progress>'+(q?'<div class="muted">'+esc(this.contributorNames(q))+'</div>':'')+'<div class="actions pool-actions">'+controls+'</div></div></div>';
    }
    rewardList(p, admin) {
      var list = this._data.rewards.filter(r => admin || r.active || (r.shared && this.sharedRequest(r.id)));
      var result = admin ? button('+ Nová odmena','edit-reward','', 'primary') : '';
      if (!list.length) result += '<div class="empty">Zatiaľ nie sú pridané odmeny.</div>';
      list.forEach(r => {
        if(r.shared){result+=this.sharedReward(r,p,admin);return;}
        var requests = this._data.requests.filter(q => q.person === p.id && q.reward.id === r.id);
        var pending = requests.some(q => q.status === 'pending');
        var needsTask = r.kind !== 'points';
        var needsPoints = r.kind !== 'task';
        var linked = this._data.reward_links && this._data.reward_links[p.id] ? this._data.reward_links[p.id][r.id] : r.task + ':' + this._data.today;
        var occ = needsTask && this._data.occurrences.find(o => o.id === linked);
        var member = occ && occ.members[p.id];
        var taskReady = !needsTask || (member && member.award && (!r.on_time || !occ.due || Date.parse(member.submitted) <= Date.parse(occ.due)));
        var pointsReady = !needsPoints || p.balance >= r.cost;
        var unlocked = taskReady && pointsReady;
        var used = needsTask && requests.some(q => q.occurrence === linked && ['pending','approved'].indexOf(q.status) >= 0);
        var description = (needsPoints ? r.cost + ' ' + p.symbol : '') + (needsTask ? (needsPoints ? ' + ' : '') + 'Splnená úloha' + (r.on_time ? ' načas' : '') : '');
        var task = this._data.tasks.find(t => t.id === r.task) || (occ && occ.task);
        if (task && needsTask) description += ': ' + task.name;
        var controls = admin ? button('Upraviť', 'edit-reward', attr('id',r.id)) : button(pending ? 'Čaká na rodiča' : used ? 'Vyžiadané' : unlocked ? 'Chcem odmenu' : !taskReady ? 'Najprv splň úlohu' : 'Chýbajú body', 'reward', attr('id',r.id) + ' ' + attr('pid',p.id) + (!unlocked || pending || used ? ' disabled' : ''), unlocked && !pending && !used ? 'positive' : '');
        if (!admin && needsPoints) controls += button(p.goal === r.id ? '🎯 Môj cieľ' : 'Dať ako cieľ', 'goal', attr('id',r.id) + ' ' + attr('pid',p.id), 'quiet');
        result += '<div class="task reward"><span class="task-icon">' + esc(r.icon) + '</span><div class="grow"><h3>' + esc(r.name) + (!r.active ? ' · neaktívna' : '') + '</h3><div class="muted">' + esc(description) + '</div></div><div class="actions">' + controls + '</div></div>';
      });
      if (!admin) result += '<p class="hint">Pri žiadosti sa body rezervujú. Rodič odmenu potvrdí alebo zamietne a body vráti.</p>';
      return result;
    }
    statistics(p) {
      if (!p) return '<div class="empty">Najprv pridaj účastníka.</div>';
      if (!p.show_statistics && !(this._data.admin && this._config.mode !== 'child')) return '<div class="empty">Štatistiky sprístupňuje rodič v nastaveniach.</div>';
      var weeks = (this._data.statistics || {})[p.id] || [];
      if (!weeks.length) return '<div class="empty">Štatistiky sa načítajú po aktualizácii integrácie.</div>';
      var index = Math.min(this._week || 0, weeks.length - 1), w = weeks[index];
      var shortDate = function (d) { var parts=d.split('-');return Number(parts[2])+'. '+Number(parts[1])+'.'; };
      var ratio = w.rate == null ? '—' : w.rate + '%';
      var html = '<div class="week-nav">' + button('‹', 'week', attr('step',1) + (index >= weeks.length-1?' disabled':'') + ' aria-label="Predchádzajúci týždeň"') + '<div><b>' + (w.current?'Tento týždeň':'Týždenné vyhodnotenie') + '</b><small>' + shortDate(w.start) + ' – ' + shortDate(w.end) + ' ' + w.end.slice(0,4) + (w.current?' · priebežne':'') + '</small></div>' + button('›','week',attr('step',-1) + (index===0?' disabled':'') + ' aria-label="Novší týždeň"') + '</div>';
      html += '<div class="week-message">'+esc(w.summary)+'</div><div class="stat-grid"><div><b>'+w.completed+'<small> / '+w.assigned+'</small></b><span>Hotové úlohy</span></div><div><b>'+ratio+'</b><span>Úspešnosť</span></div><div><b>'+w.earned+' '+esc(p.symbol)+'</b><span>Získané za úlohy</span></div></div>';
      html += '<div class="pills"><span>⏰ '+w.on_time+' načas</span><span>◷ '+w.late+' neskôr</span><span>'+w.waiting+' čaká na schválenie / ostatných</span><span>'+w.open+' ešte otvorených</span><span>'+w.missed+' nesplnených</span><span>'+w.exempt+' ospravedlnených</span></div>';
      html += '<h4>Týždeň po dňoch</h4><div class="week-days">'+w.days.map((d,i)=>{
        var pct=d.assigned?Math.round(100*d.completed/d.assigned):0;
        return '<div class="day '+(d.future?'future':'')+'" title="'+esc(d.date)+': '+d.completed+' z '+d.assigned+'"><span>'+days[i]+'</span><div class="day-track"><div style="height:'+pct+'%"></div></div><b>'+(d.future?'—':d.completed+'/'+d.assigned)+'</b></div>';
      }).join('')+'</div>';
      html += '<p class="hint">Počítajú sa doteraz priradené úlohy. Ospravedlnené úlohy a súťaže, v ktorých vyhral niekto iný, úspešnosť neznižujú. Dni bez úloh sa nehodnotia.</p>';
      if(w.groups.length) html += '<h4>Ako sa darí rutinám</h4>'+w.groups.map(g=>'<div class="routine-stat"><div><b>'+esc(g.name)+'</b><span>'+g.completed+' / '+g.assigned+'</span></div><progress max="'+g.assigned+'" value="'+g.completed+'"></progress></div>').join('');
      if(w.badges.length) html += '<h4>Týždenné odznaky</h4><div class="badges">'+w.badges.map(b=>'<span>'+esc(b.icon)+' '+esc(b.label)+'</span>').join('')+'</div>';
      html += '<details class="points-detail"><summary>Prehľad bodov · '+(w.net>=0?'+':'')+w.net+' '+esc(p.symbol)+'</summary><div class="point-line"><span>Za úlohy</span><b>+'+w.earned+'</b></div><div class="point-line"><span>Bonusy</span><b>+'+w.bonus+'</b></div><div class="point-line"><span>Postihy a ručné odpočty</span><b>−'+w.penalties+'</b></div><div class="point-line"><span>Odmeny vrátane rezervácií</span><b>−'+w.spent+'</b></div><p class="hint">Vrátené operácie sú z hodnotenia vyradené. Odznaky nepridávajú ďalšie body. Hotový deň sa vyhodnotí po skončení kalendárneho dňa.</p></details>';
      return html;
    }
    settings() {
      var order=this._data.group_order || [];
      var html='<h4>Štatistiky na detskej karte</h4><p class="hint">Zapni ich iba tým účastníkom, ktorým chceš zobrazovať týždenné vyhodnotenie. Rodičovský prehľad zostáva dostupný.</p>'+this._data.people.map(p=>'<div class="task"><div class="grow"><b>'+esc(p.name)+'</b><small> · '+(p.show_statistics?'Sprístupnené':'Skryté')+'</small></div>'+button(p.show_statistics?'Skryť':'Sprístupniť','statistics-toggle',attr('pid',p.id),p.show_statistics?'quiet':'positive')+'</div>').join('');
      html+='<h4>Poradie skupín úloh</h4><p class="hint">Poradie platí pre všetkých účastníkov. Úlohy vo vnútri skupiny sa radia podľa termínu. Nová skupina pribudne na koniec.</p>';
      html += order.map((g,i)=>'<div class="task"><div class="grow"><b>'+esc(g)+'</b></div>'+button('↑','group-move',attr('index',i)+' '+attr('step',-1)+(i===0?' disabled':'')+' aria-label="Posunúť vyššie"')+button('↓','group-move',attr('index',i)+' '+attr('step',1)+(i===order.length-1?' disabled':'')+' aria-label="Posunúť nižšie"')+'</div>').join('') || '<div class="empty">Skupinu vytvoríš vyplnením poľa Rutina / skupina pri úlohe.</div>';
      html += '<details class="maintenance"><summary>Prechod z testovania do ostrej prevádzky</summary><p class="hint">Vynuluje body a vymaže splnenia, históriu a žiadosti o odmeny celej domácnosti. Zachová profily, definície úloh a odmien aj poradie skupín. Obnoviť ich bude možné iba zo zálohy HA.</p>'+button('Pripraviť vymazanie testovania','reset-editor','','negative')+'</details>';
      return html;
    }
    admin(p) {
      var result = '<nav>' + [['today','Dnes'],['tasks','Úlohy'],['rewards','Odmeny'],['people','Účastníci'],['history','História'],['stats','Štatistiky'],['settings','Nastavenia']].map(x => button(x[1],'tab',attr('tab',x[0]),this._tab===x[0]?'selected':'')).join('') + '</nav>';
      if (this._tab === 'settings') return result + this.settings();
      if (this._tab === 'stats') return result + this.statistics(p);
      if (this._tab === 'people') return result + button('+ Pridať účastníka','edit-person','', 'primary') + this._data.people.map(x => '<div class="task"><div class="grow"><h3>' + esc(x.name) + ' ' + esc(x.symbol) + '</h3><small>' + (x.active?'Aktívny':'Neaktívny') + ' · ' + x.balance + ' bodov</small></div>' + button('Upraviť','edit-person',attr('id',x.id)) + '</div>').join('');
      if (this._tab === 'tasks') return result + button('+ Nová úloha','edit-task','', 'primary') + this._data.tasks.map(t => '<div class="task"><span class="task-icon">' + esc(t.icon) + '</span><div class="grow"><h3>' + esc(t.name) + '</h3><small>' + esc(modes[t.mode]) + ' · ' + esc(({repeat:'Viackrát za deň',weekly:'Raz za týždeň',ongoing:'Bez termínu',once:'Do ' + t.date,daily:t.due})[t.frequency]) + ' · ' + (t.active?'Aktívna':'Neaktívna') + '</small></div>' + button('Upraviť','edit-task',attr('id',t.id)) + '</div>').join('');
      if (!p) return result + '<div class="empty">Začni pridaním účastníka.</div>';
      if (this._tab === 'rewards') return result + this.rewardList(p,true);
      if (this._tab === 'history') return result + '<p class="hint">Posledných 100 bodových udalostí domácnosti. Úplná história zostáva uložená v HA.</p>' + this._data.history.filter(e => Object.prototype.hasOwnProperty.call(e.deltas,p.id)).map(e => '<div class="history"><div class="grow"><b>' + esc(e.reason) + '</b><small>' + esc(new Date(e.at).toLocaleString('sk-SK')) + (e.reversed_by ? ' · vrátené' : '') + '</small></div><strong>' + (e.deltas[p.id]>=0?'+':'') + e.deltas[p.id] + ' ' + esc(p.symbol) + '</strong>' + (e.kind==='manual'&&!e.reversed_by ? button('↶','reverse-adjustment',attr('id',e.id),'quiet') : '') + '</div>').join('');
      result += '<div class="adjust">' + [-10,-2,-1,1,2,10].map(n => button((n>0?'+':'')+n,'adjust',attr('pid',p.id)+' '+attr('delta',n),n>0?'positive':'negative')).join('') + '</div>';
      result += button('Iná suma / dôvod','edit-adjust',attr('pid',p.id),'quiet');
      var pending = this._data.requests.filter(q => q.status==='pending');
      if (pending.length) result += '<h4>Žiadosti o odmeny</h4>' + pending.map(q => '<div class="task"><div class="grow"><h3>' + esc(q.reward.name) + '</h3><small>' + esc(q.shared?this.contributorNames(q):(this.person(q.person)||{}).name) + '</small></div><div class="actions">' + button('Potvrdiť','decide',attr('id',q.id)+' '+attr('decision','approve'),'positive') + button('Zamietnuť','decide',attr('id',q.id)+' '+attr('decision','reject'),'quiet') + '</div></div>').join('');
      result += '<h4>Úlohy · ' + esc(p.name) + '</h4>';
      var rows = this._data.occurrences.filter(o=>o.members[p.id]).sort((a,b)=>b.day.localeCompare(a.day));
      result += rows.map(o=>this.taskRow(o,p.id,true)).join('') || '<div class="empty">Žiadne úlohy. Pridaj ich v záložke Úlohy.</div>';
      return result;
    }
    editor() {
      var ed=this._editor, v=ed.value || {}, type=ed.type, body='', title='';
      if (type==='reset') {
        title='Vymazať testovaciu históriu';
        body='<p class="error">Táto operácia vymaže históriu a body všetkých účastníkov. Profily, úlohy a odmeny zostanú. Operáciu nemožno vrátiť tlačidlom späť.</p>'+select('Novú evidenciu začať','start','tomorrow',{tomorrow:'Zajtra (odporúčané)',today:'Dnes'})+check('Mám vytvorenú zálohu Home Assistanta','backup_confirmed',false)+field('Na potvrdenie napíš VYMAZAT HISTORIU','confirmation','','text','required autocomplete="off"')+'<p class="hint">Pri začiatku dnes sa už uzavreté úlohy spätne nevyhodnotia. Dnešné ešte otvorené úlohy zostanú v platnosti.</p>';
      } else if (type==='person') {
        title=v.id?'Upraviť účastníka':'Nový účastník';
        body=field('Meno','name',v.name||'','text','required maxlength="50"') + field('Symbol bodov (emoji)','symbol',v.symbol||'⭐','text','required maxlength="16" list="symbols"') + field('Názov bodov','unit',v.unit||'Hviezdičky','text','required maxlength="40"') + field('Fotka – cesta /local/...','avatar',v.avatar||'') + check('Aktívny účastník','active',v.active!==false) + check('Sprístupniť štatistiky dieťaťu','show_statistics',!!v.show_statistics) + '<p class="hint">Fotku nahraj do /config/www/ a sem zadaj napr. /local/maty.jpg. Deaktivovanie ospravedlní dnešné nesplnené úlohy.</p>';
      } else if(type==='symbols') {
        title='Čo chceš zbierať?';
        body=field('Symbol','symbol',v.symbol,'text','required list="symbols" maxlength="16"') + field('Názov','unit',v.unit,'text','required maxlength="40"') + '<p class="hint">Napríklad ❤️ Srdiečka, 🐴 Koníky alebo ⭐ Hviezdičky. Počet bodov zostane rovnaký.</p>';
      } else if(type==='task') {
        title=v.id?'Upraviť úlohu':'Nová úloha';
        body=field('Názov','name',v.name||'','text','required maxlength="100"') + field('Ikona (emoji)','icon',v.icon||'✓','text','required maxlength="16"') + select('Spôsob plnenia','mode',v.mode||'independent',modes) + check('Všetci aktívni účastníci','everyone',v.everyone!==false) + '<div class="checks">' + this._data.people.map(p=>check(p.name,'people',(v.people||[]).indexOf(p.id)>=0,p.id)).join('') + '</div><small>Výber jednotlivcov platí po vypnutí „Všetci“.</small>' + select('Opakovanie','frequency',v.frequency||'daily',{daily:'Vybrané dni v týždni',repeat:'Viackrát za deň',weekly:'Raz za týždeň (ľubovoľný deň)',once:'Dlhodobá / jednorazová do dátumu',ongoing:'Bez termínu (jednorazovo)'}) + '<div class="checks">' + days.map((d,i)=>check(d,'days',(v.days||[0,1,2,3,4,5,6]).indexOf(i)>=0,i)).join('') + '</div>' + '<p class="hint">Dni a časy platia pre denné úlohy. Týždenná úloha trvá od pondelka do nedele, bez oneskorených bodov. Bez termínu zostáva otvorená do splnenia, bez postihu. Dátum a časy pri dlhodobej úlohe určujú jej koniec; dostupná je ihneď.</p>' + '<details><summary>Viackrát za deň – nastavenia</summary><p class="hint">Plnenie počas celého dňa vo vybrané dni. Body za každé splnenie; iba Každý samostatne alebo Na striedačku. Denné časy sa ignorujú. Postih sa vyhodnotí raz po polnoci, iba ak nie je splnený cieľ.</p>' + field('Denný limit (0 = bez limitu)','repeat_limit',v.repeat_limit==null?4:v.repeat_limit,'number','min="0" max="100"') + field('Denný cieľ (0 = dobrovoľná úloha)','repeat_goal',v.repeat_goal||0,'number','min="0" max="100"') + field('Odstup splnení v minútach','repeat_gap',v.repeat_gap==null?5:v.repeat_gap,'number','min="0" max="1440"') + '</details>' + field('Konečný dátum dlhodobej úlohy','date',v.date||this._data.today,'date','required') + '<div class="form-grid">' + field('Splniť načas do','due',v.due||'19:45','time','required') + field('Uzavrieť úlohu o','cutoff',v.cutoff||'22:00','time','required') + field('Body načas','points',v.points==null?1:v.points,'number','min="0" max="10000" required') + '</div><details><summary>Rozšírené nastavenia</summary><div class="form-grid">' + field('Body po termíne','late_points',v.late_points||0,'number','min="0" required') + field('Postih za nesplnenie','penalty',v.penalty||0,'number','min="0" required') + field('Rutina / skupina','group',v.group||'') + '</div>' + check('Vyžaduje schválenie rodičom','approval',!!v.approval) + check('Spoločnú odmenu rozdeliť medzi účastníkov','split',!!v.split) + check('Úloha je aktívna','active',v.active!==false) + '</details><p class="hint">Pri „Kto prvý“ ostatní nedostávajú postih. Spoločné delenie: zvyšné celé body idú podľa poradia profilov. Dnešná rozpracovaná úloha si zachová pôvodné pravidlá; úprava sa prejaví v ďalšom výskyte. Bez aktivity sa upraví aj dnes.</p>';
      } else if(type==='reward') {
        title=v.id?'Upraviť odmenu':'Nová odmena';
        var tasks={"":"Vyber úlohu"}; this._data.tasks.forEach(t=>{tasks[t.id]=t.name;});
        body=field('Názov','name',v.name||'','text','required maxlength="100"') + field('Ikona (emoji)','icon',v.icon||'🎁','text','required maxlength="16"') + select('Druh','kind',v.kind||'points',{points:'Za body',task:'Za konkrétnu úlohu (bez míňania bodov)',task_points:'Body + splnená úloha'}) + field('Cena v bodoch','cost',v.cost==null?10:v.cost,'number','min="0" required') + check('Spoločná odmena – účastníci sa skladajú bodmi','shared',!!v.shared) + '<p class="hint">Spoločná odmena: druh Za body, kladná cena. Každý môže prispieť ľubovoľnou sumou zo svojich bodov. 1 hviezdička = 1 srdiečko = 1 bod. Po nazbieraní ceny rozhodne rodič.</p>' + select('Súvisiaca úloha','task',v.task||'',tasks) + check('Súvisiaca úloha musí byť splnená načas','on_time',!!v.on_time) + check('Odmena je aktívna','active',v.active!==false);
      } else if(type==='contribution') {
        title='Prispieť na spoločnú odmenu';
        body='<p>'+esc(v.name)+' · zostáva '+v.remaining+' bodov</p>'+field('Môj príspevok','amount',Math.min(v.remaining,v.balance),'number','required min="1" max="'+Math.min(v.remaining,v.balance)+'"')+'<p class="hint">Body sa rezervujú hneď. Kým zbieranie nie je dokončené, môžeš svoj príspevok vrátiť. Potom ho môže vrátiť rodič zrušením žiadosti.</p>';
      } else if(type==='adjust') {
        title='Ručná úprava bodov';
        body=field('Zmena (+ alebo −)','delta',1,'number','required min="-10000" max="10000"') + field('Dôvod','reason','','text','required maxlength="200"');
      } else if(type==='exempt') {
        title='Ospravedlniť úlohu'; body=field('Dôvod','reason','Ospravedlnené rodičom','text','required maxlength="200"') + '<p class="hint">Za tento výskyt nebude postih. Prípadný postih sa vráti.</p>';
      }
      return '<div class="editor"><h2>'+title+'</h2><form><datalist id="symbols"><option value="⭐"><option value="❤️"><option value="🐴"><option value="💎"><option value="🦖"></datalist>'+body+'<div class="form-actions"><button class="primary" type="submit">Uložiť</button>'+button('Zrušiť','cancel','','quiet')+'</div></form></div>';
    }
    async submit(ev) {
      ev.preventDefault();
      var ed=this._editor; if(!ed||this._busy)return;
      var fd=new FormData(ev.target), get=n=>fd.get(n), num=n=>Number(get(n)), yes=n=>fd.has(n), data={}, action='';
      if(ed.value.id) data.id=ed.value.id;
      if(ed.type==='reset') {
        if(!window.confirm('Naozaj vymazať skúšobné splnenia, všetky body, históriu a žiadosti celej domácnosti?'))return;
        action='reset_progress';data={start:get('start'),confirmation:get('confirmation'),backup_confirmed:yes('backup_confirmed')};
      }
      if(ed.type==='person') { action='save_person'; ['name','symbol','unit','avatar'].forEach(n=>data[n]=get(n)); data.active=yes('active'); data.show_statistics=yes('show_statistics'); }
      if(ed.type==='symbols') { action='set_symbol'; data={person:ed.value.id,symbol:get('symbol'),unit:get('unit')}; }
      if(ed.type==='task') {
        action='save_task'; ['name','icon','group','mode','frequency','date','due','cutoff'].forEach(n=>data[n]=get(n));
        ['everyone','approval','split','active'].forEach(n=>data[n]=yes(n));
        ['points','late_points','penalty','repeat_limit','repeat_goal','repeat_gap'].forEach(n=>data[n]=num(n));
        data.days=fd.getAll('days').map(Number); data.people=fd.getAll('people');
      }
      if(ed.type==='reward') { action='save_reward'; ['name','icon','kind','task'].forEach(n=>data[n]=get(n)); data.cost=num('cost'); data.on_time=yes('on_time'); data.active=yes('active'); data.shared=yes('shared'); }
      if(ed.type==='contribution') {action='contribute_reward';data={person:ed.value.pid,reward:ed.value.rid,amount:num('amount')};}
      if(ed.type==='adjust') { action='adjust'; data={person:ed.value.id,delta:num('delta'),reason:get('reason')}; }
      if(ed.type==='exempt') { action='exempt'; data={person:ed.value.pid,occurrence:ed.value.oid,reason:get('reason')}; }
      // Preserve typed fields when the backend rejects validation or a stale version.
      if(['person','task','reward'].indexOf(ed.type)>=0) ed.value=Object.assign({},ed.value,data);
      await this.act(action,data);
    }
    click(ev) {
      var b=ev.target.closest('button[data-action]'); if(!b||b.disabled||this._busy)return;
      var a=b.dataset.action, d=b.dataset, p=this._data ? this.chosen() : null;
      if(a==='contribute') {
        var reward=this._data.rewards.find(r=>r.id===d.id), pool=this.sharedRequest(d.id), who=this.person(d.pid);
        this._editor={type:'contribution',value:{pid:d.pid,rid:d.id,name:reward.name,remaining:(pool?pool.reward.cost-pool.funded:reward.cost),balance:who.balance}};this.render();return;
      }
      if(a==='withdraw') {if(window.confirm('Vrátiť všetky tvoje príspevky z tohto zbierania?'))this.act('withdraw_contribution',{person:d.pid,request:d.id});return;}
      if(a==='cancel-pool') {if(window.confirm('Zrušiť spoločné zbieranie a vrátiť každému jeho príspevky?'))this.act('decide_reward',{request:d.id,decision:'reject'});return;}
      if(a==='statistics-toggle') {this.act('set_statistics',{person:d.pid,enabled:!this.person(d.pid).show_statistics});return;}
      if(a==='unexempt'||a==='approve_full') {
        var message=a==='unexempt'?'Zrušiť ospravedlnenie? Po uzávierke sa znovu vyhodnotí prípadný postih. Pri spoločnej úlohe sa vráti skupinová odmena.':'Uznať úlohu za plné body aj po termíne? Prípadný postih sa vráti. Pri spoločnom delení stále platia pravidlá spoločnej odmeny.';
        if(window.confirm(message))this.act(a,{occurrence:d.oid,person:d.pid,attempt:d.attempt});return;
      }
      if(a==='week') {this._week=Math.max(0,Math.min(7,(this._week||0)+Number(d.step)));this.render();return;}
      if(a==='group-move') {
        var order=(this._data.group_order||[]).slice(), index=Number(d.index), other=index+Number(d.step);
        if(index>=0&&other>=0&&index<order.length&&other<order.length){var moved=order[index];order[index]=order[other];order[other]=moved;this.act('set_group_order',{groups:order});}return;
      }
      if(a==='reset-editor') {this._editor={type:'reset',value:{}};this.render();return;}
      if(a==='refresh') {this._error='';this.refresh();return;}
      if(a==='person') {this._person=d.id;this.render();return;}
      if(a==='tab') {this._tab=d.tab;this._editor=null;this.render();return;}
      if(a==='cancel') {this._editor=null;this._error='';this.refresh();return;}
      if(a.indexOf('edit-')===0) {
        var type=a.slice(5), collection={person:'people',task:'tasks',reward:'rewards'}[type];
        this._editor={type:type,value:type==='adjust'?{id:d.pid}:Object.assign({},(this._data[collection]||[]).find(x=>x.id===d.id)||{})};this.render();return;
      }
      if(a==='symbols') {this._editor={type:'symbols',value:Object.assign({},this.person(d.pid))};this.render();return;}
      if(a==='exempt') {this._editor={type:'exempt',value:{oid:d.oid,pid:d.pid}};this.render();return;}
      if(a==='complete'||a==='approve') {this.act(a,{occurrence:d.oid,person:d.pid,attempt:d.attempt});return;}
      if(a==='undo') {
        if(window.confirm('Vrátiť splnenie aj presne získané body? Pri spoločnej úlohe sa vráti odmena celej skupine. Po uzávierke sa znovu vyhodnotí nesplnenie.'))this.act('undo',{occurrence:d.oid,person:d.pid,attempt:d.attempt});return;
      }
      if(a==='adjust') {this.act('adjust',{person:d.pid,delta:Number(d.delta),reason:'Ručná úprava rodičom'});return;}
      if(a==='reverse-adjustment') {this.act('reverse_adjustment',{entry:d.id});return;}
      if(a==='reward') {this.act('request_reward',{person:d.pid,reward:d.id});return;}
      if(a==='goal') {this.act('set_goal',{person:d.pid,reward:p.goal===d.id?'':d.id});return;}
      if(a==='decide') {this.act('decide_reward',{request:d.id,decision:d.decision});}
    }
    render() {
      if(!this._config)return;
      var admin=this._config.mode==='admin', data=this._data;
      var html='<div class="shell"><div class="topline"><span>RODINNÉ ÚLOHY'+(admin?' · RODIČ':'')+'</span>'+button('↻','refresh','aria-label="Obnoviť"','quiet')+'</div>';
      if(this._error) html+='<div class="error" role="alert">'+esc(this._error)+'</div>';
      if(!data) html+='<div class="empty">'+(this._error?'Skontroluj pripojenie a nastavenie integrácie.':'Načítavam…')+'</div>';
      else if(admin&&!data.admin) html+='<div class="empty">Rodičovský panel je dostupný iba správcovi Home Assistanta. Otvor ho zo svojho rodičovského účtu.</div>';
      else {
        if(data.notices.length)html+='<div class="hint">'+data.notices.map(esc).join('<br>')+'</div>';
        if(data.tracking_start)html+='<p class="hint">Nová evidencia od '+esc(data.tracking_start)+'.</p>';
        var p=this.chosen();
        if(!this._config.person)html+='<div class="people">'+data.people.filter(x=>admin||x.active).map(x=>button(esc(x.name),'person',attr('id',x.id),p&&x.id===p.id?'selected':'')).join('')+'</div>';
        html+=this.header(p,admin);
        html+=this._editor?this.editor():(admin?this.admin(p):this._config.mode==='stats'?this.statistics(p):this.child(p));
      }
      html+='<footer>Rodinné úlohy · 0.5.0</footer></div>';
      this.shadowRoot.innerHTML='<style>'+FamilyQuestsCard.styles+'</style><ha-card>'+html+'</ha-card>';
      if(this._busy)this.shadowRoot.querySelectorAll('button').forEach(b=>{b.disabled=true;});
    }
  }
  FamilyQuestsCard.styles = `
    :host{display:block;color:#f2f5f7;font-family:var(--paper-font-body1_-_font-family,Arial,sans-serif)}
    *{box-sizing:border-box}ha-card{background:#111719;color:inherit;border:1px solid #2c3e45;border-radius:26px;overflow:hidden}
    .shell{padding:20px}.topline{display:flex;align-items:center;justify-content:space-between;color:#92a7b0;font-size:11px;font-weight:700;letter-spacing:2px}
    button,input,select{font:inherit}button{min-height:46px;border:1px solid #374b54;border-radius:13px;background:#1c292f;color:#ecf3f6;padding:10px 15px;cursor:pointer;font-size:15px;touch-action:manipulation}
    button:hover{background:#283f49}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #60d5ff;outline-offset:3px}button:disabled{opacity:.5;cursor:default}
    button.selected,.primary{background:#12637c;border-color:#35bce2;color:white}.quiet{background:transparent}.positive{background:#193627;color:#a3eab7;border-color:#367c4d}.negative{background:#3d2526;color:#ffb6b0;border-color:#884e4a}
    .people,nav{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}.people button{border-radius:24px}.hero{display:flex;align-items:center;gap:16px;padding:24px 18px;background:#1c272d;border-radius:22px;border-left:6px solid #36b8db;margin:14px 0}
    .avatar{height:64px;width:64px;flex-shrink:0;display:flex;align-items:center;justify-content:center;border-radius:19px;background:#304852;color:#8adcf2;font-size:30px;font-weight:bold;overflow:hidden}.avatar img{width:100%;height:100%;object-fit:cover}
    .grow{flex:1;min-width:0}h2,h3{margin:0 0 6px;overflow-wrap:anywhere}h2{font-size:25px}h3{font-size:19px;font-weight:650}h4{display:flex;justify-content:space-between;color:#b9c9cf;margin:24px 2px 12px;font-size:14px}h4 span{color:#6ecfe8}
    .balance{text-align:right}.balance b{font-size:34px;white-space:nowrap}.balance small{display:block;color:#a8bbc4;font-size:12px;margin-top:4px}.muted,small{color:#a9bac2;font-size:13px;line-height:1.5}
    .task{display:flex;align-items:center;gap:14px;padding:18px 15px;margin:10px 0;background:#202a2f;border:1px solid #34434a;border-left:4px solid #6594a4;border-radius:18px}.task-icon{font-size:30px;width:40px;text-align:center;flex-shrink:0}.task.done{border-left-color:#72cd8d;background:#1c2b24}.task.done h3,.status-icon{color:#87dca0}.task.exempt{opacity:.65}.task.missed{border-left-color:#bd7770}
    .fq-icon{width:36px;height:36px;display:inline-block;vertical-align:middle;pointer-events:none}.star,.status-icon{position:relative;flex-shrink:0}.token-check{display:inline-flex;align-items:center;justify-content:center;flex:0 0 20px;margin-left:3px}.token-check .fq-icon{width:20px;height:20px}.custom-token{display:inline-block;flex-shrink:0;font-size:32px;line-height:1.4;padding:3px 2px;overflow:visible}.task.missed .status-icon{color:#e6a19b}.attempt{padding:10px 0;border-bottom:1px solid #34434a}.attempt .actions{margin-top:8px}
    .actions{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}.star{font-size:39px;border:2px solid #35b9dc;border-radius:50%;width:60px;height:60px;padding:0;display:inline-flex;align-items:center;justify-content:center;line-height:1.4;overflow:visible;color:#49c5e8;background:transparent}.status-icon{display:inline-flex;align-items:center;justify-content:center;font-size:40px;width:76px;min-width:76px;min-height:60px;padding:4px;line-height:1.4;overflow:visible;text-align:center}
    .pool-actions{margin-top:12px;justify-content:flex-start}.shared-reward progress{display:block}
    .pills{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.pills span{padding:9px 12px;border-radius:20px;background:#1b2d32;color:#b5d3de;font-size:12px}.goal{padding:16px;border-radius:16px;background:#203437;margin:14px 0;font-size:14px}.right{float:right;color:#c7d9df;margin-left:8px}progress{width:100%;height:9px;margin-top:12px;accent-color:#55c4df}
    .adjust{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin:18px 0 10px}.adjust button{min-height:65px;padding:8px;font-size:21px;font-weight:bold}.history{display:flex;align-items:center;gap:12px;border-bottom:1px solid #2a3b43;padding:16px 2px}.history small{display:block}.history strong{white-space:nowrap}
    .week-nav{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:20px 0}.week-nav>div{text-align:center}.week-nav small{display:block;margin-top:5px}.week-message{background:#1c3637;border-left:4px solid #64c9b1;border-radius:12px;padding:16px;line-height:1.6;font-size:15px}
    .stat-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:16px 0}.stat-grid>div{background:#1b2a32;border:1px solid #34525e;border-radius:16px;padding:17px 8px;text-align:center}.stat-grid b{font-size:27px;display:block;color:#80d5e9}.stat-grid b small{font-size:14px}.stat-grid span{font-size:11px;display:block;color:#b0c4cd;margin-top:6px}
    .week-days{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}.day{text-align:center;font-size:12px;color:#bfd1d9}.day b{display:block;font-size:12px;margin-top:8px}.day-track{height:80px;background:#23333c;border-radius:9px;margin:8px 3px 0;position:relative;overflow:hidden}.day-track>div{position:absolute;bottom:0;left:0;right:0;background:#56bca7}.day.future{opacity:.35}.routine-stat{padding:12px 0}.routine-stat>div{display:flex;justify-content:space-between;font-size:14px}.routine-stat span{color:#8fd3e6}.badges{display:flex;flex-wrap:wrap;gap:9px}.badges span{background:#33331e;color:#e4dc9e;border:1px solid #615e32;border-radius:22px;padding:10px 13px;font-size:13px}.point-line{display:flex;justify-content:space-between;gap:10px;padding:9px 0;font-size:14px}.points-detail,.maintenance{margin-top:24px}.maintenance summary{color:#e2a9a1}
    .editor{margin-top:18px;padding:20px;background:#1c292f;border-radius:20px}.editor h2{font-size:22px;margin-bottom:18px}.editor label:not(.check){display:flex;flex-direction:column;gap:6px;margin:12px 0;font-size:14px;color:#c7d6dc}.editor input:not([type=checkbox]),.editor select{width:100%;min-height:46px;background:#101b20;color:#f0f4f6;border:1px solid #536b76;border-radius:9px;padding:10px}
    .checks{display:flex;flex-wrap:wrap;gap:8px}.check{display:flex;align-items:center;gap:8px;min-height:44px;font-size:14px;color:#d7e2e6}.check input{width:21px;height:21px;accent-color:#39bddf}.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}.form-actions{display:flex;gap:12px;margin-top:20px}details{margin-top:20px;border-top:1px solid #41555e;padding-top:15px}summary{cursor:pointer;min-height:44px;color:#80d2e8}
    .hint{color:#a8bdc6;line-height:1.6;font-size:12px;margin:14px 0}.error{background:#552c2e;color:#ffd3d3;padding:15px;border-radius:12px;margin:12px 0;line-height:1.5}.empty{text-align:center;padding:32px 12px;color:#b7cad2;line-height:1.7}footer{text-align:center;margin-top:24px;color:#708891;font-size:10px;letter-spacing:1px}
    @media(max-width:520px){.shell{padding:12px}.hero{padding:18px 12px;gap:12px}.avatar{height:48px;width:48px;font-size:24px}h2{font-size:22px}.balance b{font-size:27px}.task{gap:10px;padding:14px 10px}.task-icon{font-size:25px;width:30px}h3{font-size:17px}.task .actions{max-width:135px}.actions button:not(.star){font-size:12px;padding:8px}.editor{padding:14px}.right{float:none;display:block;margin:6px 0 0}.adjust{gap:5px}.adjust button{font-size:18px;padding:4px}}
  `;
  if (!customElements.get('family-quests-card')) customElements.define('family-quests-card',FamilyQuestsCard);
  window.customCards = window.customCards || [];
  window.customCards.push({type:'family-quests-card',name:'Rodinné úlohy',description:'Úlohy, odmeny a rodičovský panel',preview:true});
})();
