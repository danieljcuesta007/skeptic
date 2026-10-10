"""Ephemeral, consent-gated task review. No model calls or project/session writes."""
import hashlib
import json
from pathlib import Path
import re

import sessions as history
import switcher as host

STATUSES = ('completed and verified', 'completion claimed but unverified',
            'unfinished', 'blocked', 'future idea', 'unknown')
MAX_TASKS = 100


def label(record):
    return (record.get('message_id', '?') + ' @ ' + record.get('timestamp', '?') +
            ' (line ' + str(record.get('window_line', '?')) + ')')


REQUEST = re.compile(r"(?i)^(?:(?:please\s+|also\s+|now\s+|instead[, ]+|actually[, ]+)*"
    r"(?:implement|build|fix|add|create|update|write|verify|check|review|investigate|make|record|continue|"
    r"remove|change|keep|use|test|explain|help|show|design|draft|plan|audit|debug|resolve|install|summarize|summarise|compare|find|"
    r"can (?:you|we)|could (?:you|we)|would you|i (?:want|need)|i'd like|let's|"
    r"what|how|why|maybe later|someday)\b)")
SPEC = re.compile(r'(?i)^\s*(?:#{1,6}\s*)?(?:(?:pasted|technical|implementation|component)\s+)?'
    r'(?:specification|spec|requirements|tech stack|dependencies|questions to ask|installation steps|'
    r'implementation steps|reference material|source excerpt|tool output)\b')


def request_surface(text):
    """Separate overt source material from the user's surrounding request.

    This is conservative syntax recognition, not authorship/semantic certainty.
    The full bounded message always remains supporting context in the inventory.
    """
    lines, fence, source = [], None, False
    for line in text.splitlines():
        stripped = line.strip()
        marker = re.match(r'^(`{3,}|~{3,}|"{3}|\x27{3})', stripped)
        if marker:
            token = marker[1][0]
            if fence is None: fence = token
            elif fence == token: fence = None
            continue
        if fence is not None: continue
        if re.match(r'(?i)^<(?:spec|specification|reference|quoted_text|tool_result|tool_output|code)\b', stripped):
            source = True; continue
        if re.match(r'(?i)^</(?:spec|specification|reference|quoted_text|tool_result|tool_output|code)>', stripped):
            source = False; continue
        if (stripped.startswith('>') or line.startswith(('    ', '\t')) or
                re.match(r'^(?:".*"|\x27.*\x27|“.*”)\s*$', stripped)): continue
        if SPEC.match(stripped) or re.match(r'(?i)^(?:here (?:is|are)|below is|pasted)\b.*\b(?:spec|specification|reference|output|code)\b', stripped):
            source = True; continue
        if source: continue
        # Inline quoted examples cannot supply request verbs or split boundaries.
        stripped = re.sub(r'`[^`]*`|"[^"\n]*"|“[^”\n]*”', '[quoted context]', stripped)
        lines.append(stripped)
    return '\n'.join(lines).strip()


def request_parts(text):
    """Only direct requests can become candidates; specification bullets cannot."""
    surface = request_surface(text)
    matches = list(re.finditer(r'(?m)^\s*(?:\d+[.)]|[-*])\s+(\S.*)', surface))
    if matches:
        # Split only a wholly directive list. Mixed requirement/technology lists
        # belong to the enclosing request, even when a step uses an imperative.
        directives = [m[1].strip() for m in matches]
        intro = surface[:matches[0].start()].strip()
        enclosing = any(REQUEST.match(line) and not re.match(r'(?i)^keep\b', line) for line in intro.splitlines())
        independent = bool(re.search(r'(?i)(?:\b(?:separate|independent|two|three)\s+(?:tasks|requests)\b|\b(?:tasks|requests)\s*:)', intro))
        if len(matches) >= 2 and all(REQUEST.match(value) for value in directives) and (not enclosing or independent):
            return directives  # The inventory's global task budget discloses overflow.
        surface = intro
    statements = [part.strip() for part in re.split(r'\n|(?<=[.!?;])\s+', surface) if REQUEST.match(part.strip())]
    return ['\n'.join(statements)] if statements else []


