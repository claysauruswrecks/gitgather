import os
import tempfile
import shutil
import subprocess
from typing import Generator
import pytest
from gitgather.gather import (
    capture_tree_output,
    get_git_files,
    match_patterns,
    apply_filters,
    generate_repo_overview,
)

from typing import Any


@pytest.fixture
def test_repo() -> Generator[str, Any, None]:
    temp_dir: str = tempfile.mkdtemp()
    subprocess.run(args=["git", "init"], cwd=temp_dir)
    with open(file=os.path.join(temp_dir, "file1.txt"), mode="w") as f:
        f.write("File 1 contents")
    with open(file=os.path.join(temp_dir, "file2.txt"), mode="w") as f:
        f.write("File 2 contents")
    subprocess.run(args=["git", "add", "."], cwd=temp_dir)
    subprocess.run(args=["git", "commit", "-m", "Initial commit"], cwd=temp_dir)
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_capture_tree_output(test_repo: str) -> None:
    filtered_file_paths = [
        f"{test_repo}/file1.txt",
        f"{test_repo}/file2.txt",
    ]
    tree_output: str = capture_tree_output(
        repo_path=test_repo, filtered_file_paths=filtered_file_paths
    )
    assert "file1.txt" in tree_output
    assert "file2.txt" in tree_output


def test_get_git_files(test_repo: str) -> None:
    git_files: list[str] = get_git_files(repo_path=test_repo)
    assert "file1.txt" in git_files
    assert "file2.txt" in git_files


def test_match_patterns(test_repo: str) -> None:
    assert match_patterns(path="file1.txt", patterns=["*.txt"], base_path=test_repo)
    assert match_patterns(
        path=f"{test_repo}/file1.txt", patterns=["*.txt"], base_path=test_repo
    )
    assert not match_patterns(path="file1.txt", patterns=["*.md"], base_path=test_repo)
    assert not match_patterns(
        path=f"{test_repo}/file1.txt", patterns=["*.md"], base_path=test_repo
    )


def test_apply_filters(test_repo: str) -> None:
    files: list[str] = ["file1.txt", "file2.md", "file3.txt", "file4.rtf", "file5.rtf"]
    filtered_files: list = apply_filters(
        paths=files,
        repo_path=test_repo,
        include_patterns=["*.txt", "file4.rtf"],
        exclude_patterns=["file1.txt", "*.rtf"],
    )
    assert "file3.txt" in filtered_files
    assert "file4.rtf" in filtered_files
    assert "file1.txt" not in filtered_files
    assert "file2.md" not in filtered_files
    assert "file5.rtf" not in filtered_files


def test_apply_filters_with_directories(test_repo: str) -> None:
    # Create directories and files
    os.makedirs(os.path.join(test_repo, "dir1"))
    os.makedirs(os.path.join(test_repo, "dir2"))
    os.makedirs(os.path.join(test_repo, "dir3"))
    os.makedirs(os.path.join(test_repo, "dir4"))
    os.makedirs(os.path.join(test_repo, "dir4", "subdir"))

    paths = [
        "file1.txt",
        "file2.md",
        "file3.txt",
        "file4.rtf",
        "file5.rtf",
        "dir1",
        "dir2",
        "dir3",
        "dir4",
        os.path.join("dir4", "subdir"),
    ]

    filtered_paths = apply_filters(
        paths=paths,
        repo_path=test_repo,
        include_patterns=["*.txt", "dir1", "dir4/subdir"],
        exclude_patterns=["file1.txt", "dir2", "dir4", ".git"],
    )

    assert "file3.txt" in filtered_paths
    assert "dir1" in filtered_paths
    assert os.path.join("dir4", "subdir") in filtered_paths
    assert "file1.txt" not in filtered_paths
    assert "file2.md" not in filtered_paths
    assert "file4.rtf" not in filtered_paths
    assert "file5.rtf" not in filtered_paths
    assert "dir2" not in filtered_paths
    assert "dir3" not in filtered_paths
    assert "dir4" not in filtered_paths
    assert ".git" not in filtered_paths


