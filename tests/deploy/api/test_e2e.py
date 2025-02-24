import os

import httpx
import pytest

from ragna._utils import timeout_after
from ragna.core._utils import default_user
from ragna.deploy import Config
from tests.utils import ragna_api


@pytest.mark.parametrize("database", ["memory", "sqlite"])
def test_e2e(tmp_local_root, database):
    if database == "memory":
        database_url = "memory"
    elif database == "sqlite":
        database_url = f"sqlite:///{tmp_local_root / 'ragna.db'}"

    config = Config(
        local_cache_root=tmp_local_root, api=dict(database_url=database_url)
    )
    check_api(config)


@timeout_after()
def check_api(config):
    document_root = config.local_cache_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")

    with ragna_api(config), httpx.Client(base_url=config.api.url) as client:
        username = default_user()
        token = (
            client.post(
                "/token",
                data={
                    "username": username,
                    "password": os.environ.get(
                        "AI_PROXY_DEMO_AUTHENTICATION_PASSWORD", username
                    ),
                },
            )
            .raise_for_status()
            .json()
        )
        client.headers["Authorization"] = f"Bearer {token}"

        assert client.get("/chats").raise_for_status().json() == []

        document_info = (
            client.get("/document", params={"name": document_path.name})
            .raise_for_status()
            .json()
        )
        document = document_info["document"]
        assert document["name"] == document_path.name

        with open(document_path, "rb") as file:
            client.post(
                document_info["url"],
                data=document_info["data"],
                files={"file": file},
            ).raise_for_status()

        components = client.get("/components").raise_for_status().json()
        documents = components["documents"]
        assert set(documents) == config.document.supported_suffixes()
        source_storages = [
            json_schema["title"] for json_schema in components["source_storages"]
        ]
        assert source_storages == [
            source_storage.display_name()
            for source_storage in config.components.source_storages
        ]
        assistants = [json_schema["title"] for json_schema in components["assistants"]]
        assert assistants == [
            assistant.display_name() for assistant in config.components.assistants
        ]

        source_storage = source_storages[0]
        assistant = assistants[0]

        chat_metadata = {
            "name": "test-chat",
            "source_storage": source_storage,
            "assistant": assistant,
            "params": {},
            "documents": [document],
        }
        chat = client.post("/chats", json=chat_metadata).raise_for_status().json()
        assert chat["metadata"] == chat_metadata
        assert not chat["prepared"]
        assert chat["messages"] == []

        assert client.get("/chats").raise_for_status().json() == [chat]
        assert client.get(f"/chats/{chat['id']}").raise_for_status().json() == chat

        json = client.post(f"/chats/{chat['id']}/prepare").raise_for_status().json()
        message, chat = json["message"], json["chat"]
        assert message["role"] == "system"
        assert message["sources"] == []
        assert chat["prepared"]
        assert len(chat["messages"]) == 1
        assert chat["messages"][-1] == message

        prompt = "?"
        json = (
            client.post(f"/chats/{chat['id']}/answer", params={"prompt": prompt})
            .raise_for_status()
            .json()
        )
        message, chat = json["message"], json["chat"]
        assert message["role"] == "assistant"
        assert {source["document"]["name"] for source in message["sources"]} == {
            document_path.name
        }
        assert len(chat["messages"]) == 3
        assert (
            chat["messages"][-2]["role"] == "user"
            and chat["messages"][-2]["sources"] == []
            and chat["messages"][-2]["content"] == prompt
        )
        assert chat["messages"][-1] == message

        client.delete(f"/chats/{chat['id']}").raise_for_status()
        assert client.get("/chats").raise_for_status().json() == []
