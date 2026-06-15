import re
import uuid


MVC_ID_PREFIX = "mvc_"
MVC_ID_RE = re.compile(r"^mvc_[0-9a-f]{32}$")


def new_id() -> str:
    return f"{MVC_ID_PREFIX}{uuid.uuid4().hex}"


def is_mvc_id(value: object) -> bool:
    return isinstance(value, str) and bool(MVC_ID_RE.match(value))
