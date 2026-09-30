import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_path(final_path: Path) -> Iterator[Path]:
    """Yield a temporary sibling path to write to; on clean exit, move it over final_path.

    os.replace is atomic on a single filesystem, so a concurrent reader sees either the
    complete old file or the complete new file, never a partially written one. If the
    body or the replace raises, final_path is left untouched and the temp file is removed.
    """
    tmp_path = final_path.with_name(final_path.name + ".tmp")
    try:
        yield tmp_path
        os.replace(tmp_path, final_path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise