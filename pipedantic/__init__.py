import json
import re
import typing as t

import pydantic

from pipedantic import utils


class FileParseError(Exception):
    def __init__(self, *, error: str, line_number: int | None = None):
        self.error = error
        self.line_number = line_number

    def __str__(self):
        return json.dumps({"error": self.error, "line_number": self.line_number})


T = t.TypeVar("T", bound=pydantic.BaseModel)


class PipeDelimitedFileParser(t.Generic[T]):
    def __init__(
        self,
        *,
        root_model: type[T],
        line_models: dict[str, type[pydantic.BaseModel]],
    ):
        self._spec: dict[str, type[pydantic.BaseModel]] = {
            "__root__": root_model,
            **line_models,
        }
        self._reverse_spec = {v: k for k, v in self._spec.items()}

    def parse(self, *, file: t.Iterator[str]) -> T:
        self._peek_lines = utils.PeekLines(
            lines=file, skip_line_patterns=[re.compile(r"^$"), re.compile(r"^#")]
        )
        data = self._parse_rule("__root__")
        if self._peek_lines.peek() != (None, None):
            line_number, _ = self._peek_lines.peek()
            raise FileParseError(
                error="Incomplete parsing, malformed data?", line_number=line_number
            )
        return data

    def _parse_rule(self, rule):
        rule_model = self._spec[rule]
        line_fields = {
            k: v
            for k, v in rule_model.model_fields.items()
            if self._get_child_type(v.annotation) is None
        }
        child_fields = {
            k: v for k, v in rule_model.model_fields.items() if k not in line_fields
        }

        data = {}
        if line_fields:
            line_number, line = self._peek_lines.consume()
            if not line.endswith("|"):
                raise FileParseError(
                    error="Line missing terminating pipe", line_number=line_number
                )
            line_parts = line.split("|")[:-1]
            line_parts = [s or None for s in line_parts]
            assert line_parts[0] == rule
            line_parts = line_parts[1:]
            if len(line_parts) < len(line_fields):
                first_missing_field = list(line_fields)[len(line_parts)]
                raise FileParseError(
                    error=f"[{first_missing_field}] Field is missing",
                    line_number=line_number,
                )
            elif len(line_parts) > len(line_fields):
                raise FileParseError(
                    error="Line has extra data",
                    line_number=line_number,
                )
            for idx, line_field_name in enumerate(line_fields):
                data[line_field_name] = line_parts[idx]
        else:
            line_number = None

        for child_field_name, child_field_details in child_fields.items():
            child_type, child_multiplicity = self._get_child_type(
                child_field_details.annotation
            )
            child_rule = self._reverse_spec[child_type]
            if child_multiplicity in ("1", "?"):
                if self._peek_lines.peek_starts_with(f"{child_rule}|"):
                    data[child_field_name] = self._parse_rule(child_rule)
            elif child_multiplicity == "*":
                items = []
                while self._peek_lines.peek_starts_with(f"{child_rule}|"):
                    items.append(self._parse_rule(child_rule))
                data[child_field_name] = items

        try:
            return rule_model.model_validate(data)
        except pydantic.ValidationError as e:
            raise FileParseError(
                error=self._format_pydantic_validation_error(e, child_fields),
                line_number=line_number,
            ) from e

    def _get_child_type(self, type_) -> tuple[type, str] | None:
        if t.get_origin(type_) == t.Literal:
            return None
        elif self._is_subclass_safe(type_, pydantic.BaseModel):
            return type_, "1"
        elif self._is_union_type(type_) and type(None) in t.get_args(type_):  # Optional
            args = [arg for arg in t.get_args(type_) if arg != type(None)]
            assert len(args) == 1
            inner_type = args[0]
            if self._is_subclass_safe(inner_type, pydantic.BaseModel):
                return inner_type, "?"
        elif t.get_origin(type_) == list:
            inner_type = t.get_args(type_)[0]
            if self._is_subclass_safe(inner_type, pydantic.BaseModel):
                return inner_type, "*"
        return None

    @staticmethod
    def _is_union_type(type_: type) -> bool:
        origin = t.get_origin(type_)
        # hack (t.get_origin(int | None) == t.Union not working?)
        return origin == t.Union or origin == t.get_origin(int | None)

    @staticmethod
    def _is_subclass_safe(type_, class_) -> bool:
        try:
            return issubclass(type_, class_)
        except TypeError:
            return False

    def _format_pydantic_validation_error(
        self, e: pydantic.ValidationError, child_fields: dict
    ) -> str:
        first_error = e.errors()[0]

        def explain_loc(loc):
            if loc in child_fields:
                child_field_details = child_fields[loc]
                child_type, child_multiplicity = self._get_child_type(
                    child_field_details.annotation
                )
                child_rule = self._reverse_spec[child_type]
                return f"{loc} ({child_rule})"
            else:
                return str(loc)

        return (
            "["
            + " -> ".join([explain_loc(x) for x in first_error["loc"]])
            + "] "
            + first_error["msg"]
        )
