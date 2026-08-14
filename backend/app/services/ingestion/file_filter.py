"""
Repository file filtering.
"""

from pathlib import PurePosixPath


DEFAULT_IGNORED_DIRECTORIES = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "coverage",
    ".next",
}

DEFAULT_IGNORED_FILES = {
    ".DS_Store",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".gitignore",
    ".dockerignore",
}

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".kts",
    ".sql",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".md",
    ".txt",
}


class RepositoryFileFilter:
    """
    Determines which repository files should be
    processed by RepoRAG.
    """

    def __init__(
        self,
        include_tests: bool = True,
        include_documentation: bool = True,
    ) -> None:
        self.include_tests = include_tests
        self.include_documentation = include_documentation

    def should_ignore_directory(
        self,
        path: str,
    ) -> bool:

        parts = PurePosixPath(path).parts

        return any(
            part in DEFAULT_IGNORED_DIRECTORIES
            for part in parts
        )

    def should_ignore_file(
        self,
        path: str,
    ) -> bool:

        pure_path = PurePosixPath(path)

        if pure_path.name in DEFAULT_IGNORED_FILES:
            return True

        if self.should_ignore_directory(path):
            return True

        filename_lower = pure_path.name.lower()

        if not self.include_tests:
            if (
                "test" in filename_lower
                or "spec" in filename_lower
            ):
                return True

        if not self.include_documentation:
            if pure_path.suffix.lower() in {
                ".md",
                ".txt",
            }:
                return True

        return False

    def is_supported_extension(
        self,
        path: str,
    ) -> bool:

        suffix = PurePosixPath(
            path
        ).suffix.lower()

        return suffix in SUPPORTED_EXTENSIONS

    def should_process(
        self,
        path: str,
    ) -> bool:

        if self.should_ignore_file(path):
            return False

        return self.is_supported_extension(path)