def add_evidence(task, record):
    if len(task['evidence']) < 12: task['evidence'].append(record)
    else:
        task['evidence'][-1] = record
        task['evidence_omitted'] = True


def followup(text):
    text = re.sub(r'(?is)^\s*(?:actually|correction)[,: ]+\s*', '', text)
    return bool(re.match(r"(?is)^\s*(?:(?:for|on) (?:this|that|it)\b|"
        r"(?:make|keep|change|update|fix|adjust|move|resize) (?:it|that|this)\b|use\b.+\binstead\b)", text))


def inventory(snapshot):
    tasks, gaps, current = [], [], []
    if snapshot.get('partial'): gaps.append('Transcript snapshot exceeds 8 MiB; unread middle may contain tasks or resolutions.')
    if snapshot.get('chain_gap'): gaps.append('Missing/uncertain ancestry; historical requests require confirmation.')
    if snapshot.get('malformed_records'): gaps.append('Malformed records were omitted.')
    if snapshot.get('appended_during_read'): gaps.append('Transcript appended during review; refresh before continuation.')
    if snapshot.get('inventory_omitted'): gaps.append('Inventory record/byte budget reached; additional work may be omitted.')
    records = snapshot.get('records', [])
    if any(record.get('excerpt_truncated') for record in records):
        gaps.append('Some message excerpts were clipped; inspect the bounded request/evidence before deciding.')
    # Extraction can recover the same message through historical ancestry; dedupe by
    # provenance/content, preserving distinct blocks in one user message.
    seen = set()
    for record in records:
        role, text = record.get('role', ''), record.get('untrusted_text', '')
        key = (record.get('message_id'), record.get('window_offset'), record.get('window_line'), text)
        if key in seen: continue
        seen.add(key)
        user = role == 'user' or role.startswith('historical-user-request')
        if user:
            surface = request_surface(text)
            parts = request_parts(text)
            # Standalone cancellation/replacement controls attach to the preceding
            # request only as a candidate relation; scope must be reviewed by owner.
            control = re.match(r"(?is)^\s*(?:cancel (?:that|the previous)|forget (?:that|the previous)|never mind|nevermind|instead\b|stop\b)", surface)
            if control and current:
                for task in current:
                    task['relations'].append({'kind': 'possible cancellation/supersession; confirm scope', 'record': record})
                    task['status'] = 'unknown'
                    add_evidence(task, record)
            if not control and current and followup(surface):
                for task in current:
                    add_evidence(task, record)
                    combined = task['context'] + '\nFOLLOW-UP (attributed user evidence):\n' + text
                    task['context'] = history.excerpt(combined, history.SESSION_TEXT_LIMIT)
                    if len(combined.encode()) > history.SESSION_TEXT_LIMIT: task['evidence_omitted'] = True
                    # A correction invalidates prior completion/blocker inference.
                    task['status'] = 'unknown' if (len(current) != 1 or any(snapshot.get(flag) for flag in
                        ('chain_gap', 'partial', 'malformed_records', 'appended_during_read', 'inventory_omitted')) or
                        record.get('excerpt_truncated') or task['origin'].get('excerpt_truncated') or
                        task['origin'].get('role', '').startswith('historical-') or task['relations']) else 'unfinished'
                    if re.search(r'(?i)\b(?:maybe later|someday|defer (?:this|that)|park (?:this|that))\b', surface):
                        if task['status'] != 'unknown': task['status'] = 'future idea'
                continue
            if not parts:
                if current:
                    for task in current:
                        add_evidence(task, record)
                        if record.get('excerpt_truncated'): task['status'] = 'unknown'
                    if surface and not control:
                        note = 'Ambiguous user wording retained as context; additional task scope may be unrecovered.'
                        if note not in gaps: gaps.append(note)
                elif text:
                    note = 'User material without a clear enclosing request retained as context; task scope unknown.'
                    if note not in gaps: gaps.append(note)
                continue
            current = []
            for part in parts:
                if len(tasks) >= MAX_TASKS:
                    if 'Task limit reached; remaining requests omitted.' not in gaps:
                        gaps.append('Task limit reached; remaining requests omitted.')
                    break
                future = re.search(r'(?i)\b(?:someday|future idea|maybe later|backlog|park (?:this|that)|defer (?:this|that))\b', part)
                actionable = re.search(r'(?i)\b(?:implement|build|fix|add|create|update|write|verify|check|review|investigate|make|record|continue|can (?:you|we)|please)\b', part)
                status = 'future idea' if future else ('unfinished' if actionable else 'unknown')
                if (any(snapshot.get(flag) for flag in ('chain_gap', 'partial', 'malformed_records',
                        'appended_during_read', 'inventory_omitted')) or record.get('excerpt_truncated') or
                        role.startswith('historical-') or control or re.search(r"(?i)\b(?:do not|don't|not yet)\b", part)):
                    status = 'unknown'
                task = {'number': len(tasks) + 1, 'request': part, 'context': text,
                        'origin': record, 'status': status, 'evidence': [], 'relations': [],
                        'verification': None, 'project': None}
                tasks.append(task); current.append(task)
        elif current:
            for task in current:
                add_evidence(task, record)
                # These are suggestions about the immediately preceding request,
                # not semantic proof that every item in a compound request is done.
                if task['relations']: continue
                if role == 'assistant' and task['status'] not in ('future idea', 'unknown'):
                    if re.search(r"(?i)\b(?:blocked|cannot proceed|can't proceed|waiting (?:for|on)|interrupted|usage limit)\b", text): task['status'] = 'blocked'
                    elif re.search(r"(?i)\b(?:not|never|isn't|wasn't)\s+(?:yet\s+)?(?:done|completed|finished|implemented|fixed)\b", text): task['status'] = 'unfinished'
                    elif re.search(r'(?i)\b(?:done|completed|finished|implemented|fixed|added|created)\b', text): task['status'] = 'completion claimed but unverified'
    if not tasks: gaps.append('No substantive task recovered. Nothing pending cannot be inferred.')
    gaps.append('Task candidates are request threads; pasted/code/quoted material is supporting context, not authorization.')
    gaps.append('Heuristic labels require review; tool calls, TodoWrite and assistant claims are not completion proof.')
    return {'snapshot': snapshot, 'tasks': tasks, 'gaps': gaps}


