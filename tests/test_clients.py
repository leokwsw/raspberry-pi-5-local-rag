import unittest

from backend.app.clients import strip_thinking_output


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


if __name__ == "__main__":
    unittest.main()
