MENU_STYLESHEET = """
QMenu {
    background-color: rgba(245, 245, 245, 210);  /* Translucent Light Gray Background */
    border: 1px solid rgba(0, 0, 0, 0.1);  /* Subtle Border */
    margin: 2px;  /* To separate the menu from the main content */
    font-family: 'Concord'; 
    font-size: 14px;
}

QMenu::item {
    padding: 6px 25px 6px 25px;  /* Top, Right, Bottom, Left Padding */
    margin: 1px 0;  /* Spacing between items */
    background-color: rgba(245, 245, 245, 210);  /* Consistent Translucent Background for items */
}

QMenu::item:selected {
    background-color: rgba(60, 60, 60, 210);  /* Translucent Dark Gray when selected */
    color: white;  /* Text color when selected */
}

QMenu::item:disabled {
    color: rgba(0, 0, 0, 0.3);  /* Lighter text for disabled items */
}
"""