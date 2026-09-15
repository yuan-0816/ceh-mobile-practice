const DATA_URLS = [
  'data/source-questions/ceh13-01.json',
  'data/source-questions/ceh13-02.json',
  'data/source-questions/ceh13-03.json',
  'data/source-questions/ECCouncil-312-50v13-2026.json',
];
const LETTERS = ['A', 'B', 'C', 'D'];
const LAST_QUESTION_KEY = 'ceh-last-question';
const SOURCE_LABELS = {
  'ceh13-01.pdf': 'CEH 13-01',
  'ceh13-02.pdf': 'CEH 13-02',
  'ceh13-03.pdf': 'CEH 13-03',
  'ECCouncil-312-50v13-2026.pdf': 'ECCouncil 2026',
};

let questions = [];
let sourceGroups = [];
let currentIndex = 0;
let answerVisible = false;
let darkMode = localStorage.getItem('ceh-theme') === 'dark';

function rememberQuestion(question) {
  localStorage.setItem(LAST_QUESTION_KEY, String(question.id));
}

function rememberCurrentQuestion() {
  if (questions.length) rememberQuestion(questions[currentIndex]);
}

function applyTheme() {
  document.documentElement.dataset.theme = darkMode ? 'dark' : 'light';
  document.querySelector('meta[name="theme-color"]')?.setAttribute(
    'content',
    darkMode ? '#101820' : '#edf0e9',
  );
}

