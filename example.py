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


# Open and parse the file

with open("./example-data") as f:
    data = parser.parse(file=f)

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

with open("./example-data-invalid") as f:
    try:
        parser.parse(file=f)
        assert False, "Expected an error, but no error was raised."
    except FileParseError as e:
        assert e.error == "[posted_at] invalid date format"
        assert e.line_number == 5
