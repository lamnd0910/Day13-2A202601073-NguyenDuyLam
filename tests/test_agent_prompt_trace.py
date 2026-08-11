from __future__ import annotations

from structlog.contextvars import bind_contextvars, clear_contextvars

from app import agent as agent_module


class ManagedPrompt:
    version = 3

    def compile(self, **variables: str) -> str:
        return (
            f"Feature={variables['feature']}\n"
            f"Docs={variables['docs']}\n"
            f"Question={variables['message']}"
        )


class RecordingLangfuseClient:
    def __init__(self) -> None:
        self.prompt = ManagedPrompt()
        self.trace_updates: list[dict] = []
        self.span_updates: list[dict] = []
        self.generation_updates: list[dict] = []

    def get_prompt(self, name: str, **kwargs):
        return self.prompt

    def update_current_trace(self, **kwargs) -> None:
        self.trace_updates.append(kwargs)

    def update_current_span(self, **kwargs) -> None:
        self.span_updates.append(kwargs)

    def update_current_generation(self, **kwargs) -> None:
        self.generation_updates.append(kwargs)


def run_without_observers(
    monkeypatch,
    agent: agent_module.LabAgent,
    **run_kwargs,
):
    monkeypatch.setattr(
        agent,
        "_retrieve",
        lambda message: agent_module.LabAgent._retrieve.__wrapped__(agent, message),
    )
    monkeypatch.setattr(
        agent,
        "_generate",
        lambda prompt, **kwargs: agent_module.LabAgent._generate.__wrapped__(
            agent,
            prompt,
            **kwargs,
        ),
    )
    return agent_module.LabAgent.run.__wrapped__(agent, **run_kwargs)


def test_agent_links_prompt_version_to_trace_and_generation(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public-key")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    monkeypatch.setenv("LANGFUSE_PROMPT_LABEL", "production")
    client = RecordingLangfuseClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)

    agent = agent_module.LabAgent()
    run_without_observers(
        monkeypatch,
        agent,
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="Explain traces",
    )

    trace_metadata = client.trace_updates[-1]["metadata"]
    generation_update = client.generation_updates[-1]
    assert trace_metadata == {
        "prompt_name": "day13-chat",
        "prompt_label": "production",
        "prompt_version": "3",
        "prompt_source": "langfuse",
    }
    assert generation_update["prompt"] is client.prompt
    assert generation_update["metadata"]["component"] == "llm"
    assert generation_update["metadata"]["prompt_version"] == "3"
    assert client.span_updates[-1]["metadata"]["component"] == "rag"
    assert client.span_updates[-1]["metadata"]["doc_count"] == 1


def test_agent_links_correlation_id_to_trace(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public-key")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret-key")
    client = RecordingLangfuseClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    clear_contextvars()
    bind_contextvars(correlation_id="req-a1b2c3d4")

    try:
        agent = agent_module.LabAgent()
        run_without_observers(
            monkeypatch,
            agent,
            user_id="student-01",
            feature="qa",
            session_id="session-01",
            message="Explain traces",
        )
    finally:
        clear_contextvars()

    assert client.trace_updates[-1]["metadata"]["correlation_id"] == "req-a1b2c3d4"