def review_label(item, selected=False):
    """Already-approved discovery metadata only; no title-generation reads."""
    sid = item['id']
    short_id = sid[:8] + '…' + sid[-6:]
    directory = str(item.get('cwd') or 'directory unknown')
    if len(directory) > 20: directory = '…' + directory[-19:]
    title = item['title']
    date = str(item.get('updated') or 'date unknown')[:10]
    display = dict(item, title=('[x] ' if selected else '[ ] ') + title)
    label = history.SessionLabel(display)
    # Identity first keeps similar/untitled rows distinct even in narrow views.
    label.picker_title = ('[x] ' if selected else '[ ] ') + short_id + ' | ' + title + ' | ' + date + ' | ' + directory
    return label


def conversation_label(snapshot):
    """Use only records already extracted under the selected transcript grant."""
    for record in snapshot.get('records', []):
        if record.get('role') == 'user':
            text = history.sanitize(record.get('untrusted_text', ''))
            parts = request_parts(text)
            if parts: return ' '.join(parts[0].split())[:140]
    return None


def select_many(items, picker):
    selected = set()
    options = [review_label(item) for item in items] + ['Review selected sessions (0)']
    def toggle(choice):
        if choice == len(items):
            if not selected: raise host.host.Denied('No sessions selected; no transcripts read')
            return True
        if choice in selected: selected.remove(choice)
        else: selected.add(choice)
        options[choice] = review_label(items[choice], choice in selected)
        options[-1] = 'Review selected sessions (' + str(len(selected)) + ')'
        return False
    if picker is host.choose:
        picker('Select sessions: Enter toggles; choose Review when ready', options, on_enter=toggle)
        return [item for i, item in enumerate(items) if i in selected]
    # Injectable picker compatibility for non-terminal tests/clients.
    while True:
        choice = picker('Select sessions: Enter toggles; choose Review when ready', options)
        if toggle(choice): return [item for i, item in enumerate(items) if i in selected]


