"""Temporary boundary/behavior faults; source files and real account files untouched."""
import io
import unittest
from unittest.mock import patch
import usage
from test_usage import UsageTests

original=usage.Usage.request

def wrong_request(self,data):
    result=original(self,data)
    for row in result['rows']:
        for w in row['windows']: w['display_remaining']=w['remaining']
    return result

def without_catalog(self,data):
    result=original(self,data);result['catalog']=[];return result

def implicit_read(self,data):
    if data=={'op':'read'}:self.enabled=True;self.next_read=0
    return original(self,data)

def inverted_quota(raw,minutes,at):
    result=real_quota(raw,minutes,at)
    if result:result['remaining']=100-result['remaining']
    return result

def retain_failed_save(self,data):
    try:return original(self,data)
    except OSError:
        self.manual['fault']={'provider':'hermes','model':'failed','remaining':8,'limit':10,'unit':'USD','resets_at':2000,'observed_at':1000}
        raise

real_quota=usage.quota
faults=[
 ('test_failed_save_does_not_change_memory',patch.object(usage.Usage,'request',retain_failed_save)),
 ('test_connection_revocation_and_poll_budget',patch.object(usage.Usage,'request',implicit_read)),
 ('test_persistence_multiple_models_and_remove_one',patch.object(usage.Usage,'save',lambda self:None)),
 ('test_expired_is_unknown',patch.object(usage.Usage,'request',wrong_request)),
 ('test_future_reading_is_unknown',patch.object(usage.Usage,'request',wrong_request)),
 ('test_bad_readings_rejected',patch.object(usage.Usage,'validate',lambda self,data:data)),
 ('test_linked_output_refused',patch.object(usage.Usage,'save',lambda self:None)),
 ('test_missing_unknown',patch.object(usage.Usage,'request',without_catalog)),
 ('test_claude_cached_quota',patch.object(usage,'quota',inverted_quota)),
 ('test_codex_quota_bucket_and_private_output',patch.object(usage.Usage,'local',lambda self:[])),
 ('test_invalid_quota',patch.object(usage,'quota',lambda *args:{})),
]
for name,fault in faults:
    with fault:
        result=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([UsageTests(name)]))
    if result.wasSuccessful():raise AssertionError('Fault survived: '+name)
from test_app import ServerTests
import app
original_guard=app.Handler.guard

def no_session_guard(self,api=False):return original_guard(self,api=False)
http_faults=[
 ('test_usage_route_requires_session_and_refuses_extra_fields',patch.object(app.Handler,'guard',no_session_guard)),
 ('test_usage_http_save_restore_and_no_file_context',patch.object(usage.Usage,'save',lambda self:None)),
]
for name,fault in http_faults:
    with fault:
        result=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([ServerTests(name)]))
    if result.wasSuccessful():raise AssertionError('Fault survived: '+name)
print('13 planted usage faults caught; original source unchanged.')
