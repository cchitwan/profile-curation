// Use '/api' for Docker (Nginx proxy) or 'http://localhost:8000/api' for local dev
const isLocal = window.location.hostname === 'localhost' || 
                 window.location.hostname === '127.0.0.1' || 
                 window.location.hostname.includes('192.168.') ||
                 window.location.port === '5173';
const API_URL = isLocal ? 'http://localhost:8000/api' : '/api';
console.log('Detected API_URL:', API_URL);
console.log('Current Origin:', window.location.origin);
let token = localStorage.getItem('token');
let userEmail = null;
let currentJobId = null;
let pollInterval = null;

// DOM Elements
const els = {
  authSection: document.getElementById('auth-section'),
  dashboardSection: document.getElementById('dashboard-section'),
  processingSection: document.getElementById('processing-section'),
  resultsSection: document.getElementById('results-section'),
  emailInput: document.getElementById('email'),
  passwordInput: document.getElementById('password'),
  loginBtn: document.getElementById('login-btn'),
  registerBtn: document.getElementById('register-btn'),
  authError: document.getElementById('auth-error'),
  userEmailDisplay: document.getElementById('user-email'),
  logoutBtn: document.getElementById('logout-btn'),
  uploadZone: document.getElementById('upload-zone'),
  resumeUpload: document.getElementById('resume-upload'),
  resumeStatus: document.getElementById('resume-status'),
  curationCard: document.getElementById('curation-card'),
  tabs: document.querySelectorAll('.tab'),
  tabContents: document.querySelectorAll('.tab-content'),
  startCurationBtn: document.getElementById('start-curation-btn'),
  jobUrl: document.getElementById('job-url'),
  jobText: document.getElementById('job-text'),
  processingStatus: document.getElementById('processing-status'),
  steps: document.querySelectorAll('.step'),
  finalScore: document.getElementById('final-score'),
  scoreFeedback: document.getElementById('score-feedback'),
  scoreGaps: document.getElementById('score-gaps'),
  resumePreview: document.getElementById('resume-preview'),
  downloadPdfBtn: document.getElementById('download-pdf-btn'),
  downloadDocxBtn: document.getElementById('download-docx-btn'),
  downloadJsonBtn: document.getElementById('download-json-btn'),
  backBtn: document.getElementById('back-btn'),
  historyList: document.getElementById('history-list'),
  insightsSection: document.getElementById('insights-section'),
  initialScore: document.getElementById('initial-score-display'),
  finalScoreDisplay: document.getElementById('final-score-display'),
  tokenUsage: document.getElementById('token-usage-display'),
  improvementList: document.getElementById('improvement-list'),
  companyName: document.getElementById('company-name'),
  targetRole: document.getElementById('target-role'),
  socialSection: document.getElementById('social-links-section'),
  socialContainer: document.getElementById('social-links-container'),
  addSocialBtn: document.getElementById('add-social-btn'),
  profileCard: document.getElementById('profile-card'),
  profileEmail: document.getElementById('profile-email'),
  profilePhone: document.getElementById('profile-phone'),
  linkedinUrl: document.getElementById('linkedin-url'),
  githubUrl: document.getElementById('github-url'),
  durationDisplay: document.getElementById('duration-display'),
  viewPdfBtn: document.getElementById('view-pdf-btn'),
  jobInfoPreview: document.getElementById('job-info-preview'),
  
  // Review Section (HITL)
  reviewSection: document.getElementById('review-section'),
  initialScoreVal: document.getElementById('initial-score-val'),
  alignmentWarning: document.getElementById('alignment-warning'),
  alignmentFeedback: document.getElementById('alignment-feedback'),
  reviewMissingList: document.getElementById('review-missing-list'),
  reviewImprovementList: document.getElementById('review-improvement-list'),
  confirmCurationBtn: document.getElementById('confirm-curation-btn'),
  cancelCurationBtn: document.getElementById('cancel-curation-btn'),
  
  processingTitle: document.getElementById('processing-title'),
  processingSubtitle: document.getElementById('processing-subtitle'),
  resumeSelector: document.getElementById('resume-selector')
};

