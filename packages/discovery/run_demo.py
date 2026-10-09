"""Run ONLY the included synthetic sample; persist a private index outside notes."""
from pathlib import Path
import json
import tempfile
from engine import Engine,save_index
base=Path(__file__).resolve().parent
config=json.loads((base/'policy.example.json').read_text())
config['root']=str(base/'sample')
# Keep derived indexes outside Git, including when this prototype is migrated.
cache=Path(tempfile.mkdtemp(prefix='skeptic-synthetic-cache-')).resolve()/'sample-index.json'
previous=json.loads(cache.read_text()) if cache.exists() else None
with Engine(config) as engine:
 index=engine.index('atlas',previous)
 receipt=engine.query(index,'orchard milestone','atlas')
 save_index(cache,index)
 print(json.dumps(receipt,indent=2))
