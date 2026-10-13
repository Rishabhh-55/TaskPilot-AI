from tools.files import search_files, read_file
from tools.invoices import (
    create_invoice,
    get_invoice,
    list_invoices,
)

AVAILABLE_TOOLS = {
    "search_files": search_files,
    "read_file": read_file,
    "create_invoice": create_invoice,
    "get_invoice": get_invoice,
    "list_invoices": list_invoices,
}