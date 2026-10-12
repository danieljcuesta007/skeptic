import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('inventory',Path(__file__).with_name('live_inventory.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class InventoryTests(unittest.TestCase):
 def test_scope_and_agents(self):
  d=m.parse('501 1 ttys001 /bin/zsh\n501 2 ttys001 /opt/bin/codex\n501 3 ttys002 /bin/claude\n502 4 ttys003 /bin/hermes\n501 5 ?? /bin/codex\n501 6 ttys004 /bin/python\n501 7 ttys004 /bin/hermes',501)
  self.assertEqual(d['ttys'],['ttys001','ttys002','ttys004']);self.assertEqual(d['terminals'],3);self.assertEqual([a['agent'] for a in d['agents']],['Codex','Claude Code','Hermes']);self.assertTrue(all(a['model']=='unknown' and a['activity']=='unknown' for a in d['agents']))
 def test_no_guess_from_arguments(self):
  self.assertEqual(m.parse('501 2 ttys001 python hermes.py',501)['agents'],[])

class HermesTests(unittest.TestCase):
 def test_wrapped_hermes_cli(self):
  code="from hermes_cli.main import main\nsys.exit(main())"
  self.assertEqual(m.python_agent(["python3","-I","-c",code]),"Hermes")
  self.assertEqual(m.python_agent(["python3","-m","hermes_cli.main","chat"]),"Hermes")
 def test_helpers_and_other_python_are_not_agents(self):
  self.assertIsNone(m.python_agent(["python3","-c","print('hermes')"]))
  self.assertIsNone(m.python_agent(["python3","-m","hermes_cli.main","gateway"]))
  self.assertIsNone(m.python_agent(["python3","-I","-c","from hermes_cli.main import main\nsys.exit(main())","--run-module","tools.browser"]))
 def test_unknown_python_is_visible_without_guessing(self):
  d=m.parse("501 2 ttys001 /bin/python3",501)
  self.assertEqual(d["unidentified_python"],1)
 def test_detected_python_is_counted_once(self):
  d=m.parse("501 2 ttys001 /bin/python3",501,{2:"Hermes"})
  self.assertEqual(d["agents"][0]["agent"],"Hermes")
  self.assertEqual(d["unidentified_python"],0)

class EntryPointSafetyTests(unittest.TestCase):
 def test_string_mention_does_not_identify_hermes(self):
  code="print('from hermes_cli.main import main'); sys.exit(main())"
  self.assertIsNone(m.python_agent(["python3","-c",code]))
 def test_helpers_do_not_count_on_nonterminal(self):
  d=m.parse("501 2 ?? /bin/python3",501,{2:"Hermes"})
  self.assertEqual(d["terminals"],0)
  self.assertEqual(d["agents"],[])
 def test_missing_launch_arguments_degrade(self):
  self.assertIsNone(m.python_agent([]))
  self.assertIsNone(m.python_agent(["python3","-m"]))
  self.assertIsNone(m.python_agent(["python3","-c"]))
if __name__=="__main__":unittest.main()
