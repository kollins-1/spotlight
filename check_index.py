import os
from whoosh.index import open_dir

INDEX_DIR = "search_index"

if not os.path.exists(INDEX_DIR):
    print("❌ Index directory does not exist. Run `python manage.py index_files` first.")
else:
    ix = open_dir(INDEX_DIR)
    with ix.searcher() as searcher:
        results = list(searcher.documents())
        if results:
            print(f"✅ Found {len(results)} indexed files.")
            for doc in results[:5]:  # Show first 5 files
                print(doc)
        else:
            print("⚠️ No files are indexed. Try re-running `python manage.py index_files`.")