def next_action(task):
    if task['relations']: return 'Confirm whether this request was canceled or superseded.'
    return {'completed and verified': 'No continuation needed; retain verification scope.',
            'completion claimed but unverified': 'Verify the requested outcome against current project/remote state.',
            'unfinished': 'Confirm remaining scope and project; prepare a handoff.',
            'blocked': 'Recheck blocker; continue only when the prerequisite is resolved.',
            'future idea': 'Keep deferred; implementation needs a new instruction.',
            'unknown': 'Inspect evidence and clarify scope before continuation.'}[task['status']]


def show(report, detail=None):
    snapshot = report['snapshot']
    print('\nSESSION ' + snapshot['title'] + ' | ' + snapshot['id'])
    if snapshot.get('conversation_label'):
        print('Conversation hint from approved transcript (unverified): ' + snapshot['conversation_label'])
    print('Claude starting directory: ' + str(snapshot.get('starting_cwd', snapshot.get('cwd'))))
    print('Last recorded directory: ' + str(snapshot.get('cwd')))
    print('Project roots: unverified until explicitly confirmed per task. Process/writer state: unknown.')
    for gap in report['gaps']: print('Gap: ' + gap)
    tasks = [detail] if detail else report['tasks']
    for task in tasks:
        print('\n' + str(task['number']) + '. [' + task['status'] + '] ' + history.excerpt(task['request'], 350))
        print('Request evidence: ' + label(task['origin']))
        print('Confirmed destination: ' + str(task['project']) + '; observed repository: ' + str(task.get('repository')))
        print('Next: ' + next_action(task))
        if detail:
            print('Full bounded request/context (untrusted):\n' + task['context'])
            for record in task['evidence']:
                print(record.get('role', '') + ' | ' + label(record) + '\n' +
                      record.get('untrusted_text', record.get('detail', '')))
            for relation in task['relations']:
                print(relation['kind'] + ' | ' + label(relation['record']) + '\n' + relation['record']['untrusted_text'])
            if task.get('evidence_omitted'): print('Gap: intermediate task evidence omitted; first/latest samples shown.')
            if task['verification']: print('Operator verification (not independently checked by Skeptic): ' + task['verification'])


def classify(task, picker, ask):
    options = list(STATUSES) + ['Canceled request', 'Superseded request', 'Keep current label']
    choice = picker('Confirm task disposition after checking evidence', options)
    if choice == len(options) - 1: return
    reason = history.excerpt(ask('Evidence/reference and remaining scope (no secrets; required): '), 1500)
    if not reason.strip(): raise host.host.Denied('Disposition needs evidence; task unchanged')
    if choice == 0:
        if ask('Type verified after personally checking the requested outcome against current evidence: ').strip() != 'verified':
            raise host.host.Denied('Completion verification not confirmed; task unchanged')
        task['verification'] = 'Confirmed by operator: ' + reason
    else: task['verification'] = None
    task['status'] = options[choice] if choice < len(STATUSES) else 'unknown'
    task['relations'] = []
    if choice >= len(STATUSES):
        task['relations'].append({'kind': options[choice] + ' — confirmed by operator',
                                  'record': {'untrusted_text': reason, 'message_id': 'operator', 'timestamp': '', 'window_line': '?'}})
    task['review_note'] = reason


