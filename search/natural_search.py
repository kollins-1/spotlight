import os
import datetime
import dateparser
import spacy
from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser
from whoosh.query import Every

# Load NLP model
nlp = spacy.load("en_core_web_sm")

# Path to the Whoosh index
INDEX_DIR = "search_index"

# Supported file categories and their extensions
CATEGORY_EXTENSIONS = {
    "documents": {".pdf", ".docx", ".txt", ".pptx", ".xlsx"},
    "videos": {".mp4", ".avi", ".mov"},
    "pictures": {".jpg", ".png", ".jpeg", ".gif"},
    "music": {".mp3", ".wav", ".flac"},
}

def parse_natural_query(query):
    """
    Extracts a date and file category from a natural language query.
    """
    doc = nlp(query.lower())

    # Extract date
    extracted_date = dateparser.parse(query)
    if extracted_date:
        extracted_date = extracted_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Extract file category
    file_category = None
    for token in doc:
        if token.text in CATEGORY_EXTENSIONS.keys():
            file_category = token.text

    return {"date": extracted_date, "category": file_category}

def search_files(natural_query):
    """
    Searches indexed files based on a natural language query, 
    filtering by file type and date.
    """
    ix = open_dir(INDEX_DIR)
    parsed_query = parse_natural_query(natural_query)

    results = []
    with ix.searcher() as searcher:
        query_parser = MultifieldParser(["title", "path"], ix.schema)
        query = query_parser.parse("*")  # Match all files

        matches = searcher.search(query, limit=100)  # Get broader results first

        for hit in matches:
            file_path = hit["path"]
            file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

            # ✅ Apply date filtering manually
            if parsed_query["date"]:
                start_date = parsed_query["date"]
                end_date = start_date + datetime.timedelta(days=1)  # Include entire day
                if not (start_date <= file_mtime < end_date):
                    continue  # Skip files outside the range

            # ✅ Filter by file category (file extension)
            if parsed_query["category"]:
                allowed_extensions = CATEGORY_EXTENSIONS.get(parsed_query["category"], set())
                if allowed_extensions and not file_path.lower().endswith(tuple(allowed_extensions)):
                    continue  # Skip files that don't match the category

            results.append({
                "title": hit["title"],
                "path": file_path,
                "last_accessed": file_mtime,
            })

    return results

# Example usage
if __name__ == "__main__":
    search_query = input("Enter your search: ")
    results = search_files(search_query)

    print("\nSearch Results:")
    if not results:
        print("No matching files found.")
    else:
        for result in results:
            print(f"- {result['title']} ({result['path']}) | Last accessed: {result['last_accessed']}")
