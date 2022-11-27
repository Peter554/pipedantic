import json
import typing as t

import pydantic


from pipedantic import utils


class FileParseError(Exception):
    def __init__(self, *, error: str, line_number: t.Optional[int] = None):
        self.error = error
        self.line_number = line_number

    def __str__(self):
        return json.dumps({"error": self.error, "line_number": self.line_number})


T = t.TypeVar("T", bound=pydantic.BaseModel)


class PipeDelimitedFileParser(t.Generic[T]):
    def __init__(
        self,
        *,
        doc_model: t.Type[T],
        line_models: dict[str, t.Type[pydantic.BaseModel]],
    ):
        self._spec: dict[str, t.Type[pydantic.BaseModel]] = {
            "__root__": doc_model,
            **line_models,
        }
        self._reverse_spec = {v: k for k, v in self._spec.items()}

    def parse(self, *, lines: t.Iterator[str]) -> T:
        self._peek_lines = utils.PeekLines(lines=lines, skip_empty_lines=True)
        return self._parse_rule("__root__")

    def _parse_rule(self, rule):
        rule_model = self._spec[rule]
        line_fields = {
            k: v
            for k, v in rule_model.__fields__.items()
            if self._get_child_type(v.annotation) is None
        }
        child_fields = {
            k: v for k, v in rule_model.__fields__.items() if k not in line_fields
        }

        data = {}
        if line_fields:
            line_number, line = self._peek_lines.consume()
            line_parts = line.split("|")
            assert line_parts[0] == rule
            line_parts = line_parts[1:]
            if len(line_parts) < len(line_fields):
                raise FileParseError(error="Missing data", line_number=line_number)
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
            return rule_model.parse_obj(data)
        except pydantic.ValidationError as e:
            raise FileParseError(
                error=self._format_pydantic_validation_error(e), line_number=line_number
            ) from e

    def _get_child_type(self, type_):
        if t.get_origin(type_) == t.Literal:
            return None
        elif self._is_subclass_safe(type_, pydantic.BaseModel):
            return (type_, "1")
        elif t.get_origin(type_) == t.Union and type(None) in t.get_args(
            type_
        ):  # Optional
            inner_type = t.get_args(type_)[0]
            if self._is_subclass_safe(inner_type, pydantic.BaseModel):
                return (inner_type, "?")
        elif t.get_origin(type_) == list:
            inner_type = t.get_args(type_)[0]
            if self._is_subclass_safe(inner_type, pydantic.BaseModel):
                return (inner_type, "*")
        return None

    @staticmethod
    def _is_subclass_safe(type_, class_) -> bool:
        try:
            return issubclass(type_, class_)
        except TypeError:
            return False

    @staticmethod
    def _format_pydantic_validation_error(e: pydantic.ValidationError) -> str:
        first_error = e.errors()[0]
        return (
            "["
            + "->".join([str(x) for x in first_error["loc"]])
            + "] "
            + first_error["msg"]
        )
