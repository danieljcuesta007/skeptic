"""Minimal owned AF_UNIX bind/connect probe; never opens project or provider data."""
import json,os,socket,tempfile
from pathlib import Path

def main():
 with tempfile.TemporaryDirectory(prefix='sk45-probe-',dir='/private/tmp') as tmp:
  root=Path(tmp);root.chmod(0o700)
  try:
   with socket.socket(socket.AF_UNIX) as listener:
    listener.bind(str(root/'probe.sock'));(root/'probe.sock').chmod(0o600);listener.listen(1)
    with socket.socket(socket.AF_UNIX) as client:
     client.settimeout(2);client.connect(str(root/'probe.sock'))
     peer,_=listener.accept()
     with peer:
      peer.settimeout(2);client.sendall(b'ping');assert peer.recv(4)==b'ping';peer.sendall(b'pong');assert client.recv(4)==b'pong'
   print(json.dumps({'result':'passed','bind':True,'connect':True,'exchange':True,'scope':'owner-only temporary directory'}));return 0
  except OSError as error:
   print(json.dumps({'result':'blocked','errno':error.errno,'reason':str(error),'bind_connect_exchange':'not established'}));return 2
if __name__=='__main__':raise SystemExit(main())
