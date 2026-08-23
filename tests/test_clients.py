import unittest

from backend.app.clients import parse_triples, strip_thinking_output


class StripThinkingOutputTests(unittest.TestCase):
    def test_removes_complete_thinking_block(self):
        content = "<think>Internal reasoning</think>\n\nThe final answer [1]."

        self.assertEqual(strip_thinking_output(content), "The final answer [1].")

    def test_removes_trace_when_opening_tag_is_missing(self):
        content = "Internal reasoning leaked here.\n</think>\n\nThe final answer [1]."

        self.assertEqual(strip_thinking_output(content), "The final answer [1].")

    def test_preserves_normal_answer(self):
        content = "The MLP predicts color and volume density [1]."

        self.assertEqual(strip_thinking_output(content), content)


class ParseTriplesTests(unittest.TestCase):
    def test_parses_valid_json_and_rejects_empty_relationships(self):
        content = '{"triples":[{"subject":"Pi 5","predicate":"uses","object":"ARM64"},' \
                  '{"subject":"Pi 5","predicate":"","object":"Linux"}]}'

        self.assertEqual(parse_triples(content, 7), [
            {"subject": "Pi 5", "predicate": "uses", "object": "ARM64", "chunk_index": 7}
        ])

    def test_returns_empty_list_for_non_json_output(self):
        self.assertEqual(parse_triples("not json", 0), [])


if __name__ == "__main__":
    unittest.main()
