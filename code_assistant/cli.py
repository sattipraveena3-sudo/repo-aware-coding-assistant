import argparse
import json
from pathlib import Path

from code_assistant.core import answer, index_repo, load_index, save_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Repo-aware Python code assistant")
    sub = parser.add_subparsers(dest="command", required=True)

    index_cmd = sub.add_parser("index", help="Index a Python repository")
    index_cmd.add_argument("repo_path", nargs="?", default=".")
    index_cmd.add_argument("--output", default=".code-index.json")

    ask_cmd = sub.add_parser("ask", help="Ask a question about the indexed repository")
    ask_cmd.add_argument("question")
    ask_cmd.add_argument("--index", default=".code-index.json")
    ask_cmd.add_argument("--top-k", type=int, default=6)

    args = parser.parse_args()

    if args.command == "index":
        idx = index_repo(Path(args.repo_path))
        save_index(idx, args.output)
        print(
            f'Indexed {idx["files_indexed"]} Python files and {len(idx["chunks"])} symbols '
            f'to {args.output}'
        )
        if idx["files_skipped"]:
            print(f'Skipped {len(idx["files_skipped"])} files: {", ".join(idx["files_skipped"])}')
        return

    result = answer(load_index(args.index), args.question, k=args.top_k)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
