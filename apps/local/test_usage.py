import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import usage

class UsageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name); self.fd=os.open(self.home,os.O_RDONLY|os.O_DIRECTORY);self.addCleanup(os.close,self.fd)
        self.u=usage.Usage(self.fd,self.home,clock=lambda:1000)
    def reading(self,model='Hermes / test'):
        return {'provider':'hermes','model':model,'remaining':8,'limit':10,'unit':'USD','resets_at':2000,'observed_at':None}
    def test_connection_revocation_and_poll_budget(self):
        with patch.object(self.u,'local',side_effect=AssertionError('read')):
            self.assertEqual(self.u.request({'op':'read'})['rows'],[])
            self.u.request({'op':'disable'})
        with patch.object(self.u,'local',return_value=[]) as read:
            self.u.request({'op':'enable'});self.u.request({'op':'read'});self.assertEqual(read.call_count,1)
            self.u.request({'op':'disable'});self.u.request({'op':'read'});self.assertEqual(read.call_count,1)
    def test_persistence_multiple_models_and_remove_one(self):
        self.u.request({'op':'save','reading':self.reading()});self.u.request({'op':'save','reading':self.reading('Hermes / second')})
        restored=usage.Usage(self.fd,self.home,clock=lambda:1000)
        rows=restored.request({'op':'read'})['rows'];self.assertEqual(len(rows),2)
        self.assertEqual(os.stat(self.home/'usage.json').st_mode & 0o777,0o600)
        rows=restored.request({'op':'delete','id':rows[0]['id']})['rows'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['windows'][0]['source'],'Manual reading')
    def test_expired_is_unknown(self):
        r=self.reading();r['resets_at']=900
        w=self.u.request({'op':'save','reading':r})['rows'][0]['windows'][0]
        self.assertIsNone(w['display_remaining']);self.assertTrue(w['expired']);self.assertEqual(w['remaining'],8)
    def test_future_reading_is_unknown(self):
        self.u.request({'op':'save','reading':self.reading()});self.u.clock=lambda:100
        self.assertIsNone(self.u.request({'op':'read'})['rows'][0]['windows'][0]['display_remaining'])
    def test_bad_readings_rejected(self):
        for field,value in [('provider','invented'),('remaining',float('nan')),('remaining',True),('remaining',11),('resets_at',float('inf')),('unit','arbitrary'),('model','x\nsecret')]:
            with self.subTest(field=field,value=value):
                r=self.reading();r[field]=value
                with self.assertRaises(ValueError):self.u.request({'op':'save','reading':r})
    def test_linked_output_refused(self):
        (self.home/'usage.pending').symlink_to(self.home/'target')
        with self.assertRaises(OSError):self.u.request({'op':'save','reading':self.reading()})
        self.assertFalse((self.home/'target').exists())
    def test_failed_save_does_not_change_memory(self):
        with patch.object(self.u,'save',side_effect=OSError('blocked')):
            with self.assertRaises(OSError): self.u.request({'op':'save','reading':self.reading()})
        self.assertEqual(self.u.request({'op':'read'})['rows'],[])

    def test_missing_unknown(self):
        result=self.u.request({'op':'enable'});self.assertEqual(result['rows'],[])
        self.assertIn('midjourney',[p['id'] for p in result['catalog']])
    def test_claude_cached_quota(self):
        state=self.home/'.claude/state';state.mkdir(parents=True)
        (state/'rate-limits.json').write_text(json.dumps({'at':950,'rate_limits':{'seven_day':{'used_percentage':46,'resets_at':2000}}}))
        windows=self.u.request({'op':'enable'})['rows'][0]['windows'];self.assertEqual(windows[0]['display_remaining'],54)
        self.assertEqual(windows[0]['window_minutes'],10080);self.assertEqual(len(windows),1)
    def test_codex_quota_bucket_and_private_output(self):
        root=self.home/'.codex/sessions';root.mkdir(parents=True)
        event={'timestamp':'2026-10-09T15:00:00Z','type':'event_msg','payload':{'type':'token_count','rate_limits':{'limit_id':'codex','primary':{'used_percent':25,'window_minutes':300,'resets_at':2000000000}}}}
        (root/'test.jsonl').write_text(json.dumps({'secret':'PRIVATE_MARKER'})+'\n'+json.dumps(event)+'\n')
        self.u.clock=lambda:1791573000
        result=self.u.request({'op':'enable'});self.assertEqual(result['rows'][0]['windows'][0]['remaining'],75)
        self.assertNotIn('PRIVATE_MARKER',json.dumps(result))
        event['payload']['rate_limits']['limit_id']='other-model';(root/'test.jsonl').write_text(json.dumps(event))
        self.u.next_read=0;self.assertEqual(self.u.request({'op':'read'})['rows'],[])
    def test_invalid_quota(self):
        for used in [None,True,-1,101,float('nan')]:self.assertIsNone(usage.quota({'used_percent':used,'resets_at':2000},300,1000))
        self.assertIsNone(usage.quota({'used_percent':20,'resets_at':2000},None,1000))
if __name__=='__main__':unittest.main()
