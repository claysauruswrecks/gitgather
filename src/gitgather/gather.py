import subprocess
import os
import logging
import fnmatch
from typing import LiteralString

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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
        logging.error("Failed to get Git files: %s", e)
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


def apply_filters(paths, repo_path, include_patterns=None, exclude_patterns=None):
    debug = False
    if logger.isEnabledFor(logging.DEBUG):
        debug = True
    include_patterns = include_patterns or []
    exclude_patterns = exclude_patterns or []

    include_globs = [p for p in include_patterns if is_glob_pattern(p)]
    include_files = [p for p in include_patterns if not is_glob_pattern(p)]
    exclude_globs = [p for p in exclude_patterns if is_glob_pattern(p)]
    exclude_files = [p for p in exclude_patterns if not is_glob_pattern(p)]

    if debug:
        logger.debug("Include globs: %s", include_globs)
        logger.debug("Include files: %s", include_files)
        logger.debug("Exclude globs: %s", exclude_globs)
        logger.debug("Exclude files: %s", exclude_files)

    def is_excluded(path):
        if debug:
            logger.debug(
                "checking path %s against exclude_files %s", path, exclude_files
            )
        if path in exclude_files:
            return True
        rel_path = os.path.relpath(path, start=repo_path)
        return any(rel_path == pattern for pattern in exclude_files) or any(
            rel_path.startswith(pattern + os.sep) for pattern in exclude_files
        )

    def is_included(path):
        if debug:
            logger.debug(
                "checking path %s against include_files %s", path, include_files
            )
        if path in include_files:
            return True
        rel_path = os.path.relpath(path, start=repo_path)
        return any(
            rel_path.startswith(pattern + os.sep) for pattern in include_files
        ) or any(os.path.basename(path) == pattern for pattern in include_files)

    def matches_glob(path, glob_patterns):
        if debug:
            logging.debug("checking %s against glob_patterns %s", path, glob_patterns)
        rel_path = os.path.relpath(path, start=repo_path)
        return any(fnmatch.fnmatch(rel_path, pattern) for pattern in glob_patterns)

    filtered_paths = []
    for path in paths:
        if debug:
            logger.debug("Processing path: %s", path)

        if is_excluded(path):
            if debug:
                logger.debug(
                    "Path %s is excluded, skipping",
                    path,
                )
            continue

        if is_included(path):
            if debug:
                logger.debug("Path %s is included, adding", path)
            filtered_paths.append(path)
            continue

        if include_globs:
            if matches_glob(path, include_globs) and not matches_glob(
                path, exclude_globs
            ):
                if debug:
                    logger.debug(
                        "Path %s matches include glob pattern %s, adding",
                        path,
                        include_globs,
                    )
                filtered_paths.append(path)
            else:
                if debug:
                    logger.debug(
                        "Path %s does not match include glob %s or matches exclude glob %s, skipping",
                        path,
                        include_globs,
                        exclude_globs,
                    )
        else:
            if not matches_glob(path, exclude_globs):
                if debug:
                    logger.debug(
                        "Path %s does not match exclude glob pattern %s, adding",
                        path,
                        exclude_globs,
                    )
                filtered_paths.append(path)
            else:
                if debug:
                    logger.debug(
                        "Path %s matches exclude glob pattern %s, skipping",
                        path,
                        exclude_globs,
                    )

    if debug:
        logger.debug("Filtered paths: %s", filtered_paths)
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
    """
    Generate an overview of a Git repository by concatenating file contents.

    Args:
        repo_path (str): Path to the Git repository.
        output_file (str): Output file path.
        include (list, optional): List of file patterns to include. Defaults to None.
        exclude (list, optional): List of file patterns to exclude. Defaults to None.
        no_git (bool, optional): Include all files, not just those tracked by Git. Defaults to False.
        all_files (bool, optional): Include all files, including hidden ones. Defaults to False.
        no_dotfiles (bool, optional): Exclude dotfiles. Defaults to False.
        verbose (bool, optional): Enable verbose output. Defaults to False.
        tree_output (bool, optional): Include directory tree structure in the output. Defaults to True.

    Returns:
        None
    """
    # Get all file paths in the repository
    all_file_paths = [
        os.path.join(dp, f)
        for dp, _, filenames in os.walk(repo_path)
        for f in filenames
    ]
    logger.debug("All file paths: %s", all_file_paths)

    # Determine the file paths to process based on the `no_git` flag
    if no_git:
        file_paths = all_file_paths
    else:
        file_paths = [os.path.join(repo_path, f) for f in get_git_files(repo_path)]
    logger.debug("File paths to process: %s", file_paths)

    # Apply filters to the file paths
    prefiltered_file_paths = apply_filters(
        paths=file_paths,
        repo_path=repo_path,
        include_patterns=include,
        exclude_patterns=exclude,
    )
    logger.debug("Prefiltered file paths: %s", prefiltered_file_paths)

    # If `include` patterns are provided, apply filters to all file paths as well
    if include:
        all_included_filtered_file_paths = apply_filters(
            paths=all_file_paths,
            repo_path=repo_path,
            include_patterns=include,
            exclude_patterns=exclude,
        )
        logger.debug(
            "All included filtered file paths: %s", all_included_filtered_file_paths
        )

        # Combine the prefiltered and all included filtered file paths
        filtered_file_paths = list(
            set(prefiltered_file_paths + all_included_filtered_file_paths)
        )
    else:
        filtered_file_paths = prefiltered_file_paths
    logger.debug("Final filtered file paths: %s", filtered_file_paths)

    # Generate the directory tree structure if `tree_output` is True
    if tree_output:
        tree_lines = capture_tree_output(
            repo_path=repo_path, filtered_file_paths=filtered_file_paths
        )
        logger.debug("Directory tree structure:\n%s", tree_lines)

    # Write the repository overview to the output file
    with open(output_file, "w", encoding="utf-8") as outfile:
        # Write the directory tree structure if `tree_output` is True
        if tree_output:
            outfile.write(f"```\n{tree_lines}\n```\n\n")

        # Process each filtered file path
        for filepath in filtered_file_paths:
            relative_path = os.path.relpath(filepath, start=repo_path)
            try:
                logger.info(f"Processing file: {relative_path}")
                with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
                    file_contents = file.read()
                    outfile.write(
                        f"File: {relative_path}\n```\n{file_contents}\n```\n\n"
                    )
            except Exception as e:
                logger.error(f"Failed to process {filepath}: {e}")
