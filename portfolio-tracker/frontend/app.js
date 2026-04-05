// ══════════════════════════════════════════════
//  FOLIO v5 — app.js (Production Cloud Version)
// ══════════════════════════════════════════════

const API = "https://folio-backend-ldny.onrender.com"; 

// Change the Auth Guard section to this:
const isAuthPage = window.location.pathname.includes("login.html") || 
                   window.location.pathname.includes("register.html");

if (!isAuthPage) {
    if (!token || !user || user === "null") {
        console.log("No credentials found, redirecting to login.");
        window.location.href = "login.html";
    }
}
// Prevent access to index if credentials are missing
if (!window.location.pathname.includes("login.html") && !window.location.pathname.includes("register.html")) {
    if (!token || !user) {
        window.location.href = "login.html";
    }
}

/**
 * Enhanced authFetch to prevent 404s and handle Render URLs correctly
 */
function authFetch(endpoint, options = {}) {
    // This logic ensures we don't end up with double slashes or missing slashes
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = endpoint.startsWith('http') ? endpoint : `${API}${cleanEndpoint}`;
    
    return fetch(url, {
        ...options,
        headers: { 
            "Content-Type": "application/json", 
            "Authorization": `Bearer ${token}`, 
            ...(options.headers || {}) 
        },
    }).then(res => {
        if (res.status === 401) { 
            localStorage.clear(); 
            window.location.href = "login.html"; 
        }
        return res;
    });
}

function logout() { 
    localStorage.clear(); 
    window.location.href = "login.html"; 
}

// ── State ──────────────────────────────────────
let holdings = [], transactions = [], watchlist = [], chatHistory = [];
let txnFilter = "all", txnType = "buy", paperType = "buy";
let allocChart = null, perfChart = null, benchChart = null;
let pendingDeleteId = null, pendingDeleteType = null;
let tickerTimer = null, benchLoaded = false, newsLoaded = false;
let copyProfile = { is_public: false, bio: "" };
let copyTab = "famous";
let currentPersona = "default";
let personas = [];
const PALETTE = ["#f5b731","#26d9a0","#5b8af5","#f0546a","#a78bfa","#34d399","#fb923c","#38bdf8","#f472b6","#facc15"];
const TT = (fn) => ({ callbacks:{label:fn}, backgroundColor:"#181c28", titleColor:"#e9ebf2", bodyColor:"#9aa0b8", borderColor:"rgba(255,255,255,0.08)", borderWidth:1, padding:10, cornerRadius:8 });

const EMOTION_LABELS = { conviction:"💪 Conviction", fomo:"😰 FOMO", panic_sell:"😱 Panic", patient:"🧘 Patient", opportunistic:"🎯 Opportunistic", disciplined:"📐 Disciplined" };
const STRATEGY_LABELS = { conviction:"High Conviction", research:"Deep Research", momentum:"Momentum", value:"Value Play", dividend:"Dividend", hedge:"Hedge", speculative:"Speculative" };

// ── Boot ───────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  if (user) {
    const init = (user.username || "?")[0].toUpperCase();
    setText("user-avatar", init);
    setText("user-name",  user.username);
    setText("user-email", user.email);
  }
  setupNav();
  document.getElementById("refreshBtn").addEventListener("click", () => loadAll());
  setupTickerValidation();
  setupAddFormPreview();
  setupTxnPreview();
  loadAll();
  loadPersonas();
});

async function loadAll() {
  await Promise.all([loadHoldings(), loadTransactions(), loadWatchlist()]);
}

// ── Navigation ─────────────────────────────────
function setupNav() {
  document.querySelectorAll(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });
}

function switchView(view) {
  document.querySelectorAll(".view").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
  const el = document.getElementById(`view-${view}`);
  if (el) el.classList.add("active");
  const btn = document.querySelector(`[data-view="${view}"]`);
  if (btn) btn.classList.add("active");
  if (view === "benchmark")  loadBenchmark();
  if (view === "news")       loadNews();
  if (view === "insider")    loadInsider();
  if (view === "copy")       loadCopyTrading();
  if (view === "strategies") loadStrategies();
  if (view === "paper")      loadPaperPortfolio();
}

function setStatus(online, text) {
  const dot = document.getElementById("status-dot");
  dot.className = `status-dot ${online ? "online" : "offline"}`;
  setText("last-updated-text", text);
}

// ══════════════════════════════════════════════
//  HOLDINGS
// ══════════════════════════════════════════════
async function loadHoldings() {
  try {
    const res = await authFetch(`${API}/holdings/`);
    holdings = await res.json();
    renderDashboard(); renderHoldingsTable();
    const t = new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
    setStatus(true, `Updated ${t}`);
  } catch { setStatus(false, "Backend offline"); }
}

function renderDashboard() {
  const totalVal  = holdings.reduce((s,h) => s + h.current_value, 0);
  const totalCost = holdings.reduce((s,h) => s + h.cost_basis, 0);
  const gl = totalVal - totalCost, pct = totalCost ? (gl/totalCost)*100 : 0;
  setText("s-total-value", fmt$(totalVal));
  setText("s-total-cost",  fmt$(totalCost));
  setText("s-positions",   holdings.length);
  setText("s-txn-count",   `${transactions.length} trade${transactions.length!==1?"s":""} logged`);
  const glEl = document.getElementById("s-total-gl");
  const sign = gl >= 0 ? "+" : "";
  glEl.textContent = `${sign}${fmt$(gl)}  (${sign}${pct.toFixed(2)}%)`;
  glEl.className = `stat-delta ${gl >= 0 ? "green" : "red"}`;
  const best = [...holdings].sort((a,b) => b.gain_loss_pct - a.gain_loss_pct)[0];
  if (best) {
    setText("s-best-ticker", best.ticker);
    const bEl = document.getElementById("s-best-pct");
    const bs = best.gain_loss_pct >= 0 ? "+" : "";
    bEl.textContent = `${bs}${best.gain_loss_pct.toFixed(2)}%`;
    bEl.className = `stat-delta ${best.gain_loss_pct >= 0 ? "green" : "red"}`;
  } else { setText("s-best-ticker","—"); setText("s-best-pct",""); }
  renderAllocChart(); renderPerfChart(); renderPositionRows();
}

function renderAllocChart() {
  const ctx = document.getElementById("allocationChart").getContext("2d");
  document.getElementById("alloc-empty").style.display = holdings.length ? "none" : "block";
  if (allocChart) { allocChart.destroy(); allocChart = null; }
  if (!holdings.length) return;
  allocChart = new Chart(ctx, { type:"doughnut", data:{labels:holdings.map(h=>h.ticker), datasets:[{data:holdings.map(h=>h.current_value), backgroundColor:PALETTE, borderColor:"#0c0e13", borderWidth:3, hoverOffset:9}]}, options:{responsive:true, maintainAspectRatio:false, cutout:"70%", plugins:{legend:{position:"right",labels:{color:"#9aa0b8",font:{family:"'DM Mono',monospace",size:11},boxWidth:10,padding:13}}, tooltip:TT(v=>` ${v.label}: ${fmt$(v.raw)}`)}}} );
}

function renderPerfChart() {
  const ctx = document.getElementById("perfChart").getContext("2d");
  document.getElementById("perf-empty").style.display = holdings.length ? "none" : "block";
  if (perfChart) { perfChart.destroy(); perfChart = null; }
  if (!holdings.length) return;
  const sorted = [...holdings].sort((a,b) => b.gain_loss_pct - a.gain_loss_pct);
  perfChart = new Chart(ctx, { type:"bar", data:{labels:sorted.map(h=>h.ticker), datasets:[{data:sorted.map(h=>h.gain_loss_pct), backgroundColor:sorted.map(h=>h.gain_loss_pct>=0?"rgba(38,217,160,0.45)":"rgba(240,84,106,0.45)"), borderColor:sorted.map(h=>h.gain_loss_pct>=0?"#26d9a0":"#f0546a"), borderWidth:1, borderRadius:4}]}, options:{responsive:true, maintainAspectRatio:false, indexAxis:"y", plugins:{legend:{display:false}, tooltip:TT(v=>` ${v.raw>=0?"+":""}${v.raw.toFixed(2)}%`)}, scales:{x:{grid:{color:"rgba(255,255,255,0.04)"}, ticks:{color:"#565d78",font:{family:"'DM Mono',monospace",size:11},callback:v=>`${v}%`}}, y:{grid:{display:false}, ticks:{color:"#9aa0b8",font:{family:"'Syne',sans-serif",size:12,weight:"700"}}}}}});
}

function renderPositionRows() {
  const el = document.getElementById("position-rows");
  if (!holdings.length) { el.innerHTML = `<p class="empty-hint">No positions yet — <a href="#" onclick="switchView('add')" style="color:var(--accent)">add one</a>.</p>`; return; }
  const totalVal = holdings.reduce((s,h) => s+h.current_value, 0);
  const maxAbs = Math.max(...holdings.map(h => Math.abs(h.gain_loss_pct))) || 1;
  el.innerHTML = holdings.map((h,i) => {
    const sign = h.gain_loss_pct >= 0 ? "+" : "";
    const cls = h.gain_loss_pct >= 0 ? "green" : "red";
    const color = h.gain_loss_pct >= 0 ? "var(--green)" : "var(--red)";
    const weight = totalVal ? (h.current_value/totalVal*100).toFixed(1) : "0.0";
    const barW = (Math.abs(h.gain_loss_pct)/maxAbs*100).toFixed(1);
    return `<div class="pos-row"><span class="pos-ticker" style="color:${PALETTE[i%PALETTE.length]}">${h.ticker}</span><div class="pos-bar-track"><div class="pos-bar-fill" style="width:${barW}%;background:${color}"></div></div><span class="pos-weight">${weight}%</span><span class="pos-pct ${cls}">${sign}${h.gain_loss_pct.toFixed(2)}%</span></div>`;
  }).join("");
}

function renderHoldingsTable() {
  const tbody = document.getElementById("holdings-tbody");
  if (!holdings.length) { tbody.innerHTML = `<tr class="empty-row"><td colspan="9">No holdings — <a href="#" onclick="switchView('add')" style="color:var(--accent)">add your first</a>.</td></tr>`; return; }
  tbody.innerHTML = holdings.map(h => {
    const gl = h.gain_loss, pct = h.gain_loss_pct, sign = gl>=0?"+":"";
    return `<tr><td class="cell-ticker">${h.ticker}</td><td class="cell-mono">${h.shares.toLocaleString(undefined,{maximumFractionDigits:4})}</td><td class="cell-mono">${fmt$(h.purchase_price)}</td><td class="cell-mono">${fmt$(h.current_price)}</td><td class="cell-mono">${fmt$(h.current_value)}</td><td class="cell-mono ${gl>=0?"green":"red"}">${sign}${fmt$(gl)}</td><td><span class="badge ${gl>=0?"badge-green":"badge-red"}">${sign}${pct.toFixed(2)}%</span></td><td class="cell-mono muted">${h.purchase_date||"—"}</td><td><button class="btn btn-icon" onclick="openDeleteModal('holding',${h.id},'${h.ticker}')">✕</button></td></tr>`;
  }).join("");
}

// ══════════════════════════════════════════════
//  TRADE LOG
// ══════════════════════════════════════════════
async function loadTransactions() {
  try {
    const res = await authFetch(`${API}/transactions/`);
    transactions = await res.json();
    renderTransactions();
    renderTradeStats();
    setText("s-txn-count", `${transactions.length} trade${transactions.length!==1?"s":""} logged`);
  } catch {}
}

function renderTradeStats() {
  const stats = document.getElementById("trade-stats");
  if (!stats) return;
  const buys  = transactions.filter(t => t.type === "buy");
  const sells = transactions.filter(t => t.type === "sell");
  const totalBuyVal  = buys.reduce((s,t)  => s + t.total_value, 0);
  const totalSellVal = sells.reduce((s,t) => s + t.total_value, 0);
  // Most common emotion
  const emotions = transactions.map(t => t.emotion_tag).filter(Boolean);
  const topEmotion = emotions.length ? emotions.sort((a,b) => emotions.filter(e=>e===b).length - emotions.filter(e=>e===a).length)[0] : null;
  stats.innerHTML = `
    <div class="stat-card"><p class="stat-label">Total Buys</p><p class="stat-value sm">${buys.length}</p><p class="stat-delta muted">${fmt$(totalBuyVal)} deployed</p></div>
    <div class="stat-card"><p class="stat-label">Total Sells</p><p class="stat-value sm">${sells.length}</p><p class="stat-delta muted">${fmt$(totalSellVal)} realized</p></div>
    <div class="stat-card"><p class="stat-label">Trades Total</p><p class="stat-value sm">${transactions.length}</p><p class="stat-delta muted">All time</p></div>
    <div class="stat-card"><p class="stat-label">Top Emotion</p><p class="stat-value sm" style="font-size:16px">${topEmotion ? (EMOTION_LABELS[topEmotion]||topEmotion) : "—"}</p><p class="stat-delta muted">Most frequent</p></div>
  `;
}

function renderTransactions() {
  const search = (document.getElementById("txn-search")?.value||"").toUpperCase();
  const tbody = document.getElementById("txn-tbody");
  let filtered = transactions;
  if (txnFilter !== "all") filtered = filtered.filter(t => t.type === txnFilter);
  if (search) filtered = filtered.filter(t => t.ticker.includes(search));
  if (!filtered.length) { tbody.innerHTML = `<tr class="empty-row"><td colspan="10">${transactions.length?"No matching trades.":"No trades logged yet."}</td></tr>`; return; }
  tbody.innerHTML = filtered.map(t => {
    const emotLabel = t.emotion_tag ? (EMOTION_LABELS[t.emotion_tag]||t.emotion_tag) : "—";
    const stratLabel = t.strategy_tag ? (STRATEGY_LABELS[t.strategy_tag]||t.strategy_tag) : "—";
    return `<tr><td class="cell-mono muted">${t.date||"—"}</td><td class="cell-ticker">${t.ticker}</td><td><span class="badge ${t.type==="buy"?"badge-green":"badge-red"}">${t.type==="buy"?"▲ Buy":"▼ Sell"}</span></td><td class="cell-mono">${t.shares.toLocaleString(undefined,{maximumFractionDigits:4})}</td><td class="cell-mono">${fmt$(t.price_per_share)}</td><td class="cell-mono">${fmt$(t.total_value)}</td><td style="font-size:11.5px;color:var(--text-2)">${stratLabel}</td><td style="font-size:11.5px">${emotLabel}</td><td class="muted" style="font-size:11.5px">${t.notes||""}</td><td><button class="btn btn-icon" onclick="openDeleteModal('transaction',${t.id},'${t.ticker} trade')">✕</button></td></tr>`;
  }).join("");
}

function setTxnFilter(btn) { document.querySelectorAll(".pill-group .pill").forEach(p=>p.classList.remove("active")); btn.classList.add("active"); txnFilter = btn.dataset.filter; renderTransactions(); }
function setTxnType(type) { txnType=type; document.getElementById("txn-type-buy").className=`toggle-btn${type==="buy"?" active buy":""}`; document.getElementById("txn-type-sell").className=`toggle-btn${type==="sell"?" active sell":""}`; }
function openTxnForm() { document.getElementById("txn-form-card").style.display="block"; document.getElementById("txn-form-toggle").style.display="none"; setTxnType("buy"); }
function closeTxnForm() { document.getElementById("txn-form-card").style.display="none"; document.getElementById("txn-form-toggle").style.display=""; ["txn-ticker","txn-shares","txn-price","txn-date","txn-notes"].forEach(id=>{const e=document.getElementById(id);if(e)e.value="";}); document.getElementById("txn-total-preview").style.display="none"; }

function setupTxnPreview() { ["txn-shares","txn-price"].forEach(id => { const el=document.getElementById(id); if(el) el.addEventListener("input",()=>{ const s=parseFloat(document.getElementById("txn-shares").value),p=parseFloat(document.getElementById("txn-price").value),el2=document.getElementById("txn-total-preview"); if(!s||!p){el2.style.display="none";return;} el2.style.display="block"; el2.textContent=`Total: ${fmt$(s*p)}`; }); }); }

async function submitTransaction() {
  const ticker=document.getElementById("txn-ticker").value.trim().toUpperCase(),shares=parseFloat(document.getElementById("txn-shares").value),price=parseFloat(document.getElementById("txn-price").value),date=document.getElementById("txn-date").value,notes=document.getElementById("txn-notes").value.trim();
  const strategy=document.getElementById("txn-strategy").value,emotion=document.getElementById("txn-emotion").value;
  const errEl=document.getElementById("txn-error"),okEl=document.getElementById("txn-success");
  errEl.style.display="none"; okEl.style.display="none";
  if(!ticker){showMsg(errEl,"Ticker required.");return;} if(!shares||shares<=0){showMsg(errEl,"Enter valid shares.");return;} if(!price||price<=0){showMsg(errEl,"Enter valid price.");return;}
  try {
    const res=await authFetch(`${API}/transactions/`,{method:"POST",body:JSON.stringify({ticker,type:txnType,shares,price_per_share:price,date:date||null,notes:notes||null,strategy_tag:strategy||null,emotion_tag:emotion||null})});
    if(!res.ok){const e=await res.json();throw new Error(e.detail);}
    showMsg(okEl,`✓ ${txnType==="buy"?"Buy":"Sell"} of ${ticker} logged.`);
    await loadTransactions();
    setTimeout(()=>{okEl.style.display="none";closeTxnForm();},1500);
  } catch(e){showMsg(errEl,e.message||"Failed");}
}

// ══════════════════════════════════════════════
//  WATCHLIST
// ══════════════════════════════════════════════
async function loadWatchlist() {
  try { const res = await authFetch(`${API}/watchlist/`); watchlist = await res.json(); renderWatchlist(); } catch {}
}

function renderWatchlist() {
  const tbody = document.getElementById("watchlist-tbody");
  if (!watchlist.length) { tbody.innerHTML = `<tr class="empty-row"><td colspan="7">Watchlist is empty.</td></tr>`; return; }
  tbody.innerHTML = watchlist.map(w => {
    const dist = w.distance_pct;
    const distEl = dist !== null && dist !== undefined ? `<span class="${dist>=0?"green":"red"}">${dist>=0?"+":""}${dist.toFixed(2)}%</span>` : "—";
    return `<tr><td class="cell-ticker">${w.ticker}</td><td class="cell-mono">${w.current_price ? fmt$(w.current_price) : "—"}</td><td class="cell-mono">${w.target_price ? fmt$(w.target_price) : "—"}</td><td>${distEl}</td><td class="muted">${w.notes||""}</td><td class="cell-mono muted">${w.added_at||"—"}</td><td><button class="btn btn-icon" onclick="openDeleteModal('watchlist',${w.id},'${w.ticker}')">✕</button></td></tr>`;
  }).join("");
}

function openWatchlistForm() { document.getElementById("watchlist-form-card").style.display="block"; }
function closeWatchlistForm() { document.getElementById("watchlist-form-card").style.display="none"; ["wl-ticker","wl-target","wl-notes"].forEach(id=>{const e=document.getElementById(id);if(e)e.value="";}); }

async function submitWatchlist() {
  const ticker=document.getElementById("wl-ticker").value.trim().toUpperCase(),target=parseFloat(document.getElementById("wl-target").value)||null,notes=document.getElementById("wl-notes").value.trim();
  const errEl=document.getElementById("wl-error"); errEl.style.display="none";
  if(!ticker){showMsg(errEl,"Ticker required.");return;}
  try { const res=await authFetch(`${API}/watchlist/`,{method:"POST",body:JSON.stringify({ticker,target_price:target,notes:notes||null})}); if(!res.ok){const e=await res.json();throw new Error(e.detail);} closeWatchlistForm(); await loadWatchlist(); } catch(e){showMsg(errEl,e.message||"Failed");}
}

