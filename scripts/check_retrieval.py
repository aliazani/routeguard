from routeguard.knowledge.store import KnowledgeStore

QUESTIONS = [
    "Can a shipment on a planned tour be moved?",
    "What happens if the tour already started?",
    "Do I need confirmation before applying a route change?",
    "What information must be audited?",
    "What is the company's employee travel reimbursement policy?",
]


def main() -> None:
    store = KnowledgeStore()

    for question in QUESTIONS:
        print("\n" + "=" * 70)
        print(f"QUESTION: {question}")
        print("=" * 70)

        raw_results = store.search(
            question,
            limit=3,
        )

        print("\nRAW RETRIEVAL")

        if not raw_results:
            print("No documents retrieved.")

        for index, result in enumerate(
            raw_results,
            start=1,
        ):
            print(
                f"\nResult {index}"
                f" | score={result.score:.3f}"
                f" | source={result.source}"
                f" | document={result.document_id}"
                f" | chunk={result.chunk_index}"
            )

            print(result.text)

        filtered_results = store.search(
            question,
            limit=3,
            min_score=0.45,
        )

        print("\nFILTERED RETRIEVAL (min_score=0.35)")

        if not filtered_results:
            print("No sufficiently relevant policy evidence found.")

        for index, result in enumerate(
            filtered_results,
            start=1,
        ):
            print(
                f"\nResult {index}"
                f" | score={result.score:.3f}"
                f" | source={result.source}"
                f" | document={result.document_id}"
                f" | chunk={result.chunk_index}"
            )

            print(result.text)


if __name__ == "__main__":
    main()