def test_generate_repo_overview(test_repo: str) -> None:
    output_file: str = os.path.join(test_repo, "output.txt")
    # Run it without tree output.
    generate_repo_overview(
        repo_path=test_repo, output_file=output_file, tree_output=False
    )
    with open(file=output_file, mode="r") as f:
        content: str = f.read()
        assert content.count("file1.txt") == 1
        assert content.count("file2.txt") == 1
        assert "File 1 contents" in content
        assert "File 2 contents" in content

    # Run it again with the tree output enabled.
    generate_repo_overview(
        repo_path=test_repo, output_file=output_file, tree_output=True
    )
    with open(file=output_file, mode="r") as f:
        content = f.read()
        # Filenames should exist twice from tree and overview.
        assert content.count("file1.txt") == 2
        assert content.count("file2.txt") == 2

        # Contents should be present once.
        assert content.count("File 1 contents") == 1
        assert content.count("File 2 contents") == 1


def test_nogit_and_exclude_git_directory(test_repo: str) -> None:
    # Create a non-Git file in the repository
    with open(file=os.path.join(test_repo, "file.txt"), mode="w") as f:
        f.write("Regular file")

    # Generate the repository overview with --no-git and --exclude .git options.
    output_file: str = os.path.join(test_repo, "output.txt")
    generate_repo_overview(
        repo_path=test_repo, output_file=output_file, exclude=[".git"], no_git=True
    )

    # Check that the .git directory and its contents are not included in the output.
    with open(file=output_file, mode="r") as f:
        content = f.read()
        assert ".git/config" not in content
        assert ".git/HEAD" not in content

    with open(file=output_file, mode="r") as f:
        content = f.read()
        # Check that the non-Git file is included in the output.
        assert "file.txt" in content
        assert content.count("file.txt") == 2

        # Git files should be in here as well.
        assert content.count("file1.txt") == 2
        assert content.count("file2.txt") == 2

        # Contents should be present once.
        assert content.count("File 1 contents") == 1
        assert content.count("File 2 contents") == 1


def test_nogit_exclude_multiple_patterns(test_repo):
    # Create additional files and directories
    os.makedirs(os.path.join(test_repo, "dir1"))
    os.makedirs(os.path.join(test_repo, "dir2"))
    os.makedirs(os.path.join(test_repo, "dir3"))
    os.makedirs(os.path.join(test_repo, "dir4"))
    os.makedirs(os.path.join(test_repo, "dir5"))
    os.makedirs(os.path.join(test_repo, "dir6"))
    os.makedirs(os.path.join(test_repo, "dir7"))
    # Should not be included.
    with open(os.path.join(test_repo, "file3.txt"), "w") as f:
        f.write("File 3 contents")

    # Should be included
    with open(os.path.join(test_repo, "file4.md"), "w") as f:
        f.write("File 4 contents")
    with open(os.path.join(test_repo, "file5.md"), "w") as f:
        f.write("File 5 contents")

    # Make sure we create a file in this directory so dir2 is included.
    with open(os.path.join(f"{test_repo}/dir2", "file6.md"), "w") as f:
        f.write("File 6 contents")
    # Make sure they're sorted.
    with open(os.path.join(f"{test_repo}/dir2", "file7.md"), "w") as f:
        f.write("File 7 contents")

    # This directory should not be included.
    with open(os.path.join(f"{test_repo}/dir3", "file8.txt"), "w") as f:
        f.write("File 8 contents")

    # This directory should be included.
    with open(os.path.join(f"{test_repo}/dir4", "file9.md"), "w") as f:
        f.write("File 9 contents")
    with open(os.path.join(f"{test_repo}/dir4", "file10.md"), "w") as f:
        f.write("File 10 contents")
    # But not this file.
    with open(os.path.join(f"{test_repo}/dir4", "file11.txt"), "w") as f:
        f.write("File 11 contents")

    # Put some matching inclusion files in dir1 to be excluded.
    with open(os.path.join(f"{test_repo}/dir1", "file12.md"), "w") as f:
        f.write("File 12 contents")

    # Put some matching exclusion files in dir5 to be included by filename.
    with open(os.path.join(f"{test_repo}/dir5", "file13.txt"), "w") as f:
        f.write("File 13 contents")

    # Put some matching exclusion files in dir6 to be included by directory.
    with open(os.path.join(f"{test_repo}/dir6", "file14.txt"), "w") as f:
        f.write("File 14 contents")

    # Generate the repository overview with multiple exclude patterns
    output_file = os.path.join(test_repo, "output.txt")
    # exclude .git directory here, because file1.txt is contained in .git/index
    generate_repo_overview(
        repo_path=test_repo,
        output_file=output_file,
        include=["file13.txt", "dir6"],
        exclude=["*.txt", "dir1", ".git"],
        no_git=True,
        tree_output=True,
    )

    # Check that the excluded files and directories are not included in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert "dir1" not in content
        assert ".git" not in content
        assert "file1.txt" not in content
        assert "file2.txt" not in content
        assert "file3.txt" not in content
        assert "file8.txt" not in content
        assert "file11.txt" not in content
        assert "file12.md" not in content

    # Check that the non-excluded files and directories are included in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert "dir2" in content
        assert "dir5" in content
        assert "dir6" in content
        assert "file4.md" in content
        assert "file5.md" in content
        assert "file6.md" in content
        assert "file7.md" in content
        assert "file9.md" in content
        assert "file10.md" in content
        assert "file13.txt" in content
        assert "file14.txt" in content
        assert (
            content.count(
                """```\n"""
                """.\n"""
                """├── dir2\n"""
                """│   ├── file6.md\n"""
                """│   └── file7.md\n"""
                """├── dir4\n"""
                """│   ├── file10.md\n"""
                """│   └── file9.md\n"""
                """├── dir5\n"""
                """│   └── file13.txt\n"""
                """├── dir6\n"""
                """│   └── file14.txt\n"""
                """├── file4.md\n"""
                """└── file5.md\n"""
                """```\n\n"""
            )
            == 1
        )


