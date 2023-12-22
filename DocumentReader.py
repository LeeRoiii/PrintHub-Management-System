import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QScrollArea, QFrame, QAction, QMessageBox, QProgressBar
from PyQt5.QtPrintSupport import QPrintDialog
from PyQt5.QtGui import QPixmap, QImage, QPainter, QKeySequence, QIcon
from PyQt5.QtCore import QSize, Qt, QTimer
from openpyxl import load_workbook 
import fitz
import docx2pdf
from docx.shared import Pt
from PyQt5.QtCore import Qt
from docx import Document
from qtawesome import icon
from qtawesome import icon as qta_icon
import openpyxl
import win32com.client
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


class DocumentReader(QMainWindow):
    EditShortcut = "Ctrl+E"
    def __init__(self, file_path):
        super().__init__()

        # Set the main window's properties
        self.setWindowTitle("Document Reader")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(qta_icon('fa.file-text-o', color='black'))
        self.initUI()
        self.createActions()
        self.createToolbar()
        self.current_document_path = file_path
        self.showFilePreview(file_path)
        self.converted_pdf_path = None
        self.current_page_index = 0  
    def initUI(self):
        self.scrollArea = QScrollArea(self)
        self.container = QWidget()
        self.scrollLayout = QVBoxLayout(self.container)
        
        primary_color = "#24292E"  # Almost black - for main background
        secondary_color = "#586069"  # Dark grey - for text and icons
        accent_color = "#0366D6"  # Bright blue - for accents and highlights
        content_bg_color = "linear-gradient(to bottom, #FAFAFA, #EAEAEA)"  # Gradient for content
        
        # Apply styles
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {primary_color};
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
                margin: 15px;
            }}
            QWidget {{
                background: {content_bg_color};
                border-radius: 10px;
                padding: 20px;
            }}
            QLabel {{
                color: {secondary_color};
                font-size: 14px;
            }}
        """)
        self.scrollArea.setFrameShape(QFrame.NoFrame)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.container)
        
        self.setWindowTitle("Document Reader")
        self.setGeometry(100, 100, 800, 600)  # Keep the window size spacious
        self.setCentralWidget(self.scrollArea)
        
    def onDocumentReaderClosed(self):
        self.documentClosed.emit(self.current_document_path)

    def createActions(self):
        
        self.editDocumentAction = QAction(icon('fa.edit', color='#333'), "Edit Document", self)
        self.editDocumentAction.setShortcut(QKeySequence(self.EditShortcut))
        self.editDocumentAction.triggered.connect(self.editDocument)

        self.fullScreenAction = QAction(icon('fa.expand', color='#333'), "Full Screen", self)
        self.fullScreenAction.setShortcut(QKeySequence.FullScreen)
        self.fullScreenAction.triggered.connect(self.fullScreen)

        self.printAction = QAction(icon('fa.print', color='#333'), "Print", self)
        self.printAction.setShortcut(QKeySequence.Print)
        self.printAction.triggered.connect(self.printDocument)
        
        self.nextPageAction = QAction(icon('fa.arrow-right', color='#333'), "Next Page", self)
        self.nextPageAction.setShortcut(QKeySequence("Ctrl+Right"))
        self.nextPageAction.triggered.connect(self.nextPage)

        self.prevPageAction = QAction(icon('fa.arrow-left', color='#333'), "Previous Page", self)
        self.prevPageAction.setShortcut(QKeySequence("Ctrl+Left"))
        self.prevPageAction.triggered.connect(self.previousPage)
    def createToolbar(self):
        toolbar_style = """
        QToolBar {
            background-color: #FFFFFF;
            spacing: 10px;
            border: 1px solid #E1E1E1;
            border-radius: 5px;
        }
        QToolButton {
            background-color: transparent;
            padding: 5px;
            font-size: 16px;
            color: #333;
            border: none;
        }
        QToolButton:hover {
            background-color: #E0E0E0;
        }
        QToolButton:pressed {
            background-color: #D0D0D0;
        }
        """
        
        self.setStyleSheet(toolbar_style)
        self.toolbar = self.addToolBar("Tools")
        self.toolbar.setMovable(False)
        self.toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        self.toolbar.setIconSize(QSize(20, 20))  # Slightly reduced icon size
        self.toolbar.addAction(self.editDocumentAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.printAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.fullScreenAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.prevPageAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.nextPageAction)
        # Remove hover effect
        for action in self.toolbar.actions():
            widget = self.toolbar.widgetForAction(action)
            widget.setGraphicsEffect(None)
            
    def closeEvent(self, event):
        print("Closing the window")  # Add this line to check if closeEvent is called
        
        # Ask the user for confirmation before closing the window
        reply = QMessageBox.question(self, 'Confirm Close',
                                    'Are you sure you want to close?',
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)

        if reply == QMessageBox.Yes:
            # Delete the converted PDF file when the window is closed
            if hasattr(self, 'converted_pdf_path') and self.converted_pdf_path and os.path.exists(self.converted_pdf_path):
                try:
                    os.remove(self.converted_pdf_path)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to delete PDF file: {str(e)}")        

            # Continue with the default close event
            super().closeEvent(event)
        else:
            # Cancel the close event
            event.ignore()

            
    def get_current_document_path(self):
        # You can use this method to retrieve the current document path
        return self.current_document_path
    
    def editDocument(self):
        current_document_path = self.get_current_document_path()

        if current_document_path:
            try:
                if current_document_path.lower().endswith('.pdf'):
                    # If the current document is a PDF, open it with the default PDF viewer
                    os.startfile(current_document_path)
                else:
                    # If it's not a PDF, assume it's a DOCX and open it with the default application
                    os.startfile(current_document_path)
            except Exception as e:
                print(f"Error opening document: {e}")
        else:
            print("No document loaded.")

    def fullScreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def printDocument(self):
        # Currently supports image printing
        printer = QPrintDialog(self)
        if printer.exec_() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            rect = painter.viewport()
            size = self.container.size()
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(self.container.rect())
            self.container.render(painter)
            
    def showFilePreview(self, filePath):
        if filePath.endswith('.pdf'):
            self.showPDFPreview(filePath)
        elif filePath.endswith('.docx'):
            self.showDOCXPreview(filePath)
        elif filePath.endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            self.showImagePreview(filePath)
        else:
            print(f"Unsupported file type: {filePath}")

        
    def showPDFPreview(self, filePath):
        doc = fitz.open(filePath)

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            img = page.get_pixmap()
            qt_img = QPixmap.fromImage(QImage(img.samples, img.width, img.height, img.stride, QImage.Format_RGB888))
            img_label = QLabel()
            img_label.setPixmap(qt_img)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setContentsMargins(10, 10, 10, 10)
            
            # Page numbers for clarity
            page_number = QLabel(f"Page {page_num + 1}")
            page_number.setAlignment(Qt.AlignCenter)
            page_number.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; background-color: #EEE; border-radius: 4px;")
            
            self.scrollLayout.addWidget(page_number)
            self.scrollLayout.addWidget(img_label)

        self.scrollLayout.addStretch()
        


    def showDOCXPreview(self, filePath):
        # Get the base filename without extension
        base_filename = os.path.splitext(os.path.basename(filePath))[0]

        # Convert DOCX to PDF
        self.converted_pdf_path = os.path.join(os.path.dirname(filePath), f"{base_filename}_converted.pdf")
        try:
            docx2pdf.convert(filePath, self.converted_pdf_path)
        except Exception as e:
            error_message = f"Failed to convert DOCX to PDF: {str(e)}"
            QMessageBox.warning(self, "Conversion Error", error_message)
            print(error_message)  # Print the error to the console for debugging
            return

        # Show the PDF preview using the converted PDF path
        self.showPDFPreview(self.converted_pdf_path)



    def nextPage(self):
        # Navigate to the next page
        if self.current_page_index < self.scrollLayout.count() - 2:  # Subtract 2 to account for the stretch item
            self.current_page_index += 2
            self.scrollToPage(self.current_page_index)

    def previousPage(self):
        # Navigate to the previous page
        if self.current_page_index >= 2:
            self.current_page_index -= 2
            self.scrollToPage(self.current_page_index)

    def scrollToPage(self, page_index):
        # Calculate the position in the layout based on the page index
        position = self.scrollLayout.itemAt(page_index).geometry().top()
        self.scrollArea.verticalScrollBar().setValue(position)

    def pixmap_to_image(self, pixmap):
        image = QImage(pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, QImage.Format_RGB888)
        return image
        
    def showImagePreview(self, filePath):
        pixmap = QPixmap(filePath)
        img_label = QLabel()
        img_label.setPixmap(pixmap)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setContentsMargins(10, 10, 10, 10)
        
        self.scrollLayout.addWidget(img_label)
        self.scrollLayout.addStretch()