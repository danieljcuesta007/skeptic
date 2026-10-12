import contextlib
import io
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import open_sessions as live
import switcher as s
import test_sessions as fixture

class CandidateIdentificationTests(unittest.TestCase):
    setUp=fixture.SessionTests.setUp
    tearDown=fixture.SessionTests.tearDown
    rows=fixture.SessionTests.rows
    write_session=fixture.SessionTests.write_session
    approved=fixture.SessionTests.approved
    discover=fixture.SessionTests.discover
    snapshot=fixture.SessionTests.snapshot
    def tabs(self, sid=fixture.ID):
        candidate=dict(pid=23,id=sid,cwd=self.origin,name='native hint',busy=False)
        return [dict(window=17,tab=1,tty='/dev/ttys003',busy=True,pids=[23],process='Claude',candidates=[candidate])]
    def identify(self, tabs=None):
        return self.approved(lambda:live.identify_candidates(tabs or self.tabs(),self.adapter,self.access,self.origin))
    def test_offline_recognizable_context_before_association(self):
        before=self.file.read_bytes()
        with patch.object(live,'command',side_effect=AssertionError('No OS calls for transcript hints')),patch.object(s,'providers',side_effect=AssertionError('No online provider')):
            profiles=self.identify()
        profile=profiles[fixture.ID]
        self.assertEqual(profile['session']['title'],'Email contact with Boris')
        self.assertEqual(profile['request'],'Continue the reply, without sending.')
        self.assertNotIn('records',profile['receipt'])
        tab=self.tabs()[0]; label=live.candidate_label(tab,tab['candidates'][0],profiles)
        self.assertTrue(label.picker_title.startswith('Email contact with Boris | Window 17'))
        self.assertIn('UNCONFIRMED',label.picker_title)
        self.assertNotIn(self.origin,label.picker_title);self.assertNotIn(fixture.ID[:8],label.picker_title)
        self.assertEqual(str(label),label.picker_title)
        self.assertIn(self.repo.name,str(label.picker_details));self.assertIn(fixture.ID,str(label.picker_details))
        self.assertIn('Continue the reply',str(label.picker_details));self.assertNotIn('RAW_TOOL_SECRET',str(profiles))
        self.assertEqual(self.file.read_bytes(),before)
    def test_extraction_denial_keeps_title_but_no_request_read(self):
        self.access.ask=lambda prompt:'no' if 'Type approve' in prompt and self.access.data['grants'] else 'approve'
        with patch('sessions.read_chunks',wraps=__import__('sessions').read_chunks) as chunks:
            profiles=self.identify()
        self.assertEqual(chunks.call_count,1) # only consented discovery head/tail, no snapshot body read
        self.assertEqual(profiles[fixture.ID]['session']['title'],'Email contact with Boris')
        self.assertIsNone(profiles[fixture.ID]['request'])
    def test_metadata_denial_reads_no_transcript(self):
        self.access.ask=lambda _:'no'
        with patch('sessions.read_chunks',side_effect=AssertionError('Denied scope read')):
            profiles=self.identify()
        self.assertIsNone(profiles[fixture.ID]['session']);self.assertIsNone(profiles[fixture.ID]['request'])
    def test_only_exact_candidates_read_and_duplicate_uuid_reuses_approvals(self):
        other=self.write_session(self.origin,self.rows(title='UNSELECTED_PRIVATE'),fixture.OTHER)
        tabs=self.tabs()*2
        profiles=self.identify(tabs)
        self.assertEqual(list(profiles),[fixture.ID]);self.assertNotIn('UNSELECTED_PRIVATE',str(profiles))
        self.assertEqual(len([key for key in self.access.data['grants'] if key.startswith('transcript:')]),1)
        self.assertNotIn(str(other),str(self.access.data['grants']))
    def test_untitled_and_similar_titles_retain_uuid_window_identity(self):
        self.file=self.write_session(self.origin,self.rows(title='Untitled session'))
        self.write_session(self.origin,self.rows(title='Untitled session'),fixture.OTHER)
        tabs=self.tabs()+self.tabs(fixture.OTHER);tabs[1]['window']=18
        profiles=self.identify(tabs)
        labels=[live.candidate_label(tab,tab['candidates'][0],profiles) for tab in tabs]
        self.assertNotEqual(labels[0].picker_title,labels[1].picker_title)
        self.assertIn('Continue the reply',str(labels[0].picker_details))
    def test_context_visible_in_picker_then_safe_uuid_cancellation(self):
        answers=iter(['discover','identify','cancel'])
        captured=[]
        def picker(title,options):
            captured.extend(options)
            self.assertIn('Email contact with Boris',options[0].picker_title)
            self.assertIn('CANDIDATE ONLY',str(options[0].picker_details))
            self.assertIn('Continue the reply',str(options[0].picker_details))
            return 0
        with patch('session_review.continue_selected',side_effect=AssertionError('Canceled association continued')):
            with self.assertRaises(s.host.Denied):
                self.approved(lambda:live.run(SimpleNamespace(continue_open=True),self.state,self.adapter,self.access,self.origin,
                    picker=picker,ask=lambda _:next(answers),collector=self.tabs))
        self.assertTrue(captured)
    def test_appended_candidate_request_is_withheld(self):
        original=self.adapter.snapshot
        def append(access,item,*args,**kwargs):
            result=original(access,item,*args,**kwargs)
            with self.file.open('a') as out:out.write('\n')
            return result
        with patch.object(self.adapter,'snapshot',side_effect=append):profiles=self.identify()
        self.assertIsNone(profiles[fixture.ID]['request'])
        self.assertIn('changed',profiles[fixture.ID]['availability'])

    def test_independent_transcript_keeps_association_unknown_and_existing_continuation(self):
        answers=iter(['discover','identify','transcript'])
        args=SimpleNamespace(continue_open=True,open_source_check=lambda:None,conversation_only=False,repo=[])
        rows=self.tabs();rows[0]['candidates'][0]['busy']=True
        # An uncertain window is not asserted to be the selected transcript's source.
        with patch('session_review.continue_selected',return_value=0) as continuation:
            self.approved(lambda:live.run(args,self.state,self.adapter,self.access,self.origin,
                picker=lambda *_:0,ask=lambda _:next(answers),collector=lambda:rows))
        self.assertIsNone(args.open_source_check)
        self.assertIn('UNCONFIRMED',args.session_association)
        self.assertIn('UNKNOWN',args.session_association)
        self.assertEqual(continuation.call_args.args[4]['id'],fixture.ID)
        import session_review
        snapshot=self.snapshot()
        report=session_review.inventory(snapshot)
        evidence=session_review.task_evidence(args,report,report['tasks'][0])
        self.assertIn(args.session_association,evidence['document']['text'])

    def test_independent_transcript_does_not_bypass_changed_receipt(self):
        def ask(prompt):
            if 'Type discover' in prompt:return 'discover'
            if 'Type identify' in prompt:return 'identify'
            with self.file.open('a') as out:out.write('\n')
            return 'transcript'
        with patch('session_review.continue_selected',side_effect=AssertionError('Changed source continued')):
            with self.assertRaisesRegex(s.host.Denied,'changed since identification'):
                self.approved(lambda:live.run(SimpleNamespace(continue_open=True),self.state,self.adapter,self.access,self.origin,
                    picker=lambda *_:0,ask=ask,collector=self.tabs))

if __name__=='__main__':unittest.main()
