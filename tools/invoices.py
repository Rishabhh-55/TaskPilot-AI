import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "taskpilot.db"


def get_connection():
    """Create a connection to the local invoice database."""

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    """Create the invoice table if it does not exist."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                company TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount >= 0),
                status TEXT NOT NULL,
                source_document TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def create_invoice(
    invoice_number: str,
    company: str,
    amount: float,
    status: str,
    source_document: str,
) -> dict:
    """Save an invoice in the simulated company application."""

    initialize_database()

    invoice_number = invoice_number.strip()
    company = company.strip()
    status = status.strip()
    source_document = source_document.strip()

    if not invoice_number:
        raise ValueError("Invoice number cannot be empty.")

    if not company:
        raise ValueError("Company cannot be empty.")

    if not status:
        raise ValueError("Invoice status cannot be empty.")

    if not source_document:
        raise ValueError("Source document cannot be empty.")

    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ValueError("Invoice amount must be numeric.")

    if amount < 0:
        raise ValueError("Invoice amount cannot be negative.")

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE invoice_number = ?
            """,
            (invoice_number,),
        ).fetchone()

        if existing:
            return {
                "success": False,
                "error": "duplicate_invoice",
                "message": (
                    f"Invoice {invoice_number} already exists. "
                    "No new record was created."
                ),
                "existing_invoice": dict(existing),
            }

        cursor = connection.execute(
            """
            INSERT INTO invoices (
                invoice_number,
                company,
                amount,
                status,
                source_document
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                invoice_number,
                company,
                amount,
                status,
                source_document,
            ),
        )

        invoice_id = cursor.lastrowid

        saved_invoice = connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE id = ?
            """,
            (invoice_id,),
        ).fetchone()

    return {
        "success": True,
        "message": "Invoice saved successfully.",
        "invoice": dict(saved_invoice),
    }


def get_invoice(invoice_number: str) -> dict:
    """Retrieve an invoice by its invoice number."""

    initialize_database()

    invoice_number = invoice_number.strip()

    if not invoice_number:
        raise ValueError("Invoice number cannot be empty.")

    with get_connection() as connection:
        invoice = connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE invoice_number = ?
            """,
            (invoice_number,),
        ).fetchone()

    if invoice is None:
        return {
            "success": False,
            "error": "invoice_not_found",
            "message": (
                f"Invoice {invoice_number} was not found."
            ),
        }

    return {
        "success": True,
        "invoice": dict(invoice),
    }


def list_invoices() -> dict:
    """List all invoices stored in the simulated application."""

    initialize_database()

    with get_connection() as connection:
        invoices = connection.execute(
            """
            SELECT *
            FROM invoices
            ORDER BY id DESC
            """
        ).fetchall()

    return {
        "success": True,
        "count": len(invoices),
        "invoices": [
            dict(invoice)
            for invoice in invoices
        ],
    }