function escapeHtml(value = '') {
  return value.replace(/[&<>"']/g, character => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[character]);
}

function renderQuestion() {
  const question = questions[currentIndex];
  const answerIndex = question.correctIndex;
  const progress = ((currentIndex + 1) / questions.length) * 100;
  const sourceOptions = sourceGroups.map(group => `
    <option value="${escapeHtml(group.source)}" ${group.source === question.source ? 'selected' : ''}>
      ${escapeHtml(SOURCE_LABELS[group.source] || group.source)} (${group.count})
    </option>
  `).join('');

  document.querySelector('#app').innerHTML = `
    <header class="site-header">
      <div class="site-header-inner">
        <a class="brand" href="./" aria-label="回到第一題">
          <span class="brand-kicker">CEH v13</span>
          <strong>Exam Reader</strong>
        </a>
        <div class="header-status"><span></span>Source verified</div>
        <button type="button" class="theme-toggle" data-theme-toggle aria-label="切換深色模式" title="切換深色模式">
          <span aria-hidden="true">☾</span>
        </button>
      </div>
    </header>

    <main class="reader-shell">
      <aside class="reader-sidebar">
        <div class="question-index">
          <span>QUESTION</span>
          <strong>${String(currentIndex + 1).padStart(3, '0')}</strong>
          <small>of ${questions.length}</small>
        </div>
        <form class="question-jump" data-question-jump>
          <label for="desktop-question-number">跳至題號</label>
          <div>
            <input id="desktop-question-number" name="questionNumber" type="number" min="1" max="${questions.length}" value="${currentIndex + 1}" inputmode="numeric" />
            <button type="submit" aria-label="跳至指定題號">→</button>
          </div>
        </form>
        <div class="progress-track" aria-label="題庫進度"><span style="width:${progress}%"></span></div>
        <dl class="source-details">
          <div><dt>TOPIC</dt><dd>${escapeHtml(question.topic || 'General CEH')}</dd></div>
          <div>
            <dt>SOURCE</dt>
            <dd>
              <select class="source-select" data-source-select aria-label="切換題目來源">${sourceOptions}</select>
              <span class="source-question-number">Question #${question.sourceQuestionId}</span>
            </dd>
          </div>
        </dl>
      </aside>

      <article class="question-page">
        <div class="mobile-meta">
          <span>Question ${currentIndex + 1} / ${questions.length}</span>
          <span>${escapeHtml(question.topic || 'General CEH')}</span>
        </div>
        <form class="question-jump mobile-question-jump" data-question-jump>
          <label for="mobile-question-number">跳至題號</label>
          <div>
            <input id="mobile-question-number" name="questionNumber" type="number" min="1" max="${questions.length}" value="${currentIndex + 1}" inputmode="numeric" />
            <button type="submit" aria-label="跳至指定題號">→</button>
          </div>
        </form>
        <div class="mobile-source">
          <label for="mobile-source-select">題目來源</label>
          <select id="mobile-source-select" class="source-select" data-source-select>${sourceOptions}</select>
        </div>

        <h1 id="question-title" tabindex="-1">${escapeHtml(question.question)}</h1>

        <ol class="options" aria-label="選項">
          ${question.options.map((option, index) => `
            <li class="option ${answerVisible && index === answerIndex ? 'is-answer' : ''}">
              <span class="option-letter">${LETTERS[index]}</span>
              <span class="option-text">${escapeHtml(option)}</span>
              ${answerVisible && index === answerIndex ? '<span class="answer-check" aria-label="正確答案">✓</span>' : ''}
            </li>
          `).join('')}
        </ol>

        <nav class="desktop-nav" aria-label="題目導覽">
          <button type="button" data-direction="previous" ${currentIndex === 0 ? 'disabled' : ''}>← 上一題</button>
          <button type="button" class="next" data-direction="next" ${currentIndex === questions.length - 1 ? 'disabled' : ''}>下一題 →</button>
          <button type="button" class="answer-toggle" data-answer-toggle aria-expanded="${answerVisible}">
            ${answerVisible ? '隱藏答案' : '顯示答案'}
          </button>
        </nav>

      </article>

      <nav class="mobile-nav" aria-label="題目導覽">
        <button type="button" data-direction="previous" ${currentIndex === 0 ? 'disabled' : ''}>
          <span aria-hidden="true">←</span> 上一題
        </button>
        <button type="button" class="next" data-direction="next" ${currentIndex === questions.length - 1 ? 'disabled' : ''}>
          下一題 <span aria-hidden="true">→</span>
        </button>
        <button type="button" class="answer-toggle" data-answer-toggle aria-expanded="${answerVisible}">
          ${answerVisible ? '隱藏答案' : '顯示答案'}
        </button>
      </nav>
    </main>
  `;

  document.querySelectorAll('[data-direction]').forEach(button => {
    button.addEventListener('click', () => moveQuestion(button.dataset.direction));
  });
  document.querySelectorAll('[data-answer-toggle]').forEach(button => {
    button.addEventListener('click', () => {
      answerVisible = !answerVisible;
      renderQuestion();
    });
  });
  document.querySelector('[data-theme-toggle]').addEventListener('click', () => {
    darkMode = !darkMode;
    localStorage.setItem('ceh-theme', darkMode ? 'dark' : 'light');
    applyTheme();
    renderQuestion();
  });
  document.querySelectorAll('[data-question-jump]').forEach(form => {
    form.addEventListener('submit', event => {
      event.preventDefault();
      jumpToQuestion(form.elements.questionNumber.value);
    });
  });
  document.querySelectorAll('[data-source-select]').forEach(select => {
    select.addEventListener('change', () => moveToSource(select.value));
  });
}

function jumpToQuestion(value) {
  const questionNumber = Number(value);
  if (!Number.isInteger(questionNumber) || questionNumber < 1 || questionNumber > questions.length) return;
  if (questionNumber - 1 === currentIndex) return;

  currentIndex = questionNumber - 1;
  answerVisible = false;
  rememberQuestion(questions[currentIndex]);
  const url = new URL(window.location.href);
  url.searchParams.set('q', questions[currentIndex].id);
  history.replaceState(null, '', url);
  renderQuestion();
  window.scrollTo({ top: 0, behavior: 'smooth' });
  document.querySelector('#question-title').focus({ preventScroll: true });
}

function moveQuestion(direction) {
  if (!questions.length) return;
  const offset = direction === 'next' ? 1 : -1;
  const nextIndex = Math.min(questions.length - 1, Math.max(0, currentIndex + offset));
  if (nextIndex === currentIndex) return;

  currentIndex = nextIndex;
  answerVisible = false;
  const question = questions[currentIndex];
  rememberQuestion(question);
  const url = new URL(window.location.href);
  url.searchParams.set('q', question.id);
  history.replaceState(null, '', url);
  renderQuestion();
  window.scrollTo({ top: 0, behavior: 'smooth' });
  document.querySelector('#question-title').focus({ preventScroll: true });
}

function moveToSource(source) {
  const nextIndex = questions.findIndex(question => question.source === source);
  if (nextIndex < 0) return;
  currentIndex = nextIndex;
  answerVisible = false;
  rememberQuestion(questions[currentIndex]);
  const url = new URL(window.location.href);
  url.searchParams.set('q', questions[currentIndex].id);
  history.replaceState(null, '', url);
  renderQuestion();
  window.scrollTo({ top: 0, behavior: 'smooth' });
  document.querySelector('#question-title').focus({ preventScroll: true });
}

function renderError() {
  document.querySelector('#app').innerHTML = `
    <main class="state-message">
      <strong>題庫載入失敗</strong>
      <p>請確認你是透過本機 HTTP server 開啟網站，再重新整理頁面。</p>
    </main>
  `;
}

async function boot() {
  try {
    const responses = await Promise.all(DATA_URLS.map(url => fetch(url)));
    const failedResponse = responses.find(response => !response.ok);
    if (failedResponse) throw new Error(`HTTP ${failedResponse.status}`);
    const questionBanks = await Promise.all(responses.map(response => response.json()));
    sourceGroups = questionBanks.map(bank => ({
      source: bank[0].source,
      count: bank.length,
    }));
    questions = questionBanks.flat().sort((a, b) => a.id - b.id);
    if (!questions.length) throw new Error('Empty question bank');

    const requestedQuestion = Number(new URLSearchParams(location.search).get('q'));
    const savedQuestion = Number(localStorage.getItem(LAST_QUESTION_KEY));
    const questionToRestore = requestedQuestion || savedQuestion;
    const requestedIndex = questions.findIndex(question => question.id === questionToRestore);
    currentIndex = requestedIndex >= 0 ? requestedIndex : 0;
    rememberQuestion(questions[currentIndex]);
    renderQuestion();
  } catch (error) {
    console.error(error);
    renderError();
  }

  if ('serviceWorker' in navigator) {
    const localHosts = new Set(['localhost', '127.0.0.1', '[::1]']);
    if (localHosts.has(location.hostname)) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map(registration => registration.unregister()));
      const keys = await caches.keys();
      await Promise.all(keys.map(key => caches.delete(key)));
    } else {
      navigator.serviceWorker.register('sw.js').catch(() => {});
    }
  }
}

applyTheme();

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') rememberCurrentQuestion();
});
window.addEventListener('pagehide', rememberCurrentQuestion);

document.addEventListener('keydown', event => {
  const target = event.target;
  const isFormControl = target instanceof HTMLElement && (
    ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'A'].includes(target.tagName)
    || target.isContentEditable
  );
  if (isFormControl || event.repeat) return;

  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault();
    moveQuestion(event.key === 'ArrowLeft' ? 'previous' : 'next');
  }
  if (event.code === 'Space') {
    event.preventDefault();
    answerVisible = !answerVisible;
    renderQuestion();
  }
});

boot();
