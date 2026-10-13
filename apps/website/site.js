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

function initCopy(button, clipboard) {
  button.addEventListener('click', async () => {
    const label = button.textContent;
    try { await clipboard.writeText(button.dataset.copy); button.textContent = 'Copied'; }
    catch { button.textContent = 'Select and copy'; }
    setTimeout(() => { button.textContent = label; }, 1600);
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
  document.querySelectorAll('[data-copy]').forEach(b => clipboard ? initCopy(b, clipboard) : b.remove());
  document.querySelectorAll('[data-replay]').forEach(r => { r.classList.add('playing'); initReplay(r); });
}

