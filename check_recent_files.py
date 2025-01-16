import os
import datetime
from whoosh.index import open_dir

INDEX_DIR = "search_index"
DAYS_AGO = 3  # Change this to test different days

if not os.path.exists(INDEX_DIR):
    print("❌ Index directory does not exist. Run `python manage.py index_files` first.")
else:
    ix = open_dir(INDEX_DIR)
    with ix.searcher() as searcher:
        results = []
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=DAYS_AGO)

        for doc in searcher.documents():
            accessed_date = doc["accessed"]
            if accessed_date.date() == cutoff_date.date():
                results.append(doc)

        print(f"📅 Files accessed {DAYS_AGO} days ago: {len(results)}")
        for doc in results[:10]:  # Show first 10 results
            print(f"{doc['title']} | Last accessed: {doc['accessed']} | Path: {doc['path']}")
