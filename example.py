# Suppose we have a file.
# Here use io.StringIO to fake a file.

import io

file = io.StringIO(
    """01|Peter|1990-02-18|
02|I like cake|42|
02|Dogs are fun|101|
03|dog|Molly|
01|Luke|1991-02-18|
03|cat|Tilly|
01|Alice|1994-02-25|"""
)


##################################################

# Let's parse this file into Pydantic models!

import typing as t
import datetime
import pydantic

from pipedantic import PipeDelimitedFileParser


# Define the models


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


# Define the parser

parser = PipeDelimitedFileParser[Root](
    doc_model=Root,
    line_models={
        "01": User,
        "02": Comment,
        "03": Pet,
    },
)


# Parse the file


lines = iter(file.read().splitlines())

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
