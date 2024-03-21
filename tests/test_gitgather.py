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


def test_nogit_and_exclude_git_directory(test_repo):
    # Create a non-Git file in the repository
    with open(os.path.join(test_repo, "file.txt"), "w") as f:
        f.write("Regular file")

    # Generate the repository overview with --no-git and --exclude .git options
    output_file = os.path.join(test_repo, "output.txt")
    generate_repo_overview(test_repo, output_file, exclude=[".git"], no_git=True)

    # Check that the .git directory and its contents are not included in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert ".git/config" not in content
        assert ".git/HEAD" not in content

    # Check that the non-Git file is included in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert "file.txt" in content


def test_exclude_multiple_patterns(test_repo):
    # Create additional files and directories
    os.makedirs(os.path.join(test_repo, "dir1"))
    os.makedirs(os.path.join(test_repo, "dir2"))
    with open(os.path.join(test_repo, "file3.txt"), "w") as f:
        f.write("File 3 contents")
    with open(os.path.join(test_repo, "file4.md"), "w") as f:
        f.write("File 4 contents")

    # Generate the repository overview with multiple exclude patterns
    output_file = os.path.join(test_repo, "output.txt")
    generate_repo_overview(
        test_repo, output_file, exclude=["*.txt", "dir1"], no_git=True
    )

    # Check that the excluded files and directories are not included in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert "file1.txt" not in content
        assert "file2.txt" not in content
        assert "file3.txt" not in content
        assert "dir1" not in content

    # Check that the non-excluded files and directories are included in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert "file4.md" in content
        assert "dir2" in content


def test_include_specific_patterns(test_repo):
    # Create additional files
    with open(os.path.join(test_repo, "file3.txt"), "w") as f:
        f.write("File 3 contents")
    with open(os.path.join(test_repo, "file4.md"), "w") as f:
        f.write("File 4 contents")

    # Generate the repository overview with specific include patterns
    output_file = os.path.join(test_repo, "output.txt")
    generate_repo_overview(test_repo, output_file, include=["*.txt"], no_git=True)

    # Check that only the included files are present in the output
    with open(output_file, "r") as f:
        content = f.read()
        assert "file1.txt" in content
        assert "file2.txt" in content
        assert "file3.txt" in content
        assert "file4.md" not in content


def test_empty_repository():
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = os.path.join(temp_dir, "output.txt")
        generate_repo_overview(temp_dir, output_file, no_git=True)

        # Check that the output file is created and empty
        assert os.path.exists(output_file)
        with open(output_file, "r") as f:
            content = f.read()
            assert content.strip() == ""


def test_nested_directories(test_repo):
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
