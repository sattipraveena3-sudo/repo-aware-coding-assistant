from __future__ import annotations

import argparse
import json

from .llm import answer_with_optional_ollama
from .workspace import Workspace


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="repo-assistant", description="Repository-aware code search and local AI assistant"
    )
    parser.add_argument("--workspace", default=".repo_assistant")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Index a local repository")
    p_index.add_argument("path")
    p_index.add_argument("--name")
    p_clone = sub.add_parser("clone", help="Clone and index a remote git repository")
    p_clone.add_argument("url")
    p_clone.add_argument("--name")
    sub.add_parser("list", help="List indexed repositories")
    p_refresh = sub.add_parser("refresh", help="Refresh an indexed repository")
    p_refresh.add_argument("repo_id")
    p_ask = sub.add_parser("ask", help="Ask a repository-grounded question")
    p_ask.add_argument("repo_id")
    p_ask.add_argument("question")
    p_ask.add_argument("--model", default=None)

    args = parser.parse_args()
    workspace = Workspace(args.workspace)
    if args.command == "index":
        result = workspace.index_local(args.path, args.name)
    elif args.command == "clone":
        result = workspace.clone_and_index(args.url, args.name)
    elif args.command == "list":
        result = workspace.list()
    elif args.command == "refresh":
        result = workspace.refresh(args.repo_id)
    else:
        result = answer_with_optional_ollama(
            workspace.load_repo_index(args.repo_id), args.question, model=args.model
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
