import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_path(final_path: Path) -> Iterator[Path]:
    """Yield a sibling temp path and replace the destination after a successful write.

    Same-filesystem replacement keeps readers from seeing a partial artifact. On failure,
    remove the temp file and leave the existing destination intact.
    """
    tmp_path = final_path.with_name(final_path.name + ".tmp")
    try:
        yield tmp_path
        os.replace(tmp_path, final_path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise