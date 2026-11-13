from textkit.strings import is_palindrome, slugify, title_case, truncate, word_count


def test_palindrome():
    assert is_palindrome("Never odd or even")
    assert not is_palindrome("agents")


def test_truncate_short_untouched():
    assert truncate("abc", 3) == "abc"
    assert truncate("abc", 5) == "abc"


def test_truncate_long():
    assert truncate("abcdef", 4) == "abc…"


def test_word_count_spaces():
    assert word_count("one  two\tthree\n") == 3
    assert word_count("") == 0


def test_slugify():
    assert slugify(" Hello, Agent World ") == "hello-agent-world"
    assert slugify("v2-release") == "v2-release"


def test_title_case():
    assert title_case("the art of war") == "The Art of War"
    assert title_case("a tale") == "A Tale"
