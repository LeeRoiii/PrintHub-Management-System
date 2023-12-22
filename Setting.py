from PyQt5.QtWidgets import QDialog, QVBoxLayout,QDoubleSpinBox,QInputDialog,QMessageBox, QGroupBox, QTableWidget, QTableWidgetItem, QAbstractItemView, QLabel, QLineEdit, QPushButton, QFormLayout, QDialogButtonBox, QHeaderView
from PyQt5.QtGui import QFont
import qtawesome as qta
import re
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Edit")
        self.setWindowIcon(qta.icon('fa5s.cog'))  # Replace 'fa5s.cog' with the desired icon name
        self.setupUI()

    def setupUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Use a consistent font
        default_font = QFont('Arial', 10)

        # Paper type settings group
        paperTypeGroup = QGroupBox("Paper Types and Prices")
        paperLayout = QVBoxLayout()

        desc_label = QLabel("Manage your paper types and their prices:")
        font = desc_label.font()
        font.setPointSize(12)
        font.setWeight(QFont.Bold)
        desc_label.setFont(font)
        paperLayout.addWidget(desc_label)

        self.tableWidget = QTableWidget(self)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["Paper Type", "Price (PHP)"])
        self.tableWidget.setToolTip("Double-click to edit prices.")
        self.tableWidget.setEditTriggers(QAbstractItemView.DoubleClicked)
        paperLayout.addWidget(self.tableWidget)

        # Adjusting header sizes
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        add_layout = QVBoxLayout()

        self.add_button = QPushButton("Add Paper Type", self)
        self.add_button.setToolTip("Add a new paper type row.")
        self.add_button.setFont(QFont('Arial', 10))
        self.add_button.clicked.connect(self.add_paper_type_dialog)
        add_layout.addWidget(self.add_button)
        # Add a Delete button
        self.delete_button = QPushButton("Delete Paper Type", self)
        self.delete_button.setToolTip("Delete the selected paper type")
        self.delete_button.setFont(QFont('Arial', 10))
        self.delete_button.clicked.connect(self.delete_paper_type)
        add_layout.addWidget(self.delete_button)

        paperLayout.addLayout(add_layout)
        paperTypeGroup.setLayout(paperLayout)
        layout.addWidget(paperTypeGroup)

        locationGroup = QGroupBox("Set Location")
        locationLayout = QFormLayout()

        self.mapsLinkInput = QLineEdit(self)
        self.mapsLinkInput.setPlaceholderText("Enter Google Maps link for your business")
        current_map_link = self.read_from_file("google_maps_link.txt")
        if current_map_link:
            self.mapsLinkInput.setText(current_map_link)
            self.lastValidMapsLink = current_map_link
        locationLayout.addRow("Google Maps Link:", self.mapsLinkInput)

        # Add an Edit/Save button for the Google Maps link
        self.editSaveMapsLinkButton = QPushButton("Edit", self)
        self.editSaveMapsLinkButton.setToolTip("Edit or Save the Google Maps link.")
        self.editSaveMapsLinkButton.setFont(QFont('Arial', 10))
        self.editSaveMapsLinkButton.clicked.connect(self.toggle_edit_save_maps_link)
        locationLayout.addWidget(self.editSaveMapsLinkButton)

        locationGroup.setLayout(locationLayout)
        layout.addWidget(locationGroup)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.setFont(default_font)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)


        # Now load and display paper types from file
        self.load_paper_types_from_file()

        # Connect cell value changed signal for inline editing
        self.tableWidget.cellChanged.connect(self.handle_cell_changed)

        # Styling (for example)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #040D12;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
            }
            QPushButton {
                background-color: #040D12;
                border: none;
                color: white;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #183D5C;
            }
        """)
            
    # Add a function to toggle the visibility of Edit and Save buttons
    # Add a function to toggle the visibility of Edit and Save buttons
    def toggle_edit_save_maps_link(self):
        current_link = self.mapsLinkInput.text().strip()

        if self.editSaveMapsLinkButton.text() == "Edit":
            # Switch to editing mode
            self.editSaveMapsLinkButton.setText("Save")
            self.mapsLinkInput.setReadOnly(False)
            self.mapsLinkInput.setFocus()  # Set focus to the input field
        else:
            # Switch to saving mode
            self.editSaveMapsLinkButton.setText("Edit")
            self.mapsLinkInput.setReadOnly(True)

            if current_link == self.lastValidMapsLink:
                QMessageBox.information(self, "No Change", "There is no change in your edit.")
            else:
                # Save the link if it has changed
                if self.is_valid_maps_link(current_link):
                    self.save_maps_link()
                    QMessageBox.information(self, "Google Maps Link Saved", "Google Maps link has been saved successfully.")
                else:
                    # If the link is invalid, restore the last valid link and set it as read-only
                    self.mapsLinkInput.setText(self.lastValidMapsLink)
                    self.mapsLinkInput.setReadOnly(True)
                    QMessageBox.warning(self, "Invalid Link", "The entered Google Maps link is invalid. Reverted to the last valid link.")


    # Add a function to check if the Google Maps link is valid
    def is_valid_maps_link(self, link):
        maps_link_pattern = re.compile(r'^https?://www\.google\.com/maps/.*$')
        return bool(maps_link_pattern.match(link))
    
    # Add a function to handle saving the Google Maps link
    def save_maps_link(self):
        maps_link = self.mapsLinkInput.text().strip()

        # Validate the Google Maps link using a regular expression
        maps_link_pattern = re.compile(r'^https?://www\.google\.com/maps/.*$')
        if not maps_link_pattern.match(maps_link):
            QMessageBox.warning(self, "Invalid Link", "Please enter a valid Google Maps link.")
            
            # Restore the last valid link
            if self.lastValidMapsLink is not None:
                self.mapsLinkInput.setText(self.lastValidMapsLink)
                
            return

        # Save the current link as the last valid link
        self.lastValidMapsLink = maps_link

        with open("google_maps_link.txt", "w") as file:
            file.write(maps_link)
        QMessageBox.information(self, "Google Maps Link Saved", "Google Maps link has been saved successfully.")
        self.mapsLinkInput.setReadOnly(True)  # Set read-only after saving
        
    def handle_cell_changed(self, row, column):
        if column == 1:
            # Price column changed, update the value and save
            price_item = self.tableWidget.item(row, column)
            if price_item:
                try:
                    if not price_item.text().strip():
                        # If the cell is left blank, make it blank and save
                        price_item.setText("")
                    else:
                        # Otherwise, try to parse the entered value as a float
                        price = float(price_item.text())
                        # Perform any additional validation if needed
                        self.save_paper_types_to_file()
                except ValueError:
                    # If the conversion to float fails, restore the previous content
                    prev_content = self.read_from_file("paper_types.txt").split('\n')[row].split(':')[1]
                    price_item.setText(prev_content)
                    QMessageBox.warning(self, "Invalid Price", "Please enter a valid price.")



    def read_from_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return f.read().strip()
        except Exception:
            return None

    def delete_paper_type(self):
        selected_rows = self.tableWidget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a paper type to delete.")
            return

        confirmation = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete the selected paper type?",
                                            QMessageBox.Yes | QMessageBox.No)
        if confirmation == QMessageBox.Yes:
            for row in selected_rows:
                if "Our printing services are as follows:" not in self.tableWidget.item(row.row(), 0).text():
                    self.tableWidget.removeRow(row.row())
            self.save_paper_types_to_file()


    def add_paper_type(self, paper_type_name, initial_price):
        row_position = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_position)

        paper_type_item = QTableWidgetItem(paper_type_name)
        self.tableWidget.setItem(row_position, 0, paper_type_item)

        price_input = QDoubleSpinBox(self)
        price_input.setRange(0.01, 1000.0)
        price_input.setValue(initial_price)
        price_input.setPrefix("PHP ")
        self.tableWidget.setCellWidget(row_position, 1, price_input)
        
    def add_paper_type_dialog(self):
        paper_type, ok1 = QInputDialog.getText(self, "Add Paper Type", "Enter Paper Type (e.g., A5):")
        if ok1:
            price, ok2 = QInputDialog.getDouble(self, "Add Paper Type", "Enter Price (PHP):", 0.0, 0.01, 1000.0, 2)
            if ok2:
                self.add_paper_type(paper_type, price)
                self.save_paper_types_to_file()
            
    def save_paper_types_to_file(self):
        with open('paper_types.txt', 'w') as f:
            f.write("Our printing services are as follows:\n")

            for row in range(self.tableWidget.rowCount()):
                paper_type_item = self.tableWidget.item(row, 0)
                price_input = self.tableWidget.cellWidget(row, 1)

                if paper_type_item and price_input:
                    paper_type = paper_type_item.text()
                    price = price_input.value()
                    # Format the price with two decimal places, add "per page", and include 'PHP' as the currency symbol
                    formatted_price = f"PHP {price:.2f} per page"
                    f.write(f"- {paper_type}: {formatted_price}\n")

            f.write("That's All. Thanks!\n")




    def load_paper_types_from_file(self):
        try:
            with open('paper_types.txt', 'r') as f:
                content = f.readlines()

            # Assuming that each line in the file has the format "- paper_type: PHP price per page"
            for line in content:
                if line.startswith('-'):
                    parts = line.split(':')
                    if len(parts) == 2:
                        paper_type = parts[0].strip()[2:]  # Extracting the paper type
                        price_str = parts[1].strip().split()[1]  # Extracting the price string
                        if price_str:  # Check if the price string is not empty
                            price = float(price_str)
                            self.add_paper_type(paper_type, price)

        except FileNotFoundError:
            print("File not found: paper_types.txt")
        except Exception as e:
            print(f"Error loading paper types from file: {e}")
