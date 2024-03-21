import subprocess
import os
import logging
import fnmatch


def capture_tree_output(repo_path, exclude_patterns=None):
    """Capture the directory tree structure using the `tree` command, excluding specified patterns."""
    exclude_patterns = exclude_patterns or [
        ".git"
    ]  # Default to excluding .git if no patterns specified
    exclude_option = "|".join(exclude_patterns)

    try:
        tree_output = subprocess.check_output(
            ["tree", repo_path, "-I", exclude_option], text=True
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


def match_patterns(filepath, patterns):
    """Check if the filepath matches any of the given patterns."""
    return any(
        fnmatch.fnmatch(filepath, pattern)
        or fnmatch.fnmatch(os.path.basename(filepath), pattern)
        for pattern in patterns
    )


def apply_filters(files, include_patterns=None, exclude_patterns=None):
    """Filter the files based on include and exclude patterns."""
    filtered_files = files

    if include_patterns:
        filtered_files = [
            f for f in filtered_files if match_patterns(f, include_patterns)
        ]

    if exclude_patterns:
        filtered_files = [
            f for f in filtered_files if not match_patterns(f, exclude_patterns)
        ]

    return filtered_files


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

    tree_output = capture_tree_output(repo_path, exclude)

    if no_git:
        file_paths = [
            os.path.join(dp, f)
            for dp, _, filenames in os.walk(repo_path)
            for f in filenames
        ]
    else:
        file_paths = [os.path.join(repo_path, f) for f in get_git_files(repo_path)]

    file_paths = apply_filters(file_paths, include, exclude)

    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write(f"```\n{tree_output}\n```\n\n")

        for filepath in file_paths:
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
