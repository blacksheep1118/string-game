// ============================================================
// 游戏前端逻辑
// ============================================================
const SID_KEY = 'xiantu_session_id';
function storageGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

function storageSet(key, value) {
  try { localStorage.setItem(key, value); } catch {}
}

const SID = (() => {
  const existing = storageGet(SID_KEY);
  if (existing) return existing;
  const next = (window.crypto && crypto.randomUUID)
    ? crypto.randomUUID()
    : 'sid-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
  storageSet(SID_KEY, next);
  return next;
})();
const API = '';

let currentNode = null;
let isEnding = false;
let activeChoices = [];
const PREF_KEY = 'xiantu_preferences';
let preferences = loadPreferences();

function loadPreferences() {
  try {
    return JSON.parse(storageGet(PREF_KEY)) || {};
  } catch {
    return {};
  }
}

function savePreferences() {
  storageSet(PREF_KEY, JSON.stringify(preferences));
}

function applyPreferences() {
  document.documentElement.dataset.theme = preferences.theme || 'dark';
  document.documentElement.dataset.fontSize = preferences.fontSize || 'normal';
}

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[ch]));
}

// 初始化粒子
function initParticles() {
  const chars = ['✦','✧','❋','•','·','。','、','～'];
  const container = document.getElementById('particles');
  for (let i = 0; i < 15; i++) {
    const p = document.createElement('span');
    p.className = 'particle';
    p.textContent = chars[Math.floor(Math.random() * chars.length)];
    p.style.left = Math.random() * 100 + '%';
    p.style.animationDuration = (8 + Math.random() * 15) + 's';
    p.style.animationDelay = Math.random() * 10 + 's';
    p.style.fontSize = (16 + Math.random() * 30) + 'px';
    container.appendChild(p);
  }
}

// API 调用
async function api(path, data = {}) {
  data.session_id = SID;
  const r = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  const payload = await r.json();
  if (!r.ok || payload.error) {
    throw new Error(payload.error || '请求失败');
  }
  return payload;
}

async function apiGet(path) {
  const r = await fetch(API + path);
  const payload = await r.json();
  if (!r.ok || payload.error) {
    throw new Error(payload.error || '请求失败');
  }
  return payload;
}

// Toast 提示
function toast(msg) {
  const t = document.createElement('div');
  t.className = 'toast'; t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2100);
}