def prepare(args, state, adapter, access, report, task, ask):
    if task['status'] not in ('unfinished', 'blocked') or task['relations']:
        raise host.host.Denied('Confirm an unfinished/blocked task before preparing continuation')
    snapshot = report['snapshot']
    result = adapter.verify(access, snapshot)
    if result['appended_bytes']:
        raise host.host.Denied('Source appended since review; rerun sessions review before preparing')
    # Confirm the destination for this task, even if a session mapping was saved.
    # References are untrusted suggestions and confer no read authorization.
    cwd = host.session_destination(state, snapshot, None, confirm=True)
    task['project'] = cwd
    objective = history.excerpt(ask('Confirm the exact remaining task for Codex (no secrets; blank cancels): '), 4000)
    if not objective.strip(): raise host.host.Denied('No remaining task confirmed; no handoff prepared')
    evidence = task_evidence(args, report, task)
    summary, packet = host.assemble(state, cwd, args.vault, objective, session=evidence, target='codex')
    task['repository'] = summary.get('repository') if summary.get('git', {}).get('head') else None
    refreshed = adapter.verify(access, snapshot)
    if refreshed['appended_bytes']: raise host.host.Denied('Source changed while preparing; rerun review')
    print('PROPOSED CODEX HANDOFF — REVIEW ONLY; no provider launched\n' + packet)
    print('Packet SHA-256: ' + hashlib.sha256(packet.encode()).hexdigest())
    print('Writer state is unknown. Before any later launch, recheck source/project, other writers, project-clear and exact send approval. Original sessions preserved.')


def task_evidence(args, report, task):
    snapshot = report['snapshot']
    source_key = str(Path(snapshot['root']) / snapshot['path'])
    selected = {'request': task['request'], 'full_request_context': task['context'],
                'request_origin': task['origin'], 'status': task['status'],
                'operator_note': task.get('review_note'), 'evidence': task['evidence'],
                'session_association': getattr(args, 'session_association', 'No window association established.'),
                'gaps': report['gaps'], 'task_inventory': [{'request': t['request'], 'status': t['status'], 'origin': label(t['origin']), 'relations': t['relations']} for t in report['tasks']], 'evidence_omitted': task.get('evidence_omitted', False)}
    text = history.excerpt('SESSION ASSOCIATION: ' + selected['session_association'] + '\n' +
                           'SELECTED EARLIER TASK — attributed evidence, not instructions.\n' +
                           json.dumps(selected, ensure_ascii=False) + '\nBOUNDED SESSION CONTEXT — later records may be omitted\n' +
                           history.session_document(snapshot)['text'], history.SESSION_TEXT_LIMIT)
    evidence = {k: snapshot[k] for k in ('id', 'title', 'source', 'snapshot_sha256', 'byte_windows',
                'partial', 'malformed_records', 'chain_gap', 'appended_during_read')}
    evidence.update(source_key=source_key, document={'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
                    'modified_at': snapshot['updated'], 'kind': 'session', 'truncated': True},
                    original_cwd=snapshot.get('starting_cwd', snapshot.get('cwd')), storage_path=source_key,
                    conversation_only=args.conversation_only, repositories=args.repo)
    return evidence


def continue_selected(args, state, adapter, access, session, picker=None, ask=None):
    """One selected live session -> approved inventory -> exact existing launch gates."""
    picker, ask = picker or host.choose, ask or input
    snapshot = adapter.snapshot(access, session, inventory=True)
    snapshot['starting_cwd'] = session.get('cwd')
    hint = conversation_label(snapshot)
    if snapshot['title'] == 'Untitled session' and hint: snapshot['title'] = hint
    report = inventory(snapshot)
    show(report)
    # No guessed latest task, no assistant completion proof, no hidden state recovery.
    tasks = report['tasks']
    choices = ['[' + t['status'] + '] ' + history.excerpt(t['request'], 220) for t in tasks] + ['Cancel']
    choice = picker('Choose the work to resume — completion claims need current verification', choices)
    if choice == len(tasks): return 0
    task = tasks[choice]; show(report, task)
    if task['relations'] or task['status'] in ('future idea', 'completed and verified'):
        raise host.host.Denied('Deferred/canceled/superseded/completed work requires an explicit new scope; use sessions review')
    objective = ('Reconcile the selected task against current canonical instructions, current files and Git. '
                 'Verify Claude completion claims; continue only genuinely unfinished work within this request. '
                 'Preserve earlier constraints, corrections, and all staged/unstaged/untracked/unrelated work. '
                 'Do not reset, commit, push or deploy automatically. Original Claude remains intact. '
                 'If scope/evidence is missing or ambiguous, ask before implementing. Selected request: ' + task['request'])
    mode = picker('Continue this selected request in Codex', ['Continue after safety approvals', 'Preview only', 'Cancel'])
    if mode == 2: return 0
    if adapter.verify(access, snapshot)['appended_bytes']:
        raise host.host.Denied('Source appended; refresh before preparing continuation')
    cwd = host.session_destination(state, snapshot, getattr(args, 'cwd', None), confirm=True)
    evidence = task_evidence(args, report, task)
    summary, packet = host.assemble(state, cwd, args.vault, objective, session=evidence, target='codex')
    if adapter.verify(access, snapshot)['appended_bytes']:
        raise host.host.Denied('Source appended while preparing; review again')
    if mode == 1:
        print('PROPOSED CODEX HANDOFF — preview only\n' + packet); return 0
    args.provider = 'codex'
    return host.launch_recovery(args, state, adapter, access, snapshot, cwd, objective, evidence, summary, packet)


