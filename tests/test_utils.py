from pipedantic import utils


def test_peek_lines():
    lines = iter(
        """foo
bar

baz
bax""".splitlines()
    )

    peek_lines = utils.PeekLines(lines=lines)

    assert peek_lines.peek() == (1, "foo")
    assert peek_lines.peek() == (1, "foo")
    assert peek_lines.consume() == (1, "foo")

    assert peek_lines.peek() == (2, "bar")
    assert peek_lines.consume() == (2, "bar")

    assert peek_lines.consume() == (3, "")

    assert peek_lines.consume() == (4, "baz")

    assert peek_lines.peek() == (5, "bax")
    assert peek_lines.consume() == (5, "bax")

    for _ in range(2):
        assert peek_lines.peek() == (None, None)
        assert peek_lines.consume() == (None, None)


def test_peek_lines_skip_empty_lines():
    lines = iter(
        """

foo

bar
baz

bax

""".splitlines()
    )

    peek_lines = utils.PeekLines(lines=lines, skip_empty_lines=True)

    assert peek_lines.peek() == (3, "foo")
    assert peek_lines.peek() == (3, "foo")
    assert peek_lines.consume() == (3, "foo")

    assert peek_lines.peek() == (5, "bar")
    assert peek_lines.consume() == (5, "bar")

    assert peek_lines.consume() == (6, "baz")

    assert peek_lines.peek() == (8, "bax")
    assert peek_lines.consume() == (8, "bax")

    for _ in range(2):
        assert peek_lines.peek() == (None, None)
        assert peek_lines.consume() == (None, None)
