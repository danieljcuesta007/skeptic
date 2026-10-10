"""Real localhost smoke test; synthetic fixtures only. Run outside restricted sandboxes."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import app
import workspace_fixture


def main():
    with tempfile.TemporaryDirectory() as name:
        base = Path(name).resolve()
        project = base/'project'; project.mkdir()
        (project/'STATUS.md').write_text('## Current State\nSynthetic live HTTP fixture.\n## Next Actions\nTest local launch.\n')
        vault, repositories = workspace_fixture.create(base)
        registry = app.Registry(base/'state')
        try:
            server = app.LocalServer(registry)
        except OSError:
            registry.close()
            print('NOT VERIFIED: this environment refused localhost socket binding.')
            return 1
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        def request(method, route, data=None, extra=None):
            connection = http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            headers={'Origin':server.origin,'Content-Type':'application/json','X-Skeptic-Token':server.token}
            headers.update(extra or {})
            try:
                connection.request(method,route,body=json.dumps(data) if data is not None else None,headers=headers)
                response=connection.getresponse()
                return response.status,response.read()
            finally: connection.close()
        try:
            assert request('GET','/')[0] == 200
            status, raw = request('POST','/api/approve',{'path':str(project),'excluded':[],'approval':True})
            assert status == 200; key=json.loads(raw)['id']
            assert request('POST','/api/overview',{'id':key})[0] == 200
            status, raw=request('POST','/api/resume',{'id':key,'selected':['STATUS.md'],'provider':'Codex','task':''})
            assert status==200 and 'Synthetic live HTTP fixture' in json.loads(raw)['prompt']
            assert request('POST','/api/projects',{}, {'Origin':'https://invalid.example'})[0] != 200
            assert request('GET','/../../etc/passwd')[0] == 404
            assert request('POST','/api/remove',{'id':key})[0] == 200
            roots = []
            for path, kind in ((vault, 'vault'), (repositories, 'repositories')):
                status, raw = request('POST','/api/workspace/connect',{'path':str(path),'kind':kind,'policy':'FULL_BRAIN','excluded':[],'approval':True})
                assert status == 200; roots.append(json.loads(raw)['id'])
            status, raw = request('POST','/api/workspace/inventory',{})
            assert status == 200
            projects = json.loads(raw)['projects']
            atlas = next(p for p in projects if p['name']=='Atlas')
            assert atlas['repository']['branch']=='main'
            assert atlas['readiness']=='READY TO RESUME'
            status, raw = request('POST','/api/workspace/detail',{'id':atlas['id']})
            assert status == 200; detail = json.loads(raw)
            for provider in ('Claude Code','Codex'):
                status, raw = request('POST','/api/workspace/resume',{'id':atlas['id'],'selected':detail['default_selection'],'provider':provider,'task':''})
                assert status == 200 and 'Resume synthetic Step 3' in json.loads(raw)['prompt']
            assert request('POST','/api/workspace/inventory',{}, {'Origin':'https://invalid.example'})[0] != 200
            assert request('POST','/api/workspace/remove',{'id':atlas['id']})[0] == 200
            assert request('POST','/api/workspace/detail',{'id':atlas['id']})[0] != 200
            for root in roots: assert request('POST','/api/workspace/disconnect',{'id':root})[0] == 200
            assert json.loads(request('POST','/api/workspace/inventory',{})[1])['projects']==[]
            print('PASS: actual loopback launch; legacy flow; workspace approvals, inventory, repository association, grounded detail, both prompts, origin/traversal refusal, project removal and root revocation.')
        finally:
            server.shutdown();thread.join();server.server_close();registry.close()
    return 0


if __name__ == '__main__': raise SystemExit(main())
