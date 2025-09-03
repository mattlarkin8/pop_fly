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

    def test_occurrence_disambiguation_replace(self):
        md = (
            "# Title\n\n"
            "## Dup\n"
            "First\n\n"
            "## Dup\n"
            "Second\n\n"
            "## Tail\n"
            "End\n"
        )
        ops = [
            {"type": "replace_section", "heading": "Dup", "content": "Repl2", "occurrence": 2}
        ]
        new_text, warnings, errors = apply_ops_to_markdown(md, ops, "README.md")
        self.assertFalse(errors)
        # First occurrence unchanged
        self.assertIn("## Dup\nFirst", new_text)
        # Second occurrence replaced
        self.assertIn("## Dup\nRepl2", new_text)
        # No defaulting warning since occurrence was provided
        self.assertTrue(all("defaulted to first occurrence" not in w for w in warnings))

    def test_occurrence_default_first_with_warning(self):
        md = (
            "# Title\n\n"
            "## Dup\n"
            "First\n\n"
            "## Dup\n"
            "Second\n\n"
            "## Tail\n"
            "End\n"
        )
        ops = [
            {"type": "replace_section", "heading": "Dup", "content": "Repl1"}
        ]
        new_text, warnings, errors = apply_ops_to_markdown(md, ops, "PRD.md")
        self.assertFalse(errors)
        # First occurrence replaced
        self.assertIn("## Dup\nRepl1", new_text)
        # Second occurrence unchanged
        self.assertIn("## Dup\nSecond", new_text)
        # Warning emitted about defaulting
        self.assertTrue(any("defaulted to first occurrence" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
