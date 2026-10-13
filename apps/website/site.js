// Skeptic site: install tabs, copy buttons and the terminal replay.
// No network, no storage. Everything degrades to readable static content.

function initTabs(root) {
  const tabs = [...root.querySelectorAll('[role="tab"]')];
  const select = tab => {
    for (const t of tabs) {
      const on = t === tab;
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      root.querySelector('#' + t.getAttribute('aria-controls')).hidden = !on;
    }
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => select(tab));
    tab.addEventListener('keydown', e => {
      const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!step) return;
      e.preventDefault();
      const next = tabs[(i + step + tabs.length) % tabs.length];
      select(next); next.focus();
    });
  });
}

// Every click copies the same text, so one success is enough. A failure is shown
// only when no copy has succeeded since that click began and none is still in
// flight; then the command is selected so the visitor can copy it by hand.
// Results are announced once through the page's status line.
function initCopy(button, clipboard, status, select) {
  const label = button.textContent;
  let timer, successes = 0, pending = 0, said = '';
  const show = (text, message) => {
    button.textContent = text;
    said = said === message ? message + '\u00a0' : message; // a changed string is re-announced
    status.textContent = said;
    clearTimeout(timer);
    timer = setTimeout(() => { button.textContent = label; }, 1600);
  };
  button.addEventListener('click', async () => {
    const before = successes;
    pending++;
    try {
      await clipboard.writeText(button.dataset.copy);
      successes++;
      show('Copied', 'Copied to clipboard');
    } catch {
      if (successes > before || pending > 1) return; // another copy landed, or still may
      const code = button.previousElementSibling;
      if (code && code.tagName === 'PRE') select(code);
      show('Copy failed', 'Copy failed. The command is selected so you can copy it yourself.');
    } finally { pending--; }
  });
}

function initReplay(root) {
  const button = root.querySelector('[data-replay-button]');
  if (!button) return;
  button.addEventListener('click', () => {
    root.classList.remove('playing');
    void root.offsetWidth; // restart the CSS animation
    root.classList.add('playing');
  });
}

if (typeof document !== 'undefined' && document.querySelectorAll) {
  document.querySelectorAll('[data-tabs]').forEach(initTabs);
  const clipboard = typeof navigator !== 'undefined' && navigator.clipboard;
  const status = document.querySelector('[data-copy-status]');
  const select = el => { const sel = typeof getSelection === 'function' && getSelection(); if (sel) sel.selectAllChildren(el); };
  document.querySelectorAll('[data-copy]').forEach(b => clipboard && status ? initCopy(b, clipboard, status, select) : b.remove());
  document.querySelectorAll('[data-replay]').forEach(r => { r.classList.add('playing'); initReplay(r); });
}

