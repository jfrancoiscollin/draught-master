import os


def pytest_unconfigure(config):
    # aiosqlite.Connection is a non-daemon Thread; a leaked connection
    # in any test blocks interpreter shutdown indefinitely on CI runners.
    # Force exit after pytest prints its summary.
    exitstatus = getattr(config, "_pytest_unconfigure_exitstatus", 0)
    os._exit(int(exitstatus) if exitstatus is not None else 0)


def pytest_sessionfinish(session, exitstatus):
    session.config._pytest_unconfigure_exitstatus = exitstatus
