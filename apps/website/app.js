const policies = {
  FULL_BRAIN: ['Full brain', 'Search eligible ordinary notes across your brain. Retrieve only what is relevant.'],
  PROJECT_SCOPED: ['Project scoped', 'Shared rules and the selected project context. Other areas remain outside this scope.'],
  ASK_TO_EXPAND: ['Ask to expand', 'Start with shared rules and project status. Request approval before expanding access.']
};
const policy = document.querySelector('#policy');
policy.addEventListener('change', () => { document.querySelector('#policy-help').textContent = policies[policy.value][1]; });
let receipts = 1;
document.querySelector('#demo-form').addEventListener('submit', event => {
  event.preventDefault();
  const model = document.querySelector('#model').value;
  const writing = document.querySelector('#task').value === 'writing';
  const project = writing ? 'essay' : 'atlas';
  const paths = [`projects / ${project} / status.md`];
  if (policy.value === 'FULL_BRAIN') paths.push(writing ? 'notes / essay-craft.md' : 'notes / planning.md');
  if (policy.value === 'PROJECT_SCOPED') paths.push(`projects / ${project} / decisions.md`);
  document.querySelector('#receipt-title').textContent = `Ready for ${model}.`;
  document.querySelector('#receipt-summary').textContent = `${writing ? 'Essay outline' : 'Project planning'} · ${policies[policy.value][0]}`;
  document.querySelector('#receipt-context').replaceChildren(...paths.map((path, index) => { const span = document.createElement('span'); span.textContent = path; if (index) span.prepend(document.createElement('br')); return span; }));
  document.querySelector('#receipt-handoff').textContent = `projects / ${project} / status.md#handoff`;
  document.querySelector('#receipt-count').textContent = String(++receipts).padStart(3, '0');
  document.querySelector('#receipt-result').textContent = policy.value === 'ASK_TO_EXPAND' ? 'Expansion requires approval · no additional access granted' : 'Synthetic references · freshness not verified';
  document.querySelector('#capability').textContent = model === 'Local model' ? 'Local agent capabilities vary. File and tool access must be verified.' : 'Concept only: no provider is connected.';
});
document.querySelector('#download').addEventListener('click', () => {
  const sample = '# Example project\n\n## Current state\nSynthetic checkpoint — replace with verified outcomes.\n\n## Handoff\n_No active handoff._\n\n## Next actions\n- Review current files and instructions before acting.\n\n## Limitations\nNo edit, publish or external-action permission is implied.\n';
  const url = URL.createObjectURL(new Blob([sample], { type: 'text/markdown' }));
  const link = document.createElement('a'); link.href = url; link.download = 'skeptic-sample-checkpoint.md'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  document.querySelector('#download-status').textContent = 'Sample download requested. It contains synthetic Markdown only.';
});
if ('IntersectionObserver' in window) {
  const links = [...document.querySelectorAll('nav a')];
  const observer = new IntersectionObserver(entries => { for (const entry of entries) if (entry.isIntersecting) { for (const link of links) { const active = link.hash === `#${entry.target.id}`; link.classList.toggle('active', active); if (active) link.setAttribute('aria-current', 'location'); else link.removeAttribute('aria-current'); } } }, { rootMargin: '-10% 0px -60% 0px' });
  for (const link of links) { const section = document.querySelector(link.hash); if (section) observer.observe(section); }
}
