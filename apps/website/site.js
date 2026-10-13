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

// Every click copies the same text, so a failure only matters if no copy has
// succeeded since that click began. On a real failure the command is selected,
// so Command-C still works. Results are announced once through the status line.
function initCopy(button, clipboard, status, select, now = Date.now) {
  const label = button.textContent;
  let timer, lastSuccess = -Infinity;
  const show = (text, said) => {
    button.textContent = text;
    if (status) status.textContent = said;
    clearTimeout(timer);
    timer = setTimeout(() => { button.textContent = label; }, 1600);
  };
  button.addEventListener('click', async () => {
    const started = now();
    try {
      await clipboard.writeText(button.dataset.copy);
      lastSuccess = now();
      show('Copied', 'Copied to clipboard');
    } catch {
      if (lastSuccess >= started) return; // another click already put it on the clipboard
      const code = button.previousElementSibling;
      if (code && select) select(code);
      show('Press \u2318C', 'Copy failed. The command is selected; press Command C.');
    }
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
  const status = document.querySelector && document.querySelector('[data-copy-status]');
  const select = el => { const sel = typeof getSelection === 'function' && getSelection(); if (sel) sel.selectAllChildren(el); };
  document.querySelectorAll('[data-copy]').forEach(b => clipboard ? initCopy(b, clipboard, status, select) : b.remove());
  document.querySelectorAll('[data-replay]').forEach(r => { r.classList.add('playing'); initReplay(r); });
}