function confirmDialog(message, title = '确认') {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <h2 id="confirm-title">${escapeHTML(title)}</h2>
        <p style="text-align:center;line-height:1.8">${escapeHTML(message)}</p>
        <div class="modal-actions">
          <button class="action-btn" data-result="false">取消</button>
          <button class="action-btn" data-result="true">确认</button>
        </div>
      </div>`;
    overlay.addEventListener('click', event => {
      if (event.target === overlay) {
        overlay.remove();
        resolve(false);
      }
    });
    overlay.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        const result = btn.dataset.result === 'true';
        overlay.remove();
        resolve(result);
      });
    });
    document.body.appendChild(overlay);
    overlay.querySelector('[data-result="true"]').focus();
  });
}

// 渲染属性面板
function renderAttrs(attrs) {
  const panel = document.getElementById('attrs-panel');
  if (!attrs) { panel.innerHTML = ''; return; }
  const maxVal = 60;
  panel.innerHTML = Object.entries(attrs).map(([k, v]) => {
    const pct = Math.min(100, (v / maxVal) * 100);
    return `<div class="attr-item">
      <span class="attr-name">${escapeHTML(k)}</span>
      <span class="attr-value">${escapeHTML(v)}</span>
      <div class="attr-bar"><div class="attr-bar-fill" style="width:${pct}%"></div></div>
    </div>`;
  }).join('');
}

// 渲染操作按钮
function renderActions() {
  const el = document.getElementById('actions');
  el.innerHTML = `
    <button class="action-btn" onclick="saveGame()" aria-label="保存进度">💾 保存进度</button>
    <button class="action-btn" onclick="showLoadModal()" aria-label="读取存档">📂 读取存档</button>
    <button class="action-btn" onclick="restartGame()" aria-label="重新开始">🔄 重新开始</button>
    <button class="action-btn" onclick="showSettingsModal()" aria-label="打开设置">⚙ 设置</button>
  `;
}

// 渲染文本（支持换行）
function renderText(text) {
  return escapeHTML(text).replace(/\n/g, '<br>');
}

// 自动存档 — 章节切换时覆盖同一文件
let lastChapter = '';
let autoSaveFile = '';  // 本次游玩的自动存档文件名

function getChapter(title) {
  const m = title.match(/^(第[〇一二三四五六七八九十终]+章)/);
  return m ? m[1] : title;
}

function resetAutoSave() {
  autoSaveFile = '';
  lastChapter = '';
}

async function autoSaveOnChapter(data) {
  const chapter = getChapter(data.title);
  if (chapter && chapter !== lastChapter && lastChapter !== '') {
    // 首次自动存档创建新文件，后续覆盖同一文件
    const payload = autoSaveFile ? { overwrite: autoSaveFile } : {};
    try {
      const r = await api('/api/save', payload);
      if (!autoSaveFile && r.filename) autoSaveFile = r.filename;
      toast('已自动存档 (' + chapter + ')');
    } catch (err) {
      toast(err.message || '自动存档失败');
    }
  }
  if (chapter) lastChapter = chapter;
}

// 显示节点
function renderNode(data) {
  currentNode = data;
  isEnding = data.is_ending;
  activeChoices = data.choices || [];
  const content = document.getElementById('content');

  // 章节切换时自动存档（静默，后台完成）
  autoSaveOnChapter(data);

  let html = `<div class="fade-in">`;
  html += `<div class="chapter-title">${escapeHTML(data.title)}</div>`;
  html += `<div class="story-text">${renderText(data.text)}</div>`;

  if (data.is_ending) {
    html += `<div class="choices">`;
    html += `<button class="choice-btn" onclick="restartGame()"><span class="idx">1</span>重新开始</button>`;
    html += `<button class="choice-btn" onclick="showStartScreen()"><span class="idx">2</span>返回主菜单</button>`;
    html += `</div>`;
  } else if (data.choices && data.choices.length > 0) {
    html += `<div class="choices">`;
    data.choices.forEach((c, i) => {
      html += `<button class="choice-btn" onclick="makeChoice(${c.index})">
        <span class="idx">${i + 1}</span><span>${escapeHTML(c.text)}</span>
      </button>`;
    });
    html += `</div>`;
  }

  html += `</div>`;
  content.innerHTML = html;

  renderAttrs(data.attrs);
  renderActions();
  content.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 做选择
async function makeChoice(idx) {
  try {
    const data = await api('/api/choice', { choice: idx });
    renderNode(data);
  } catch (err) {
    toast(err.message || '操作失败');
  }
}

// 保存
async function saveGame() {
  try {
    const d = await api('/api/save');
    if (d.ok) toast('✓ 存档已保存');
  } catch (err) {
    toast(err.message || '保存失败');
  }
}

// 加载弹窗
async function showLoadModal() {
  let saves = [];
  try {
    saves = await apiGet('/api/saves');
  } catch (err) {
    toast(err.message || '读取存档列表失败');
    return;
  }
  let html = '<div class="modal-overlay" onclick="this.remove()"><div class="modal" onclick="event.stopPropagation()">';
  html += '<h2>读取存档</h2>';
  html += `<input class="file-input" type="file" accept="application/json,.json" onchange="importSaveFile(this.files[0])">`;

  if (saves.length === 0) {
    html += '<p style="text-align:center;color:var(--text-dim)">暂无存档</p>';
  } else {
    saves.forEach(s => {
      const filename = JSON.stringify(s.filename);
      html += `<div style="display:flex;gap:8px;align-items:center;margin:6px 0">
        <button class="trait-option" style="flex:1;margin:0" onclick='loadGame(${filename})'>
          ${escapeHTML(s.name)} — ${escapeHTML(s.title)}<br>
          <small style="color:var(--text-dim)">${escapeHTML(s.saved_at)}</small>
        </button>
        <button class="action-btn" style="padding:6px 10px;flex-shrink:0"
          onclick='event.stopPropagation();exportSave(${filename})'
          title="导出存档" aria-label="导出存档">⬇</button>
        <button class="action-btn" style="padding:6px 10px;flex-shrink:0"
          onclick='event.stopPropagation();deleteSave(${filename})'
          title="删除存档" aria-label="删除存档">✕</button>
      </div>`;
    });
  }

  html += '<button class="close-btn" onclick="this.closest(\'.modal-overlay\').remove()">关闭</button>';
  html += '</div></div>';
  document.body.insertAdjacentHTML('beforeend', html);
  document.querySelector('.modal-overlay .close-btn')?.focus();
}

async function importSaveFile(file) {
  if (!file) return;
  try {
    const text = await file.text();
    const save = JSON.parse(text);
    await api('/api/import_save', { save });
    document.querySelectorAll('.modal-overlay').forEach(m => m.remove());
    await showLoadModal();
    toast('存档已导入');
  } catch (err) {
    toast(err.message || '导入失败');
  }
}

function exportSave(filename) {
  window.location.href = `/api/export_save/${encodeURIComponent(filename)}`;
}

// 加载存档
async function loadGame(filename) {
  document.querySelectorAll('.modal-overlay').forEach(m => m.remove());
  resetAutoSave();
  try {
    const data = await api('/api/load', { filename });
    renderNode(data);
    toast('存档已加载');
  } catch (err) {
    toast(err.message || '读取失败');
  }
}

// 删除存档
async function deleteSave(filename) {
  if (!await confirmDialog('确定要删除这个存档吗？此操作不可恢复。', '删除存档')) return;
  try {
    await api('/api/delete_save', { filename });
    document.querySelectorAll('.modal-overlay').forEach(m => m.remove());
    showLoadModal();
    toast('存档已删除');
  } catch (err) {
    toast(err.message || '删除失败');
  }
}

// 重新开始 — 回到命名阶段
async function restartGame() {
  if (currentNode && !await confirmDialog('确定重新开始吗？当前未保存进度可能丢失。', '重新开始')) return;
  resetAutoSave();
  try {
    await api('/api/restart');
  } catch (err) {
    toast(err.message || '重启失败');
  }
  document.getElementById('attrs-panel').innerHTML = '';
  document.getElementById('actions').innerHTML = '';
  showNewGameDialog();
  toast('已重新开始');
}

// 主菜单
function showStartScreen() {
  showMainMenu();
}

// ============================================================
// 初始流程：名字 → 属性 → 词条 → 开始
// ============================================================
async function showMainMenu() {
  const content = document.getElementById('content');
  content.innerHTML = `
    <div class="fade-in" style="text-align:center">
      <div class="chapter-title">序章 · 天降机缘</div>
      <div class="story-text" style="text-align:center;text-indent:0">
        一段机缘，一个选择，一世仙途……<br>
        你的每一个决定，都将改变命运。
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;max-width:300px;margin:0 auto">
        <button class="choice-btn" onclick="showNewGameDialog()"><span class="idx">1</span>开始新游戏</button>
        <button class="choice-btn" onclick="showLoadModal()"><span class="idx">2</span>读取存档</button>
      </div>
    </div>`;
  document.getElementById('attrs-panel').innerHTML = '';
  document.getElementById('actions').innerHTML = '';
}

async function showNewGameDialog() {
  resetAutoSave();
  currentNode = null;
  isEnding = false;
  activeChoices = [];
  const content = document.getElementById('content');
  content.innerHTML = `
    <div class="fade-in" style="text-align:center">
      <div class="chapter-title">创建角色</div>
      <p style="margin-bottom:15px">请输入你的角色名</p>
      <input class="name-input" id="name-input" value="叶尘" maxlength="10"
        style="display:block;margin:0 auto 20px">
      <button class="choice-btn" style="max-width:200px;margin:0 auto" onclick="initNewGame()">
        <span class="idx">→</span>确认
      </button>
    </div>`;
  document.getElementById('name-input').focus();
  document.getElementById('name-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') initNewGame();
  });
}

async function initNewGame() {
  const name = document.getElementById('name-input').value.trim() || '叶尘';
  try {
    await api('/api/new_game', { name });
  } catch (err) {
    toast(err.message || '新游戏创建失败');
    return;
  }

  const content = document.getElementById('content');
  const total = 100;
  const min = 5;
  let attrs = { 根骨: min, 幸运: min, 魅力: min, 精神: min, 悟性: min };
  let remaining = total - Object.keys(attrs).length * min;

  const hints = { 根骨: '战斗·肉身', 幸运: '机缘·寻宝', 魅力: '社交·交易', 精神: '意志·心魔', 悟性: '学习·功法' };

  // 只渲染一次骨架
  let rows = Object.keys(attrs).map(k => `
    <div class="attr-input-group">
      <label>${k}</label>
      <button class="attr-stepper attr-minus" type="button" data-key="${k}" aria-label="${k}减一">−</button>
      <input type="number" id="attr-${k}" value="${min}" min="${min}" max="${min + remaining}">
      <button class="attr-stepper attr-plus" type="button" data-key="${k}" aria-label="${k}加一">+</button>
      <span class="attr-hint">${hints[k]}</span>
    </div>
  `).join('');

  content.innerHTML = `
    <div class="fade-in">
      <div class="chapter-title">分配属性</div>
      <div id="remaining-points">剩余点数: <strong>${remaining}</strong></div>
      ${rows}
      <button class="choice-btn" style="max-width:200px;margin:20px auto;display:block" id="confirm-attrs-btn">
        <span class="idx">→</span>确认属性
      </button>
    </div>`;

  // 直接 DOM 更新，无闪烁
  const remainingEl = document.getElementById('remaining-points');

  function updateUI(key) {
    document.getElementById(`attr-${key}`).value = attrs[key];
    remainingEl.innerHTML = `剩余点数: <strong>${remaining}</strong>`;
  }

  // 绑定事件（不重渲染）
  content.querySelectorAll('.attr-plus').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.dataset.key;
      if (remaining <= 0) return;
      attrs[key]++; remaining--;
      updateUI(key);
    });
  });

  content.querySelectorAll('.attr-minus').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.dataset.key;
      if (attrs[key] <= min) return;
      attrs[key]--; remaining++;
      updateUI(key);
    });
  });

  content.querySelectorAll('input[type=number]').forEach(input => {
    input.addEventListener('change', () => {
      const key = input.id.replace('attr-', '');
      let val = parseInt(input.value);
      if (isNaN(val)) { input.value = attrs[key]; return; }
      const diff = val - attrs[key];
      if (diff > remaining) val = attrs[key] + remaining;
      if (val < min) val = min;
      remaining -= (val - attrs[key]);
      attrs[key] = val;
      updateUI(key);
    });
  });

  document.getElementById('confirm-attrs-btn').addEventListener('click', () => {
    if (remaining > 0) {
      confirmDialog(`还有 ${remaining} 点未分配，确定继续？`, '确认属性').then(ok => {
        if (ok) showTraitSelection(attrs);
      });
      return;
    }
    showTraitSelection(attrs);
  });
}

function showTraitSelection(attrs) {
  const content = document.getElementById('content');
  let selectedTrait = '1';

  const traits = {
    '1': { name: '天生剑骨', desc: '根骨+10，自幼筋骨异于常人', bonus: '根骨+10' },
    '2': { name: '天命所归', desc: '幸运+15，冥冥中有气运加身', bonus: '幸运+15' },
    '3': { name: '龙凤之姿', desc: '魅力+15，天生一副好皮囊', bonus: '魅力+15' },
    '4': { name: '心如磐石', desc: '精神+15，意志坚不可摧', bonus: '精神+15' },
    '5': { name: '七窍玲珑', desc: '悟性+15，一点即通举一反三', bonus: '悟性+15' },
    '6': { name: '天道酬勤', desc: '五项各+4，全面均衡发展', bonus: '五项各+4' },
  };

  // 只渲染一次，点击只切换选中样式
  content.innerHTML = `
    <div class="fade-in">
      <div class="chapter-title">选择词条</div>
      ${Object.entries(traits).map(([k, t]) => `
        <button class="trait-option${k === selectedTrait ? ' selected' : ''}" id="trait-${k}" data-trait="${k}">
          <strong>${t.name}</strong> — ${t.bonus}<br>
          <small style="color:var(--text-dim)">${t.desc}</small>
        </button>
      `).join('')}
      <button class="choice-btn" style="max-width:200px;margin:20px auto;display:block" id="confirm-trait-btn">
        <span class="idx">→</span>开始游戏
      </button>
    </div>`;

  // 点击词条：只切换 CSS class，不重渲染
  content.querySelectorAll('.trait-option').forEach(btn => {
    btn.addEventListener('click', () => {
      content.querySelectorAll('.trait-option').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      selectedTrait = btn.dataset.trait;
    });
  });

  document.getElementById('confirm-trait-btn').addEventListener('click', async () => {
    try {
      const data = await api('/api/set_attrs', { attrs, trait: selectedTrait });
      renderNode(data);
    } catch (err) {
      toast(err.message || '角色创建失败');
    }
  });
}

// ============================================================
// Web Audio API — 古风氛围音
// ============================================================
let audioCtx = null;
let audioOn = preferences.audioOn !== false;

function initAudio() {
  if (audioCtx) return;
  try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch(e) { audioOn = false; }
}

function playNote(freq, duration, type = 'sine', vol = 0.06) {
  if (!audioOn || !audioCtx) return;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(vol, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
  osc.connect(gain); gain.connect(audioCtx.destination);
  osc.start(); osc.stop(audioCtx.currentTime + duration);
}

// 点击选项时播放
function playChoiceClick() {
  playNote(880, 0.08, 'sine', 0.04);
  setTimeout(() => playNote(1100, 0.06, 'sine', 0.03), 50);
}

// 章节切换时播放
function playChapterSound() {
  playNote(220, 0.6, 'triangle', 0.05);
  setTimeout(() => playNote(330, 0.4, 'triangle', 0.04), 200);
  setTimeout(() => playNote(440, 0.3, 'triangle', 0.03), 400);
}

// 到达结局时播放
function playEndingSound() {
  [523, 659, 784, 1047].forEach((f, i) => {
    setTimeout(() => playNote(f, 0.5, 'triangle', 0.06), i * 150);
  });
}

function toggleAudio() {
  initAudio();
  audioOn = !audioOn;
  preferences.audioOn = audioOn;
  savePreferences();
  updateAudioButton();
  if (audioOn) playNote(440, 0.1, 'sine', 0.03);
}

function updateAudioButton() {
  const button = document.getElementById('audio-toggle');
  button.textContent = audioOn ? '🔊' : '🔇';
  button.setAttribute('aria-label', audioOn ? '关闭音效' : '开启音效');
}

function showSettingsModal() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="settings-title" onclick="event.stopPropagation()">
      <h2 id="settings-title">设置</h2>
      <div class="settings-row">
        <span>主题</span>
        <select class="setting-select" id="setting-theme">
          <option value="dark">水墨暗色</option>
          <option value="light">宣纸亮色</option>
        </select>
      </div>
      <div class="settings-row">
        <span>字号</span>
        <select class="setting-select" id="setting-font-size">
          <option value="small">小</option>
          <option value="normal">中</option>
          <option value="large">大</option>
        </select>
      </div>
      <div class="settings-row">
        <span>音效</span>
        <button class="action-btn" id="setting-audio">${audioOn ? '关闭' : '开启'}</button>
      </div>
      <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">关闭</button>
    </div>`;
  overlay.addEventListener('click', () => overlay.remove());
  document.body.appendChild(overlay);
  const theme = overlay.querySelector('#setting-theme');
  const fontSize = overlay.querySelector('#setting-font-size');
  theme.value = preferences.theme || 'dark';
  fontSize.value = preferences.fontSize || 'normal';
  theme.addEventListener('change', () => {
    preferences.theme = theme.value;
    savePreferences();
    applyPreferences();
  });
  fontSize.addEventListener('change', () => {
    preferences.fontSize = fontSize.value;
    savePreferences();
    applyPreferences();
  });
  overlay.querySelector('#setting-audio').addEventListener('click', event => {
    toggleAudio();
    event.currentTarget.textContent = audioOn ? '关闭' : '开启';
  });
  theme.focus();
}

