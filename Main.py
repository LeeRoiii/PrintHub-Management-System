import requests
import sys
import os
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QKeySequence
from PyQt5.QtCore import Qt, QSize, QEvent, QRect,QPoint
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                                    QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                             QSpacerItem, QSizePolicy, QShortcut, QStackedWidget,QMessageBox,QMenu,QActionGroup)
import qtawesome as qta
from FileViewer import FileViewer
from Dashboard import Dashboard
from Archived import ArchivedOrdersDialog
from Stylesheet import MENU_STYLESHEET
date_column_index = 1

class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.pages = []
        self.current_page = 0       
        self.mousePressAction = None
        self.resizeEdgeMargin = 10
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self.page_container = QStackedWidget()
        self._setup_main_window()
        self._setup_title_bar()
        self._setup_content()
        self.page_container.currentChanged.connect(self.on_page_changed)
        self.service_started = False
        # Set up the month QMenu
        self.monthActionGroup = QActionGroup(self)
        self.monthMenu = QMenu(self)
        self.monthMenu.setStyleSheet(MENU_STYLESHEET)
        months = [
            "All Time", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        for index, month in enumerate(months):
            action = self.monthMenu.addAction(month)
            action.setCheckable(True)
            self.monthActionGroup.addAction(action)
            action.triggered.connect(self.createMonthFilter(index))
            
    def _setup_main_window(self):
        self.setMinimumSize(1500, 820)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(300, 300, 1280, 850)
        self.setWindowFlags(Qt.FramelessWindowHint)
        shadow_effect = QGraphicsDropShadowEffect(self)
        shadow_effect.setBlurRadius(40)
        shadow_effect.setXOffset(0)
        shadow_effect.setYOffset(5)
        shadow_effect.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow_effect)

    def _setup_title_bar(self):
        # Constants
        HEADER_BG_COLOR = "rgba(255, 255, 255, 180)"
        HEADER_BORDER_COLOR = "rgba(255, 255, 255, 50)"
        ICON_COLOR = '#333'
        TITLE_FONT = "Concord"
        TITLE_SIZE = 18
        ICON_SIZE = 24

        # Create main title container layout
        title_container = QHBoxLayout()
        title_container.setContentsMargins(10, 10, 10, 0)

        # Set up the header widget with styles
        self.header_widget = QWidget()
        header_style = f"""
            background-color: {HEADER_BG_COLOR};
            border: 1px solid {HEADER_BORDER_COLOR};
            border-radius: 10px;
        """
        self.header_widget.setStyleSheet(header_style)

        # Layout for the header
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Set up buttons for the header
        self._setup_buttons()

        # Set up the header icon and label
        header_icon = qta.icon('fa.print', color=ICON_COLOR)
        icon_label = QLabel()
        icon_label.setPixmap(header_icon.pixmap(QSize(ICON_SIZE, ICON_SIZE)))

        # Add a title label to the __init__ method
        self.header_title = QLabel("Print Orders")  # Initial title
        header_title_style = """
            font-family: 'Concord';
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-left: 0px;
        """
        self.header_title.setStyleSheet(header_title_style)

        # Connect the on_page_changed method to the currentChanged signal
        self.page_container.currentChanged.connect(self.on_page_changed)

        # Add widgets and layouts to the header layout
        header_layout.addWidget(icon_label)
        header_layout.addWidget(self.header_title, alignment=Qt.AlignLeft)  # Use self.header_title
        header_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        header_layout.addLayout(self.title_bar)

        # Add the header widget to the main layout
        title_container.addWidget(self.header_widget)  # Keep the existing header widget
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addLayout(title_container)

    def _setup_buttons(self):
        button_common_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 230);
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(220, 220, 220, 230);
            }
        """
        self.nav_left_btn = QPushButton()
        self.nav_left_btn.setIcon(qta.icon('fa.arrow-left', color='#040D12'))
        self.nav_left_btn.setFixedSize(24, 24)
        self.nav_left_btn.setStyleSheet("background: transparent; border: none;")
        self.nav_left_btn.clicked.connect(self.navigate_previous_tab)

        self.nav_right_btn = QPushButton()
        self.nav_right_btn.setIcon(qta.icon('fa.arrow-right', color='#040D12'))
        self.nav_right_btn.setFixedSize(24, 24)
        self.nav_right_btn.setStyleSheet("background: transparent; border: none;")
        self.nav_right_btn.clicked.connect(self.navigate_next_tab) 


        self.calendarBtn = QPushButton()
        self.calendarBtn.setIcon(qta.icon('fa.calendar', color='#040D12'))
        self.calendarBtn.setFixedSize(24, 24)
        self.calendarBtn.setStyleSheet("background: transparent; border: none;")
        self.calendarBtn.clicked.connect(self.showMonthFilter)

        self.close_btn = QPushButton()
        self.close_btn.setIcon(qta.icon('fa.times', color='#040D12', scale_factor=0.8))
        self.close_btn.setStyleSheet(button_common_style)
        self.close_btn.setIconSize(QSize(16, 16))
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.close)

        self.minimize_btn = QPushButton()
        self.minimize_btn.setIcon(qta.icon('fa.minus', color='#040D12'))
        self.minimize_btn.setStyleSheet(button_common_style)
        self.minimize_btn.setIconSize(QSize(16, 16))
        self.minimize_btn.setFixedSize(24, 24)
        self.minimize_btn.clicked.connect(self.showMinimized)

        self.maximize_btn = QPushButton()
        self.maximize_btn.setIcon(qta.icon('fa.square-o', color='#040D12'))
        self.maximize_btn.setStyleSheet(button_common_style)
        self.maximize_btn.setIconSize(QSize(16, 16))
        self.maximize_btn.setFixedSize(24, 24)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        
        # Add the "Open Folder" button
        self.open_folder_btn = QPushButton()
        self.open_folder_btn.setIcon(qta.icon('fa.folder-open', color='#040D12'))
        self.open_folder_btn.setFixedSize(24, 24)
        self.open_folder_btn.setStyleSheet("background: transparent; border: none;")
        self.open_folder_btn.clicked.connect(self.open_download_folder)
        self.open_folder_btn.hide()  # Initially hide the open_folder_btn

        # Add the "Archived" button
        self.showArchivedButton = QPushButton()
        self.showArchivedButton.setIcon(qta.icon('fa.archive', color='#040D12'))
        self.showArchivedButton.setStyleSheet(button_common_style) 
        self.showArchivedButton.setIconSize(QSize(16, 16))
        self.showArchivedButton.setFixedSize(24, 24)
        self.showArchivedButton.clicked.connect(self.showArchivedOrders)
        self.showArchivedButton.hide()  # Initially hide the showArchivedButton
    
        self.title_bar = QHBoxLayout()
        self.title_bar.setSpacing(5)
        
        self.title_bar.addWidget(self.nav_left_btn)
        self.title_bar.addWidget(self.nav_right_btn)
        self.title_bar.addWidget(self.calendarBtn)
        self.title_bar.addWidget(self.showArchivedButton) 
        self.title_bar.addWidget(self.open_folder_btn)  # Add the open_folder_btn
        self.title_bar.addWidget(self.minimize_btn)
        self.title_bar.addWidget(self.maximize_btn)
        self.title_bar.addWidget(self.close_btn)
        
    def navigate_previous_tab(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.page_container.setCurrentIndex(self.current_page)
            print(f"Moved to page {self.current_page}")
        else:
            print("Already on the first page!")

    def navigate_next_tab(self):
        if self.current_page < self.page_container.count() - 1:
            self.current_page += 1
            self.page_container.setCurrentIndex(self.current_page)
            print(f"Moved to page {self.current_page}")
            
            # Check if the current page is an instance of Dashboard
            if isinstance(self.page_container.currentWidget(), Dashboard):
                # Call the update_data method in Dashboard
                self.page_container.currentWidget().update_data()
                
        else:
            print("Already on the last page!")

    def is_internet_available():
        try:
            response = requests.get("http://www.google.com", timeout=5)
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def on_page_changed(self, index):
        """Handle the change of pages in the stacked widget."""
        if index == 1:  # Assuming that theis at index 1
            self.calendarBtn.hide()
            self.showArchivedButton.show()
            self.open_folder_btn.show()  # Show the open_folder_btn
            self.header_title.setText("Dashboard")  # Update title for the graph page
        else:
            self.calendarBtn.show()
            self.showArchivedButton.hide()
            self.open_folder_btn.hide()  # Hide the open_folder_btn
            self.header_title.setText("Print Order")  # Reset title for other pages
      
    def _setup_content(self):
        self.page_container = QStackedWidget()
        self.file_viewer = FileViewer()
        self.page_container.addWidget(self.file_viewer)

        new_page = Dashboard()
        self.page_container.addWidget(new_page)
        self.main_layout.addWidget(self.page_container)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        self.startGeometry = self.geometry()
        mouseX = event.globalX()
        mouseY = event.globalY()
        x, y, w, h = self.geometry().getRect()
        if mouseX < x + self.resizeEdgeMargin:
            self.mousePressAction = "resizeLeft"
        elif mouseX > x + w - self.resizeEdgeMargin:
            self.mousePressAction = "resizeRight"
        if mouseY < y + self.resizeEdgeMargin:
            self.mousePressAction = (self.mousePressAction or "") + "resizeTop"
        elif mouseY > y + h - self.resizeEdgeMargin:
            self.mousePressAction = (self.mousePressAction or "") + "resizeBottom"
        if not self.mousePressAction:
            self.mousePressAction = "drag"

    def mouseMoveEvent(self, event):
        mouseX, mouseY = event.globalX(), event.globalY()
        if self.mousePressAction == "drag":
            self.move(event.globalPos() - self.drag_position)
        elif self.mousePressAction:
            newRect = QRect(self.startGeometry)
            if "resizeLeft" in self.mousePressAction:
                newRect.setLeft(mouseX)
            if "resizeRight" in self.mousePressAction:
                newRect.setRight(mouseX)
            if "resizeTop" in self.mousePressAction:
                newRect.setTop(mouseY)
            if "resizeBottom" in self.mousePressAction:
                newRect.setBottom(mouseY)
            if newRect.width() > self.minimumWidth() or newRect.height() > self.minimumHeight():
                self.setGeometry(newRect)
        self.updateCursor(event)

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
        painter.drawRoundedRect(10, 10, self.width() - 20, self.height() - 20, 20, 20)

    def mouseReleaseEvent(self, event):
        self.mousePressAction = None
        self.updateCursor(event)

    def updateCursor(self, event):
        mouseX = event.pos().x()
        mouseY = event.pos().y()
        x, y, w, h = self.geometry().getRect()
        if mouseX < self.resizeEdgeMargin:
            if mouseY < self.resizeEdgeMargin:
                self.setCursor(Qt.SizeFDiagCursor)
            elif mouseY > h - self.resizeEdgeMargin:
                self.setCursor(Qt.SizeBDiagCursor)
            else:
                self.setCursor(Qt.SizeHorCursor)
        elif mouseX > w - self.resizeEdgeMargin:
            if mouseY < self.resizeEdgeMargin:
                self.setCursor(Qt.SizeBDiagCursor)
            elif mouseY > h - self.resizeEdgeMargin:
                self.setCursor(Qt.SizeFDiagCursor)
            else:
                self.setCursor(Qt.SizeHorCursor)
        elif mouseY < self.resizeEdgeMargin or mouseY > h - self.resizeEdgeMargin:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseMove:
            self.updateCursor(event)
        return super().eventFilter(obj, event)
    
    def showMonthFilter(self):   
        position = self.calendarBtn.mapToGlobal(QPoint(0, self.calendarBtn.height()))
        self.monthMenu.exec_(position)
        
        
    def filterByMonth(self, month_idx):
        self.monthActionGroup.actions()[month_idx].setChecked(True)
        
        if hasattr(self, 'file_viewer'):
            self.file_viewer.loadFiles(month_idx)
            
    def createMonthFilter(self, idx):
        return lambda checked: self.filterByMonth(idx)
    
    def showArchivedOrders(self):
        archived_orders_dialog = ArchivedOrdersDialog(self)
        archived_orders_dialog.exec_()
    
    def open_download_folder(self):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        folder_path = os.path.join(script_dir, 'downloaded_files')
        os.makedirs(folder_path, exist_ok=True)  # Ensure the folder exists
        os.startfile(folder_path)  # Open the folder using the default file explorer

    def closeEvent(self, event):
            reply = QMessageBox.question(
                self, 'Exit Confirmation',
                "Are you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()
                
if __name__ == "__main__":
    try:
        QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)
        app = QApplication(sys.argv)
        window = Main()
        window.show()
        close_shortcut = QShortcut(QKeySequence("Ctrl+Q"), window)
        close_shortcut.activated.connect(window.close)
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        


