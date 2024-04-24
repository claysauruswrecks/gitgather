# gitgather

[gitgather on PyPI](https://pypi.org/project/gitgather/)

To install `gitgather`, run the following command:

```bash
pip install gitgather
```

```bash
$ gitgather --help
usage: gitgather [-h] [--no-git] [--all] [--no-dotfiles] [-v] [--include INCLUDE] [--exclude EXCLUDE] repo_path output_file

Concatenate git repository files for LLM context analysis.

positional arguments:
  repo_path          Path to the git repository
  output_file        Output file path

options:
  -h, --help         show this help message and exit
  --no-git           Include all files, not just those tracked by git
  --all              Include all files, including hidden ones (overrides --no-dotfiles)
  --no-dotfiles      Exclude dotfiles
  -v, --verbose      Enable verbose output
  --include INCLUDE  Include files matching these patterns
  --exclude EXCLUDE  Exclude files matching these patterns
```
