import os
import tempfile
import shutil
import subprocess
import pytest
from gitgather.gather import (
    capture_tree_output,
    get_git_files,
    match_patterns,
    apply_filters,
    generate_repo_overview,
)


@pytest.fixture
def test_repo():
    temp_dir = tempfile.mkdtemp()
    subprocess.run(["git", "init"], cwd=temp_dir)
    with open(os.path.join(temp_dir, "file1.txt"), "w") as f:
        f.write("File 1 contents")
    with open(os.path.join(temp_dir, "file2.txt"), "w") as f:
        f.write("File 2 contents")
    subprocess.run(["git", "add", "."], cwd=temp_dir)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir)
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_capture_tree_output(test_repo):
    tree_output = capture_tree_output(test_repo)
    assert "file1.txt" in tree_output
    assert "file2.txt" in tree_output


def test_get_git_files(test_repo):
    git_files = get_git_files(test_repo)
    assert "file1.txt" in git_files
    assert "file2.txt" in git_files


def test_match_patterns():
    assert match_patterns("file1.txt", ["*.txt"])
    assert not match_patterns("file1.txt", ["*.md"])


def test_apply_filters():
    files = ["file1.txt", "file2.md", "file3.txt"]
    filtered_files = apply_filters(files, ["*.txt"], ["file1.txt"])
    assert "file3.txt" in filtered_files
    assert "file1.txt" not in filtered_files
    assert "file2.md" not in filtered_files


def test_generate_repo_overview(test_repo):
    output_file = os.path.join(test_repo, "output.txt")
    generate_repo_overview(test_repo, output_file)
    with open(output_file, "r") as f:
        content = f.read()
        assert "file1.txt" in content
        assert "file2.txt" in content
        assert "File 1 contents" in content
        assert "File 2 contents" in content
