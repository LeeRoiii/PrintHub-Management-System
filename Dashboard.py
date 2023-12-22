from PyQt5.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,  QListWidget, QListWidgetItem, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QDateTime,pyqtSignal,QDate
from PyQt5.QtGui import QPainter, QColor, QBrush
from PyQt5.QtChart import QBarSeries, QBarSet, QChart, QChartView, QBarCategoryAxis, QValueAxis,QAbstractBarSeries
import qtawesome as qta
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta

logging.basicConfig(filename='interaction.log', level=logging.INFO)
class Dashboard(QWidget):
    update_signal = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 800, 600)
        self.notification_logs = []
        self.load_logs_from_json()
        self.total_pending_orders = 0
        self.total_finished_orders = 0
        self.total_orders = 0
        self.chart = QChart()
        # Initialize key metrics
        self.total_pending_orders = self.fetch_total_orders("Pending")
        self.total_finished_orders = self.fetch_total_orders("Finished")
        # total_orders should be defined here based on the provided code.

        # Create rectangles representing different sections
        pending_orders_rect = QFrame(self)
        pending_orders_rect.setFrameShape(QFrame.StyledPanel)
        pending_orders_rect.setObjectName("PendingOrdersRect")  # Apply a style to this rect in CSS

        finished_orders_rect = QFrame(self)
        finished_orders_rect.setFrameShape(QFrame.StyledPanel)
        finished_orders_rect.setObjectName("FinishedOrdersRect")  # Apply a style to this rect in CSS

        # Create a new rectangle representing another section
        additional_rect = QFrame(self)
        additional_rect.setFrameShape(QFrame.StyledPanel)
        additional_rect.setObjectName("AdditionalRect")  # Apply a style to this rect in CSS
        # Create a new rectangle representing another section
        # Set fixed sizes for the rectangles
        rect_width = 420
        rect_height = 120
        pending_orders_rect.setFixedSize(rect_width, rect_height)
        finished_orders_rect.setFixedSize(rect_width, rect_height)


        # Create content for the pending orders
        self.pending_orders_label = QLabel(f"Pending Orders: {self.total_pending_orders}")
        self.pending_orders_label.setStyleSheet("font-family: Arial; font-size: 12px; color: black;")
        pending_orders_icon = QLabel()
        pending_orders_icon.setPixmap(qta.icon('fa.clock-o', color='white').pixmap(35, 35))  # Use qta icon
        pending_orders_layout = QHBoxLayout(pending_orders_rect)
        pending_orders_layout.addWidget(pending_orders_icon, alignment=Qt.AlignCenter)
        pending_orders_layout.addWidget(self.pending_orders_label, alignment=Qt.AlignCenter)

        # Create content for the finished orders
        self.finished_orders_label = QLabel(f"Total Finished Orders: {self.total_finished_orders}")
        self.finished_orders_label.setStyleSheet("font-family: Arial; font-size: 12px; color: black;")
        finished_orders_icon = QLabel()
        finished_orders_icon.setPixmap(qta.icon('fa.check', color='white').pixmap(35, 35))  # Use qta icon
        finished_orders_layout = QHBoxLayout(finished_orders_rect)
        finished_orders_layout.addWidget(finished_orders_icon, alignment=Qt.AlignCenter)
        finished_orders_layout.addWidget(self.finished_orders_label, alignment=Qt.AlignCenter)

        
        # Create content for the new rectangle
        additional_label = QLabel("PRINTING SERVICE")
        additional_icon = QLabel()
        additional_layout = QHBoxLayout(additional_rect)
        additional_layout.addWidget(additional_label, alignment=Qt.AlignCenter)
        
        # Create a layout for the rectangles
        rectangles_layout = QHBoxLayout()
        rectangles_layout.addWidget(pending_orders_rect)
        rectangles_layout.addWidget(finished_orders_rect)
        rectangles_layout.addWidget(additional_rect)
        self.setStyleSheet("""
            #PendingOrdersRect {
                background-color: #FFA07A;  /* Light Salmon */
                border: 2px solid #8B4513;  /* Saddle Brown border */
                border-radius: 10px;
                margin: 10px;
                padding: 10px;  /* Add padding for content inside the rectangle */
            }
            #PendingOrdersRect QLabel {
                color: #fff;  /* Text color inside the rectangle */
                font-size: 16px;  /* Font size of the text */
            }

            #FinishedOrdersRect {
                background-color: #32CD32;  /* Lime Green */
                border: 2px solid #006400;  /* Dark Green border */
                border-radius: 10px;
                margin: 10px;
                padding: 10px;
            }
            #FinishedOrdersRect QLabel {
                color: #fff;
                font-size: 16px;
            }

            #TotalFinishedOrdersRect {
                background-color: #4682B4;  /* Steel Blue */
                border: 2px solid #1E90FF;  /* Dodger Blue border */
                border-radius: 10px;
                margin: 10px;
                padding: 10px;
            }
            #TotalFinishedOrdersRect QLabel {
                color: #fff;
                font-size: 16px;
            }

            #AdditionalRect {
                background-color: #87CEFA;  /* Light Sky Blue */
                border: 2px solid #4682B4;  /* Steel Blue border */
                border-radius: 10px;
                margin: 10px;
                padding: 10px;
            }
            #AdditionalRect QLabel {
                color: #000;  /* Different text color for this rectangle */
                font-size: 14px;  /* Different font size for this rectangle */
            }
            """)


        # Create a QLabel to display date and time
        self.date_time_label = QLabel()
        self.date_time_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        date_time_layout = QVBoxLayout()
        date_time_layout.addWidget(self.date_time_label)
        # Create a QListWidget for notifications
        self.notification_list = QListWidget()
        self.notification_list.sortItems(Qt.DescendingOrder)
        self.notification_list.setFixedWidth(280)
        self.notification_list.setWordWrap(True)

        # Set up the main layout for the Dashboard
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(rectangles_layout)
        graph_and_logs_layout = QHBoxLayout()

        # Create a wrapper frame for the notification panel with background styling
        notification_frame = QFrame(self)
        notification_frame.setObjectName("NotificationFrame")
        notification_frame.setStyleSheet("""
            QFrame#NotificationFrame {
                background-color: #f5f5f5;  /* Light Gray */
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 2 px;
            }
        """)

        # Add a title for the notification panel within the background styling
        title_label = QLabel("System Logs")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 5px; color: #333;")  # Adjust the color as needed

        # Create a QListWidget for notifications
        self.notification_list = QListWidget()
        self.notification_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
            }
            QListWidget::item {
                border-bottom: 1px solid #ddd;
            }
        """)

        # Add the title label and notification list to the wrapper frame
        notification_layout = QVBoxLayout(notification_frame)
        notification_layout.addWidget(title_label)
        notification_layout.addWidget(self.notification_list)
        # Add the graph (line chart) to the graph and logs layout
        line_chart_view = self.create_order_bar_chart_per_day_current_month()
        graph_and_logs_layout.addWidget(line_chart_view)
        
        # Add the wrapped notification panel to the graph and logs layout
        graph_and_logs_layout.addWidget(notification_frame, alignment=Qt.AlignRight)


        
        # Create a QLabel to display date and time
        self.date_time_label = QLabel()
        self.date_time_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        date_time_layout = QVBoxLayout()
        date_time_layout.addWidget(self.date_time_label)
        main_layout.addLayout(graph_and_logs_layout)
        main_layout.addLayout(date_time_layout)

        # Update date and time every second

        chart = self.create_order_bar_chart_per_day_current_month()
        self.chart_view = QChartView(chart)
        self.chart = chart  # Store a reference to the chart

        timer = QTimer(self)
        timer.timeout.connect(self.update_date_time)
        timer.start()
        # Create a QTimer for auto-refresh
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update_labels)
        self.refresh_timer.start(5000)  # Set the refresh interval in milliseconds (e.g., 5000 ms = 5 seconds)
        self.update_signal.connect(self.update_notification_list)
        # Initialize labels
        self.update_data()
        self.update_date_time()
        
    def add_notification(self, icon_name, title, timestamp):
        # Create a custom widget for the notification item
        notification_widget = QWidget()
        notification_layout = QVBoxLayout(notification_widget)

        # Timestamp
        timestamp_label = QLabel(timestamp)
        timestamp_label.setAlignment(Qt.AlignRight)

        title_label = QLabel(title)

        # Additional elements in the notification
        icon_label = QLabel()


        notification_layout.addWidget(timestamp_label)
        notification_layout.addWidget(title_label)
        notification_layout.addWidget(icon_label)
        item = QListWidgetItem(self.notification_list)
        item.setSizeHint(notification_widget.sizeHint())
        self.notification_list.setItemWidget(item, notification_widget)
        interaction_type = self.detect_interaction_type(title)
        interaction_log = {"timestamp": timestamp, "title": title, "type": interaction_type}
        self.notification_logs.insert(0, interaction_log.json)
        self.write_logs_to_json()
        logging.info(f"Interaction: {title} at {timestamp}. Type: {interaction_type}")
        self.notification_list.scrollToTop()
        self.notification_list.sortItems(Qt.DescendingOrder)


    def detect_interaction_type(self, title):
        # Customize this method based on your specific interaction types
        if "Delete Order" in title:
            return "Delete Order"
        elif "New Order" in title:
            return "New Order"
        elif "Preview Order" in title:
            return "Preview Order"
        else:
            return "Other"

    def write_logs_to_json(self):
        try:
            with open("interaction_logs.json", "a") as file:
                # Append the new logs to the existing file
                for log in self.notification_logs:
                    json.dump(log, file)
                    file.write("\n")
        except Exception as e:
            print(f"Error writing logs to JSON file: {e}")

    def load_logs_from_json(self):
        # Load existing interaction logs from the JSON file
        try:
            with open("interaction_logs.json", "r") as json_file:
                # Load the JSON file only if it's not empty
                if os.stat("interaction_logs.json").st_size > 0:
                    loaded_logs = json.load(json_file)

                    # Filter logs that are older than 7 days
                    cutoff_date = datetime.now() - timedelta(days=7)
                    self.notification_logs = [log for log in loaded_logs if self.parse_timestamp(log["timestamp"]) >= cutoff_date]

                    # Reverse the order of logs so that newest logs are first
                    self.notification_logs = self.notification_logs[::-1]
        except FileNotFoundError:
            # Handle the case where the file is not found
            pass
        except json.JSONDecodeError:
            # Handle the case where the file is empty or not a valid JSON
            self.notification_logs = []

    def parse_timestamp(self, timestamp):
        # Parse the timestamp string to a datetime object
        return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    
    def update_data(self):
        # Update any data or information that needs to be refreshed
        self.total_pending_orders = self.fetch_total_orders("Pending")
        self.total_finished_orders = self.fetch_total_orders("Finished")
        # Add any other data updates here

        # Update the labels
        self.update_labels()

        # Emit the signal to notify the UI to update
        self.update_signal.emit()

        # Update the notification list separately
        self.update_notification_list()


                
    def update_labels(self):
        # Update the labels with the latest values
        self.pending_orders_label.setText(f"Today's Pending Orders: {self.total_pending_orders}")
        self.finished_orders_label.setText(f"Today's Total Finished Orders: {self.total_finished_orders}")

        # Emit the signal to notify the UI to update
        self.update_signal.emit()
        
    def update_notification_list(self):
        self.notification_list.clear()

        for log in self.notification_logs:
            timestamp_label = QLabel(log["timestamp"])
            title_label = QLabel(log["title"])

            notification_widget = QWidget()
            notification_layout = QVBoxLayout(notification_widget)
            notification_layout.addWidget(timestamp_label)
            notification_layout.addWidget(title_label)
            item = QListWidgetItem(self.notification_list)
            item.setSizeHint(notification_widget.sizeHint())
            self.notification_list.setItemWidget(item, notification_widget)

        self.notification_list.scrollToTop()
        
    def create_order_bar_chart_per_day_current_month(self):
        order_data = self.get_order_data_current_month()
        series = QBarSeries()
        bar_set = QBarSet('Orders')
        
        for date, order_count in order_data.items():
            bar_set.append(order_count)
            bar_set.setLabel(str(order_count))

        series.append(bar_set)
        chart = QChart()
        chart.addSeries(series)

        current_month = QDate.currentDate().toString("MMMM yyyy")
        chart.setTitle(f"Order Counts per Day in {current_month}")
        categories = [str(date.day()) for date in order_data.keys()]
        axis = QBarCategoryAxis()
        axis.append(categories)

        axis.setTitleText("Days of the Month")
        chart.setAxisX(axis, series)
        value_axis = QValueAxis()
        value_axis.setLabelFormat("%d")  # Display integer values
        value_axis.setTickCount(max(order_data.values()) + 1)  # Set the tick count explicitly
        chart.setAxisY(value_axis, series)


        brush = QBrush(QColor("#3498db"))  
        bar_set.setBrush(brush)

        # Adjust bar width
        series.setBarWidth(0.8)

        # Create a chart view and set the chart
        chart_view = QChartView(chart)
        # Disable interaction (make the chart not clickable)
        chart_view.setRenderHint(QPainter.Antialiasing, False)
        chart_view.setInteractive(False)  # This line disables interaction with the chart

        chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Set the space between bars

        # Add legend
        chart.legend().setVisible(False)
        chart.legend().setAlignment(Qt.AlignBottom)

        # Enable animations
        chart.setAnimationOptions(QChart.SeriesAnimations)

        # Enable tooltips for the series
        series.setLabelsVisible(True)
        series.setLabelsPosition(QAbstractBarSeries.LabelsOutsideEnd)

        return chart_view

    def get_order_data_current_month(self):
        try:
            conn = sqlite3.connect('orders.db')
            cursor = conn.cursor()

            current_date = QDate.currentDate()
            sample_data = {}

            for day in range(1, current_date.daysInMonth() + 1):
                date = QDate(current_date.year(), current_date.month(), day)

                # Retrieve order count for each day from the database
                query = f"SELECT COUNT(*) FROM orders WHERE DATE(date) = ?"
                cursor.execute(query, (date.toString('yyyy-MM-dd'),))
                result = cursor.fetchone()

                if result is not None:
                    order_count = result[0]
                    sample_data[date] = order_count
                else:
                    # If there are no orders on that day, set the count to 0
                    sample_data[date] = 0

            conn.close()

            return sample_data

        except sqlite3.Error as e:
            print(f"Error fetching order data from the database: {e}")
            raise

    def fetch_total_orders(self, order_status):
        try:
            conn = sqlite3.connect('orders.db')
            cursor = conn.cursor()
            # Convert order_status to title case
            order_status = order_status.title()
            # Get the current date
            current_date = QDate.currentDate().toString('yyyy-MM-dd')
            query = f"SELECT COUNT(*) FROM orders WHERE order_status=? AND DATE(date) = ?"
            cursor.execute(query, (order_status, current_date))
            result = cursor.fetchone()
            total_orders = result[0] if result else 0
            conn.commit()
            return total_orders

        except sqlite3.Error as e:
            logging.error(f"Error fetching total {order_status} orders: {e}")
            raise

    def update_date_time(self):
        # Update the date and time label
        current_date_time = QDateTime.currentDateTime()
        formatted_date_time = current_date_time.toString("yyyy-MM-dd hh:mm:ss")
        self.date_time_label.setText(formatted_date_time)        