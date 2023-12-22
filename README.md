The PrintHub Management System is a Python application designed to simplify and enhance print order management for printing service businesses. This user-friendly system allows for easy navigation, efficient order processing, and overall streamlined administration of print orders. Additionally, it offers flexible configurations for printing services, business location, and more.

## Key Features

- **File Viewer:** Effortlessly browse, search, and manage print orders with an intuitive file viewer.
- **Settings:** Easily configure printing services, business location, and a Google Maps link for enhanced customization.
- **Flask Server Integration:** Seamlessly communicate with a Flask server for dynamic server components.
- **Order Details:** Retrieve and display detailed information about each order from an SQLite database.
- **Graphical User Interface:** Developed with PyQt5, ensuring a smooth and visually appealing user experience.
- **Messenger API Integration:** Enable real-time updates and communication by sending messages to users through the Facebook Messenger API.

## System Components

- **Language:** Python
- **User Interface (UI):** PyQt5
- **Web Framework:** Flask
- **Database:** SQLite
- **Libraries:**
  - **qtawesome:** Enhances the visual appeal of icons in the UI.
  - **requests:** Facilitates seamless communication with external services, specifically the Facebook Messenger API.

## Configuration

Tailor the system to your specific requirements by configuring the following settings:

- **Printing Services:** Adjust configurations such as service types and prices in the `paper_types.txt` file.
- **Business Location:** Set your business location details in the `business_location.txt` file.
- **Google Maps Link:** Add your Google Maps link for easy access to your business location in the `google_maps_link.txt` file.
- **Messenger API:** Integrate with the Facebook Messenger API by adding your Page Access Token in the `config.py` file.

## Messenger API Integration

For effective real-time updates and communication with users, the system integrates seamlessly with the Facebook Messenger API. Here's a brief guide to set it up:

1. **Obtain a Facebook Page Access Token:**
   - Create a Facebook App and associate it with a Page.
   - Generate a Page Access Token and include it in the `config.py` file.

2. **Send Messages:**
   - Utilize the `send_message_to_user` function in `main.py` to send messages and updates to users.

