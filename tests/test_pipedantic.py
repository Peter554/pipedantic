import datetime
import typing as t

import pydantic
import pytest

from pipedantic import PipeDelimitedFileParser, FileParseError


class Pet(pydantic.BaseModel):
    type: t.Literal["dog", "cat"]
    name: str


class Comment(pydantic.BaseModel):
    text: str
    likes: int


class User(pydantic.BaseModel):
    name: str
    dob: datetime.date
    comments: list[Comment]
    pet: t.Optional[Pet]


class Root(pydantic.BaseModel):
    users: list[User]


@pytest.mark.parametrize(
    "text",
    [
        # basic
        """01|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|101|
03|dog|Molly|
01|Luke|1991-02-18|
03|cat|Tilly|
01|Alice|1994-02-25|""",
        # with empty lines
        """
        
01|Peter|1990-02-18|
02|I like cake|42|

02|Dogs are fun|101|
03|dog|Molly|

01|Luke|1991-02-18|
03|cat|Tilly|
01|Alice|1994-02-25|

""",
        # without terminating |
        """01|Peter|1990-02-18
02|I like cake|42
02|Dogs are fun|101
03|dog|Molly
01|Luke|1991-02-18
03|cat|Tilly
01|Alice|1994-02-25""",
    ],
)
def test_parse_success(text):
    parser = PipeDelimitedFileParser[Root](
        doc_model=Root,
        line_models={
            "01": User,
            "02": Comment,
            "03": Pet,
        },
    )

    lines = iter(text.splitlines())

    data = parser.parse(lines=lines)
    assert data == Root(
        users=[
            User(
                name="Peter",
                dob=datetime.date(1990, 2, 18),
                comments=[
                    Comment(text="I like cake", likes=42),
                    Comment(text="Dogs are fun", likes=101),
                ],
                pet=Pet(type="dog", name="Molly"),
            ),
            User(
                name="Luke",
                dob=datetime.date(1991, 2, 18),
                comments=[],
                pet=Pet(type="cat", name="Tilly"),
            ),
            User(
                name="Alice",
                dob=datetime.date(1994, 2, 25),
                comments=[],
                pet=None,
            ),
        ]
    )


@pytest.mark.parametrize(
    "text,expected_line_number,expected_error",
    [
        # L1 bad dob
        [
            """01|Peter|oops|
02|I like cake|42|
02|Dogs are fun|101|
03|dog|Molly|
01|Luke|1991-02-18|
03|cat|Tilly|
01|Alice|1994-02-25|""",
            1,
            "[dob] invalid date format",
        ],
        # L3 likes should be int
        [
            """01|Peter|1991-03-11|
02|I like cake|42|
02|Dogs are fun|oops|
03|dog|Molly|
01|Luke|1991-02-18|
03|cat|Tilly|
01|Alice|1994-02-25|""",
            3,
            "[likes] value is not a valid integer",
        ],
        # L4 invalid pet type
        [
            """01|Peter|1991-03-11|
02|I like cake|42|
02|Dogs are fun|101|
03|snake|Molly|
01|Luke|1991-02-18|
03|cat|Tilly|
01|Alice|1994-02-25|""",
            4,
            "[type] unexpected value; permitted: 'dog', 'cat'",
        ],
    ],
)
def test_parse_failure(text, expected_line_number, expected_error):
    parser = PipeDelimitedFileParser[Root](
        doc_model=Root,
        line_models={
            "01": User,
            "02": Comment,
            "03": Pet,
        },
    )

    lines = iter(text.splitlines())

    with pytest.raises(FileParseError) as exc_info:
        parser.parse(lines=lines)

    assert exc_info.value.line_number == expected_line_number
    assert exc_info.value.error == expected_error
