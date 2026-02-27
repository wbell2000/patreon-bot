import pytest


pytestmark = pytest.mark.skip(
    reason=(
        "Legacy Python Cloudflare Worker tests are obsolete. "
        "The active worker entrypoint is JavaScript at cloudflare_worker/src/worker.js."
    )
)


def test_worker_async_placeholder():
    """Keep test module presence explicit while the worker implementation is JS-only."""
    assert True