// ══════════════════════════════════════════════
//  BENCHMARK
// ══════════════════════════════════════════════
async function loadBenchmark(force=false) {
  if (benchLoaded && !force) return;
  document.getElementById("bench-loading").style.display="flex";
  document.getElementById("bench-content").style.display="none";
  document.getElementById("bench-error").style.display="none";
  try {
    const res = await authFetch(`${API}/benchmark/`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    renderBenchmark(data);
    document.getElementById("bench-loading").style.display="none";
    document.getElementById("bench-content").style.display="block";
    benchLoaded=true;
  } catch { document.getElementById("bench-loading").style.display="none"; document.getElementById("bench-error").style.display="block"; }
}

function renderBenchmark(data) {
  const pPct=data.portfolio.return_pct, sPct=data.benchmark.return_pct, delta=data.outperformance;
  const pEl=document.getElementById("bench-port-pct");
  pEl.textContent=`${pPct>=0?"+":""}${pPct.toFixed(2)}%`; pEl.className=`bench-big ${pPct>=0?"green":"red"}`;
  setText("bench-spy-pct",`${sPct>=0?"+":""}${sPct.toFixed(2)}%`);
  const verdict=document.getElementById("bench-verdict");
  const dColor=delta>=0?"var(--green)":"var(--red)";
  verdict.style.background=delta>=0?"var(--green-bg)":"var(--red-bg)"; verdict.style.borderColor=dColor; verdict.style.color=dColor;
  setText("bench-verdict-icon",delta>=0?"🏆":"📉");
  setText("bench-verdict-text",delta>=0?`Outperforming S&P 500 by +${delta.toFixed(2)}%`:`Underperforming S&P 500 by ${Math.abs(delta).toFixed(2)}%`);
  setText("b-cost",fmt$(data.portfolio.total_cost)); setText("b-value",fmt$(data.portfolio.total_value));
  setText("b-spy-start",fmt$(data.benchmark.start_price)); setText("b-spy-now",fmt$(data.benchmark.current_price));
  const ctx=document.getElementById("benchChart").getContext("2d");
  if(benchChart){benchChart.destroy();benchChart=null;}
  const labels=[...data.per_holding.map(h=>h.ticker),"S&P 500"];
  const values=[...data.per_holding.map(h=>h.return_pct),data.benchmark.return_pct];
  const colors=values.map((v,i)=>i===values.length-1?"rgba(91,138,245,0.5)":v>=0?"rgba(38,217,160,0.5)":"rgba(240,84,106,0.5)");
  const borders=values.map((v,i)=>i===values.length-1?"#5b8af5":v>=0?"#26d9a0":"#f0546a");
  benchChart=new Chart(ctx,{type:"bar",data:{labels,datasets:[{data:values,backgroundColor:colors,borderColor:borders,borderWidth:1,borderRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:TT(v=>` ${v.raw>=0?"+":""}${v.raw.toFixed(2)}%`)},scales:{x:{grid:{color:"rgba(255,255,255,0.04)"},ticks:{color:"#9aa0b8",font:{family:"'Syne',sans-serif",size:12,weight:"700"}}},y:{grid:{color:"rgba(255,255,255,0.04)"},ticks:{color:"#565d78",font:{family:"'DM Mono',monospace",size:11},callback:v=>`${v}%`}}}}});
}

// ══════════════════════════════════════════════
//  NEWS
// ══════════════════════════════════════════════
async function loadNews(force=false) {
  if (newsLoaded && !force) return;
  document.getElementById("news-loading").style.display="flex";
  document.getElementById("news-grid").style.display="none";
  document.getElementById("news-error").style.display="none";
  try {
    const res = await authFetch(`${API}/news/`);
    if (!res.ok) throw new Error();
    const articles = await res.json();
    const grid = document.getElementById("news-grid");
    if (!articles.length) { grid.innerHTML=`<p style="color:var(--text-3)">No news found. Add holdings to see relevant news.</p>`; }
    else grid.innerHTML = articles.map(a => `<a class="news-card" href="${a.link}" target="_blank" rel="noopener">${a.thumbnail?`<img class="news-thumb" src="${a.thumbnail}" alt="" onerror="this.style.display='none'" />`:""}  <span class="news-ticker-badge">${a.ticker}</span><p class="news-title">${a.title}</p>${a.summary?`<p class="news-summary">${a.summary}</p>`:""}<div class="news-meta"><span>${a.publisher}</span><span>${a.published}</span></div></a>`).join("");
    document.getElementById("news-loading").style.display="none";
    document.getElementById("news-grid").style.display="grid";
    newsLoaded=true;
  } catch { document.getElementById("news-loading").style.display="none"; document.getElementById("news-error").style.display="block"; }
}

// ══════════════════════════════════════════════
//  INSIDER TRADING
// ══════════════════════════════════════════════
async function loadInsider(force=false) {
  const loadEl=document.getElementById("insider-loading"),contentEl=document.getElementById("insider-content"),errEl=document.getElementById("insider-error");
  loadEl.style.display="flex"; contentEl.style.display="none"; errEl.style.display="none";
  try {
    const res = await authFetch(`${API}/insider/`);
    if (!res.ok) throw new Error();
    const trades = await res.json();
    const tbody = document.getElementById("insider-tbody");
    if (!trades.length) { tbody.innerHTML=`<tr class="empty-row"><td colspan="9">No Form 4 filings found. Add holdings to your portfolio to see insider activity.</td></tr>`; }
    else tbody.innerHTML = trades.map(t => {
      const isBuy = t.transaction==="BUY"||t.transaction==="Purchase";
      const isSell = t.transaction==="SELL"||t.transaction==="Sale";
      const badge = isBuy?"badge-green":isSell?"badge-red":"badge-blue";
      const label = isBuy?"▲ BUY":isSell?"▼ SELL":t.transaction;
      return `<tr><td class="cell-mono muted">${t.filing_date}</td><td class="cell-ticker">${t.ticker}</td><td class="cell-mono" style="max-width:130px;overflow:hidden;text-overflow:ellipsis">${t.insider_name||"—"}</td><td><span class="insider-position">${t.position||"Insider"}</span></td><td><span class="badge ${badge}">${label}</span></td><td class="cell-mono">${t.shares>0?t.shares.toLocaleString(undefined,{maximumFractionDigits:0}):"—"}</td><td class="cell-mono">${t.price>0?fmt$(t.price):"—"}</td><td class="cell-mono ${isBuy?"green":isSell?"red":""}">${t.total_value>0?fmt$(t.total_value):"—"}</td><td><a class="insider-link" href="${t.sec_url}" target="_blank" rel="noopener">SEC ↗</a></td></tr>`;
    }).join("");
    loadEl.style.display="none"; contentEl.style.display="block";
  } catch { loadEl.style.display="none"; errEl.style.display="block"; }
}

// ══════════════════════════════════════════════
//  COPY TRADING
// ══════════════════════════════════════════════
async function loadCopyTrading() {
  try {
    const res = await authFetch(`${API}/copy-trading/my-profile`);
    if (res.ok) {
      copyProfile = await res.json();
      document.getElementById("copy-public-toggle").checked = copyProfile.is_public;
      document.getElementById("copy-bio").value = copyProfile.bio || "";
      document.getElementById("copy-visibility-status").textContent = copyProfile.is_public ? "Your portfolio is PUBLIC — visible on the leaderboard." : "Your portfolio is private — only you can see it.";
    }
  } catch {}
  loadCopyTab("famous");
}

function setCopyTab(tab) {
  copyTab=tab;
  document.querySelectorAll(".copy-tab").forEach(b=>b.classList.remove("active"));
  document.querySelector(`[data-copy-tab="${tab}"]`).classList.add("active");
  loadCopyTab(tab);
}

async function loadCopyTab(tab) {
  const grid=document.getElementById("leaderboard-grid"),loadEl=document.getElementById("leaderboard-loading"),errEl=document.getElementById("leaderboard-error");
  grid.style.display="none"; loadEl.style.display="flex"; errEl.style.display="none";
  const CATEGORY_COLORS={legendary:"var(--accent)",growth:"var(--green)",activist:"var(--blue)",contrarian:"var(--red)",hedge_fund:"var(--purple)",macro:"var(--text-2)"};
  try {
    if (tab==="famous") {
      const res=await fetch(`${API}/copy-trading/famous-investors`);
      const data=await res.json();
      loadEl.style.display="none"; grid.style.display="grid";
      if(!data.length){errEl.style.display="block";return;}
      grid.innerHTML=data.map(inv=>{
        const color=CATEGORY_COLORS[inv.category]||"var(--text-2)";
        return `<div class="leader-card" onclick="window.open('${inv.sec_filing_url}','_blank')">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
            <div style="width:36px;height:36px;border-radius:50%;background:${color}22;border:1px solid ${color};color:${color};display:flex;align-items:center;justify-content:center;font-family:var(--font-display);font-weight:700;font-size:12px;flex-shrink:0">${inv.avatar}</div>
            <div><p class="leader-name" style="font-size:14px">${inv.name}</p><p style="font-size:10.5px;color:var(--text-3)">${inv.title}</p></div>
          </div>
          <p class="leader-bio">${inv.bio}</p>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
            <span style="font-size:10px;color:var(--text-3)">Last 13F: ${inv.last_13f_date||"—"}</span>
            <span class="insider-link">View 13F filings ↗</span>
          </div>
        </div>`;
      }).join("");
    } else if (tab==="ceos") {
      const res=await fetch(`${API}/copy-trading/tech-ceos`);
      const data=await res.json();
      loadEl.style.display="none"; grid.style.display="grid";
      grid.innerHTML=data.map(ceo=>{
        const tags=ceo.holdings.map(h=>`<span style="display:inline-flex;align-items:center;gap:5px;background:var(--bg-3);border:1px solid var(--border-2);border-radius:6px;padding:3px 9px;font-size:11px;margin:2px"><strong style="color:var(--accent)">${h.ticker}</strong><span style="color:var(--text-3)">${h.current_price?fmt$(h.current_price):""}</span></span>`).join("");
        return `<div class="leader-card"><div style="display:flex;align-items:center;gap:10px;margin-bottom:12px"><div style="width:36px;height:36px;border-radius:50%;background:var(--blue-bg);border:1px solid var(--blue);color:var(--blue);display:flex;align-items:center;justify-content:center;font-family:var(--font-display);font-weight:700;font-size:12px;flex-shrink:0">${ceo.avatar}</div><div><p class="leader-name" style="font-size:14px">${ceo.name}</p><p style="font-size:10.5px;color:var(--text-3)">${ceo.title}</p></div></div><p class="leader-bio">${ceo.bio}</p><div style="margin-top:12px;display:flex;flex-wrap:wrap;gap:2px">${tags}</div></div>`;
      }).join("");
    } else {
      const res=await fetch(`${API}/copy-trading/leaderboard`);
      const board=await res.json();
      loadEl.style.display="none";
      if(!board.length){errEl.style.display="block";return;}
      grid.style.display="grid";
      const medals=["🥇","🥈","🥉"];
      grid.innerHTML=board.map((u,i)=>{
        const sign=u.return_pct>=0?"+":"";const color=u.return_pct>=0?"var(--green)":"var(--red)";
        return `<div class="leader-card" onclick="viewPublicPortfolio('${u.username}')"><p class="leader-rank">${medals[i]||`#${i+1}`} Rank ${i+1}</p><p class="leader-name">@${u.username}</p><p class="leader-bio">${u.bio||"No bio"}</p><p class="leader-return" style="color:${color}">${sign}${u.return_pct.toFixed(2)}%</p><p class="leader-meta">${u.num_holdings} positions · Joined ${u.joined}</p></div>`;
      }).join("");
    }
  } catch { loadEl.style.display="none"; errEl.style.display="block"; }
}

async function togglePublicProfile() {
  const isPublic=document.getElementById("copy-public-toggle").checked,bio=document.getElementById("copy-bio").value.trim();
  try { await authFetch(`${API}/copy-trading/profile`,{method:"PATCH",body:JSON.stringify({is_public:isPublic,bio})}); document.getElementById("copy-visibility-status").textContent=isPublic?"Your portfolio is PUBLIC — visible on the leaderboard.":"Your portfolio is private — only you can see it."; } catch {}
}
async function saveBio() { const isPublic=document.getElementById("copy-public-toggle").checked,bio=document.getElementById("copy-bio").value.trim(); try{await authFetch(`${API}/copy-trading/profile`,{method:"PATCH",body:JSON.stringify({is_public:isPublic,bio})});}catch{} }
async function viewPublicPortfolio(username) {
  try {
    const res=await fetch(`${API}/copy-trading/portfolio/${username}`);if(!res.ok)return;
    const data=await res.json();
    const drawer=document.getElementById("copy-portfolio-drawer"),tbody=document.getElementById("copy-portfolio-tbody");
    setText("copy-drawer-title",`@${data.username}'s Portfolio — ${data.return_pct>=0?"+":""}${data.return_pct.toFixed(2)}%`);
    tbody.innerHTML=data.portfolio.map(h=>{const sign=h.gain_loss_pct>=0?"+":"";return `<tr><td class="cell-ticker">${h.ticker}</td><td class="cell-mono">${h.shares}</td><td class="cell-mono">${fmt$(h.current_price)}</td><td class="cell-mono">${fmt$(h.current_value)}</td><td><span class="badge ${h.gain_loss_pct>=0?"badge-green":"badge-red"}">${sign}${h.gain_loss_pct.toFixed(2)}%</span></td></tr>`;}).join("");
    drawer.style.display="block"; drawer.scrollIntoView({behavior:"smooth"});
  } catch {}
}
function closeCopyDrawer() { document.getElementById("copy-portfolio-drawer").style.display="none"; }

// ══════════════════════════════════════════════
//  STRATEGIES
// ══════════════════════════════════════════════
async function loadStrategies() {
  // Load my profile
  try {
    const res = await authFetch(`${API}/strategies/my-profile`);
    if (res.ok) {
      const data = await res.json();
      if (data.strategy)       document.getElementById("my-strategy").value = data.strategy;
      if (data.time_horizon)   document.getElementById("my-horizon").value = data.time_horizon;
      if (data.risk_tolerance) document.getElementById("my-risk").value = data.risk_tolerance;
      if (data.strategy_notes) document.getElementById("my-strategy-notes").value = data.strategy_notes;
    }
  } catch {}

  // Load strategy cards
  try {
    const res = await fetch(`${API}/strategies/`);
    const strategies = await res.json();
    const grid = document.getElementById("strategy-grid");
    const RISK_COLORS = { "Low":"var(--green)", "Low–Medium":"var(--blue)", "High":"var(--red)", "Low–Medium":"var(--blue)" };
    grid.innerHTML = strategies.map(s => `
      <div class="strategy-card">
        <p class="strategy-name">${s.name}</p>
        <p class="strategy-desc">${s.description}</p>
        <div class="strategy-meta">
          <div><span style="color:var(--text-3)">Horizon:</span> ${s.typical_horizon}</div>
          <div><span style="color:var(--text-3)">Risk:</span> <span style="color:${RISK_COLORS[s.risk]||"var(--accent)"}">${s.risk}</span></div>
          <div style="margin-top:8px"><span style="color:var(--text-3)">Famous practitioners:</span><br>${s.famous_practitioners.map(p=>`<span class="strategy-tag">${p}</span>`).join("")}</div>
          <div style="margin-top:8px"><span style="color:var(--text-3)">Example tickers:</span><br>${s.example_tickers.map(t=>`<span class="strategy-tag" style="color:var(--accent);border-color:var(--accent-bg)">${t}</span>`).join("")}</div>
        </div>
      </div>
    `).join("");
  } catch {}

  // Load community strategies
  try {
    const res = await fetch(`${API}/strategies/community`);
    const community = await res.json();
    const tbody = document.getElementById("community-strategy-tbody");
    if (!community.length) { tbody.innerHTML=`<tr class="empty-row"><td colspan="5">No public strategies yet. Be the first — share yours above!</td></tr>`; return; }
    tbody.innerHTML = community.map(u => `<tr><td class="cell-ticker" style="font-size:13px">@${u.username}</td><td><span class="badge badge-blue">${u.strategy_name||u.strategy}</span></td><td class="cell-mono">${u.time_horizon||"—"}</td><td class="cell-mono">${u.risk_tolerance||"—"}</td><td class="muted" style="font-size:11.5px">${u.strategy_notes||""}</td></tr>`).join("");
  } catch {}
}

async function saveStrategyProfile() {
  const strategy=document.getElementById("my-strategy").value,horizon=document.getElementById("my-horizon").value,risk=document.getElementById("my-risk").value,notes=document.getElementById("my-strategy-notes").value.trim();
  try {
    await authFetch(`${API}/strategies/my-profile`,{method:"PATCH",body:JSON.stringify({strategy:strategy||null,time_horizon:horizon||null,risk_tolerance:risk||null,strategy_notes:notes||null})});
    const el=document.getElementById("strategy-saved"); el.style.display="block"; setTimeout(()=>el.style.display="none",2000);
  } catch {}
}

// ══════════════════════════════════════════════
//  AI ADVISOR
// ══════════════════════════════════════════════
async function loadPersonas() {
  try {
    const res = await authFetch(`${API}/ai-advisor/personas`);
    personas = await res.json();
    renderPersonaGrid();
  } catch {}
}

function renderPersonaGrid() {
  const grid = document.getElementById("persona-grid");
  if (!grid) return;
  grid.innerHTML = personas.map(p => `
    <button class="persona-btn ${p.id===currentPersona?"active":""}" onclick="selectPersona('${p.id}')" id="persona-btn-${p.id}">
      <div class="persona-avatar" style="background:${p.color}22;border:1px solid ${p.color};color:${p.color}">${p.avatar}</div>
      <span>${p.name}</span>
    </button>
  `).join("");
}

function selectPersona(id) {
  currentPersona = id;
  document.querySelectorAll(".persona-btn").forEach(b=>b.classList.remove("active"));
  const btn = document.getElementById(`persona-btn-${id}`);
  if (btn) btn.classList.add("active");
  const persona = personas.find(p=>p.id===id);
  if (!persona) return;
  // Update chat avatar and clear chat
  chatHistory = [];
  const msgs = document.getElementById("ai-messages");
  const intro = id === "default"
    ? "Hi! I'm your Folio AI Advisor. How can I help you with your portfolio today?"
    : `I'm now channeling <strong>${persona.name}</strong>. Ask me anything — I'll respond as ${persona.name.split(" ")[0]} would. What would you like to discuss about your portfolio or investments?<br><br><em style="color:var(--text-3);font-size:12px">⚠ This is an educational simulation. Not actual advice from ${persona.name}.</em>`;
  msgs.innerHTML = `<div class="ai-msg ai-msg--assistant"><div class="ai-avatar" style="background:${persona.color}22;border:1px solid ${persona.color};color:${persona.color}">${persona.avatar}</div><div class="ai-bubble">${intro}</div></div>`;
  document.getElementById("ai-suggestions").style.display = "flex";
}

async function sendMessage() {
  const input = document.getElementById("ai-input");
  const msg = input.value.trim();
  if (!msg) return;
  input.value = "";
  const persona = personas.find(p=>p.id===currentPersona) || {avatar:"?",color:"var(--accent)"};
  appendMessage("user", msg, (user?.username||"?")[0].toUpperCase(), "var(--accent)");
  document.getElementById("ai-suggestions").style.display = "none";
  showTyping(persona);
  chatHistory.push({role:"user", content:msg});
  try {
    const res = await authFetch(`${API}/ai-advisor/chat`,{method:"POST",body:JSON.stringify({messages:chatHistory, persona:currentPersona})});
    const data = await res.json();
    removeTyping();
    if (!res.ok) throw new Error(data.detail||"AI error");
    chatHistory.push({role:"assistant", content:data.reply});
    appendMessage("assistant", data.reply, persona.avatar, persona.color);
  } catch(e) { removeTyping(); appendMessage("assistant", `⚠ ${e.message||"Could not reach AI advisor."}`, persona.avatar, persona.color); }
}

function sendSuggestion(btn) { document.getElementById("ai-input").value = btn.textContent.replace(/^[^\w]+/,"").trim(); sendMessage(); }

function appendMessage(role, text, avatarText, color) {
  const container = document.getElementById("ai-messages");
  const div = document.createElement("div");
  div.className = `ai-msg ai-msg--${role}`;
  const formatted = text.replace(/\n/g,"<br>").replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>").replace(/⚠/g,"<span style='color:var(--red)'>⚠</span>");
  const avatarStyle = role==="assistant" ? `style="background:${color}22;border:1px solid ${color};color:${color}"` : `style="background:var(--accent-bg);border:1px solid var(--accent);color:var(--accent)"`;
  div.innerHTML = `<div class="ai-avatar" ${avatarStyle}>${avatarText}</div><div class="ai-bubble">${formatted}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function showTyping(persona) {
  const container = document.getElementById("ai-messages");
  const div = document.createElement("div");
  div.className = "ai-msg ai-msg--assistant"; div.id = "ai-typing-indicator";
  div.innerHTML = `<div class="ai-avatar" style="background:${persona.color}22;border:1px solid ${persona.color};color:${persona.color}">${persona.avatar}</div><div class="ai-bubble"><div class="ai-typing"><span></span><span></span><span></span></div></div>`;
  container.appendChild(div); container.scrollTop = container.scrollHeight;
}

function removeTyping() { const el=document.getElementById("ai-typing-indicator"); if(el) el.remove(); }
function clearChat() { chatHistory=[]; selectPersona(currentPersona); }

// ══════════════════════════════════════════════
//  PAPER TRADING
// ══════════════════════════════════════════════
async function loadPaperPortfolio() {
  try {
    const [portRes, tradesRes] = await Promise.all([
      authFetch(`${API}/paper-trading/portfolio`),
      authFetch(`${API}/paper-trading/trades`),
    ]);
    const port = await portRes.json();
    const trades = await tradesRes.json();
    renderPaperStats(port);
    renderPaperPositions(port.positions);
    renderPaperTrades(trades);
  } catch {}
}

function renderPaperStats(port) {
  const el = document.getElementById("paper-stats");
  if (!el) return;
  const totalReturn = port.starting_cash ? ((port.total_equity - port.starting_cash) / port.starting_cash * 100) : 0;
  const sign = totalReturn >= 0 ? "+" : "";
  el.innerHTML = `
    <div class="stat-card stat-card--accent"><p class="stat-label">Total Equity</p><p class="stat-value">${fmt$(port.total_equity)}</p><p class="stat-delta ${totalReturn>=0?"green":"red"}">${sign}${totalReturn.toFixed(2)}% total return</p></div>
    <div class="stat-card"><p class="stat-label">Cash Balance</p><p class="stat-value">${fmt$(port.cash_balance)}</p><p class="stat-delta muted">Available to invest</p></div>
    <div class="stat-card"><p class="stat-label">Invested Value</p><p class="stat-value">${fmt$(port.total_market_value)}</p><p class="stat-delta ${port.total_gain_loss>=0?"green":"red"}">${port.total_gain_loss>=0?"+":""}${fmt$(port.total_gain_loss)}</p></div>
    <div class="stat-card"><p class="stat-label">Starting Cash</p><p class="stat-value">${fmt$(port.starting_cash)}</p><p class="stat-delta muted">Virtual capital</p></div>
  `;
}

function renderPaperPositions(positions) {
  const tbody = document.getElementById("paper-positions-tbody");
  if (!positions.length) { tbody.innerHTML=`<tr class="empty-row"><td colspan="7">No paper positions yet. Execute a trade above.</td></tr>`; return; }
  tbody.innerHTML = positions.map(p => {
    const sign = p.gain_loss>=0?"+":"";
    return `<tr><td class="cell-ticker">${p.ticker}</td><td class="cell-mono">${p.shares.toLocaleString(undefined,{maximumFractionDigits:4})}</td><td class="cell-mono">${fmt$(p.avg_cost)}</td><td class="cell-mono">${fmt$(p.current_price)}</td><td class="cell-mono">${fmt$(p.market_value)}</td><td class="cell-mono ${p.gain_loss>=0?"green":"red"}">${sign}${fmt$(p.gain_loss)}</td><td><span class="badge ${p.gain_loss_pct>=0?"badge-green":"badge-red"}">${sign}${p.gain_loss_pct.toFixed(2)}%</span></td></tr>`;
  }).join("");
}

function renderPaperTrades(trades) {
  const tbody = document.getElementById("paper-trades-tbody");
  if (!trades.length) { tbody.innerHTML=`<tr class="empty-row"><td colspan="8">No trades yet.</td></tr>`; return; }
  tbody.innerHTML = trades.map(t => `<tr><td class="cell-mono muted">${t.date}</td><td class="cell-mono muted">${t.time}</td><td class="cell-ticker">${t.ticker}</td><td><span class="badge ${t.type==="buy"?"badge-green":"badge-red"}">${t.type==="buy"?"▲ BUY":"▼ SELL"}</span></td><td class="cell-mono">${t.shares.toLocaleString(undefined,{maximumFractionDigits:4})}</td><td class="cell-mono">${fmt$(t.price_per_share)}</td><td class="cell-mono">${fmt$(t.total_value)}</td><td class="muted" style="font-size:11.5px">${t.notes||""}</td></tr>`).join("");
}

function setPaperType(type) {
  paperType = type;
  document.getElementById("paper-type-buy").className=`toggle-btn${type==="buy"?" active buy":""}`;
  document.getElementById("paper-type-sell").className=`toggle-btn${type==="sell"?" active sell":""}`;
}

async function updatePaperPreview() {
  const ticker = document.getElementById("paper-ticker").value.trim().toUpperCase();
  const shares = parseFloat(document.getElementById("paper-shares").value);
  const preview = document.getElementById("paper-preview");
  if (!ticker || !shares) { preview.style.display="none"; return; }
  preview.style.display = "block";
  preview.textContent = "Fetching live price…";
}

async function executePaperTrade() {
  const ticker=document.getElementById("paper-ticker").value.trim().toUpperCase(),shares=parseFloat(document.getElementById("paper-shares").value),notes=document.getElementById("paper-notes").value.trim();
  const errEl=document.getElementById("paper-error"),okEl=document.getElementById("paper-success");
  errEl.style.display="none"; okEl.style.display="none";
  if(!ticker){showMsg(errEl,"Ticker required.");return;}
  if(!shares||shares<=0){showMsg(errEl,"Enter valid shares.");return;}
  try {
    const res=await authFetch(`${API}/paper-trading/trade`,{method:"POST",body:JSON.stringify({ticker,type:paperType,shares,notes:notes||null})});
    const data=await res.json();
    if(!res.ok)throw new Error(data.detail||"Trade failed");
    showMsg(okEl,`✓ ${data.message} | Cash remaining: ${fmt$(data.cash_left)}`);
    document.getElementById("paper-ticker").value=""; document.getElementById("paper-shares").value=""; document.getElementById("paper-notes").value=""; document.getElementById("paper-preview").style.display="none";
    await loadPaperPortfolio();
    setTimeout(()=>okEl.style.display="none",3000);
  } catch(e){showMsg(errEl,e.message||"Trade failed");}
}

async function resetPaperPortfolio() {
  if (!confirm("Reset your paper portfolio to $100,000 cash? All paper trades will be deleted.")) return;
  try { const res=await authFetch(`${API}/paper-trading/reset`,{method:"POST"}); if(res.ok){await loadPaperPortfolio();} } catch {}
}

// ══════════════════════════════════════════════
//  ADD POSITION FORM
// ══════════════════════════════════════════════
function setupTickerValidation() {
  const input = document.getElementById("input-ticker");
  input.addEventListener("input", () => {
    clearTimeout(tickerTimer);
    const val = input.value.trim().toUpperCase();
    if (!val) { setTickerStatus("",""); setText("ticker-name",""); return; }
    setTickerStatus("⏳","");
    tickerTimer = setTimeout(() => validateTicker(val), 600);
  });
}

async function validateTicker(ticker) {
  try {
    const res = await authFetch(`${API}/holdings/validate/${ticker}`);
    if (res.ok) { const d=await res.json(); setTickerStatus("✅","var(--green)"); setText("ticker-name",d.name||ticker); updateAddPreview(); }
    else { setTickerStatus("❌","var(--red)"); setText("ticker-name","Ticker not found"); }
  } catch { setTickerStatus("⚠️","var(--accent)"); setText("ticker-name","Could not validate"); }
}

function setTickerStatus(icon,color) { const el=document.getElementById("ticker-status"); el.textContent=icon; el.style.color=color; }

function setupAddFormPreview() {
  ["input-shares","input-price"].forEach(id => document.getElementById(id).addEventListener("input",updateAddPreview));
}

function updateAddPreview() {
  const shares=parseFloat(document.getElementById("input-shares").value),price=parseFloat(document.getElementById("input-price").value),ticker=document.getElementById("input-ticker").value.trim().toUpperCase(),box=document.getElementById("add-preview");
  if(!shares||!price){box.style.display="none";return;}
  box.style.display="flex"; setText("p-cost",fmt$(shares*price));
  const ex=holdings.find(h=>h.ticker===ticker);
  if(ex){const mv=ex.current_price*shares,pnl=mv-(shares*price);setText("p-value",fmt$(mv));const pnlEl=document.getElementById("p-pnl");pnlEl.textContent=`${pnl>=0?"+":""}${fmt$(pnl)}`;pnlEl.style.color=pnl>=0?"var(--green)":"var(--red)";}
  else{setText("p-value","—");setText("p-pnl","—");}
}

async function submitHolding() {
  const btn=document.getElementById("add-submit-btn"),errEl=document.getElementById("add-error"),okEl=document.getElementById("add-success");
  const ticker=document.getElementById("input-ticker").value.trim().toUpperCase(),shares=parseFloat(document.getElementById("input-shares").value),price=parseFloat(document.getElementById("input-price").value),date=document.getElementById("input-date").value,notes=document.getElementById("input-notes").value.trim();
  errEl.style.display="none"; okEl.style.display="none";
  if(!ticker){showMsg(errEl,"Ticker required.");return;} if(!shares||shares<=0){showMsg(errEl,"Enter valid shares.");return;} if(!price||price<=0){showMsg(errEl,"Enter valid price.");return;}
  btn.disabled=true; btn.textContent="Adding…";
  try {
    const res=await authFetch(`${API}/holdings/`,{method:"POST",body:JSON.stringify({ticker,shares,purchase_price:price,purchase_date:date||null,notes:notes||null})});
    if(!res.ok){const e=await res.json();throw new Error(e.detail);}
    showMsg(okEl,`✓ ${ticker} added!`);
    ["input-ticker","input-shares","input-price","input-date","input-notes"].forEach(id=>document.getElementById(id).value="");
    document.getElementById("add-preview").style.display="none";
    setTickerStatus("",""); setText("ticker-name","");
    await loadHoldings();
    setTimeout(()=>{okEl.style.display="none";switchView("holdings");},1600);
  } catch(e){showMsg(errEl,e.message||"Failed");}
  finally{btn.disabled=false;btn.textContent="Add Position";}
}

// ══════════════════════════════════════════════
//  DELETE MODAL
// ══════════════════════════════════════════════
function openDeleteModal(type, id, label) {
  pendingDeleteId=id; pendingDeleteType=type;
  setText("modal-title", type==="holding"?"Remove Position":type==="watchlist"?"Remove from Watchlist":"Delete Trade");
  document.getElementById("modal-body").innerHTML=`Are you sure you want to remove <strong>${label}</strong>? This cannot be undone.`;
  document.getElementById("modal-confirm").onclick=confirmDelete;
  document.getElementById("modal-overlay").style.display="flex";
}
function closeModal() { document.getElementById("modal-overlay").style.display="none"; pendingDeleteId=pendingDeleteType=null; }

async function confirmDelete() {
  const urls={holding:`${API}/holdings/${pendingDeleteId}`,transaction:`${API}/transactions/${pendingDeleteId}`,watchlist:`${API}/watchlist/${pendingDeleteId}`};
  try {
    const res=await authFetch(urls[pendingDeleteType],{method:"DELETE"});
    if(!res.ok)throw new Error();
    closeModal();
    if(pendingDeleteType==="holding") await loadHoldings();
    else if(pendingDeleteType==="transaction") await loadTransactions();
    else if(pendingDeleteType==="watchlist") await loadWatchlist();
  } catch { closeModal(); alert("Failed to delete."); }
}

document.addEventListener("click", e => { if(e.target.id==="modal-overlay") closeModal(); });

// ══════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════
function fmt$(n) { if(n===null||n===undefined||isNaN(n))return"—"; return new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",minimumFractionDigits:2}).format(n); }
function setText(id,val) { const el=document.getElementById(id); if(el) el.textContent=val; }
function showMsg(el,msg) { el.textContent=msg; el.style.display="block"; }
