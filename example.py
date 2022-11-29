import io
import datetime
import pydantic

from pipedantic import PipeDelimitedFileParser, FileParseError


# Define the models/spec


class Comment(pydantic.BaseModel):
    posted_at: datetime.date
    text: str


class User(pydantic.BaseModel):
    name: str
    age: int
    comments: list[Comment]


class Root(pydantic.BaseModel):
    users: list[User]


# Define the parser

parser = PipeDelimitedFileParser[Root](
    root_model=Root,
    line_models={
        "01": User,
        "02": Comment,
    },
)


# Open a file
# Fake it with io.StringIO

file = io.StringIO(
    """01|Holly|16|
02|2022-01-01|Awesome!|
01|Andy|24|
02|2022-02-02|Wicked!|
02|2022-03-03|Sweet!|"""
)
lines = iter(file.read().splitlines())


# Parse the file

data = parser.parse(lines=lines)
assert data == Root(
    users=[
        User(
            name="Holly",
            age=16,
            comments=[Comment(posted_at=datetime.date(2022, 1, 1), text="Awesome!")],
        ),
        User(
            name="Andy",
            age=24,
            comments=[
                Comment(posted_at=datetime.date(2022, 2, 2), text="Wicked!"),
                Comment(posted_at=datetime.date(2022, 3, 3), text="Sweet!"),
            ],
        ),
    ]
)


# If the file is invalid we will get an error


# Andy's 1st comment has an invalid posted_at
file = io.StringIO(
    """01|Holly|16|
02|2022-01-01|Awesome!|
01|Andy|24|
02|oops|Wicked!|
02|2022-03-03|Sweet!|"""
)
lines = iter(file.read().splitlines())

try:
    parser.parse(lines=lines)
    assert False
except FileParseError as e:
    assert e.error == "[posted_at] invalid date format"
    assert e.line_number == 4
