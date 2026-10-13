from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"

SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".json"}


def search_files(query: str) -> list[dict]:
    """Search document filenames and text contents."""

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    query = query.strip().lower()

    if not query:
        raise ValueError("Search query cannot be empty.")

    terms = query.split()
    results = []

    for path in DOCUMENTS_DIR.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        searchable_text = f"{path.name}\n{content}".lower()

        matched_terms = [
            term for term in terms
            if term in searchable_text
        ]

        if matched_terms:
            results.append({
                "name": path.name,
                "path": str(path.relative_to(DOCUMENTS_DIR)),
                "matched_terms": matched_terms,
                "match_count": len(matched_terms),
            })

    results.sort(
        key=lambda item: (
            item["match_count"],
            item["name"].lower(),
        ),
        reverse=True,
    )

    return results


def read_file(path: str) -> dict:
    """Read a supported text document inside the documents directory."""

    root = DOCUMENTS_DIR.resolve()
    target = (root / path).resolve()

    if not target.is_relative_to(root):
        raise ValueError(
            "Access outside the documents directory is prohibited."
        )

    if not target.is_file():
        raise FileNotFoundError(f"Document not found: {path}")

    if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type.")

    content = target.read_text(encoding="utf-8-sig")

    return {
        "name": target.name,
        "content": content,
        "characters": len(content),
    }
def list_files() -> dict:
    """List supported documents in the documents directory."""

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    files = []

    for path in DOCUMENTS_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append({
                "name": path.name,
                "path": str(path.relative_to(DOCUMENTS_DIR)),
                "extension": path.suffix.lower(),
            })

    files.sort(key=lambda item: item["path"].lower())

    return {
        "success": True,
        "count": len(files),
        "files": files,
    }