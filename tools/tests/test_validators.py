from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators import validate_mylang, validate_python


class ValidatorTestCase(unittest.TestCase):
    def temporary_file(self, suffix: str, source: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        path = directory / f"sample{suffix}"
        path.write_text(source, encoding="utf-8")
        return path

    def rules(self, result) -> set[str]:
        return {finding.rule for finding in result.findings}

    def test_python_plot_local_scope(self):
        path = self.temporary_file(".py", "def f():\n    plot_text('x', a, b, 'x', c, 1, 0, 0, 0)\n")
        self.assertIn("PY101", self.rules(validate_python(path)))

    def test_python_plot_limit(self):
        calls = "\n".join(f"plot_text('p{i}', a, b, 'x', c, 1, 0, 0, 0)" for i in range(51))
        path = self.temporary_file(".py", calls)
        self.assertIn("PY102", self.rules(validate_python(path)))

    def test_python_plot_name_and_stickline_signature(self):
        source = "plot_stickline('this plot name is definitely too long', a, b)\n"
        path = self.temporary_file(".py", source)
        rules = self.rules(validate_python(path))
        self.assertIn("PY103", rules)
        self.assertIn("PY104", rules)

    def test_python_client_subset_rules(self):
        source = "x = mod(a, b)\ny = (a\n    & b)\n"
        path = self.temporary_file(".py", source)
        rules = self.rules(validate_python(path))
        self.assertIn("PY105", rules)
        self.assertIn("PY106", rules)

    def test_mylang_parser_rules(self):
        source = "A:=1\nB:=NOT A;\nC:=X=-1;\nD:=(A,COLOR11223344;\n"
        path = self.temporary_file(".mylang", source)
        rules = self.rules(validate_mylang(path))
        self.assertTrue({"ML101", "ML102", "ML103", "ML104", "ML105"}.issubset(rules))

    def test_mylang_reserved_and_unsupported(self):
        path = self.temporary_file(".mylang", "NDAY:=MOD(C,2);\n")
        rules = self.rules(validate_mylang(path))
        self.assertIn("ML106", rules)
        self.assertIn("ML107", rules)

    def test_mylang_dynamic_window_is_supported(self):
        path = self.temporary_file(".mylang", "WIN:=5;\nA:=HHV(H,WIN);\n")
        self.assertNotIn("ML201", self.rules(validate_mylang(path)))

    def test_mylang_external_parameter_warning(self):
        path = self.temporary_file(".mylang", "A:=EXTERNAL+1;\n")
        self.assertIn("ML202", self.rules(validate_mylang(path)))

    def test_mylang_count_zero_warning(self):
        path = self.temporary_file(".mylang", "A:=COUNT(X,0)>0;\n")
        self.assertIn("ML204", self.rules(validate_mylang(path)))

    def test_mylang_multiline_comment_does_not_affect_parentheses(self):
        path = self.temporary_file(".mylang", "{ comment with (\ncontinued ) }\nA:=1;\n")
        self.assertNotIn("ML102", self.rules(validate_mylang(path)))


if __name__ == "__main__":
    unittest.main()
