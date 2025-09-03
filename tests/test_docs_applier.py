import unittest

from scripts.generate_docs import apply_ops_to_markdown


SAMPLE_MD = """# Title

## Section A
Line 1
Line 2

## Section B
Content B

### Subsection B1
Content B1
"""


class TestDocsApplier(unittest.TestCase):
    def test_replace_section(self):
        ops = [
            {"type": "replace_section", "heading": "Section A", "content": "New A\n- bullet"}
        ]
        new_text, warnings, errors = apply_ops_to_markdown(SAMPLE_MD, ops, "README.md")
        self.assertFalse(errors)
        self.assertIn("## Section A\nNew A\n- bullet", new_text)
        self.assertIn("## Section B\nContent B", new_text)

    def test_append_to_section(self):
        ops = [
            {"type": "append_to_section", "heading": "Section B", "content": "Appended line"}
        ]
        new_text, warnings, errors = apply_ops_to_markdown(SAMPLE_MD, ops, "PRD.md")
        self.assertFalse(errors)
        self.assertIn("## Section B\nContent B\n\nAppended line\n\n### Subsection B1", new_text)

    def test_upsert_new_section(self):
        ops = [
            {"type": "upsert_section", "heading": "New Section", "level": 2, "content": "Hello"}
        ]
        new_text, warnings, errors = apply_ops_to_markdown(SAMPLE_MD, ops, "PRD.md")
        self.assertFalse(errors)
        self.assertIn("\n## New Section\nHello", new_text)

    def test_marker_replace_missing(self):
        ops = [
            {"type": "replace_block_by_marker", "name": "FRONTEND_BUILD", "content": "X"}
        ]
        _new_text, warnings, errors = apply_ops_to_markdown(SAMPLE_MD, ops, "README.md")
        self.assertTrue(errors)
        self.assertIn("marker 'FRONTEND_BUILD' not found", "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
