import json
import unittest
from unittest.mock import Mock, patch
import open_sessions as live
import switcher
ROW=dict(window=12,tab=2,tty='/dev/ttys003',busy=True)
SID='11111111-2222-3333-4444-555555555555'
# One live process observed two ways: ps renders local time, Claude's native
# record stores procStart in UTC. They must normalize to the SAME epoch or a
# single running Claude is treated as two different processes and window
# association silently degrades to UNCONFIRMED.
PS_LOCAL='Tue Oct  6 14:14:54 2026'
PROC_UTC='Tue Oct  6 18:14:54 2026'
class OpenTests(unittest.TestCase):
    def test_metadata_only(self):
        calls=[]
        def execute(argv):
            calls.append(argv)
            return json.dumps([ROW]) if argv[0].endswith('osascript') else '23 /usr/local/bin/claude S\n24 /bin/zsh S\n'
        rows=live.collect(execute,'darwin',records=lambda _:None)
        self.assertEqual(rows[0]['pids'],[23]); self.assertEqual(rows[0]['identity'],'unmatched')
        self.assertEqual(calls[1],['/bin/ps','-t','ttys003','-o','pid=,comm=,stat='])
        for forbidden in ('contents()', 'history()', 'doShellScript', 'activate(', 'environment', 'args='):
            self.assertNotIn(forbidden,live.SCRIPT)
    def test_process_denial_unknown(self):
        def execute(argv):
            if argv[0].endswith('osascript'): return json.dumps([ROW])
            raise PermissionError()
        self.assertIn('unknown',live.collect(execute,'darwin',records=lambda _:None)[0]['process'])
    def test_invalid_tty_no_ps(self):
        execute=Mock(return_value=json.dumps([dict(ROW,tty='evil;tty')]))
        with self.assertRaises(ValueError): live.collect(execute,'darwin',records=lambda _:None)
        self.assertEqual(execute.call_count,1)
    def test_non_mac_no_execution(self):
        execute=Mock()
        with self.assertRaises(ValueError): live.collect(execute,'linux')
        execute.assert_not_called()
    def test_consent_denial_no_collection(self):
        collector=Mock()
        with self.assertRaises(switcher.host.Denied):
            live.run(None,None,None,None,None,ask=lambda _:'no',collector=collector)
        collector.assert_not_called()
    def test_manual_exact_uuid_reuses_review(self):
        answers=iter(['discover',SID,'confirm']); adapter=Mock()
        adapter.discover.return_value=[{'id':SID}]
        with patch('session_review.run',return_value=0) as review:
            self.assertEqual(live.run(None,None,adapter,None,'/project',picker=lambda *_:0,
                ask=lambda _:next(answers),collector=lambda:[dict(ROW,process='unknown')]),0)
        adapter.discover.assert_called_once_with(None,'/project',True,SID,None)
        self.assertEqual(review.call_args.kwargs['chosen'],[{'id':SID}])
    def test_disappeared_tab_no_transcript(self):
        answers=iter(['discover',SID,'confirm']); adapter=Mock()
        collector=Mock(side_effect=[[dict(ROW,process='unknown')],[]])
        with self.assertRaises(switcher.host.Denied):
            live.run(None,None,adapter,None,None,picker=lambda *_:0,ask=lambda _:next(answers),collector=collector)
        adapter.discover.assert_not_called()
    def test_automation_denied_no_history(self):
        adapter=Mock()
        with self.assertRaises(switcher.host.Denied):
            live.run(None,None,adapter,None,None,ask=lambda _:'discover',collector=Mock(side_effect=PermissionError()))
        adapter.discover.assert_not_called()
    def test_real_command_decline_never_invokes_inventory(self):
        import subprocess
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory(dir="/private/tmp") as directory:
            result=subprocess.run(['python3','-B',str(Path(__file__).with_name('switcher.py')),
                'sessions','open','--project',directory,'--state-dir',directory,'--session-root',directory],
                input='no\n',capture_output=True,text=True,timeout=10)
            self.assertIn('One-time metadata access',result.stdout)
            self.assertIn('declined',result.stdout+result.stderr)
            self.assertNotIn('Unmatched tabs below',result.stdout)
    def test_utc_and_local_birth_normalize_to_same_epoch(self):
        # The regression this guards: raw strings 'Tue Oct  6 14:14:54 2026'
        # (ps, local EDT) and 'Tue Oct  6 18:14:54 2026' (record, UTC) describe
        # the SAME instant 4h apart. Comparing the raw strings split one process
        # in two and silently broke window association. Parsed each in its real
        # zone, they must resolve to one epoch.
        self.assertEqual(live.normalize_birth(PS_LOCAL, source='ps'),
                         live.normalize_birth(PROC_UTC, source='record'))
        self.assertEqual(live.normalize_birth(PROC_UTC, source='record'),
                         live.normalize_birth('2026-10-06T18:14:54Z'))
        self.assertIsNone(live.normalize_birth('not a clock'))
        self.assertIsNone(live.normalize_birth(''))
    def test_native_record_exposes_normalized_epoch_hint(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir='/private/tmp') as d:
            (Path(d)/'23.json').write_text(json.dumps(
                {'pid':23,'sessionId':SID,'cwd':'/p','name':'n','procStart':PROC_UTC,'busy':False}))
            rec=live.native_record(23,d)
            self.assertIsNotNone(rec)
            # record's UTC procStart and a live ps-local birth are one instant
            self.assertEqual(rec['epoch_hint'],live.normalize_birth(PS_LOCAL, source='ps'))
            self.assertEqual(rec['epoch_hint'],live.normalize_birth(PROC_UTC, source='record'))
    def test_collect_stores_epoch_identity_not_raw_string(self):
        calls=[]
        def execute(argv):
            calls.append(argv)
            if argv[0].endswith('osascript'): return json.dumps([ROW])
            if '-t' in argv: return '23 /usr/local/bin/claude S\n'
            if 'lstart' in ' '.join(argv): return PS_LOCAL+'\n'
            return ''
        rows=live.collect(execute,'darwin',records=lambda _:None)
        self.assertEqual(rows[0]['process_identity'],{23:live.normalize_birth(PS_LOCAL)})
        # a raw local/UTC string must never be stored as identity
        self.assertNotIn(PS_LOCAL,str(rows[0]['process_identity']))
