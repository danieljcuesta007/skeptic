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
// flight; then the command is selected if possible so the visitor can copy it manually.
// Results are announced once through the page's status line.
const copyTurn = { n: 0 }; // shared by every copy button: who spoke last
function initCopy(button, clipboard, status, select) {
  const label = button.textContent;
  let timer, successes = 0, pending = 0;
  const show = (text, message) => {
    button.textContent = text;
    // One status line for every button; a changed string is re-announced.
    status.textContent = status.textContent === message ? message + '\u00a0' : message; // a repeat is re-announced
    const turn = ++copyTurn.n;
    clearTimeout(timer);
    timer = setTimeout(() => {
      button.textContent = label;
      if (copyTurn.n === turn) status.textContent = ''; // nobody has spoken since: clear our own message only
    }, 1600);
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
      const selected = code && code.tagName === 'PRE' && select(code);
      show('Copy failed', selected ? 'Copy failed. The command is selected so you can copy it yourself.' : 'Copy failed. Please copy the command manually.');
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
  const select = el => { try { const sel = getSelection(); sel.selectAllChildren(el); return true; } catch { return false; } };
  const silent = { textContent: '' }; // no status line: no announcement, buttons still work
  document.querySelectorAll('[data-copy]').forEach(b => clipboard ? initCopy(b, clipboard, status || silent, select) : b.remove());
  document.querySelectorAll('[data-replay]').forEach(r => { r.classList.add('playing'); initReplay(r); });
}

