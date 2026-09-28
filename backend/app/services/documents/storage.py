from pathlib import Path, PurePosixPath


class LocalFileStorage:
    """Stores uploaded files below a root directory.

    Files are addressed by a storage key: a POSIX path relative to the root. Keeping keys
    relative (instead of absolute paths) lets the upload directory move without a data
    migration and maps cleanly onto object storage later.
    """

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def save(self, key: str, data: bytes) -> None:
        path = self.resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # "xb" never overwrites an existing file; keys are random, so a clash is a bug.
        with path.open("xb") as file:
            file.write(data)

    def delete(self, key: str) -> None:
        self.resolve(key).unlink(missing_ok=True)

    def resolve(self, key: str) -> Path:
        relative = PurePosixPath(key)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError(f"Invalid storage key: {key!r}")
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"Invalid storage key: {key!r}")
        return path
