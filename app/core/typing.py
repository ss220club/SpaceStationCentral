from typing import Any


JSONObject = dict[str, Any]
JSONList = list["JSONAny"]
JSONAny = JSONObject | JSONList | str | int | float | bool
