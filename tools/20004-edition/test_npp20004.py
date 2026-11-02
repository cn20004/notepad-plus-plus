import unittest
from pathlib import Path
import importlib.util

module_path = Path(__file__).parent / "npp20004.py"
spec = importlib.util.spec_from_file_location("npp20004", module_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TextTests(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(mod.clean("a  \r\n\r\n\r\nb\r\n"), "a\n\nb\n")
    def test_dedup(self):
        self.assertEqual(mod.clean("a\nb\na", True), "a\nb\n")
    def test_extract(self):
        self.assertEqual(mod.extract("13800138000 13800138000", "phone"), ["13800138000"])
    def test_redact(self):
        self.assertNotIn("13800138000", mod.redact("13800138000"))
    def test_summary(self):
        self.assertIn("学费", mod.chat_summary("关于学费的问题"))

if __name__ == "__main__":
    unittest.main()
