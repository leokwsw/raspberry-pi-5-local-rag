import pytest

from local_rag.generation import EchoGenerator


@pytest.mark.asyncio
async def test_echo_generator_is_deterministic() -> None:
    assert await EchoGenerator().generate("hello") == "hello"
