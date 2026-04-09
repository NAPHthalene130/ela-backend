def run_agent(*args, **kwargs):
    from agent.entry import run_agent as _run_agent

    return _run_agent(*args, **kwargs)


def run_agent_stream(*args, **kwargs):
    from agent.entry import run_agent_stream as _run_agent_stream

    return _run_agent_stream(*args, **kwargs)


__all__ = ["run_agent", "run_agent_stream"]