def test_nogitfalse_include_specific_patterns(test_repo):
    # Create additional files
    with open(os.path.join(test_repo, "file3.txt"), "w") as f:
        f.write("File 3 contents")
    with open(os.path.join(test_repo, "file4.md"), "w") as f:
        f.write("File 4 contents")
    with open(os.path.join(test_repo, "file5.rtf"), "w") as f:
        f.write("File 5 contents")
    with open(os.path.join(test_repo, "file6.rtf"), "w") as f:
        f.write("File 6 contents")
    with open(os.path.join(test_repo, "file7.rtf"), "w") as f:
        f.write("File 7 contents")

    # Generate the repository overview with specific include patterns
    output_file = os.path.join(test_repo, "output.txt")
    generate_repo_overview(
        test_repo, output_file, include=["*.txt", "file5.rtf"], no_git=False
    )

    # Check that only the included files are present in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert "file1.txt" in content
        assert "file2.txt" in content
        assert "file3.txt" in content
        assert "file4.md" not in content
        assert "file5.rtf" in content


def test_empty_repository():
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = os.path.join(temp_dir, "output.txt")
        generate_repo_overview(temp_dir, output_file, no_git=True)

        # Check that the output file is created and empty
        assert os.path.exists(output_file)
        with open(output_file, "r") as f:
            content = f.read()
            assert content.strip() == "```\n.\n```"


def test_nested_directories(test_repo):
    # Remove the .git dir because no_git=True
    shutil.rmtree(f"{test_repo}/.git")

    # Create nested directories and files
    os.makedirs(os.path.join(test_repo, "dir1", "subdir1"))
    os.makedirs(os.path.join(test_repo, "dir2", "subdir2"))
    with open(os.path.join(test_repo, "dir1", "file3.txt"), "w") as f:
        f.write("File 3 contents")
    with open(os.path.join(test_repo, "dir2", "subdir2", "file4.md"), "w") as f:
        f.write("File 4 contents")

    # Generate the repository overview
    output_file = os.path.join(test_repo, "output.txt")
    generate_repo_overview(test_repo, output_file, no_git=True)

    # Check that the nested files and directories are included in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert "dir1/file3.txt" in content
        assert "dir2/subdir2/file4.md" in content


def test_symbolic_links(test_repo):
    # Remove the .git dir because no_git=True
    shutil.rmtree(f"{test_repo}/.git")

    # Create a symbolic link
    os.symlink("file1.txt", os.path.join(test_repo, "symlink.txt"))

    # Generate the repository overview
    output_file = os.path.join(test_repo, "output.txt")
    generate_repo_overview(test_repo, output_file, no_git=True)

    # Check that the symbolic link is included in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert "symlink.txt" in content


def test_special_characters(test_repo):
    # Remove the .git dir because no_git=True
    shutil.rmtree(f"{test_repo}/.git")

    # Create files with special characters in their names
    with open(os.path.join(test_repo, "file with spaces.txt"), "w") as f:
        f.write("File with spaces contents")
    with open(os.path.join(test_repo, "file_with_underscores.txt"), "w") as f:
        f.write("File with underscores contents")

    # Generate the repository overview
    output_file = os.path.join(test_repo, "output.txt")
    generate_repo_overview(test_repo, output_file, no_git=True)

    # Check that the files with special characters are included in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert "file with spaces.txt" in content
        assert "file_with_underscores.txt" in content
