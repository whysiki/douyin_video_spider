import re
from pathlib import Path
import json


def sanitize_filename(filename: str):
    assert isinstance(filename, str), "filename must be a string"
    filename = filename.replace("\n", "").replace("\r", "")
    return re.sub(r'[\/:*?"<>|]', "_", filename)


def format_digg_count(digg_count: int | float) -> str:
    assert isinstance(
        digg_count, (int, float)
    ), "digg_count must be an integer or float"
    return f"{digg_count / 10000:.1f}W" if digg_count >= 10000 else str(digg_count)


def read_statejson_and_get_cookie_headers(
    state_json_path: str | Path = None,
) -> tuple[dict, dict]:
    if state_json_path:
        assert isinstance(
            state_json_path, (str, Path)
        ), "state_json_path must be a string or Path"
        assert Path(state_json_path).exists(), "state_json_path does not exist"

    defaut_state_json_path = Path(__file__).parent / "state.json"

    assert defaut_state_json_path.exists(), "default state.json does not exist"

    with open(
        (defaut_state_json_path if not state_json_path else state_json_path),
        "r",
        encoding="utf-8",
    ) as file:
        state_data = json.load(file)

    cookies = {
        cookie["name"]: cookie["value"]
        for cookie in state_data["cookies"]
        if cookie["name"]
    }
    headers = {
        item["name"]: item["value"]
        for item in state_data["origins"][0]["localStorage"]
        if item["name"]
    }
    return cookies, headers