def inspect_project(args, state, report, task):
    snapshot = report['snapshot']
    cwd = host.session_destination(state, snapshot, None, confirm=True)
    task['project'] = cwd
    # Reuse the scoped repository/vault consent and safe Git observations. The
    # packet is local evidence only; nothing here claims semantic completion.
    source_key = str(Path(snapshot['root']) / snapshot['path'])
    evidence = {'source_key': source_key, 'document': history.session_document(snapshot),
                'conversation_only': args.conversation_only, 'repositories': args.repo}
    summary, packet = host.assemble(state, cwd, args.vault,
        'Read-only review of this task; verify current evidence without implementing: ' + task['request'],
        session=evidence, target='codex')
    task['repository'] = summary.get('repository') if summary.get('git', {}).get('head') else None
    print('CURRENT APPROVED PROJECT EVIDENCE — completion remains unverified\n' + packet)
    print('Project observation: ' + json.dumps(summary.get('git'), ensure_ascii=False))


def run(args, state, adapter, access, project, picker=None, ask=None, chosen=None):
    picker, ask = picker or host.choose, ask or input
    if chosen is None:
        items = adapter.discover(access, project, args.all_projects, args.session_id, args.title)
        if not items: raise host.host.Denied('No accessible sessions in approved scope')
        if getattr(adapter, 'discovery_truncated', False): print('Gap: only 64 newest candidate files inspected; narrow scope or use --id for older sessions.')
        chosen = select_many(items, picker)
    reports = []
    for session in chosen:
        try:
            snapshot = adapter.snapshot(access, session, inventory=True)
            snapshot['starting_cwd'] = session.get('cwd')
            snapshot['conversation_label'] = conversation_label(snapshot)
            if snapshot['title'] == 'Untitled session' and snapshot['conversation_label']:
                snapshot['title'] = snapshot['conversation_label']
            report = inventory(snapshot); reports.append(report); show(report)
        except (host.host.Denied, OSError, ValueError):
            print('Session ' + session['id'] + ': unknown — extraction declined/unavailable; original untouched.')
    flat = [(report, task) for report in reports for task in report['tasks']]
    while flat:
        options = [report['snapshot']['id'][:8] + '…' + report['snapshot']['id'][-6:] + ' | ' + report['snapshot']['title'] + ' / ' + str(task['number']) + ' [' + task['status'] + '] ' +
                   history.excerpt(task['request'], 180) for report, task in flat] + ['Finish review']
        choice = picker('Inspect a task; review labels before choosing continuation', options)
        if choice == len(flat): break
        report, task = flat[choice]; show(report, task)
        action = picker('Selected task', ['Return to task list', 'Confirm/change disposition',
                                        'Prepare Codex handoff (preview only)',
                                        'Confirm project and inspect approved current evidence'])
        try:
            if action == 1: classify(task, picker, ask)
            elif action == 2: prepare(args, state, adapter, access, report, task, ask)
            elif action == 3: inspect_project(args, state, report, task)
        except (host.host.Denied, OSError, ValueError):
            print('Action refused or source unavailable; review again. No provider launched.')
    for report in reports: show(report)
    print('Review finished. No providers launched or original sessions/project files changed. Task review is in memory only; existing consent/mapping state may be saved.')
    return 0
