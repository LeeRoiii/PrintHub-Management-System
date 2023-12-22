from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QHeaderView, QLabel, QLineEdit
from PyQt5.QtGui import QFont
import sqlite3
from PyQt5.QtCore import QDir, Qt
from qtawesome import icon
class ArchivedOrdersDialog(QDialog):
    def __init__(self, parent=None):
        super(ArchivedOrdersDialog, self).__init__(parent)
        self.setWindowTitle("Archived Orders")
        self.setWindowIcon(icon('fa5s.archive', color='black', color_active='white'))
        self.setGeometry(100, 100, 800, 400)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Add search input
        self.searchLabel = QLabel("Search by File Name:")
        self.searchLineEdit = QLineEdit()
        self.searchLineEdit.setPlaceholderText("Enter file name...")
        self.searchLineEdit.textChanged.connect(self.filterArchivedOrders)

        layout.addWidget(self.searchLabel)
        layout.addWidget(self.searchLineEdit)

        self.archivedTableWidget = QTableWidget(self)
        layout.addWidget(self.archivedTableWidget)

        # Set up the table properties and styles
        self.archivedTableWidget.setColumnCount(5)  # Set the number of columns to display
        self.archivedTableWidget.setHorizontalHeaderLabels(
            ["File Name", "Date", "Copies", "Color", "Instructions"]
        )
        self.archivedTableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.archivedTableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.archivedTableWidget.setSelectionBehavior(QTableWidget.SelectRows)
        self.archivedTableWidget.setSelectionMode(QTableWidget.SingleSelection)
        self.archivedTableWidget.setAlternatingRowColors(True)

        # Enable sorting for the table
        self.archivedTableWidget.setSortingEnabled(True)

        # Style the table
        self.archivedTableWidget.setStyleSheet(
            "QTableWidget { background-color: #ffffff; border: 1px solid #ccc; }"
            "QHeaderView::section { background-color: #f0f0f0; border: 1px solid #ccc; font-size: 12px; }"
            "QTableWidget QTableCornerButton::section { background-color: #f0f0f0; }"
        )

        # Set font for the table
        font = QFont("Arial", 10)
        self.archivedTableWidget.setFont(font)

        # Set a consistent row height
        self.archivedTableWidget.verticalHeader().setDefaultSectionSize(25)

        # Add a button to refresh the archived orders
        refresh_button = QPushButton("Refresh Archived Orders")
        refresh_button.clicked.connect(self.loadArchivedOrders)
        refresh_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; border: none; padding: 8px 12px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
        )

        # Add a button to close the dialog
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; border: none; padding: 8px 12px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #d32f2f; }"
        )

        # Create a horizontal layout for buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(close_button)

        # Add the button layout to the main layout
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect to the database and load archived orders
        self.loadArchivedOrders()



    def loadArchivedOrders(self):
        # Clear existing rows before loading new data
        self.archivedTableWidget.setRowCount(0)

        # Connect to the database
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()

        # Fetching order details for all archived files in the database
        cursor.execute("SELECT file_name, date, copies, color, instructions, order_status FROM orders WHERE archived = 'Yes'")
        orders = cursor.fetchall()
        conn.close()

        # Rest of your processing logic remains the same
        for order in orders:
            file_name, order_date, copies, color, instructions, status = order
            file_path = QDir("downloaded_files").filePath(file_name)
            paper_size = "N/A"

            try:
                if file_name.lower().endswith('.pdf'):
                    _, paper_size, _ = self.get_pdf_file_details(file_path)
                elif file_name.lower().endswith('.docx'):
                    _, paper_size, _ = self.get_docx_file_details(file_path)
                elif file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    paper_size = "N/A"
            except Exception as e:
                print(f"Error processing {file_name}: {e}")

            # Populating the table with order details
            row_position = self.archivedTableWidget.rowCount()
            self.archivedTableWidget.insertRow(row_position)
            self.archivedTableWidget.setItem(row_position, 0, QTableWidgetItem(file_name))
            date_part = order_date.split()[0]  # Extract just the date portion from the string
            self.archivedTableWidget.setItem(row_position, 1, QTableWidgetItem(date_part))
            self.archivedTableWidget.setItem(row_position, 2, QTableWidgetItem(str(copies)))
            self.archivedTableWidget.setItem(row_position, 3, QTableWidgetItem(color))
            self.archivedTableWidget.setItem(row_position, 4, QTableWidgetItem(instructions))

    def filterArchivedOrders(self):
        # Get the search text
        search_text = self.searchLineEdit.text().lower()

        # Iterate through the rows and hide those that don't match the search criteria
        for row in range(self.archivedTableWidget.rowCount()):
            file_name_item = self.archivedTableWidget.item(row, 0)
            if file_name_item:
                file_name = file_name_item.text().lower()
                row_hidden = not search_text in file_name
                self.archivedTableWidget.setRowHidden(row, row_hidden)

    def sort(self, Ncol, order):
        """Override the sort method to provide custom sorting logic."""
        self.archivedTableWidget.sortItems(Ncol, order)
