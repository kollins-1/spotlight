import os
import sys
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLineEdit, QPushButton, QTextBrowser
from PyQt5.QtCore import Qt
from django.core.management import call_command
from search.natural_search import search_files  # Import the natural language search function

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotlight Windows")
        self.setGeometry(100, 100, 800, 600)

        # Main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()

        # Search input field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files (e.g., 'files I opened yesterday')")
        layout.addWidget(self.search_input)

        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        layout.addWidget(self.search_button)

        # Results display
        self.results_display = QTextBrowser()
        layout.addWidget(self.results_display)

        self.central_widget.setLayout(layout)

    def perform_search(self):
        """Handles the search when the button is clicked."""
        query = self.search_input.text().strip()
        if query:
            results = search_files(query)  # Use natural language search
            if results:
                result_text = "\n".join([f"{res['title']} - {res['path']}" for res in results])
            else:
                result_text = "No matching files found."
            self.results_display.setText(result_text)

def start_django_server():
    """Starts the Django server in a separate thread."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spotlight_windows.settings")
    os.system("python manage.py runserver 127.0.0.1:8000")

if __name__ == "__main__":
    # Start Django server in a separate thread
    django_thread = threading.Thread(target=start_django_server, daemon=True)
    django_thread.start()

    # Create the PyQt application
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()

    # Run the PyQt event loop
    sys.exit(app.exec_())
