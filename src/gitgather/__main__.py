import argparse

from gitgather.gather import (
    generate_repo_overview,
)


def main():
    parser = argparse.ArgumentParser(
        description="Concatenate git repository files for LLM context analysis."
    )
    parser.add_argument("repo_path", help="Path to the git repository")
    parser.add_argument("output_file", help="Output file path")
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Include all files, not just those tracked by git",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include all files, including hidden ones (overrides --no-dotfiles)",
    )
    parser.add_argument("--no-dotfiles", action="store_true", help="Exclude dotfiles")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--include",
        action="append",
        help="Include files matching these patterns",
        default=[],
    )
    parser.add_argument(
        "--exclude",
        action="append",
        help="Exclude files matching these patterns",
        default=[],
    )

    args = parser.parse_args()

    if not args.all and args.no_dotfiles:
        args.exclude.append(".*")

    generate_repo_overview(
        args.repo_path,
        args.output_file,
        include=args.include,
        exclude=args.exclude,
        no_git=args.no_git,
        all_files=args.all,
        no_dotfiles=args.no_dotfiles,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