// Initialize
async function init() {
  if (token) {
    try {
      const res = await fetch(`${API_URL}/users/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const user = await res.json();
        userEmail = user.email;
        showDashboard();
      } else {
        logout();
      }
    } catch (e) {
      console.error(e);
      logout();
    }
  } else {
    showAuth();
  }
}

// Navigation
function showAuth() {
  els.authSection.classList.remove('hidden');
  els.dashboardSection.classList.add('hidden');
  els.processingSection.classList.add('hidden');
  els.resultsSection.classList.add('hidden');
  els.logoutBtn.classList.add('hidden');
  els.userEmailDisplay.textContent = '';
}

async function showDashboard() {
  console.log('--- SHOW DASHBOARD ---');
  els.authSection.classList.add('hidden');
  els.dashboardSection.classList.remove('hidden');
  els.resultsSection.classList.add('hidden');
  els.reviewSection.classList.add('hidden');
  els.processingSection.classList.add('hidden');
  els.logoutBtn.classList.remove('hidden');
  els.userEmailDisplay.textContent = userEmail;
  els.profileCard.style.display = 'block';
  
  // Prioritize unlocking curation
  await loadResumes();
  
  loadProfile(); // Non-blocking
  checkBaseResume(); // Non-blocking
}

async function loadResumes() {
  console.log('--- STARTING LOAD RESUMES ---');
  try {
    const res = await fetch(`${API_URL}/resumes/all`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    console.log('Resumes API status:', res.status);
    if (res.ok) {
      const resumes = await res.json();
      console.log('Resumes found:', resumes.length);
      if (!els.resumeSelector) {
        console.error('resumeSelector element NOT FOUND in DOM');
        return;
      }
      
      if (resumes.length > 0) {
        els.resumeSelector.innerHTML = resumes.map((r, idx) => 
          `<option value="${r.id}" ${idx === 0 ? 'selected' : ''}>${r.filename} (${new Date(r.created_at).toLocaleDateString()})</option>`
        ).join('');
        
        console.log('UNLOCKING CURATION CARD NOW');
        els.curationCard.classList.remove('disabled');
        els.curationCard.style.opacity = '1';
        els.curationCard.style.pointerEvents = 'auto';
      } else {
        console.warn('NO RESUMES IN DATABASE FOR THIS USER');
        els.resumeSelector.innerHTML = '<option value="">No resumes found. Please upload one.</option>';
        els.curationCard.classList.add('disabled');
      }
    } else {
      const errText = await res.text();
      console.error('Resumes API failed:', errText);
    }
  } catch (e) {
    console.error('CRITICAL ERROR in loadResumes:', e);
  }
}

async function loadProfile() {
  try {
    const res = await fetch(`${API_URL}/users/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const user = await res.json();
      els.profileEmail.value = user.email;
      els.profilePhone.value = user.phone_number || '';
      
      els.socialContainer.innerHTML = '';
      if (user.social_links && user.social_links.length > 0) {
        user.social_links.forEach(l => addSocialLinkRow(l.label, l.url));
      } else {
        addSocialLinkRow('LinkedIn', '');
        addSocialLinkRow('GitHub', '');
      }
    }
  } catch (e) {
    console.error(e);
  }
}

async function saveProfile() {
  const socialLinks = Array.from(els.socialContainer.querySelectorAll('.social-link-row')).map(row => ({
    label: row.querySelector('.link-label').value,
    url: row.querySelector('.link-url').value
  })).filter(l => l.label || l.url);

  try {
    await fetch(`${API_URL}/users/profile`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ 
        phone_number: els.profilePhone.value,
        social_links: socialLinks
      })
    });
  } catch (e) {
    console.error(e);
  }
}

// Social Links Dynamic UI
function addSocialLinkRow(label = '', url = '') {
  const row = document.createElement('div');
  row.className = 'social-link-row';
  row.innerHTML = `
    <input type="text" class="link-label" placeholder="Label (e.g. LinkedIn)" value="${label}">
    <input type="url" class="link-url" placeholder="https://..." value="${url}">
    <button class="btn btn-icon btn-danger remove-link-btn" title="Remove">×</button>
  `;
  
  row.querySelector('.link-label').onblur = saveProfile;
  row.querySelector('.link-url').onblur = saveProfile;
  row.querySelector('.remove-link-btn').onclick = () => {
    row.remove();
    saveProfile();
  };
  els.socialContainer.appendChild(row);
}

