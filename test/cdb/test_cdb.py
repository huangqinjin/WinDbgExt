import cdb
import pytest

class TestBracedTemplate:
    @pytest.mark.parametrize("text,values,expected", [
        ("${cwd}hello.exe", {"cwd": "C:\\work\\"}, "C:\\work\\hello.exe"),
        ("${cwd}/x", {"cwd": "/w"}, "/w/x"),
        ("${a}${b}", {"a": "1", "b": "2"}, "12"),
        ("no placeholders", {}, "no placeholders"),
        ("", {}, ""),
        # bare $name is left to the text on purpose
        ("$cwd/hello.exe", {"cwd": "/w"}, "$cwd/hello.exe"),
        ("$cwd and ${cwd}", {"cwd": "/w"}, "$cwd and /w"),
        ("$", {}, "$"),
        ("trailing$", {}, "trailing$"),
        ("plain $ text", {}, "plain $ text"),
        # only ${identifier} counts, so other braces stay
        ("{cwd}hello.exe", {"cwd": "/w"}, "{cwd}hello.exe"),
        ("${}", {}, "${}"),
        ("${cwd", {}, "${cwd"),
        ("${not-an-ident}", {}, "${not-an-ident}"),
        ("${9lives}", {}, "${9lives}"),
        # $$ is not the Template escape here: it survives verbatim
        ("$$><0001.txt", {}, "$$><0001.txt"),
        (".logopen 0001.log", {}, ".logopen 0001.log"),
        ("a$$b", {}, "a$$b"),
    ])
    def test_render(self, text, values, expected):
        assert str(cdb.BracedTemplate(text, values)) == expected
