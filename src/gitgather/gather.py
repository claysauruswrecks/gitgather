import subprocess
import os
import logging
import fnmatch


def capture_tree_output(repo_path, exclude_patterns=None):
    """Capture the directory tree structure using the `tree` command, excluding specified patterns."""
    exclude_patterns = exclude_patterns or []
    exclude_option = []
    for pattern in exclude_patterns:
        exclude_option.extend(["-I", pattern])

    try:
        tree_output = subprocess.check_output(
            ["tree", repo_path, *exclude_option], text=True
        )
        return tree_output
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to capture directory tree structure: {e}")
        return ""


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


def apply_filters(paths, repo_path, include_patterns=None, exclude_patterns=None):
    filtered_paths = []

    for path in paths:
        if exclude_patterns and match_patterns(path, exclude_patterns, repo_path):
            continue
        if include_patterns and not match_patterns(path, include_patterns, repo_path):
            continue
        filtered_paths.append(path)

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
):
    """Generate an overview of the repository including file contents."""
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    repo_path = os.path.abspath(repo_path)

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
        file_paths = [
            path
            for path in file_paths
            if not match_patterns(path, exclude_patterns, repo_path)
        ]

    filtered_file_paths = apply_filters(file_paths, repo_path, include, exclude)

    tree_output = capture_tree_output(repo_path, exclude)

    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write(f"```\n{tree_output}\n```\n\n")

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
