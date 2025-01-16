import os
import time
import threading
import logging
import datetime
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh.index import create_in, open_dir
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Command(BaseCommand):
    help = 'Indexes files dynamically from specific user directories for natural language search.'

    def handle(self, *args, **kwargs):
        index_dir = "search_index"

        schema = Schema(
            title=TEXT(stored=True), 
            path=ID(stored=True, unique=True), 
            created=DATETIME(stored=True), 
            modified=DATETIME(stored=True), 
            accessed=DATETIME(stored=True)
        )

        #  Only index these directories
        TARGET_DIRECTORIES = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Pictures"),
            os.path.expanduser("~/Videos"),
            os.path.expanduser("~/Music"),
        ]

        EXCLUDED_FILE_TYPES = [".dll", ".sys", ".tmp", ".log", ".lnk", ".bak", ".iso", ".old", ".vhd", ".vmdk"]
        MAX_FILE_SIZE_MB = 100

        event_cache = {}
        file_events = []
        index_lock = threading.Lock()

        def is_excluded_file(file_path):
            """Check if a file should be excluded based on type or size."""
            file_path = Path(file_path)
            if file_path.exists() and file_path.stat().st_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                return True
            return any(file_path.suffix.lower() == ext for ext in EXCLUDED_FILE_TYPES)

        def is_in_target_directories(file_path):
            """Ensure the file is inside one of the target directories."""
            file_path = os.path.abspath(file_path)
            return any(file_path.startswith(os.path.abspath(d)) for d in TARGET_DIRECTORIES)

        def debounce_event(event_type, file_path, debounce_time=1):
            """Debounce frequent file system events."""
            current_time = time.time()
            if (file_path, event_type) in event_cache:
                if current_time - event_cache[(file_path, event_type)] < debounce_time:
                    return False
            event_cache[(file_path, event_type)] = current_time
            return True

        def create_index():
            """Create or open the Whoosh index."""
            if not os.path.exists(index_dir):
                os.mkdir(index_dir)
                return create_in(index_dir, schema)
            try:
                return open_dir(index_dir)
            except Exception:
                return create_in(index_dir, schema)

        def index_files(directory, writer):
            """Index files in the target directories."""
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)

                    # ✅ Ensure only files in target directories are indexed
                    if is_in_target_directories(file_path) and not is_excluded_file(file_path):
                        try:
                            file_stats = os.stat(file_path)
                            writer.add_document(
                                title=file, 
                                path=file_path,
                                created=datetime.datetime.fromtimestamp(file_stats.st_ctime),
                                modified=datetime.datetime.fromtimestamp(file_stats.st_mtime),
                                accessed=datetime.datetime.fromtimestamp(file_stats.st_atime)
                            )
                        except FileNotFoundError:
                            pass  # Ignore missing files
                        except Exception as e:
                            logger.error(f"Error indexing file: {file_path} - {e}", exc_info=True)

        def start_indexing():
            """Start initial indexing."""
            ix = create_index()
            writer = ix.writer()
            try:
                logger.info("Starting indexing for specified directories...")
                for directory in TARGET_DIRECTORIES:
                    if os.path.exists(directory):
                        index_files(directory, writer)
                writer.commit()
                logger.info("Initial indexing complete.")
            except Exception as e:
                logger.error(f"Error during indexing: {e}", exc_info=True)

        class FileEventHandler(FileSystemEventHandler):
            """Handles file system events for real-time updates."""
            def on_created(self, event):
                if not event.is_directory and debounce_event("created", event.src_path):
                    with index_lock:
                        file_events.append(("created", event.src_path))

            def on_deleted(self, event):
                if not event.is_directory and debounce_event("deleted", event.src_path):
                    with index_lock:
                        file_events.append(("deleted", event.src_path))

            def on_modified(self, event):
                self.on_created(event)

        def process_events():
            """Process file events dynamically."""
            while True:
                with index_lock:
                    events_to_process = file_events[:]
                    file_events.clear()

                if events_to_process:
                    ix = open_dir(index_dir)
                    writer = ix.writer()
                    try:
                        for action, file_path in events_to_process:
                            if not is_in_target_directories(file_path):
                                continue  # Skip if not in target directories

                            try:
                                file_stats = os.stat(file_path)
                                if action == "created":
                                    writer.add_document(
                                        title=os.path.basename(file_path),
                                        path=file_path,
                                        created=datetime.datetime.fromtimestamp(file_stats.st_ctime),
                                        modified=datetime.datetime.fromtimestamp(file_stats.st_mtime),
                                        accessed=datetime.datetime.fromtimestamp(file_stats.st_atime)
                                    )
                                elif action == "deleted":
                                    writer.delete_by_term("path", file_path)
                            except FileNotFoundError:
                                pass  # Ignore missing files
                            except Exception as e:
                                logger.error(f"Error processing file event: {file_path} - {e}", exc_info=True)
                        writer.commit()
                        logger.info(f"Processed {len(events_to_process)} events.")
                    except Exception as e:
                        logger.error(f"Error processing events: {e}", exc_info=True)

                time.sleep(5)

        def start_file_monitoring():
            """Start monitoring target directories for real-time updates."""
            event_handler = FileEventHandler()
            observer = Observer()
            for directory in TARGET_DIRECTORIES:
                if os.path.exists(directory):
                    observer.schedule(event_handler, directory, recursive=True)
            observer.start()
            logger.info("File monitoring started.")

        try:
            logger.info("Starting indexing and monitoring for target directories...")
            start_indexing()
            threading.Thread(target=process_events, daemon=True).start()
            start_file_monitoring()
        except KeyboardInterrupt:
            logger.info("File monitoring stopped.")