from pathlib import Path

from routeguard.knowledge.store import KnowledgeStore


def main() -> None:
    store = KnowledgeStore()

    policy_directory = Path("data/policies")

    for path in policy_directory.glob("*.md"):
        text = path.read_text(encoding="utf-8")

        store.add_document(
            document_id=path.stem,
            text=text,
            source=str(path),
        )

        print(f"Ingested: {path}")


if __name__ == "__main__":
    main()
