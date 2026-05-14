/* ═══════════════════════════════════════════════════════════
   智能面试助手 - 前台页面
   单页应用，支持：登录 / 注册 / 简历上传分析
   ═══════════════════════════════════════════════════════════ */

const API_BASE = '/api/v1';
let authToken = localStorage.getItem('token') || null;
let currentUser = null;

/* ── DOM 引用 ─────────────────────────────────────────── */
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const pageLogin = $('#page-login');
const pageRegister = $('#page-register');
const pageDashboard = $('#page-dashboard');
const navbar = $('#navbar');
const navUsername = $('#navUsername');
const loginError = $('#loginError');
const registerError = $('#registerError');
const uploadError = $('#uploadError');
const uploadStatus = $('#uploadStatus');
const uploadBtn = $('#uploadBtn');
const progressFill = $('#progressFill');
const progressLabel = $('#progressLabel');
const resultsArea = $('#resultsArea');

/* ── 页面切换 ─────────────────────────────────────────── */
function showPage(name) {
  $$('.page').forEach(p => p.classList.remove('active'));
  const el = $(`#page-${name}`);
  if (el) el.classList.add('active');
}

function updateNav() {
  if (currentUser) {
    navbar.classList.remove('hidden');
    navUsername.textContent = currentUser.display_name || currentUser.username;
  } else {
    navbar.classList.add('hidden');
  }
}

/* ── API 请求 ─────────────────────────────────────────── */
async function api(method, path, data) {
  const opts = { method, headers: {} };
  if (authToken) opts.headers['Authorization'] = `Bearer ${authToken}`;

  if (data instanceof FormData) {
    opts.body = data;
  } else if (data) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(data);
  }

  const res = await fetch(`${API_BASE}${path}`, opts);
  const body = await res.json();
  if (!res.ok) throw new Error(body.detail || body.message || '请求失败');
  return body;
}

/* ── Token 存储 ───────────────────────────────────────── */
function saveToken(token, user) {
  authToken = token;
  currentUser = user;
  localStorage.setItem('token', token);
  localStorage.setItem('user', JSON.stringify(user));
}

function clearAuth() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem('token');
  localStorage.removeItem('user');
}

/* ── 登录 ─────────────────────────────────────────────── */
$('#loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  loginError.textContent = '';
  const username = $('#loginUsername').value.trim();
  const password = $('#loginPassword').value;

  try {
    const res = await api('POST', '/auth/login', { username, password });
    saveToken(res.access_token, res.user);
    enterDashboard();
  } catch (err) {
    loginError.textContent = err.message;
  }
});

/* ── 注册 ─────────────────────────────────────────────── */
$('#registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  registerError.textContent = '';
  const username = $('#regUsername').value.trim();
  const email = $('#regEmail').value.trim();
  const password = $('#regPassword').value;
  const display_name = $('#regDisplayName').value.trim() || null;

  try {
    const res = await api('POST', '/auth/register', { username, email, password, display_name });
    saveToken(res.access_token, res.user);
    enterDashboard();
  } catch (err) {
    registerError.textContent = err.message;
  }
});

/* ── 退出 ─────────────────────────────────────────────── */
$('#logoutBtn').addEventListener('click', () => {
  clearAuth();
  showPage('login');
  updateNav();
});

/* ── 页面跳转链接 ────────────────────────────────────── */
$$('[data-page]').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    showPage(link.dataset.page);
  });
});

/* ── 进入仪表盘 ────────────────────────────────────────── */
async function enterDashboard() {
  showPage('dashboard');
  updateNav();
  // 如果 token 可能过期，拉取 /auth/me 验证
  // 若失败则退回登录
}

/* ── 上传简历（SSE 流式） ────────────────────────────────── */
$('#uploadForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  uploadError.textContent = '';
  resultsArea.classList.add('hidden');

  const file = $('#resumeFile').files[0];
  if (!file) { uploadError.textContent = '请选择简历文件'; return; }

  const jobDesc = $('#jobDesc').value.trim();

  const fd = new FormData();
  fd.append('file', file);
  if (jobDesc) fd.append('job_description', jobDesc);

  // 显示进度条
  uploadBtn.disabled = true;
  uploadBtn.textContent = '分析中...';
  uploadStatus.classList.remove('hidden');
  progressFill.style.width = '0%';
  progressLabel.textContent = '正在启动分析流程...';

  try {
    await uploadViaSSE(fd);
  } catch (err) {
    uploadError.textContent = `分析失败：${err.message}`;
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = '开始分析';
    uploadStatus.classList.add('hidden');
  }
});

async function uploadViaSSE(fd) {
  const opts = { method: 'POST', body: fd };
  if (authToken) opts.headers = { 'Authorization': `Bearer ${authToken}` };

  const resp = await fetch(`${API_BASE}/upload/stream`, opts);
  if (!resp.ok) {
    const errBody = await resp.json().catch(() => ({}));
    throw new Error(errBody.detail || `请求失败 (${resp.status})`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let eventType = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7);
      } else if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        if (eventType === 'progress') {
          updateProgress(data);
        } else if (eventType === 'result') {
          renderResults(data);
          resultsArea.classList.remove('hidden');
        } else if (eventType === 'error') {
          throw new Error(data.message);
        }
        eventType = '';
      }
    }
  }
}

/* ── 进度更新 ──────────────────────────────────────────── */
function updateProgress(progress) {
  const pct = progress.percentage || 0;
  progressFill.style.width = `${pct}%`;
  progressLabel.textContent = progress.message || '';
}

/* ── 渲染结果 ──────────────────────────────────────────── */
function renderResults(data) {
  renderResume(data.parsed_resume);
  renderMatch(data.match_analysis);
  renderQuestions(data.interview_questions);
  // 滚动到结果区
  resultsArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ── 简历渲染 ─────────────────────────────────────────── */
function renderResume(resume) {
  const el = $('#resumeContent');
  const p = resume.personal_info || {};

  let html = '<div class="info-grid">';
  if (p.name) html += `<div class="info-item"><div class="label">姓名</div><div class="value">${esc(p.name)}</div></div>`;
  if (p.title) html += `<div class="info-item"><div class="label">职位</div><div class="value">${esc(p.title)}</div></div>`;
  if (p.email) html += `<div class="info-item"><div class="label">邮箱</div><div class="value">${esc(p.email)}</div></div>`;
  if (p.phone) html += `<div class="info-item"><div class="label">电话</div><div class="value">${esc(p.phone)}</div></div>`;
  html += '</div>';

  if (p.summary) html += `<p style="margin:12px 0;color:#555">${esc(p.summary)}</p>`;

  // 技能
  if (resume.skills && resume.skills.length) {
    html += '<h3 style="margin-top:16px">技能</h3><div class="skill-tags">';
    resume.skills.forEach(s => {
      html += `<span class="skill-tag">${esc(s.name)}${s.proficiency ? ` (${(s.proficiency * 100).toFixed(0)}%)` : ''}</span>`;
    });
    html += '</div>';
  }

  // 工作经历
  if (resume.experiences && resume.experiences.length) {
    html += '<h3 style="margin-top:16px">工作经历</h3>';
    resume.experiences.forEach(exp => {
      html += `<div style="margin:10px 0;padding:12px;background:#f9fafb;border-radius:8px">
        <strong>${esc(exp.title)}</strong> @ ${esc(exp.company)}
        ${exp.start_date ? `<span style="color:#888;margin-left:8px">${esc(exp.start_date)} ~ ${esc(exp.end_date || '至今')}</span>` : ''}
        ${exp.description ? `<p style="margin-top:4px;color:#555;font-size:14px">${esc(exp.description)}</p>` : ''}
      </div>`;
    });
  }

  // 教育
  if (resume.education && resume.education.length) {
    html += '<h3 style="margin-top:16px">教育背景</h3>';
    resume.education.forEach(edu => {
      html += `<div style="margin:10px 0">${esc(edu.degree)} - ${esc(edu.institution)}${edu.field ? ` (${esc(edu.field)})` : ''}</div>`;
    });
  }

  // 项目
  if (resume.projects && resume.projects.length) {
    html += '<h3 style="margin-top:16px">项目经历</h3>';
    resume.projects.forEach(proj => {
      html += `<div style="margin:10px 0;padding:12px;background:#f9fafb;border-radius:8px">
        <strong>${esc(proj.name)}</strong>
        <p style="margin-top:4px;color:#555;font-size:14px">${esc(proj.description)}</p>
        ${proj.technologies.length ? `<div class="skill-tags" style="margin-top:6px">${proj.technologies.map(t => `<span class="skill-tag">${esc(t)}</span>`).join('')}</div>` : ''}
      </div>`;
    });
  }

  el.innerHTML = html;
}

/* ── 匹配分析渲染 ─────────────────────────────────────── */
function renderMatch(match) {
  const el = $('#matchContent');
  const score = match.overall_score * 100;
  const scoreClass = score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low';

  let html = `<div class="match-score ${scoreClass}">
    <div class="score-number">${score.toFixed(0)}%</div>
    <div class="score-label">总体匹配度</div>
  </div>`;

  if (match.summary) html += `<p style="text-align:center;color:#555;margin-bottom:16px">${esc(match.summary)}</p>`;

  if (match.experience_years !== null && match.experience_years !== undefined) {
    html += `<p style="text-align:center;margin-bottom:16px;font-size:14px;color:#666">经验年限：${match.experience_years} 年</p>`;
  }

  // 分类得分
  if (match.category_scores && match.category_scores.length) {
    html += '<h3>分类得分</h3><div class="category-scores">';
    match.category_scores.forEach(cat => {
      const pct = (cat.score * 100).toFixed(0);
      const color = cat.score >= 0.7 ? '#27ae60' : cat.score >= 0.4 ? '#f39c12' : '#e74c3c';
      html += `<div class="category-bar">
        <span class="cat-label">${esc(cat.category)}</span>
        <div class="cat-track"><div class="cat-fill" style="width:${pct}%;background:${color}"></div></div>
        <span class="cat-pct">${pct}%</span>
      </div>`;
    });
    html += '</div>';
  }

  // 优势与差距
  const hasStrength = match.strengths && match.strengths.length;
  const hasGaps = match.gaps && match.gaps.length;
  if (hasStrength || hasGaps) {
    html += '<div class="strength-gap">';
    html += '<div><h4 style="color:#27ae60;margin-bottom:8px">优势</h4><ul class="strengths">';
    (match.strengths || []).forEach(s => html += `<li>${esc(s)}</li>`);
    html += '</ul></div>';
    html += '<div><h4 style="color:#e74c3c;margin-bottom:8px">差距</h4><ul class="gaps">';
    (match.gaps || []).forEach(g => html += `<li>${esc(g)}</li>`);
    html += '</ul></div>';
    html += '</div>';
  }

  el.innerHTML = html;
}

/* ── 面试题渲染 ────────────────────────────────────────── */
function renderQuestions(questions) {
  const el = $('#questionsContent');
  let html = '';

  const groups = [
    { key: 'technical', label: '💻 技术题' },
    { key: 'behavioral', label: '🤝 行为题' },
    { key: 'project_deep_dive', label: '🔍 项目深挖题' },
  ];

  groups.forEach(group => {
    const items = questions[group.key];
    if (!items || !items.length) return;

    html += `<div class="question-group"><h3>${group.label}（${items.length} 题）</h3>`;
    items.forEach((q, i) => {
      const diffMap = { basic: '基础', intermediate: '进阶', advanced: '深入' };
      const diff = diffMap[q.difficulty] || q.difficulty;
      html += `<div class="question-item">
        <div class="q-content">${i + 1}. ${esc(q.content)}</div>
        <div class="q-meta">难度：${diff}</div>`;
      if (q.rationale) {
        html += `<div class="toggle-link" onclick="toggleVisible(this,'rationale-${group.key}-${i}')">📖 出题理由</div>
        <div id="rationale-${group.key}-${i}" class="q-rationale hidden">${esc(q.rationale)}</div>`;
      }
      if (q.reference_answer) {
        html += `<div class="toggle-link" onclick="toggleVisible(this,'answer-${group.key}-${i}')">✅ 参考答案</div>
        <div id="answer-${group.key}-${i}" class="q-answer hidden">${esc(q.reference_answer)}</div>`;
      }
      html += '</div>';
    });
    html += '</div>';
  });

  if (!html) html = '<p style="color:#888">暂无面试题数据</p>';
  el.innerHTML = html;
}

/* ── 辅助函数 ─────────────────────────────────────────── */
function esc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}

function toggleVisible(link, id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle('hidden');
  link.textContent = el.classList.contains('hidden')
    ? (link.textContent.includes('理由') ? '📖 出题理由' : '✅ 参考答案')
    : (link.textContent.includes('理由') ? '📖 收起理由' : '✅ 收起答案');
}

/* ── 初始化 ───────────────────────────────────────────── */
(async function init() {
  // 尝试从 localStorage 恢复登录状态
  const savedUser = localStorage.getItem('user');
  const savedToken = localStorage.getItem('token');
  if (savedToken && savedUser) {
    try {
      // 验证 token 是否有效
      const user = await api('GET', '/auth/me');
      currentUser = user;
      authToken = savedToken;
      enterDashboard();
      return;
    } catch {
      // token 过期，清空
      clearAuth();
    }
  }
  showPage('login');
  updateNav();
})();