// ============================================================
// 章节过渡
// ============================================================
function showChapterTransition(title, callback) {
  const chars = '仙途问道剑丹宗魔缘尘世命运劫';
  const el = document.createElement('div');
  el.className = 'chapter-transition';
  const char = chars[Math.floor(Math.random() * chars.length)];
  el.innerHTML = `<span class="chinese-char">${char}</span>`;
  document.body.appendChild(el);
  setTimeout(() => {
    el.classList.add('out');
    setTimeout(() => { el.remove(); if (callback) callback(); }, 400);
  }, 800);
}

// ============================================================
// 结局画廊
// ============================================================
async function showGallery() {
  let endings = [];
  try {
    endings = await apiGet('/api/gallery');
  } catch (err) {
    toast(err.message || '读取画廊失败');
    return;
  }
  const total = 46; // 总共有 46 个结局
  const content = document.getElementById('content');

  function getRankClass(title) {
    const t = title || '';
    if (t.includes('SS')) return 'rank-ss';
    if (t.includes('S——') || t.includes('S：')) return 'rank-s';
    if (t.includes('A——') || t.includes('A：')) return 'rank-a';
    if (t.includes('B——') || t.includes('B：')) return 'rank-b';
    return 'rank-d';
  }
  function getRankLabel(title) {
    const t = title || '';
    if (t.includes('SS')) return 'SS';
    if (t.includes('S——') || t.includes('S：')) return 'S';
    if (t.includes('A——') || t.includes('A：')) return 'A';
    if (t.includes('B——') || t.includes('B：')) return 'B';
    if (t.includes('C——') || t.includes('C：')) return 'C';
    return 'D';
  }

  let html = `<div class="fade-in">
    <div class="chapter-title">结局画廊</div>
    <div class="gallery-count">已收集: ${endings.length} / ${total}</div>`;

  if (endings.length === 0) {
    html += '<p style="text-align:center;color:var(--text-dim)">还没有达成任何结局，去探索吧。</p>';
  } else {
    html += '<div class="gallery-grid">';
    endings.forEach(e => {
      html += `<div class="gallery-card">
        <div class="rank-badge ${getRankClass(e.title)}">${escapeHTML(getRankLabel(e.title))}</div>
        <p style="margin:8px 0;font-size:0.9rem">${escapeHTML((e.title || '').replace('【结局】',''))}</p>
        <p style="font-size:0.75rem;color:var(--text-dim)">${escapeHTML(e.saved_at || e.achieved_at || '')}</p>
        <p style="font-size:0.75rem;color:var(--text-dim)">${escapeHTML(e.player_name || '')} · ${escapeHTML(e.trait || '')}</p>
      </div>`;
    });
    html += '</div>';
  }
  html += `<button class="choice-btn" style="max-width:200px;margin:10px auto;display:block" onclick="showMainMenu()">
    <span class="idx">←</span>返回主菜单</button></div>`;

  content.innerHTML = html;
  document.getElementById('attrs-panel').innerHTML = '';
  document.getElementById('actions').innerHTML = '';
}