if (els.addSocialBtn) {
  els.addSocialBtn.onclick = () => {
    addSocialLinkRow();
    saveProfile();
  };
}

if (els.profilePhone) els.profilePhone.onblur = saveProfile;
if (els.linkedinUrl) els.linkedinUrl.onblur = saveProfile;
if (els.githubUrl) els.githubUrl.onblur = saveProfile;

// Auth Handlers
async function handleAuth(type) {
  const email = els.emailInput.value;
  const password = els.passwordInput.value;
  
  if (!email || !password) {
    showError('Please fill in both fields');
    return;
  }

  try {
    const endpoint = type === 'login' ? '/users/login' : '/users/register';
    const body = type === 'login' ? { email, password } : { email, password };
    
    console.log('Attempting auth:', type, `${API_URL}${endpoint}`);
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    
    console.log('Auth response status:', res.status);
    const data = await res.json();
    console.log('Auth data:', data);
    
    if (res.ok) {
      token = data.access_token;
      localStorage.setItem('token', token);
      userEmail = email;
      showDashboard();
    } else {
      showError(data.detail || 'Authentication failed');
    }
  } catch (e) {
    console.error('Auth error:', e);
    showError('Network error: ' + e.message);
  }
}

function logout() {
  token = null;
  userEmail = null;
  localStorage.removeItem('token');
  showAuth();
}

function showError(msg) {
  console.warn('UI Error:', msg);
  const displayMsg = typeof msg === 'object' ? JSON.stringify(msg) : msg;
  els.authError.textContent = displayMsg;
  els.authError.classList.remove('hidden');
}

// Resume Handlers
async function checkBaseResume() {
  try {
    const res = await fetch(`${API_URL}/resumes/latest`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      els.resumeStatus.textContent = `Latest master resume: ${data.filename}`;
      els.resumeStatus.style.display = 'block';
      els.socialSection.style.display = 'block';
    } else {
      els.resumeStatus.innerHTML = `<p>No resume uploaded yet.</p>`;
    }
  } catch (e) {
    console.error(e);
  }
}

els.uploadZone.addEventListener('click', () => els.resumeUpload.click());

els.resumeUpload.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  els.resumeStatus.innerHTML = '<p>Uploading & Parsing...</p>';
  
  try {
    const res = await fetch(`${API_URL}/resumes/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });
    
    if (res.ok) {
      await checkBaseResume();
      await loadResumes();
    } else {
      const err = await res.json();
      els.resumeStatus.innerHTML = `<p class="error-text">Upload failed: ${err.detail}</p>`;
    }
  } catch (err) {
    els.resumeStatus.innerHTML = `<p class="error-text">Network error</p>`;
  }
});

// UI Tabs
els.tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    els.tabs.forEach(t => t.classList.remove('active'));
    els.tabContents.forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
    
    if (tab.dataset.tab === 'history') {
      fetchHistory();
    }
  });
});

async function fetchHistory() {
  try {
    const res = await fetch(`${API_URL}/curation/history`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      renderHistory(data);
    }
  } catch (e) {
    console.error(e);
  }
}

function renderHistory(items) {
  if (!items || items.length === 0) {
    els.historyList.innerHTML = '<p>No past curations found.</p>';
    return;
  }

  els.historyList.innerHTML = items.map(item => {
    const scoreClass = item.score >= 95 ? '' : (item.score >= 80 ? 'mid' : 'low');
    const dateTime = new Date(item.created_at).toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      dateStyle: 'medium',
      timeStyle: 'short'
    }); // e.g. 22 Apr 2024, 6:30 PM
    const versionTag = `<span class="version-badge">v${item.version}</span>`;
    const durationTag = `<span class="duration-badge">${item.time_taken}s</span>`;
    const itemEl = document.createElement('div');
    itemEl.className = 'history-item fade-in';
    itemEl.innerHTML = `
      <div class="history-info" onclick="viewHistoryDetails(${item.id})" style="cursor: pointer;">
        <strong>${item.company_name || 'General'} - ${item.target_role || 'Role'}</strong>
        <p>${dateTime} • Score: ${item.score || 0}% • ${durationTag}</p>
      </div>
      <div class="history-actions">
        <button class="btn-icon" title="View Details" onclick="viewHistoryDetails(${item.id})">📊</button>
        <button class="btn-icon" title="View PDF" onclick="viewFile(${item.id}, 'pdf')">👁️</button>
        <button class="btn-icon" title="Download PDF" onclick="downloadFile(${item.id}, 'pdf')">📄</button>
        <button class="btn-icon" title="Download DOCX" onclick="downloadFile(${item.id}, 'docx')">📝</button>
        <button class="btn-icon btn-danger" title="Delete" onclick="deleteCuration(${item.id})">🗑️</button>
      </div>
    `;
    return itemEl.outerHTML;
  }).join('');
}

async function deleteCuration(jobId) {
  if (!confirm('Are you sure you want to delete this curation history?')) return;
  
  try {
    const res = await fetch(`${API_URL}/curation/${jobId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      fetchHistory(); // Refresh list
    } else {
      alert('Failed to delete item');
    }
  } catch (e) {
    console.error(e);
  }
}

