from app.memory import ConversationMemory


def test_memory_keeps_only_recent_messages(tmp_path):
    memory = ConversationMemory(str(tmp_path / "memory.db"), max_messages=4)
    session_id = memory.new_session_id()

    memory.append_exchange(session_id, "q1", "a1")
    memory.append_exchange(session_id, "q2", "a2")
    memory.append_exchange(session_id, "q3", "a3")

    assert memory.recent(session_id) == [
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "q3"},
        {"role": "assistant", "content": "a3"},
    ]


def test_memory_can_clear_session(tmp_path):
    memory = ConversationMemory(str(tmp_path / "memory.db"))
    memory.append_exchange("session", "question", "answer")

    memory.clear("session")

    assert memory.recent("session") == []
