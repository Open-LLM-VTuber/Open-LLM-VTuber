"""Tests for :mod:`open_llm_vtuber.chat_history_manager`.

Chat histories live in ``chat_history/<conf_uid>/<history_uid>.json`` relative to
the working directory, so every test runs inside a temporary directory.  The
module also validates the ``conf_uid``/``history_uid`` values that arrive from a
WebSocket client, which is why the path helpers are covered as well.
"""

from __future__ import annotations

import json
import os
import re

import pytest

from open_llm_vtuber import chat_history_manager as chm

UID_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_[0-9a-f]{32}$")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Run each test inside its own temporary working directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def history_path(conf_uid: str, history_uid: str):
    return os.path.join("chat_history", conf_uid, f"{history_uid}.json")


def write_history(conf_uid: str, history_uid: str, data) -> None:
    path = history_path(conf_uid, history_uid)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False)


def write_raw(conf_uid: str, history_uid: str, text: str) -> None:
    path = history_path(conf_uid, history_uid)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def read_history(conf_uid: str, history_uid: str):
    with open(history_path(conf_uid, history_uid), encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------------- #
# Creating and reading histories
# --------------------------------------------------------------------------- #
def test_create_new_history_returns_a_uid_and_writes_metadata(workspace):
    uid = chm.create_new_history("char_a")

    assert UID_PATTERN.match(uid)
    assert os.path.exists(history_path("char_a", uid))

    data = read_history("char_a", uid)
    assert len(data) == 1
    assert data[0]["role"] == "metadata"
    assert "timestamp" in data[0]


def test_create_new_history_without_conf_uid_returns_an_empty_string(workspace):
    assert chm.create_new_history("") == ""
    assert not os.path.exists("chat_history")


def test_store_message_appends_messages_and_get_history_hides_metadata(workspace):
    uid = chm.create_new_history("char_a")

    chm.store_message("char_a", uid, "human", "hello", name="You")
    chm.store_message("char_a", uid, "ai", "hi there", avatar="mao.png")

    messages = chm.get_history("char_a", uid)
    assert [message["role"] for message in messages] == ["human", "ai"]
    assert messages[0]["content"] == "hello"
    assert messages[0]["name"] == "You"
    assert messages[1]["avatar"] == "mao.png"
    assert all(
        "name" not in message or message["role"] == "human" for message in messages
    )


def test_store_message_omits_optional_fields_when_not_given(workspace):
    uid = chm.create_new_history("char_a")
    chm.store_message("char_a", uid, "human", "hello")

    message = chm.get_history("char_a", uid)[0]
    assert "name" not in message
    assert "avatar" not in message
    assert message["role"] == "human"
    assert message["content"] == "hello"
    assert "timestamp" in message


@pytest.mark.parametrize(
    ("conf_uid", "history_uid"),
    [("", "uid"), ("char_a", ""), ("", "")],
)
def test_store_message_ignores_missing_uids(workspace, conf_uid, history_uid):
    chm.store_message(conf_uid, history_uid, "human", "hello")
    assert not os.path.exists("chat_history")


def test_get_history_returns_an_empty_list_for_an_unknown_history(workspace):
    assert chm.get_history("char_a", "missing") == []


def test_get_history_returns_an_empty_list_without_uids(workspace):
    assert chm.get_history("", "uid") == []
    assert chm.get_history("char_a", "") == []


def test_store_message_replaces_a_history_file_with_invalid_json(workspace):
    chm.create_new_history("char_a")
    write_raw("char_a", "broken", "{not json at all")

    chm.store_message("char_a", "broken", "human", "hello")

    assert [message["content"] for message in chm.get_history("char_a", "broken")] == [
        "hello"
    ]


@pytest.mark.xfail(
    reason=(
        "the json.JSONDecodeError guard does not cover valid JSON that is not a list: "
        "history_data.append() then raises AttributeError and the message is lost"
    ),
    strict=False,
)
def test_store_message_survives_a_history_file_that_is_not_a_list(workspace):
    chm.create_new_history("char_a")
    write_raw("char_a", "broken", '{"role": "metadata"}')

    chm.store_message("char_a", "broken", "human", "hello")

    assert [message["content"] for message in chm.get_history("char_a", "broken")] == [
        "hello"
    ]


def test_unicode_conf_uid_is_stored_in_its_own_directory(workspace):
    uid = chm.create_new_history("角色_一")
    chm.store_message("角色_一", uid, "ai", "你好")

    assert os.path.isdir(os.path.join("chat_history", "角色_一"))
    assert chm.get_history("角色_一", uid)[0]["content"] == "你好"


# --------------------------------------------------------------------------- #
# Metadata
# --------------------------------------------------------------------------- #
def test_get_metadata_returns_the_first_metadata_entry(workspace):
    uid = chm.create_new_history("char_a")
    assert chm.get_metadata("char_a", uid)["role"] == "metadata"


def test_get_metadata_returns_an_empty_dict_for_unknown_histories(workspace):
    assert chm.get_metadata("char_a", "missing") == {}
    assert chm.get_metadata("", "uid") == {}


def test_update_metadate_merges_with_the_existing_metadata(workspace):
    uid = chm.create_new_history("char_a")
    original_timestamp = chm.get_metadata("char_a", uid)["timestamp"]

    assert chm.update_metadate("char_a", uid, {"title": "greeting"}) is True

    metadata = chm.get_metadata("char_a", uid)
    assert metadata["title"] == "greeting"
    assert metadata["timestamp"] == original_timestamp


def test_update_metadate_inserts_metadata_when_the_file_has_none(workspace):
    write_history(
        "char_a", "uid", [{"role": "human", "timestamp": "t", "content": "hello"}]
    )

    assert chm.update_metadate("char_a", "uid", {"title": "greeting"}) is True

    data = read_history("char_a", "uid")
    assert data[0]["role"] == "metadata"
    assert data[0]["title"] == "greeting"
    assert data[1]["content"] == "hello"


def test_update_metadate_returns_false_for_an_unknown_history(workspace):
    assert chm.update_metadate("char_a", "missing", {"title": "x"}) is False
    assert chm.update_metadate("", "", {"title": "x"}) is False


# --------------------------------------------------------------------------- #
# Listing, renaming, deleting and editing
# --------------------------------------------------------------------------- #
def test_get_history_list_returns_the_latest_message_per_history(workspace):
    first = chm.create_new_history("char_a")
    second = chm.create_new_history("char_a")
    chm.store_message("char_a", first, "human", "older")
    chm.store_message("char_a", second, "human", "newer")
    write_history(
        "char_a",
        first,
        [
            {"role": "metadata", "timestamp": "2024-01-01T00:00:00"},
            {"role": "human", "timestamp": "2024-01-01T00:00:01", "content": "older"},
        ],
    )
    write_history(
        "char_a",
        second,
        [
            {"role": "metadata", "timestamp": "2024-01-01T00:00:00"},
            {"role": "human", "timestamp": "2024-02-01T00:00:01", "content": "newer"},
        ],
    )

    histories = chm.get_history_list("char_a")

    assert [history["uid"] for history in histories] == [second, first]
    assert histories[0]["latest_message"]["content"] == "newer"
    assert histories[0]["timestamp"] == "2024-02-01T00:00:01"


def test_get_history_list_removes_empty_histories(workspace):
    with_messages = chm.create_new_history("char_a")
    empty = chm.create_new_history("char_a")
    chm.store_message("char_a", with_messages, "human", "hello")

    histories = chm.get_history_list("char_a")

    assert [history["uid"] for history in histories] == [with_messages]
    assert not os.path.exists(history_path("char_a", empty))


def test_get_history_list_without_conf_uid_returns_an_empty_list(workspace):
    assert chm.get_history_list("") == []


def test_modify_latest_message_updates_the_matching_role(workspace):
    uid = chm.create_new_history("char_a")
    chm.store_message("char_a", uid, "human", "hello")
    chm.store_message("char_a", uid, "ai", "hi")

    assert chm.modify_latest_message("char_a", uid, "ai", "changed") is True
    assert chm.get_history("char_a", uid)[-1]["content"] == "changed"


def test_modify_latest_message_returns_false_when_the_role_differs(workspace):
    uid = chm.create_new_history("char_a")
    chm.store_message("char_a", uid, "ai", "hi")

    assert chm.modify_latest_message("char_a", uid, "human", "nope") is False
    assert chm.get_history("char_a", uid)[-1]["content"] == "hi"


def test_modify_latest_message_returns_false_for_an_unknown_history(workspace):
    assert chm.modify_latest_message("char_a", "missing", "ai", "x") is False


def test_rename_history_file_moves_the_file(workspace):
    uid = chm.create_new_history("char_a")
    chm.store_message("char_a", uid, "human", "hello")

    assert chm.rename_history_file("char_a", uid, "renamed") is True
    assert os.path.exists(history_path("char_a", "renamed"))
    assert not os.path.exists(history_path("char_a", uid))
    assert chm.get_history("char_a", "renamed")[0]["content"] == "hello"


def test_rename_history_file_returns_false_for_a_missing_source(workspace):
    assert chm.rename_history_file("char_a", "missing", "renamed") is False
    assert chm.rename_history_file("char_a", "", "renamed") is False


def test_delete_history_removes_the_file(workspace):
    uid = chm.create_new_history("char_a")

    assert chm.delete_history("char_a", uid) is True
    assert not os.path.exists(history_path("char_a", uid))
    assert chm.delete_history("char_a", uid) is False


def test_delete_history_returns_false_without_uids(workspace):
    assert chm.delete_history("", "") is False


# --------------------------------------------------------------------------- #
# Path validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("component", "expected"),
    [
        ("char_a", "char_a"),
        ("  char_a  ", "char_a"),
        ("../other", "other"),  # only the basename is kept
        ("nested/name", "name"),
        ("名字", "名字"),
    ],
)
def test_path_components_are_reduced_to_a_safe_basename(component, expected):
    assert chm._sanitize_path_component(component) == expected


@pytest.mark.parametrize("component", ["", "x" * 256, "bad\x01name"])
def test_invalid_path_components_are_rejected(component):
    with pytest.raises(ValueError):
        chm._sanitize_path_component(component)


@pytest.mark.xfail(
    reason="'..' passes the filename check, so conf_uid='..' escapes the chat_history directory",
    strict=False,
)
def test_dotdot_path_component_is_rejected():
    with pytest.raises(ValueError):
        chm._sanitize_path_component("..")


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("history", True), ("", False), ("x" * 255, True), ("x" * 256, False)],
)
def test_is_safe_filename(filename, expected):
    assert chm._is_safe_filename(filename) is expected