// ============================================================
// 结局总结
// ============================================================
async function showEndingSummary(data) {
  try {
    await api('/api/record_ending');
  } catch (err) {
    toast(err.message || '结局记录失败');
  }
  playEndingSound();

  const node = data;
  let summaryHTML = '<div class="ending-summary">';
  summaryHTML += '<div class="chapter-title">通关总结</div>';

  // 属性概览
  summaryHTML += '<table><tr><td colspan="2" style="color:var(--gold);text-align:center">最终属性</td></tr>';
  for (const [k, v] of Object.entries(data.attrs || {})) {
    const bar = '█'.repeat(Math.min(20, Math.round(v / 3))) + '░'.repeat(Math.max(0, 20 - Math.round(v / 3)));
    summaryHTML += `<tr><td>${escapeHTML(k)}</td><td>${escapeHTML(v)} ${bar}</td></tr>`;
  }
  summaryHTML += '</table>';

  // 决策轮数
  summaryHTML += `<p style="text-align:center;color:var(--text-dim);margin-top:12px">
    词条: ${escapeHTML(data.trait || '无')} · 结局: ${escapeHTML((node.title || '').replace('【结局】',''))}
  </p>`;
  summaryHTML += '</div>';

  return summaryHTML;
}

// ============================================================
// 重写 renderNode — 接入所有新功能
// ============================================================
const _renderNode_original = renderNode;
renderNode = async function(data) {
  const chapter = getChapter(data.title);

  // 章节切换过渡
  if (chapter && chapter !== lastChapter && lastChapter !== '') {
    showChapterTransition(chapter);
    playChapterSound();
  }

  _renderNode_original(data);

  // 结局总结 — 渲染到正文下方
  if (data.is_ending) {
    const summary = await showEndingSummary(data);
    const storyEl = document.querySelector('.story-text');
    if (storyEl) {
      const div = document.createElement('div');
      div.innerHTML = summary;
      storyEl.parentNode.insertBefore(div, storyEl.nextSibling);
    }
  }
};

