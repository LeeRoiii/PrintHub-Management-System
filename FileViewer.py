#FileViewer
import requests
import sqlite3
import sys
import os
import json
from PyQt5.QtWidgets import QApplication,QMessageBox,QFrame,QTextEdit,QGridLayout,QDialog,QLineEdit,QInputDialog, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QLabel, QMessageBox, QFileDialog, QAbstractItemView
from PyQt5.QtCore import QDir
from PyQt5.QtCore import Qt

from qtawesome import icon
import qtawesome as qta
import fitz
from PyQt5.QtGui import QColor
from docx import Document
from docx.shared import Inches
from PyQt5.QtCore import QTimer,QDateTime
from database_operations import update_order_status
#FILE IMPORT 
from DocumentReader import DocumentReader
from Dashboard import Dashboard
from Setting import SettingsDialog
from Connection import FlaskThread, create_connection
from Config import  PAGE_ACCESS_TOKEN
from datetime import datetime
import platform

DARK_BLUE = "#040D12"
LIGHT_BLUE = "#183D5C"
LIGHT_GRAY = "#837493"
LIGHT_BEIGE = "#B1A6A6"
BUSINESS_LOCATION = "Default business location. Please update through the application settings."
GOOGLE_MAPS_LINK = "Default Google Maps link. Please update through the application settings."

class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)

class FileViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.flaskRunning = False
        self.initUI()
        self.last_order_count = self.get_order_count()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_new_orders)
        self.timer.start(10000)  # 10 seconds
        self.notification_logs = []

    def initUI(self):
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self.setWindowTitle('File Viewer')
        self.setGeometry(300, 300, 950, 700)
        mainLayout = QVBoxLayout(centralWidget)
        mainLayout.setContentsMargins(20, 20, 20, 20)

        # Assuming mainLayout is a QVBoxLayout
        searchLayout = QHBoxLayout()
        mainLayout.addLayout(searchLayout)

        # Add the search bar to the search layout
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Search files...")
        self.searchBar.textChanged.connect(self.filter_files)
        searchLayout.addWidget(self.searchBar)
        
        self.fileTableWidget = QTableWidget()
        self.fileTableWidget.setColumnCount(7)
        self.fileTableWidget.setHorizontalHeaderLabels(["File Name", "Date", "Paper Size", "Copies", "Color", "Instructions", "Order Status"])
        self.fileTableWidget.horizontalHeader().setStretchLastSection(True)
        self.fileTableWidget.setSortingEnabled(True)
        self.fileTableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        mainLayout.addWidget(self.fileTableWidget, 1)

        buttonGrid = QGridLayout()
        self.previewBtn = self.createStyledButton("fa.eye", "Preview", "primary")
        self.previewBtn.clicked.connect(self.previewFile)
        buttonGrid.addWidget(self.previewBtn, 0, 0)

        self.deleteBtn = self.createStyledButton("fa.trash", "Delete", "secondary")
        self.deleteBtn.clicked.connect(self.delete_file)
        buttonGrid.addWidget(self.deleteBtn, 1, 0)

        self.settingsBtn = self.createStyledButton("fa.cog", "Edit Preferences ", "secondary")
        self.settingsBtn.clicked.connect(self.showSettingsDialog)
        buttonGrid.addWidget(self.settingsBtn, 1, 1)

        self.refreshBtn = self.createStyledButton("fa.refresh", "Refresh", "primary")
        self.refreshBtn.clicked.connect(self.refreshFiles)
        buttonGrid.addWidget(self.refreshBtn, 0, 3)

        self.finishOrderBtn = self.createStyledButton("fa.check", "Finish Order", "primary")
        self.finishOrderBtn.clicked.connect(self.finish_order)
        buttonGrid.addWidget(self.finishOrderBtn, 0, 2)

        self.finishBtn = self.createStyledButton("fa.check", "Ready for Pickup", "primary")
        self.finishBtn.clicked.connect(self.on_finish_button_clicked)
        buttonGrid.addWidget(self.finishBtn, 0, 1)

        self.toggleServerButton = self.createStyledButton("fa5s.server", "Start Service", "secondary")
        self.toggleServerButton.clicked.connect(self.toggleFlaskServer)
        buttonGrid.addWidget(self.toggleServerButton, 1, 2)

        # Create the PRINTING SERVICE button (not clickable)
        printingServiceButton = self.createStyledButton("fa5s.print", "PRINTING SERVICE", "secondary")
        printingServiceButton.setEnabled(False)  # Set the button to disabled
        buttonGrid.addWidget(printingServiceButton, 1, 3)

        mainLayout.addLayout(buttonGrid)
        self.flask_thread = FlaskThread()
        self.loadFiles()

    def createStyledButton(self, iconName, buttonText, colorHex):
        if iconName:
            button = QPushButton(qta.icon(iconName, color="white"), buttonText)
        else:
            button = QPushButton(buttonText)

        if colorHex == "primary":
            bgColor = DARK_BLUE
        elif colorHex == "secondary":
            bgColor = LIGHT_BLUE
        elif colorHex == "background":
            bgColor = LIGHT_BEIGE
        elif colorHex == "text":
            bgColor = DARK_BLUE
        else:
            bgColor = colorHex

        button.setStyleSheet(
            f"font-size: 14px; "
            f"background-color: {bgColor}; "
            f"color: white; "
            f"border: none; "
            f"padding: 8px 16px; "
            f"border-radius: 4px; "
            f"min-width: 130px; "
            f"height: 40px; "
            f"text-align: left; "
            f"padding-left: 12px;"
        )
        button.setFlat(True)
        return button

    def refreshFiles(self):
 
        self.fileTableWidget.clearContents()
        self.loadFiles()  
        QMessageBox.information(self, "Refresh ", "Table has been refreshed.")

    def loadFiles(self, month_idx=0, search_text=None):
        self.fileTableWidget.setRowCount(0)  # Clear existing rows

        # Set up table columns
        self.fileTableWidget.setColumnCount(9)  # Increase column count for 'User Name' and 'Cost'
        self.fileTableWidget.setHorizontalHeaderLabels(
            ["File Name","Customer", "Date", "Paper Size", "Copies", "Color","Print Cost", "Order Status", "Instructions"]
        )
        # Connect to the database
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()

        if month_idx == 0:
            cursor.execute("SELECT file_name, date, copies, color, instructions, order_status, archived, user_name, print_cost FROM orders WHERE archived = 'No' ORDER BY date DESC")
        else:
            # Filter based on the specified month and exclude archived orders
            query = "SELECT file_name, date, copies, color, instructions, order_status, archived, user_name, print_cost FROM orders WHERE strftime('%m', date) = ? AND archived = 'No' ORDER BY date DESC"
            cursor.execute(query, (str(month_idx).zfill(2),))

        orders = cursor.fetchall()
        conn.close()

        # Counters for pending and finished orders
        pending_count = 0
        finished_count = 0

        # Rest of your processing logic remains the same
        for order in orders:
            file_name, order_date, copies, color, instructions, status, archived, user_name, print_cost = order
            file_path = QDir("downloaded_files").filePath(file_name)
            paper_size = "N/A"

            try:
                if file_name.lower().endswith('.pdf'):
                    _, paper_size, _ = self.get_pdf_file_details(file_path)
                elif file_name.lower().endswith('.docx'):
                    _, paper_size, _ = self.get_docx_file_details(file_path)
                elif file_name.lower().endswith(('.png', '.jpg', '.jpeg','xlxs')):
                    paper_size = "N/A"
            except Exception as e:
                print(f"Error processing {file_name}: {e}")

            # Check if the file matches the search criteria
            if search_text and search_text.lower() not in file_name.lower():
                continue

            # Populating the table with order details
            row_position = self.fileTableWidget.rowCount()
            self.fileTableWidget.insertRow(row_position)
            self.fileTableWidget.setItem(row_position, 0, QTableWidgetItem(file_name))
            date_part = order_date.split()[0]  # Extract just the date portion from the string
            self.fileTableWidget.setItem(row_position, 2, QTableWidgetItem(date_part))
            self.fileTableWidget.setItem(row_position, 3, QTableWidgetItem(paper_size))
            self.fileTableWidget.setItem(row_position, 4, QTableWidgetItem(str(copies)))
            self.fileTableWidget.setItem(row_position, 5, QTableWidgetItem(color))
            self.fileTableWidget.setItem(row_position, 7, QTableWidgetItem(status))
            self.fileTableWidget.setItem(row_position, 8, QTableWidgetItem(instructions))
            self.fileTableWidget.setItem(row_position, 1, QTableWidgetItem(user_name))
            self.fileTableWidget.setItem(row_position, 6, QTableWidgetItem(str(print_cost)))  # Assuming print_cost is a numeric value

            # Color the row based on the order status
            if status == "Pending":
                for col in range(self.fileTableWidget.columnCount()):
                    self.fileTableWidget.item(row_position, col).setBackground(QColor(255, 255, 0))  # Yellow RGB value
                pending_count += 1

            elif status == "Ready for Pickup":
                for col in range(self.fileTableWidget.columnCount()):
                    self.fileTableWidget.item(row_position, col).setBackground(QColor(173, 216, 230))  # LightBlue RGB value

            elif status == "Finished":
                for col in range(self.fileTableWidget.columnCount()):
                    self.fileTableWidget.item(row_position, col).setBackground(QColor(144, 238, 144))  # LightGreen RGB value
                finished_count += 1

                    
    def show_table_structure():
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(orders)")
        columns = cursor.fetchall()

        for column in columns:
            print(column)

        conn.close()

    show_table_structure()

    def previewFile(self):
        selected_items = self.fileTableWidget.selectedItems()
        if selected_items:
            file_name = selected_items[0].text()
            file_path = os.path.join('downloaded_files', file_name)# Join the directory with the file name

            if os.path.exists(file_path):
                if file_name.lower().endswith(('.xlsx', '.xls')):
                    os.startfile(file_path)
                else:
                    # For non-Excel files, open in DocumentReader
                    self.reader = DocumentReader(file_path)
                    self.reader.show()
            else:
                # Show a message box if the file does not exist
                QMessageBox.warning(self, 'File Not Found', f'The selected file "{file_name}" does not exist.', QMessageBox.Ok)
        else:
            # Show a message box if no item is selected
            QMessageBox.warning(self, 'No File Selected', 'Please select a file to preview.', QMessageBox.Ok)

            
    def on_finish_button_clicked(self):
        if not self.flask_thread.isRunning():
            QMessageBox.warning(self, "Service Not Running", "Cannot finish order. Start the Service first.")
            return

        selected_rows = self.fileTableWidget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Error", "Please select an order first.")
            return

        row = selected_rows[0].row()

        # Extract details from the table for the selected order
        file_name = self.fileTableWidget.item(row, 0).text()
        copies = self.fileTableWidget.item(row, 4).text()
        order_status = self.fileTableWidget.item(row, 7).text()  # Index 7 is for "Order Status"

        if order_status == "Finished":
            QMessageBox.warning(self, "Error", "This order is already finished.")
            return

        if order_status == "Ready for Pickup":
            # If the order is already "Ready for Pickup," skip prompting for the print cost
            # You can add additional handling/logic if needed
            QMessageBox.warning(self, "Error", "Order is waiting to be picked up.")
            return

        if order_status == "Pending":
            confirmation = QMessageBox.question(self, "Confirmation",
                                                "Are you sure you want to mark this order as Ready For Pickup?",
                                                QMessageBox.Yes | QMessageBox.No)
            if confirmation == QMessageBox.No:
                return

        if not all([file_name, copies]):
            QMessageBox.warning(self, "Error", "Invalid selection.")
            return

        # Create a QTextEdit to display the paper_types.txt content
        paper_types_content = self.read_from_file("paper_types.txt")
        paper_types_text_edit = QTextEdit()
        paper_types_text_edit.setPlainText(paper_types_content)
        paper_types_text_edit.setReadOnly(True)

        # Create a label for the paper types text
        paper_types_label = QLabel("Our printing services are as follows:")
        paper_types_label.setAlignment(Qt.AlignCenter)

        # Create a layout for the paper types text
        paper_types_layout = QVBoxLayout()
        paper_types_layout.addWidget(paper_types_label)
        paper_types_layout.addWidget(paper_types_text_edit)

        # Create the input dialog
        input_dialog = QInputDialog(self)
        input_dialog.setOption(QInputDialog.UseListViewForComboBoxItems, True)
        input_dialog.setInputMode(QInputDialog.DoubleInput)
        input_dialog.setLabelText("Enter Print Cost:")
        input_dialog.setDoubleMinimum(0)
        input_dialog.setDoubleMaximum(100000)
        input_dialog.setDoubleValue(0)
        input_dialog.setOkButtonText("OK")
        input_dialog.setCancelButtonText("Cancel")
        
        # Add a custom widget to the input dialog
        input_dialog.layout().addLayout(paper_types_layout)

        # Execute the input dialog
        ok_pressed = input_dialog.exec_()
        if not ok_pressed:
            return  # User pressed Cancel or closed the dialog

        cost_input = input_dialog.doubleValue()

        # Check if the print cost is zero before proceeding with confirmation
        if cost_input == 0:
            QMessageBox.warning(self, "Error", "Print cost cannot be zero. Please enter a valid print cost.")
            return

        confirmation = QMessageBox.question(self, "Confirmation",
                                            f"Are you sure the print cost for '{file_name}' is ₱{cost_input:.2f}?",
                                            QMessageBox.Yes | QMessageBox.No)
        if confirmation == QMessageBox.Yes:
            sender_id = self.get_sender_id_for_file(file_name)
            if not sender_id:
                QMessageBox.warning(self, "Error", "Could not find user for this order.")
                return

            # Construct the message to send to the user
            user_message = (
                f"Your order for the file '{file_name}' is ready!\n"
                f"You've requested {copies} copies.\n"
                f"The total print cost is: ₱{cost_input:.2f}\n"
                "Feel free to come by and pick up your printed documents.\n"
            )

            # Update order details in the database
            update_order_status(file_name, "Ready for Pickup", cost_input)
            send_message_to_user(sender_id, user_message)

            self.log_server_interaction(f"Order Ready for pickup: {file_name}")
            self.loadFiles()
            QMessageBox.information(self, "Order Ready For Pickup", f"The order '{file_name}' Ready For Pickup.")


    def start_flask_server(self):
        if not self.flask_thread.isRunning():
            self.flask_thread.start()
            self.startServerBtn.setText("Bot Running")
            self.startServerBtn.setEnabled(False)
            
    def filter_files(self):
        search_text = self.searchBar.text().lower()
        self.loadFiles(search_text=search_text)
 
            
    def get_sender_id_for_file(self, file_name):
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT sender_id FROM orders WHERE file_name = ?", (file_name,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            return result[0]
        return None
        

    def get_paper_size(self, page):
        # Define common paper sizes with popular terms
        paper_sizes = {
            (595, 842): "A4",
            (842, 595): "A4 ",
            (612, 792): "Short",
            (792, 612): "Short",
            (612, 1008): "Long",
            (1008, 612): "Long",
            # Add more paper sizes with popular terms as needed
        }
        # Get the page dimensions
        width = round(page.bound().width)
        height = round(page.bound().height)

        # Find the closest matching paper size
        closest_match = None
        min_distance = float("inf")

        for size, name in paper_sizes.items():
            distance = min(
                abs(width - size[0]) + abs(height - size[1]),
                abs(width - size[1]) + abs(height - size[0])
            )
            if distance < min_distance:
                min_distance = distance
                closest_match = name

        return closest_match

    
    def get_docx_paper_size(self, doc):
        section_width = 0
        section_height = 0
        paper_sizes = {
            (Inches(8.5), Inches(11)): "Short",
            (Inches(11), Inches(8.5)): "Short",
            (Inches(8.5), Inches(14)): "Long",
            (Inches(14), Inches(8.5)): "Long",
            (Inches(8.27), Inches(11.69)): "A4",
            (Inches(11.69), Inches(8.27)): "A4 ",
            (Inches(5.5), Inches(8.5)): "Half Letter",
            (Inches(4), Inches(6)): "Postcard",
            (Inches(17), Inches(22)): "Tabloid",
            # Include other sizes based on your requirements
            }

        # Using a set to collect sizes from different sections
        found_sizes = set()

        for section in doc.sections:
            # Get the page width and height
            section_width = section.page_width
            section_height = section.page_height

            # Check the dimensions against predefined sizes
            for size, name in paper_sizes.items():
                if abs(section_width - size[0]) < 0.1 and abs(section_height - size[1]) < 0.1:  # Increased tolerance to 0.1
                    found_sizes.add(name)

        # If there's only one unique size found
        if len(found_sizes) == 1:
            return next(iter(found_sizes))
        elif len(found_sizes) > 1:
            return "Mixed Sizes"
        else:
            # Return the actual dimensions if not a known size
            return f"{section_width} x {section_height}"


    def read_from_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return f.read().strip()
        except Exception:
            return None
                    
    def determineFileType(self, file_path):
        # Determine the file type based on the file extension (e.g., PDF, DOCX, image)
        if file_path.lower().endswith('.pdf'):
            return "PDF"
        elif file_path.lower().endswith('.docx'):
            return "DOCX"
        else:
            return "Unsupported"
        
    def get_pdf_file_details(self, file_path):
        doc = fitz.open(file_path)
        num_pages = len(doc)
        first_page = doc.load_page(0)
        paper_size = self.get_paper_size(first_page)
        additional_detail = ""  # You can set additional details here for PDFs
        return num_pages, paper_size, additional_detail

    def get_docx_file_details(self, file_path):
        doc = Document(file_path)
        num_paragraphs = len(doc.paragraphs)
        
        # Get the paper size for DOCX files
        paper_size = self.get_docx_paper_size(doc)
        
        additional_detail = f"Paragraphs: {num_paragraphs}"
        return 1, paper_size, additional_detail    
        
    def fetch_order_details(self, file_name):
        """Fetch order details for a given file name from the database."""
        conn = None
        try:
            # Connect to the database
            conn = sqlite3.connect('orders.db')
            cursor = conn.cursor()

            # Fetch the order details for the given file name
            cursor.execute("SELECT copies, color, instructions FROM orders WHERE file_name=?", (file_name,))
            order = cursor.fetchone()

            if order:
                return order
            else:
                return None, None, None

        except sqlite3.Error as e:
            print(f"Database error while fetching '{file_name}': {e}")
            return None, None, None
        
        finally:
            if conn:
                conn.close()

    def write_logs_to_json(self):
        try:
            with open("interaction_logs.json", "a") as file:
                # Check if the file is not empty
                if file.tell() != 0:
                    # Move the file cursor to the end of the file
                    file.seek(file.tell() - 2)
                    file.truncate()
                # Append the new logs to the existing file
                for log in self.notification_logs:
                    file.write(",\n")
                    json.dump(log, file)
                # Close the JSON array if there are logs
                if self.notification_logs:
                    file.write("\n]")
                    
        except Exception as e:
            print(f"Error writing logs to JSON file: {e}")


    def showSettingsDialog(self):
        # Create the settings dialog
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            
            # Extracting services info
            services_message_parts = []
            
            with open('paper_types.txt', 'w') as f:  # Opening file in write mode
                f.write("Our printing services are as follows:\n")
                for row in range(dialog.tableWidget.rowCount()):
                    paper_type = dialog.tableWidget.item(row, 0).text()
                    price_input = dialog.tableWidget.cellWidget(row, 1)
                    price = price_input.value()
                    # Write to the file
                    formatted_message = f"- {paper_type} : PHP {price:.2f} per page"
                    f.write(formatted_message + "\n")  # This writes to the paper_types.txt file in your desired format
                    
                    services_message_parts.append(formatted_message)
                
                f.write("Thats All Thanks!\n")
            
            # Update business location and Google Maps link
            global GOOGLE_MAPS_LINK
            GOOGLE_MAPS_LINK = dialog.mapsLinkInput.text().strip()
            # Save BUSINESS_LOCATION, and GOOGLE_MAPS_LINK to other files
            with open('google_maps_link.txt', 'w') as f:
                f.write(GOOGLE_MAPS_LINK)
                
    def check_new_orders(self):
        current_order_count = self.get_order_count()
        if current_order_count > self.last_order_count:
            QMessageBox.information(self, "New Order", "There's a new print order!")

            self.loadFiles()
            self.last_order_count = current_order_count
            
    def get_order_count(self):
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _save_settings_to_files(self):
        try:
            with open('paper_types.txt', 'w') as f:
                f.write(SERVICES_MESSAGE)
            with open('google_maps_link.txt', 'w') as f:
                f.write(GOOGLE_MAPS_LINK)
            QMessageBox.information(self, "Saved", "Settings have been successfully saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while saving the settings: {str(e)}")
        
        
    def delete_file(self):
        selected_items = self.fileTableWidget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a file to delete.")
            return

        selected_row = selected_items[0].row()
        file_name_item = self.fileTableWidget.item(selected_row, 0)
        file_status_item = self.fileTableWidget.item(selected_row, 5)  # Assuming the status is in the sixth column
        file_name = file_name_item.text()
        file_status = file_status_item.text()

        if file_status.lower() == "Ready for Pickup":
            QMessageBox.warning(self, "Cannot Delete", "Pickup orders cannot be deleted.")
            return

        confirmation = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the order '{file_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirmation == QMessageBox.Yes:
            file_path = os.path.join("downloaded_files", file_name)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)

                # Update the order details in the database and set 'archived' to 'Yes'
                conn = sqlite3.connect("orders.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE orders SET archived = ? WHERE file_name = ?", ('Yes', file_name))
                conn.commit()
                conn.close()

                # Refresh the table
                self.loadFiles()

                # Log the successful deletion
                interaction_log = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": f"Order '{file_name}' deleted",
                    "type": "Delete Order"
                }
                self.notification_logs.append(interaction_log)
                self.write_logs_to_json()

                QMessageBox.information(self, "Order Deleted", f"The Order '{file_name}' has been deleted.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while deleting the file: {str(e)}")
                return

    def toggleFlaskServer(self):

        
        global SERVICES_MESSAGE

        # Check if Flask server is not running
        if not self.flask_thread.isRunning():
            # Show confirmation prompt before starting the service
            result = QMessageBox.question(self, "Start Service", "Are you sure you want to start the service?", QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.Yes:
                self.toggleServerButton.setText("Shutdown Service")
                self.flask_thread.start()

                # Log and notify the start of the Flask server
                self.log_server_interaction("Service Started")
                QTimer.singleShot(2000, self.initializeServerComponents)

        else:  # If Flask server is already running
            # Show confirmation prompt before stopping the service
            result = QMessageBox.question(self, "Stop Service", "Are you sure you want to stop the service?", QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.Yes:
                self.toggleServerButton.setText("Start Service")
                self.flask_thread.terminate()

                # Log and notify the shutdown of the Flask server
                self.log_server_interaction("Service Stopped")
                QMessageBox.information(self, "Service Status", "The Service has been stopped.")

    def finish_order(self):
        if not self.flask_thread.isRunning():
            QMessageBox.warning(self, "Service Not Running", "Cannot finish order. Start the Service first.")
            return

        selected_rows = self.fileTableWidget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Error", "Please select an order first.")
            return

        row = selected_rows[0].row()

        # Extract details from the table for the selected order
        file_name = self.fileTableWidget.item(row, 0).text()
        order_status = self.fileTableWidget.item(row, 7).text()  # Index 7 is for "Order Status"

        # Check if the order is pending
        if order_status == "Pending":
            QMessageBox.warning(self, "Error", "Cannot mark the order as finished.")
            return

        if order_status == "Finished":
            QMessageBox.warning(self, "Error", "This order is already finished.")
            return

        # Check if the order has been picked up
        confirmation_pickup = QMessageBox.question(
            self, "Confirm Pickup",
            f"Have you confirmed that the order '{file_name}' has been picked up?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirmation_pickup == QMessageBox.No:
            return  # If the user selects "No" in the confirmation prompt, do not proceed

        # Update order status in the database
        update_order_status(file_name, "Finished", 0)  # Assuming cost_input is not needed for "Finished" status

        # Log and notify the successful finish of the order
        self.log_server_interaction(f"Order Finished: {file_name}")
        self.loadFiles()

        # Get the sender_id for the user associated with the finished order
        sender_id = self.get_sender_id_for_file(file_name)

        if sender_id:
            # Construct the thank-you message
            thank_you_message = (
                f"Thank you for trusting us with your print order!\n"
                f"Feel free to reach out if you have any more printing needs.\n"
                "Have a great day!"
            )

            # Send the thank-you message to the user
            send_message_to_user(sender_id, thank_you_message)

            # Show an information message indicating that the order has been marked as finished
            QMessageBox.information(self, "Order Finished", f"The order '{file_name}' has been marked as finished.")

        else:
            QMessageBox.warning(self, "Error", "Could not find user for this order.")




        #pwede isama 
    def isInternetConnected(self):
        try:
            # Attempt to ping a known server, e.g., Google's public DNS server
            # You can replace this with any reliable server or use a different method
            response = os.system("ping -n 1 8.8.8.8 > nul") if platform.system().lower() == "windows" else os.system("ping -c 1 8.8.8.8 > /dev/null")
            return response == 0
        except Exception as e:
            print(f"Error checking internet connection: {e}")
            return False

    def log_server_interaction(self, title):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        interaction_log = {"timestamp": timestamp, "title": title, "type": title}
        self.notification_logs.append(interaction_log)
        self.write_logs_to_json()

    def initializeServerComponents(self):
        try:
            response = requests.post("http://localhost:5000/initialize")
            if response.json().get('status') == 'initialized':
                QMessageBox.information(self, "Server Status", "The server is running!")
            else:
                QMessageBox.warning(self, "Server Status", "There was an error initializing server components.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not initialize server components: {e}")
            
    def serverStartedMessage(self):
        QMessageBox.information(self, "Bot Status", "The Bot is running!")
                     
    def start_flask_server(self):
        if not self.flask_thread.isRunning():
            self.flask_thread.start()
            self.startServerBtn.setText("Bot Running")
            self.startServerBtn.setEnabled(False)
            
    def shutdownFlask(self):
        global flask_thread  # Make sure the flask_thread is in global scope or accessible here
        flask_thread.shutdown()
        self.shutdownButton.setDisabled(True)  # Optional: Disable the button after shutting down

def send_message_to_user(sender_id, message_text):
    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "recipient": {
            "id": sender_id
        },
        "message": {
            "text": message_text
        }
    }
    response = requests.post(f"https://graph.facebook.com/v12.0/me/messages?access_token={PAGE_ACCESS_TOKEN}", headers=headers, json=data)
    return response.json()
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FileViewer()
    window.show()
    sys.exit(app.exec_())