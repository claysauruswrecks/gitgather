import subprocess
import os
import logging
import fnmatch
from typing import LiteralString


def capture_tree_output(repo_path, filtered_file_paths):
    """Capture the directory tree structure using the filtered file paths."""
    tree_lines = ["."]
    path_tree = {}

    for file_path in filtered_file_paths:
        relative_path = os.path.relpath(file_path, start=repo_path)
        path_parts = relative_path.split(os.sep)

        current_level = path_tree
        for part in path_parts:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]

    def build_tree(tree, level=0, prefix=""):
        empty_dirs = []
        dirs_with_files = []
        files = []

        for name, subtree in tree.items():
            if subtree:
                dirs_with_files.append((name, subtree))
            else:
                if os.path.isdir(os.path.join(repo_path, name)):
                    empty_dirs.append(name)
                else:
                    files.append(name)

        for name in sorted(empty_dirs):
            tree_lines.append(f"{prefix}├── {name}")

        for i, (name, subtree) in enumerate(sorted(dirs_with_files)):
            is_last = i == len(dirs_with_files) - 1 and not files
            tree_lines.append(f"{prefix}{'└── ' if is_last else '├── '}{name}")
            build_tree(subtree, level + 1, prefix + ("    " if is_last else "│   "))

        for i, name in enumerate(sorted(files)):
            is_last = i == len(files) - 1
            tree_lines.append(f"{prefix}{'└── ' if is_last else '├── '}{name}")

    build_tree(path_tree)

    return "\n".join(tree_lines)


def get_git_files(repo_path):
    """Return a list of all files tracked by Git in the given repository path."""
    try:
        with subprocess.Popen(
            ["git", "-C", repo_path, "ls-files"], stdout=subprocess.PIPE, text=True
        ) as proc:
            tracked_files = proc.stdout.read().splitlines()
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get Git files: {e}")
        tracked_files = []
    return tracked_files


def match_patterns(path, patterns, base_path):
    """Check if the path matches any of the given patterns."""
    relative_path = os.path.relpath(path, start=base_path)
    for pattern in patterns:
        if os.path.isdir(os.path.join(base_path, pattern)):
            # Directory pattern
            if relative_path == pattern or relative_path.startswith(pattern + os.sep):
                return True
        elif fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(
            os.path.basename(relative_path), pattern
        ):
            # File pattern
            return True
    return False


def is_glob_pattern(pattern):
    return any(char in pattern for char in "*?[]")


import os
import fnmatch
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def apply_filters(paths, repo_path, include_patterns=None, exclude_patterns=None):
    filtered_paths = []

    include_globs = (
        [pattern for pattern in include_patterns if is_glob_pattern(pattern)]
        if include_patterns
        else []
    )
    include_files = (
        [pattern for pattern in include_patterns if not is_glob_pattern(pattern)]
        if include_patterns
        else []
    )
    exclude_globs = (
        [pattern for pattern in exclude_patterns if is_glob_pattern(pattern)]
        if exclude_patterns
        else []
    )
    exclude_files = (
        [pattern for pattern in exclude_patterns if not is_glob_pattern(pattern)]
        if exclude_patterns
        else []
    )

    logger.debug(f"Include globs: {include_globs}")
    logger.debug(f"Include files: {include_files}")
    logger.debug(f"Exclude globs: {exclude_globs}")
    logger.debug(f"Exclude files: {exclude_files}")

    for path in paths:
        logger.debug(f"Processing path: {path}")

        # Check exclude file patterns first
        if any(path == pattern for pattern in exclude_files):
            logger.debug(f"Path {path} matches exclude file pattern, skipping")
            continue

        # Process glob patterns second
        if include_globs:
            if any(fnmatch.fnmatch(path, pattern) for pattern in include_globs):
                logger.debug(f"Path {path} matches include glob pattern")
                if not any(fnmatch.fnmatch(path, pattern) for pattern in exclude_globs):
                    logger.debug(
                        f"Path {path} does not match exclude glob pattern, adding to filtered paths"
                    )
                    filtered_paths.append(path)
                else:
                    logger.debug(f"Path {path} matches exclude glob pattern, skipping")
            else:
                logger.debug(
                    f"Path {path} does not match include glob pattern, skipping"
                )
        else:
            if not any(fnmatch.fnmatch(path, pattern) for pattern in exclude_globs):
                logger.debug(
                    f"Path {path} does not match exclude glob pattern, adding to filtered paths"
                )
                filtered_paths.append(path)
            else:
                logger.debug(f"Path {path} matches exclude glob pattern, skipping")

        # Process include file patterns last
        if include_files:
            if any(path == pattern for pattern in include_files):
                logger.debug(
                    f"Path {path} matches include file pattern, adding to filtered paths"
                )
                filtered_paths.append(path)
            else:
                logger.debug(
                    f"Path {path} does not match include file pattern, skipping"
                )

    logger.debug(f"Filtered paths: {filtered_paths}")
    return filtered_paths


def generate_repo_overview(
    repo_path,
    output_file,
    include=None,
    exclude=None,
    no_git=False,
    all_files=False,
    no_dotfiles=False,
    verbose=False,
    tree_output=True,
):
    # ...

    if no_git:
        file_paths = [
            os.path.join(dp, f)
            for dp, _, filenames in os.walk(repo_path)
            for f in filenames
        ]
    else:
        file_paths = [os.path.join(repo_path, f) for f in get_git_files(repo_path)]

    if exclude:
        exclude_patterns = [os.path.join(repo_path, pattern) for pattern in exclude]
    else:
        exclude_patterns = []

    filtered_file_paths = apply_filters(file_paths, repo_path, include, exclude)

    if tree_output:
        tree_lines = capture_tree_output(
            repo_path=repo_path, filtered_file_paths=filtered_file_paths
        )

    with open(output_file, "w", encoding="utf-8") as outfile:
        if tree_output:
            outfile.write(f"```\n{tree_lines}\n```\n\n")

        for filepath in filtered_file_paths:
            relative_path = os.path.relpath(filepath, start=repo_path)
            try:
                logging.info(f"Processing file: {relative_path}")
                with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
                    file_contents = file.read()
                    outfile.write(
                        f"File: {relative_path}\n```\n{file_contents}\n```\n\n"
                    )
            except Exception as e:
                logging.error(f"Failed to process {filepath}: {e}")