async function downloadFile(jobId, format) {
  try {
    const res = await fetch(`${API_URL}/curation/download/${jobId}/${format}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `curated_resume_${jobId}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } else {
      alert('Download failed');
    }
  } catch (e) {
    console.error(e);
    alert('Network error during download');
  }
}

async function viewFile(jobId, format = 'pdf') {
  const url = `${API_URL}/curation/download/${jobId}/${format}?disposition=inline`;
  // We need to pass the token. Since it's a new tab, we can't easily set headers.
  // We'll use a temporary link with the token as a query param if needed, 
  // but for simplicity here, we'll try to use the same fetch blob approach.
  try {
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    window.open(blobUrl, '_blank');
  } catch (e) {
    console.error(e);
  }
}

async function viewHistoryDetails(jobId) {
  try {
    const res = await fetch(`${API_URL}/curation/status/${jobId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      showResults(data);
    } else {
      alert('Failed to fetch curation details');
    }
  } catch (e) {
    console.error(e);
  }
}

// Attach handlers to window for inline onclick
window.downloadFile = downloadFile;
window.viewFile = viewFile;
window.viewHistoryDetails = viewHistoryDetails;
window.deleteCuration = deleteCuration;
window.showDashboard = showDashboard;

// Curation Handlers
els.startCurationBtn.addEventListener('click', async () => {
  const jobText = els.jobText.value;
  const isUrl = document.querySelector('.tab.active').dataset.tab === 'url';
  const company = els.companyName.value;
  const role = els.targetRole.value;

  if (!company || !role) {
    alert('Please enter both Company Name and Target Role.');
    return;
  }

  if (isUrl && !els.jobUrl.value) return alert('Please enter a job URL');
  if (!isUrl && !jobText) return alert('Please enter job description text');

  // Collect social links
  const socialLinks = Array.from(els.socialContainer.querySelectorAll('.social-link-row')).map(row => ({
    label: row.querySelector('.link-label').value,
    url: row.querySelector('.link-url').value
  })).filter(l => l.label && l.url);

  try {
    // Phase 1: Analyze
    els.dashboardSection.classList.add('hidden');
    els.processingSection.classList.remove('hidden');
    els.processingTitle.textContent = "Analyzing Gap & Alignment";
    els.processingSubtitle.textContent = "Checking if the role matches your career path...";
    updateProgress(1);

    const res = await fetch(`${API_URL}/curation/analyze`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ 
        job_input: isUrl ? els.jobUrl.value : jobText, 
        is_url: isUrl,
        company_name: company,
        target_role: role,
        resume_id: els.resumeSelector ? els.resumeSelector.value : null,
        social_links: socialLinks,
        submitted_at: new Date().toISOString()
      })
    });
    
    if (res.ok) {
      const data = await res.json();
      currentJobId = data.job_id;
      showReview(data);
    } else {
      alert('Failed to start analysis');
      showDashboard();
    }
  } catch (e) {
    console.error(e);
    showDashboard();
  }
});

function showReview(data) {
  els.processingSection.classList.add('hidden');
  els.reviewSection.classList.remove('hidden');
  
  els.initialScoreVal.textContent = data.initial_score;
  const gap = data.gap_report;
  
  // Alignment Check
  if (!gap.is_aligned) {
    els.alignmentWarning.classList.remove('hidden');
    els.alignmentFeedback.textContent = gap.alignment_feedback;
  } else {
    els.alignmentWarning.classList.add('hidden');
  }
  
  const allMissing = [...(gap.missing_skills || []), ...(gap.missing_keywords || [])];
  els.reviewMissingList.innerHTML = allMissing.map(m => `<li>${m}</li>`).join('');
  els.reviewImprovementList.innerHTML = (gap.improvement_areas || []).map(i => `<li>${i}</li>`).join('');
  
  els.confirmCurationBtn.onclick = () => confirmCuration(data.job_id);
  els.cancelCurationBtn.onclick = () => {
    els.reviewSection.classList.add('hidden');
    showDashboard();
  };
}

async function confirmCuration(jobId) {
  els.reviewSection.classList.add('hidden');
  els.processingSection.classList.remove('hidden');
  els.processingTitle.textContent = "Optimizing Resume";
  els.processingSubtitle.textContent = "Naturally integrating keywords and rephrasing experience...";
  updateProgress(2);
  
  try {
    const res = await fetch(`${API_URL}/curation/confirm/${jobId}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (res.ok) {
      startPolling();
    } else {
      alert('Failed to confirm curation');
      showDashboard();
    }
  } catch (e) {
    console.error(e);
    showDashboard();
  }
}

function startPolling() {
  els.dashboardSection.classList.add('hidden');
  els.processingSection.classList.remove('hidden');
  updateProgress(0);
  
  pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`${API_URL}/curation/status/${currentJobId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      
      els.processingStatus.textContent = `Status: ${data.status}`;
      
      // Simulate progress visually since backend runs synchronously in background
      updateProgress(data.status === 'completed' ? 4 : 2);

      if (data.status === 'completed') {
        clearInterval(pollInterval);
        showResults(data);
      } else if (data.status === 'failed') {
        clearInterval(pollInterval);
        alert('Curation failed. Check console.');
        console.log(data);
        showDashboard();
      }
    } catch (e) {
      console.error(e);
    }
  }, 2000);
}

function updateProgress(stepIndex) {
  els.steps.forEach((s, idx) => {
    if (idx < stepIndex) {
      s.className = 'step completed';
    } else if (idx === stepIndex) {
      s.className = 'step active';
    } else {
      s.className = 'step';
    }
  });
}

function showResults(data) {
  console.log('--- SHOWING RESULTS ---', data);
  els.dashboardSection.classList.add('hidden');
  els.processingSection.classList.add('hidden');
  els.resultsSection.classList.remove('hidden');
  
  const score = data.score || data.final_score || 0;
  els.finalScore.textContent = score;
  
  const scoreCircle = document.querySelector('.score-circle');
  if (scoreCircle) {
    if (score < 40) scoreCircle.style.borderColor = 'var(--error)';
    else if (score < 80) scoreCircle.style.borderColor = 'orange';
    else scoreCircle.style.borderColor = 'var(--success)';
  }

  // Populate side-by-side previews
  if (els.jobInfoPreview) els.jobInfoPreview.textContent = data.job_description || "No job description available.";
  if (els.resumePreview) {
    if (data.curated_resume) {
      els.resumePreview.textContent = formatResumeText(data.curated_resume);
    } else {
      els.resumePreview.textContent = "Processing details...";
    }
  }
  // Show dynamic feedback from AI
  const improvements = data.improvements || [];
  if (improvements.length > 0) {
    els.scoreFeedback.textContent = score < 30 ? "AI identified a critical career mismatch." : "AI curated your resume with the following improvements:";
    els.improvementList.innerHTML = improvements.map(i => `<li>${i}</li>`).join('');
  } else {
    els.scoreFeedback.textContent = "AI successfully tailored your resume for this specific role.";
    els.improvementList.innerHTML = "<li>General optimizations applied for ATS matching.</li>";
  }
  
  // Insights Section update
  if (els.insightsSection) {
    els.insightsSection.style.display = 'block';
    
    if (els.initialScore) els.initialScore.textContent = `${data.initial_score || 0}%`;
    if (els.finalScoreDisplay) els.finalScoreDisplay.textContent = `${score}%`;
    if (els.durationDisplay) els.durationDisplay.textContent = `${data.time_taken || 0}s`;
    
    // Cost calculation (approximate for Gemini Flash)
    const tokens = data.token_usage || { input: 0, output: 0 };
    const inCost = (tokens.input / 1000000) * 0.075;
    const outCost = (tokens.output / 1000000) * 0.30;
    const totalCost = (inCost + outCost).toFixed(4);
    
    if (els.tokenUsage) {
      els.tokenUsage.innerHTML = `
        <span>In: ${tokens.input} | Out: ${tokens.output}</span>
        <span class="cost-tag">$${totalCost} USD</span>
      `;
    }
    if (els.improvementList) {
      els.improvementList.innerHTML = (data.improvements || []).map(i => `<li>${i}</li>`).join('');
    }
  }

  els.downloadPdfBtn.onclick = () => downloadFile(data.id, 'pdf');
  els.viewPdfBtn.onclick = () => viewFile(data.id, 'pdf');
  els.downloadDocxBtn.onclick = () => downloadFile(data.id, 'docx');
  els.downloadJsonBtn.onclick = () => {
    const blob = new Blob([JSON.stringify(data.curated_resume, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `curated_resume_${data.id}.json`;
    a.click();
  };
}

function formatResumeText(resume) {
  let text = `SUMMARY\n${resume.summary}\n\n`;
  text += `SKILLS\n${resume.skills.join(', ')}\n\n`;
  text += `EXPERIENCE\n`;
  resume.experience.forEach(exp => {
    text += `\n${exp.role} at ${exp.company} (${exp.duration})\n`;
    text += `${exp.description}\n`;
    exp.bullets.forEach(b => { text += `• ${b}\n`; });
  });
  return text;
}

if (els.backBtn) els.backBtn.addEventListener('click', showDashboard);

// Auto-populate Company/Role
async function autoExtractInfo() {
  const isUrl = document.querySelector('.tab.active').dataset.tab === 'url';
  const jobInput = isUrl ? els.jobUrl.value : els.jobText.value;
  
  if (!jobInput || jobInput.length < 20) return;
  
  els.companyName.placeholder = "AI is extracting...";
  els.targetRole.placeholder = "AI is extracting...";
  
  try {
    const res = await fetch(`${API_URL}/curation/extract-info`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ job_input: jobInput, is_url: isUrl })
    });
    
    if (res.ok) {
      const data = await res.json();
      if (data.company_name && data.company_name !== 'Unknown') {
        els.companyName.value = data.company_name;
      }
      if (data.target_role && data.target_role !== 'Unknown') {
        els.targetRole.value = data.target_role;
      }
    }
  } catch (e) {
    console.error(e);
  } finally {
    els.companyName.placeholder = "e.g. Google, Amazon";
    els.targetRole.placeholder = "e.g. SDE II, Product Manager";
  }
}

// Event Listeners
console.log('Attaching click listeners...');
if (els.loginBtn) els.loginBtn.addEventListener('click', () => {
  console.log('Login button clicked!');
  handleAuth('login');
});
if (els.registerBtn) els.registerBtn.addEventListener('click', () => {
  console.log('Register button clicked!');
  handleAuth('register');
});
if (els.logoutBtn) els.logoutBtn.addEventListener('click', logout);
if (els.jobUrl) els.jobUrl.addEventListener('blur', autoExtractInfo);
if (els.jobText) els.jobText.addEventListener('blur', autoExtractInfo);

// Run
console.log('Initializing app...');
init();
