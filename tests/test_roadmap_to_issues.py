import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import the parser directly from scripts by adjusting sys.path
scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, scripts_dir)

from roadmap_to_issues import parse_roadmap, RoadmapItem


class TestRoadmapParser(unittest.TestCase):
    def test_parse_basic_sections_and_status_emojis(self):
        md = """# Roadmap

## Now
- Feature A (🟡)
  - Do stuff

## Next
- Feature B (⚪)
  - Some notes

## Later
- Feature C (🟢) #123
  - Done already
"""
        items = parse_roadmap(md)
        self.assertEqual(len(items), 3)
        a, b, c = items
        self.assertEqual(a.section, "Now")
        self.assertEqual(a.title, "Feature A")
        self.assertEqual(a.status, "In progress")
        self.assertEqual(a.body, "Do stuff")

        self.assertEqual(b.section, "Next")
        self.assertEqual(b.title, "Feature B")
        self.assertEqual(b.status, "Planned")
        self.assertEqual(b.body, "Some notes")

        self.assertEqual(c.section, "Later")
        self.assertEqual(c.title, "Feature C")
        self.assertEqual(c.status, "Done")
        self.assertEqual(c.issue_ref, 123)

    def test_parse_word_status_and_missing_status(self):
        md = """## Now
- Feature X (In progress)
- Feature Y
  - details
"""
        items = parse_roadmap(md)
        self.assertEqual(len(items), 2)
        x, y = items
        self.assertEqual(x.title, "Feature X")
        self.assertEqual(x.status, "In progress")
        self.assertEqual(y.title, "Feature Y")
        self.assertEqual(y.status, "Planned")
        self.assertEqual(y.body, "details")


if __name__ == "__main__":
    unittest.main()
