"""Export the currently compiled LangGraph workflow for inspection."""

from argparse import ArgumentParser
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agent import create_workflow  # noqa: E402


def main() -> None:
    parser = ArgumentParser(description="Export the current document assistant graph.")
    parser.add_argument(
        "--png",
        action="store_true",
        help="Also attempt to render docs/langgraph_workflow.png.",
    )
    args = parser.parse_args()

    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(exist_ok=True)

    graph = create_workflow(None, []).get_graph()
    mermaid_path = docs_dir / "langgraph_workflow.mmd"
    mermaid_path.write_text(graph.draw_mermaid(), encoding="utf-8")
    print(f"Saved Mermaid graph: {mermaid_path}")

    if args.png:
        png_path = docs_dir / "langgraph_workflow.png"
        try:
            png_path.write_bytes(graph.draw_mermaid_png())
        except Exception as exc:
            print(f"PNG export unavailable: {exc}")
            print("The Mermaid file was still exported successfully.")
        else:
            print(f"Saved PNG graph: {png_path}")


if __name__ == "__main__":
    main()