// 重写 makeChoice — 播放点击音效
const _makeChoice_original = makeChoice;
makeChoice = async function(idx) {
  initAudio();
  playChoiceClick();
  await _makeChoice_original(idx);
};

// ============================================================
// 重写主菜单 — 加入画廊入口
// ============================================================
const _showMainMenu_original = showMainMenu;
showMainMenu = function() {
  currentNode = null;
  isEnding = false;
  activeChoices = [];
  const content = document.getElementById('content');
  content.innerHTML = `
    <div class="fade-in" style="text-align:center">
      <div class="chapter-title">仙 途</div>
      <div class="story-text" style="text-align:center;text-indent:0">
        一段机缘，一个选择，一世仙途……<br>
        你的每一个决定，都将改变命运。
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;max-width:300px;margin:0 auto">
        <button class="choice-btn" onclick="initAudio();playChoiceClick();showNewGameDialog()"><span class="idx">1</span>开始新游戏</button>
        <button class="choice-btn" onclick="initAudio();playChoiceClick();showLoadModal()"><span class="idx">2</span>读取存档</button>
        <button class="choice-btn" onclick="initAudio();playChoiceClick();showGallery()"><span class="idx">3</span>结局画廊</button>
        <button class="choice-btn" onclick="showSettingsModal()"><span class="idx">4</span>设置</button>
      </div>
    </div>`;
  document.getElementById('attrs-panel').innerHTML = '';
  document.getElementById('actions').innerHTML = '';
};

// 桌面浏览器键盘操作，Mac/Windows 都可用
document.addEventListener('keydown', event => {
  const tag = event.target && event.target.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

  if (/^[1-9]$/.test(event.key)) {
    const idx = Number(event.key) - 1;
    if (activeChoices[idx]) {
      event.preventDefault();
      makeChoice(activeChoices[idx].index);
    }
  } else if (event.key.toLowerCase() === 's' && currentNode && !isEnding) {
    event.preventDefault();
    saveGame();
  } else if (event.key === 'Escape') {
    const modal = document.querySelector('.modal-overlay');
    if (modal) {
      const cancel = modal.querySelector('[data-result="false"]');
      if (cancel) cancel.click();
      else modal.remove();
    } else {
      showMainMenu();
    }
  }
});

// ============================================================
// 启动
// ============================================================
applyPreferences();
updateAudioButton();
initParticles();
showMainMenu();

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {});
  });
}
