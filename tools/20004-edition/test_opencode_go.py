import importlib.util
import pathlib
import unittest
from unittest.mock import patch

file=pathlib.Path(__file__).parent/"opencode_go.py"
spec=importlib.util.spec_from_file_location("opencode_go",file)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class GoTests(unittest.TestCase):
    def test_key_required(self):
        with self.assertRaises(ValueError):
            m.chat([{"role":"user","content":"hello"}],"")
    def test_https(self):
        with self.assertRaises(ValueError):
            m.chat([{"role":"user","content":"hello"}],"test",endpoint="http://example.org")
    def test_payload(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,n): return b'{"choices":[{"message":{"content":"OK"}}]}'
        with patch.object(m.urllib.request,"urlopen",return_value=FakeResponse()) as request:
            result=m.chat([{"role":"user","content":"hello"}],"test-key")
            self.assertEqual(result,"OK")
            sent=request.call_args.args[0]
            self.assertIn("deepseek-v4-pro",sent.data.decode())
            self.assertEqual(sent.get_header("Authorization"),"Bearer test-key")

if __name__=="__main__": unittest.main()
