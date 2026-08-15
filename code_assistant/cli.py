import argparse,json
from pathlib import Path
from code_assistant.core import answer,index_repo,load_index,save_index
def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True); i=sub.add_parser("index"); i.add_argument("repo_path"); i.add_argument("--output",default=".code-index.json"); a=sub.add_parser("ask"); a.add_argument("question"); a.add_argument("--index",default=".code-index.json"); args=p.parse_args()
    if args.command=="index": idx=index_repo(Path(args.repo_path)); save_index(idx,args.output); print(f'Indexed {len(idx["chunks"])} symbols')
    else: print(json.dumps(answer(load_index(args.index),args.question),indent=2))
if __name__=="__main__": main()
