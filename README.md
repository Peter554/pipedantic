# pipedantic

[![CI](https://github.com/Peter554/pipedantic/actions/workflows/ci.yml/badge.svg)](https://github.com/Peter554/pipedantic/actions/workflows/ci.yml)

Parse & validate hierarchical pipe delimited text into [Pydantic](https://github.com/pydantic/pydantic) models.

A bit rough and hacky at the moment, mostly here just for fun and interest. Use with caution!

## Install

Requires Python 3.9+

```
pip install pipedantic
```

## What the heck is hierarchical pipe delimited text?

A poor explanation would be:

* Lines of data where fields are delimited with a pipe (`|`)
  * The first field of each line identifies the node type.
  * The later fields are actual data.
* The node types each have a spec. E.g. the names and types of the fields for that node.
* The node spec may be hierarchical, i.e. a node can contain children.

It's easiest to explain with an example. For example, suppose we have `User`s, each with a `name` (string) and an `age` (int). 
And suppose those `User`s have `Comment`s. The comments have a `posted_at` (date) and a `text` (string).

We could then represent those `User`s and their `Comment`s in a pipe delimited text file as so:

```txt
01|Holly|16|
02|2022-01-01|Awesome!|
01|Andy|24|
02|2022-02-02|Wicked!|
02|2022-03-03|Sweet!|
```

This would correspond to the hierarchical data:

```json
{
  "users": [
    {
      "name": "Holly",
      "age": 16,
      "comments": [
        {
          "posted_at": "2022-01-01",
          "text": "Awesome!"
        }
      ]
    },
    {
      "name": "Andy",
      "age": 24,
      "comments": [
        {
          "posted_at": "2022-02-02",
          "text": "Wicked!"
        },
        {
          "posted_at": "2022-03-03",
          "text": "Sweet!"
        }
      ]
    }
  ]
}
```

We could codify this spec and parse the pipe delimited text into Pydantic models using pipedantic!
A spec might look like this:

```py
class Comment(pydantic.BaseModel):
    posted_at: datetime.date
    text: str

class User(pydantic.BaseModel):
    name: str
    age: int
    comments: list[Comment]

class Root(pydantic.BaseModel):
    users: list[User]
```

At which point we're ready to parse the file:

```py
parser = PipeDelimitedFileParser[Root](
    doc_model=Root,
    line_models={
        "01": User,
        "02": Comment,
    },
)
data = parser.parse(lines=lines)
```

A `FileParseError` will be raised if the file is invalid, which contains error details and the line number of the error.
If the file is valid the return type will be `Root`. 

See [example.py](/example.py) and also the tests for more.
