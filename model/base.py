import re
from datetime import datetime

from pydantic import BaseModel as PydanticBaseModel, ConfigDict


def to_snake_case(camel_case):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_case).lower()


class BaseField(PydanticBaseModel):
    model_config = ConfigDict(
        defer_build=True,
        protected_namespaces=()
    )

    def validate(self, value):
        pass


class StringField(BaseField):
    name: str = ""
    default: str = ""
    is_required: bool = False
    regex: str = ""
    max_len: int = None
    choice: list[str] = []
    invalid_message: str = "应该是字符串"
    multi: bool = False

    def validate(self, value):
        if not isinstance(value, str):
            raise ValueError(f"{self.name}字段：{self.invalid_message}")
        if self.regex and not re.findall(self.regex, value):
            raise ValueError(f"{self.name}字段：{self.invalid_message}，不符合{self.regex}")
        if self.choice and value not in self.choice:
            raise ValueError(f"{self.name}字段：{self.invalid_message}，不在{self.choice}里")
        if self.max_len and len(value) > self.max_len:
            raise ValueError(f"{self.name}字段：{self.invalid_message}，长度不能超过{self.max_len}")
        value = value.encode("utf-16", "surrogatepass").decode("utf-16")
        return value


class IntegerField(BaseField):
    name: str = ""
    default: int = None
    is_required: bool = False
    invalid_message: str = "应该是整数"
    multi: bool = False

    def validate(self, value):
        if not isinstance(value, int):
            raise ValueError(f"{self.name}字段，{self.invalid_message}")
        return value


class BooleanField(BaseField):
    name: str = ""
    default: bool = None
    is_required: bool = False
    invalid_message: str = "应该是bool"
    multi: bool = False

    def validate(self, value):
        if not isinstance(value, bool):
            raise ValueError(f"{self.name}字段，{self.invalid_message}")
        return value


class FloatField(BaseField):
    name: str = ""
    default: float = None
    is_required: bool = False
    invalid_message: str = "应该是Float"
    multi: bool = False

    def validate(self, value):
        if isinstance(value, int):
            return float(value)
        if not isinstance(value, float):
            raise ValueError(f"{self.name}字段，{self.invalid_message}")
        return value


class ListField(BaseField):
    name: str = ""
    default: list = None
    is_required: bool = False
    length: int = None
    invalid_message: str = "应该是list"

    def validate(self, value):
        if not isinstance(value, list):
            raise ValueError(f"{self.name}字段，{self.invalid_message}")
        if self.length is not None and len(value) != self.length:
            raise ValueError(f"{self.name}字段：长度为{self.length}")
        new_value = []
        for element in value:
            if isinstance(element, str):
                element = element.encode("utf-16", "surrogatepass").decode("utf-16")
            new_value.append(element)
        return new_value


class DictField(BaseField):
    name: str = ""
    default: dict = None
    is_required: bool = False
    invalid_message: str = "应该是dict"
    multi: bool = False

    def _serialize(self, value):
        if isinstance(value, str):
            return value.encode("utf-16", "surrogatepass").decode("utf-16")
        elif isinstance(value, list):
            new_value = []
            for item in value:
                new_value.append(self._serialize(item))
            return new_value
        elif isinstance(value, dict):
            new_value = {}
            for t_k, t_v in value.items():
                if isinstance(t_k, str):
                    t_k = t_k.encode("utf-16", "surrogatepass").decode("utf-16")
                new_value[t_k] = self._serialize(t_v)
            return new_value
        else:
            return value

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValueError(f"{self.name}字段，{self.invalid_message}")
        return self._serialize(value)


class DateTimeField(BaseField):
    name: str = ""
    default: str = None
    is_required: bool = False
    invalid_message: str = "应该是datetime"
    multi: bool = False
    time_format: str = "%Y-%m-%d %H:%M:%S"

    def validate(self, value):
        try:
            return datetime.strptime(value, self.time_format)
        except ValueError:
            raise ValueError(f"{self.name}字段，{self.invalid_message}，不符合{self.time_format}格式")


BASE_FIELD = (StringField, IntegerField, FloatField, ListField, BooleanField, DictField)


class BaseModel:
    def __init__(self, **kwargs):
        self.pre(**kwargs)
        self._permission()

    @staticmethod
    def _to_snake_case(inputs: dict):
        output = {}
        for key, value in inputs.items():
            if isinstance(value, dict):
                output[to_snake_case(key)] = BaseModel._to_snake_case(value)
            else:
                output[to_snake_case(key)] = value
        return output

    def pre(self, **kwargs):
        self._validate(**kwargs)

    def post(self, response):
        self._log(response)

    def _permission(self):
        pass

    def _validate(self, **kwargs):
        kwargs = BaseModel._to_snake_case(kwargs)
        object_dict = {}
        for attribute in [attr for attr in self.__dir__() if isinstance(self.__getattribute__(attr), BaseField)]:
            field: BaseField = self.__getattribute__(attribute)
            if getattr(field, "multi", False):
                values = kwargs.get(attribute, None)
                if (values is None or values == []) and field.default is None and field.is_required:
                    raise ValueError(f"{field.name}字段：必填")
                if values and not isinstance(values, list):
                    raise ValueError(f"{field.name}字段：是list")
                object_dict[attribute] = []
                if (values is None or values == []) and field.default is None:
                    if isinstance(field, ModelField):
                        object_dict[f"original_{attribute}"] = None
                    continue
                if (values is None or values == []) and field.default is None:
                    values = [field.default]
            else:
                values = kwargs.get(attribute, None)
                if values is None and field.default is None and field.is_required:
                    raise ValueError(f"{field.name}字段：必填")
                object_dict[attribute] = None
                if values is None and field.default is None:
                    if isinstance(field, ModelField):
                        object_dict[f"original_{attribute}"] = None
                    continue
                if values is not None:
                    values = [values]
                elif field.default is None:
                    values = []
                else:
                    values = [field.default]
            if not isinstance(values, list):
                raise ValueError(f"{field.name}: {field.invalid_message}")
            attribute_values = []
            for value in values:
                validated_value = field.validate(value)
                attribute_values.append(validated_value)
            if getattr(field, "multi", False):
                object_dict[attribute] = attribute_values
                if not isinstance(field, BASE_FIELD):
                    object_dict[f"original_{attribute}"] = values
            else:
                if attribute_values:
                    object_dict[attribute] = attribute_values[0]
                    if not isinstance(field, BASE_FIELD):
                        object_dict[f"original_{attribute}"] = values[0]
                else:
                    object_dict[attribute] = None

        self.__dict__.update(object_dict)

    def _log(self, response):
        pass

    def to_original_dict(self):
        keys = {attr for attr in self.__dict__ if not attr.startswith("_")}
        result = {}
        while keys:
            key = keys.pop()
            if key.startswith("original") and key[9:] in keys:
                result[key[9:]] = self.__dict__[key]
                keys.remove(key[9:])
            elif f"original_{key}" in self.__dict__:
                result[key] = self.__dict__[f"original_{key}"]
                keys.remove(f"original_{key}")
            else:
                result[key] = self.__dict__[key]
        return result

    def to_validate_dict(self):
        keys = {attr for attr in self.__dict__ if not attr.startswith("_")}
        result = {}
        while keys:
            key = keys.pop()
            if key.startswith("original") and key[9:] in keys:
                result[key[9:]] = self.__dict__[key[9:]]
                keys.remove(key[9:])
            elif f"original_{key}" in self.__dict__:
                result[key] = self.__dict__[key]
                keys.remove(f"original_{key}")
            else:
                result[key] = self.__dict__[key]
        return result

    def __repr__(self):
        r = ", ".join(f"{k}={str(v)}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({r})"


class ModelField(BaseField):
    name: str = ""
    default: object = None
    model: BaseModel.__class__ = None
    is_required: bool = False
    invalid_message: str = "应该是model"
    multi: bool = False

    def validate(self, value):
        if not self.model:
            raise ValueError(f"{self.name}字段：model字段必填")
        if not isinstance(value, dict):
            raise ValueError(f"{self.name}字段：格式错误，应为dict类型")
        try:
            return self.model(**value)
        except ValueError as e:
            raise ValueError(f"{self.name}字段：{e}")

    class Config:
        arbitrary_types_allowed = True
