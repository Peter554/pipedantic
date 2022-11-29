import datetime
import pathlib
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


class BestFriend(pydantic.BaseModel):
    id: int


class User(pydantic.BaseModel):
    id: int
    name: str
    dob: datetime.date
    comments: list[Comment]
    pet: t.Optional[Pet]
    best_friend: BestFriend


class Root(pydantic.BaseModel):
    users: list[User]


@pytest.mark.parametrize(
    "text",
    [
        # basic
        """01|1|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|101|
03|dog|Molly|
04|2|
01|2|Luke|1991-02-18|
03|cat|Tilly|
04|3|
01|3|Alice|1994-02-25|
04|1|""",
        # with empty lines
        """
        
01|1|Peter|1990-02-18|
02|I like cake|42|

02|Dogs are fun|101|
03|dog|Molly|
04|2|

01|2|Luke|1991-02-18|
03|cat|Tilly|
04|3|

01|3|Alice|1994-02-25|
04|1|

""",
        # with comments
        """
# starting
01|1|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|101|
# Peter has a pet dog
03|dog|Molly|
04|2|
01|2|Luke|1991-02-18|
03|cat|Tilly|
04|3|
01|3|Alice|1994-02-25|
04|1|
# ending
""",
    ],
)
def test_parse_success(text):
    parser = PipeDelimitedFileParser[Root](
        root_model=Root,
        line_models={"01": User, "02": Comment, "03": Pet, "04": BestFriend},
    )

    lines = iter(text.splitlines())

    data = parser.parse(file=lines)
    assert data == Root(
        users=[
            User(
                id=1,
                name="Peter",
                dob=datetime.date(1990, 2, 18),
                comments=[
                    Comment(text="I like cake", likes=42),
                    Comment(text="Dogs are fun", likes=101),
                ],
                pet=Pet(type="dog", name="Molly"),
                best_friend=BestFriend(id=2),
            ),
            User(
                id=2,
                name="Luke",
                dob=datetime.date(1991, 2, 18),
                comments=[],
                pet=Pet(type="cat", name="Tilly"),
                best_friend=BestFriend(id=3),
            ),
            User(
                id=3,
                name="Alice",
                dob=datetime.date(1994, 2, 25),
                comments=[],
                pet=None,
                best_friend=BestFriend(id=1),
            ),
        ]
    )


def test_parse_success_from_file():
    parser = PipeDelimitedFileParser[Root](
        root_model=Root,
        line_models={
            "01": User,
            "02": Comment,
            "03": Pet,
            "04": BestFriend,
        },
    )

    with open(pathlib.Path(__file__).parent.joinpath(pathlib.Path("./data"))) as f:
        data = parser.parse(file=f)

    assert data == Root(
        users=[
            User(
                id=1,
                name="Peter",
                dob=datetime.date(1990, 2, 18),
                comments=[
                    Comment(text="I like cake", likes=42),
                    Comment(text="Dogs are fun", likes=101),
                ],
                pet=Pet(type="dog", name="Molly"),
                best_friend=BestFriend(id=2),
            ),
            User(
                id=2,
                name="Luke",
                dob=datetime.date(1991, 2, 18),
                comments=[],
                pet=Pet(type="cat", name="Tilly"),
                best_friend=BestFriend(id=3),
            ),
            User(
                id=3,
                name="Alice",
                dob=datetime.date(1994, 2, 25),
                comments=[],
                pet=None,
                best_friend=BestFriend(id=1),
            ),
        ]
    )


@pytest.mark.parametrize(
    "text,expected_line_number,expected_error",
    [
        # L1 bad dob
        [
            """01|1|Peter|oops|
02|I like cake|42|
02|Dogs are fun|101|
03|dog|Molly|
04|2|
01|2|Luke|1991-02-18|
03|cat|Tilly|
04|3|
01|3|Alice|1994-02-25|
04|1|""",
            1,
            "[dob] invalid date format",
        ],
        # L3 likes should be int
        [
            """01|1|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|oops|
03|dog|Molly|
04|2|
01|2|Luke|1991-02-18|
03|cat|Tilly|
04|3|
01|3|Alice|1994-02-25|
04|1|""",
            3,
            "[likes] value is not a valid integer",
        ],
        # L4 invalid pet type
        [
            """01|1|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|101|
03|snake|Molly|
04|2|
01|2|Luke|1991-02-18|
03|cat|Tilly|
04|3|
01|3|Alice|1994-02-25|
04|1|""",
            4,
            "[type] unexpected value; permitted: 'dog', 'cat'",
        ],
        # L1 is missing a required child (best_friend, 04)
        [
            """01|1|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|101|
03|dog|Molly|
01|2|Luke|1991-02-18|
03|cat|Tilly|
04|3|
01|3|Alice|1994-02-25|
04|1|""",
            1,
            "[best_friend (04)] field required",
        ],
        # L6 is missing a field (dob)
        [
            """01|1|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|101|
03|dog|Molly|
04|2|
01|2|Luke|
03|cat|Tilly|
04|3|
01|3|Alice|1994-02-25|
04|1|""",
            6,
            "[dob] Field is missing",
        ],
        # L6 has extra data
        [
            """01|1|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|101|
03|dog|Molly|
04|2|
01|2|Luke|1991-03-18|oops|
03|cat|Tilly|
04|3|
01|3|Alice|1994-02-25|
04|1|""",
            6,
            "Line has extra data",
        ],
        # L6 has extra data
        [
            """01|1|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|101|
03|dog|Molly|
04|2|
01|2|Luke|1991-03-18|oops|
03|cat|Tilly|
04|3|
01|3|Alice|1994-02-25|
04|1|""",
            6,
            "Line has extra data",
        ],
        # L7 is malformed, and causes incomplete parsing
        [
            """01|1|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|101|
03|dog|Molly|
04|2|
# A pet is not expected at this part of the document
03|dog|Milly|
01|2|Luke|1991-02-18|
03|cat|Tilly|
04|3|
01|3|Alice|1994-02-25|
04|1|""",
            7,
            "Incomplete parsing, malformed data?",
        ],
    ],
)
def test_parse_failure(text, expected_line_number, expected_error):
    parser = PipeDelimitedFileParser[Root](
        root_model=Root,
        line_models={
            "01": User,
            "02": Comment,
            "03": Pet,
            "04": BestFriend,
        },
    )

    lines = iter(text.splitlines())

    with pytest.raises(FileParseError) as exc_info:
        parser.parse(file=lines)

    assert exc_info.value.line_number == expected_line_number
    assert exc_info.value.error == expected_error
