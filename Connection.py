import random
import string
import datetime
from threading import Timer
import os
import threading
import time
from flask import Flask, request
from flask import jsonify
import logging
import json
from PyQt5.QtCore import QThread
import sqlite3
from Config import GRAPH_API_VERSION, PAGE_ACCESS_TOKEN
import requests
from Verification import verify

DATABASE_NAME = 'orders.db'
SERVICES_MESSAGE = "Default services message. Please update through the application settings."
TIMEOUT = 30
message_queue = []
upload_timers = {}
users_order_data = {
 
    'order_confirmed': False
}
app = Flask(__name__)
class FlaskThread(QThread):
    def run(self):
        if not os.path.exists("downloaded_files"):
            os.makedirs("downloaded_files")
        app.run(debug=False, use_reloader=False, port=5000)

    def shutdown(self):
        try:
            requests.get('http://127.0.0.1:5000/shutdown')
        except:
            pass  

@app.route('/initialize', methods=['POST'])
def initialize():
    # All your other initializations go here, like connecting to the Graph API.
    set_get_started_button()
    set_persistent_menu()
    return jsonify(status='initialized')

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server = request.environ.get('werkzeug.server.shutdown')
    if shutdown_server is None:
        raise RuntimeError('Not running the Werkzeug Server')
    shutdown_server()
    return 'Server shutting down...'
        
logging.basicConfig(level=logging.DEBUG)


# ------------------ Routes ------------------

def get_message(message_id):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{message_id}?access_token={PAGE_ACCESS_TOKEN}"
    response = requests.get(url)
    message = json.loads(response.text)
    return message

def get_file_url(message):
    attachments = message.get("attachments", {}).get("data", [])
    for attachment in attachments:
        if "file_url" in attachment:
            return attachment["file_url"]
    return None


@app.route('/fetch-file', methods=['GET'])
def fetch_file():
    message_id = request.args.get('message_id')
    if not message_id:
        return "No message_id provided", 400

    message = get_message(message_id)
    file_url = get_file_url(message)
    if file_url:
        if not os.path.exists("downloaded_files"):
            os.makedirs("downloaded_files")

        if not users_order_data.get('order_confirmed', False):
            # Only store the file URL if the order is not confirmed yet
            uploaded_files = users_order_data.get('files', [])
            uploaded_files.append({"url": file_url})
            users_order_data['files'] = uploaded_files

        return "File URL stored successfully", 200
    else:
        return "No file found in message", 404


def process_file_on_confirmation(sender_id):
    # Process files when the order is confirmed
    uploaded_files = users_order_data.get('files', [])

    for file_info in uploaded_files:
        file_url = file_info.get('url')
        if file_url:
            original_file_name = file_url.split('/')[-1].split('?')[0]
            # Generate a unique filename with a random 4-digit number appended at the end
            random_number = generate_unique_identifier()
            unique_filename = f"{original_file_name.split('.')[0]}_Order_{random_number}.{original_file_name.split('.')[-1]}"
            destination_path = os.path.join("downloaded_files", unique_filename)

            try:
                download_file(file_url, destination_path)
                send_message(sender_id, f"Received and saved your file as: {unique_filename}")
            except Exception as e:
                logging.error(f"Error processing file from URL {file_url}: {e}", exc_info=True)
                send_message(sender_id, "There was an error processing your file. Please try again.")
                
    # Reset the order_confirmed flag
    users_order_data['order_confirmed'] = False
    # Clear the stored files
    users_order_data['files'] = []
    
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return verify()

    elif request.method == 'POST':
        data = request.get_json()
        if data.get('object') == 'page':
            sender_id = data['entry'][0]['messaging'][0]['sender']['id']
            messaging_event = data['entry'][0]['messaging'][0]

            current_stage = users_order_data.get(sender_id, {}).get('stage')

            if 'postback' in messaging_event:
                handle_postback(messaging_event)
                return 'Okay', 200 

            if 'message' in messaging_event:
                user_message = messaging_event['message'].get('text', '').lower()
                payload = messaging_event['message'].get('quick_reply', {}).get('payload', '')

                # Check for cancel or new order commands
                if user_message.lower() in ["cancel", "stop", "abort"]:
                    if sender_id in users_order_data:
                        del users_order_data[sender_id]
                        send_message(sender_id, "Your order has been cancelled.")
                        send_message(sender_id, "Try to upload file again.")
                    else:
                        send_message(sender_id, "No active order to cancel.")
                        send_message(sender_id, "Please click 'Upload Your Order Queries' if you want to start the upload process.")
                    return '', 200



                elif user_message in ["start", "restart", "new order"]:
                    if sender_id in users_order_data:
                        del users_order_data[sender_id]
                    send_message(sender_id, "Let's start a new order! Please upload the file you wish to print.")
                    return 'Okay', 200


                elif 'attachments' in messaging_event.get('message', {}):
                    uploaded_files = users_order_data.get(sender_id, {}).get('files', [])
                    upload_successful = True  # Assume success at first

                    # Process only the first attachment
                    attachment = messaging_event['message']['attachments'][0]

                    if attachment['type'] == 'file':
                        file_url = attachment['payload'].get('url')
                        if not file_url or not file_url.startswith('http'):
                            upload_successful = False

                        file_name = file_url.split('/')[-1].split('?')[0]
                        # Store file information without downloading immediatelys
                        uploaded_files.append({"name": file_name, "url": file_url})

                    elif attachment['type'] == 'image':  # Handle image attachments
                        # For image attachments, the URL can be obtained directly
                        file_url = attachment['payload'].get('url')
                        if not file_url or not file_url.startswith('http'):
                            upload_successful = False

                        file_name = file_url.split('/')[-1].split('?')[0]
                        # Store file information without downloading immediately
                        uploaded_files.append({"name": file_name, "url": file_url})

                    users_order_data.setdefault(sender_id, {})['files'] = uploaded_files

                    if not upload_successful:
                        send_message(sender_id, "Your file upload failed. Please try again!")
                        reset_order(sender_id)
                        return '', 200

                    timer = threading.Timer(30, file_upload_timer_expired, args=[sender_id])
                    timer.start()
                    upload_timers[sender_id] = timer
                    return '', 200

                elif current_stage == 'ask_copies':
                    # Check if the user message is a valid integer
                    if user_message.isdigit():
                        copies = int(user_message)
                        if 1 <= copies <= 100:
                            # Ensure that users_order_data[sender_id] exists
                            if sender_id in users_order_data:
                                users_order_data[sender_id]['copies'] = copies
                                # Move to the next stage (e.g., asking for color)
                                users_order_data[sender_id]['stage'] = 'ask_color'
                                ask_for_color(sender_id)
                                return '', 200  # Add this line to exit the function after a valid input

                    send_message(sender_id, "Invalid input. Please enter a valid number of the copies.")
                    ask_for_copies(sender_id)

                elif current_stage == 'ask_color':
                    # Check the payload to determine the color preference
                    if payload in ['COLOR_YES', 'COLOR_NO']:
                        users_order_data[sender_id]['color'] = 'Colored' if payload == 'COLOR_YES' else 'Black & White'
                        users_order_data[sender_id]['stage'] = 'ask_instructions'  # Transition to the 'ask_instructions' stage
                        ask_for_instructions(sender_id)  # Prompt the user for any additional instructions
                    else:
                        send_message(sender_id, "I couldn't understand your color preference. Please choose either 'Colored' or 'Black & White'.")
                        ask_for_color(sender_id)

                elif current_stage == 'ask_instructions':
                    if user_message and user_message.lower() != 'none':  # Capture any given instruction
                        users_order_data[sender_id]['instructions'] = user_message
                    else:
                        users_order_data[sender_id]['instructions'] = None  # No instructions provided
                        
                    users_order_data[sender_id]['stage'] = 'confirm_order'
                    confirm_order(sender_id)  # Display the order details including instructions, if any

                elif current_stage == 'confirm_order':
                    if payload == 'CANCEL_ORDER':
                        if sender_id in users_order_data:
                            if 'CONFIRM_ORDER' in users_order_data[sender_id].get('actions', []):
                                send_message(sender_id, "Your order has already been confirmed and cannot be cancelled.")
                            else:
                                del users_order_data[sender_id]
                                send_message(sender_id, "Your order has been cancelled.")
                        else:
                            send_message(sender_id, "No active order to cancel.")
                                                    
                    elif payload == 'CONFIRM_ORDER':
                        # Check if there are files to process
                        if users_order_data[sender_id]['files_to_process']:
                            # Download the file only when the order is confirmed
                            downloaded_file_name = download_file_on_confirmation(users_order_data[sender_id]['files_to_process'][0], sender_id)

                            if downloaded_file_name:
                                # Save the order details to the database
                                copies = users_order_data[sender_id]['copies']
                                color = users_order_data[sender_id]['color']
                                instructions = users_order_data[sender_id].get('instructions', '')  # Retrieve instructions, defaulting to empty if not provided

                                # Call the function to save to the database
                                save_order(sender_id, downloaded_file_name, copies, color, instructions)

                                # Clear the current file from files_to_process
                                file_processed = users_order_data[sender_id]['files_to_process'].pop(0)
                                if file_processed in users_order_data[sender_id]['files']:
                                    users_order_data[sender_id]['files'].remove(file_processed)

                                # Check if there are more files to process
                                if users_order_data[sender_id]['files']:
                                    # Set the next file to process and inform the user
                                    next_file = users_order_data[sender_id]['files'].pop(0)
                                    users_order_data[sender_id]['files_to_process'].append(next_file)
                                    send_message(sender_id, f"Next file: {next_file['name']}.")

                                    # Restart the order process for the next file
                                    users_order_data[sender_id]['stage'] = 'ask_copies'
                                    ask_for_copies(sender_id)
                                else:
                                    # If no more files, then confirm the complete order
                                    message = "Your order has been confirmed and is now being processed!\n\n" \
                                            "You will receive a notification when your paper is ready for pickup.\n\n" \
                                            "Feel free to upload another file if you want to place another order."
                                    send_message(sender_id, message)
                            else:
                                # Handle the case where file download failed
                                send_message(sender_id, "File download failed. Please try again.")
                                reset_order(sender_id)
                        else:
                            # Handle the case where there are no files to process
                            send_message(sender_id, "No files to process. Please upload a file to proceed.")
                    else:
                        send_message(sender_id, "Invalid choice. Please confirm or cancel the order using the provided options.")
                        
                else:
                    # This block catches messages that don't match the expected sequence
                    if current_stage:
                        send_message(sender_id, f"You are currently at the '{current_stage}' stage. Please follow the process or send 'cancel' to start over.")
                    else:
                        send_message(sender_id, "Please click 'Upload Your Order Queries' to start the upload process.")
                    return '', 200

    return '', 200

def generate_unique_identifier():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def download_file_on_confirmation(file_info, sender_id):
    try:
        file_url = file_info['url']
        file_name = file_info['name']
        unique_identifier = generate_unique_identifier()

        # Determine the file extension
        file_extension = file_name.split('.')[-1].lower()
        allowed_file_types = ['pdf', 'docx', 'xlsx', 'png', 'jpg']

        if file_extension not in allowed_file_types:
            raise ValueError(f"Invalid file extension: {file_extension}")

        # Adjust the file name to match the expected format
        downloaded_file_name = f"{file_name}_order_{unique_identifier}.{file_extension}"
        downloaded_file_path = os.path.join("downloaded_files", downloaded_file_name)
        download_file(file_url, downloaded_file_path)
        send_message(sender_id, f"Received and saved your file")

        return downloaded_file_name

    except ValueError as e:
        # Inform the user about the invalid file extension
        send_message(sender_id, f"Invalid file: {e}. Please upload a valid PDF, DOCX, XLSX, PNG, or JPG file.")
        reset_order(sender_id)
        return None

    except RuntimeError as e:
        # Log the error
        logging.error(f"Error downloading file from URL {file_url}: {e}", exc_info=True)

        # Inform the user about the download failure
        send_message(sender_id, f"File download failed: {e}. Please try again.")
        reset_order(sender_id)
        return None

# ------------------ Facebook Setup Functions ------------------
def set_get_started_button():
    headers = {'Content-Type': 'application/json'}  
    data = {"get_started": {"payload": "GET_STARTED_PAYLOAD"}}
    url = f"https://graph.facebook.com/v17.0/me/messenger_profile?access_token={PAGE_ACCESS_TOKEN}"
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(response.content)

def set_persistent_menu():
    headers = {'Content-Type': 'application/json'}
    data = {
        "persistent_menu": [
            {
                "locale": "default",
                "composer_input_disabled": False,
                "call_to_actions": [
                    {"type": "postback", "title": "Upload Your Order Queries ", "payload": "UPLOAD_FILE"},
                    {"type": "postback", "title": "Services & Prices", "payload": "SERVICES_PRICES"},
                    {"type": "postback", "title": "Shop Location", "payload": "BUSINESS_LOCATION"},
                    {"type": "postback", "title": "How To Order", "payload": "GET_INSTRUCTION"},
                    {"type": "postback", "title": "Rules of uploading files", "payload": "GET_RULES"}
                ]
            }
        ]
    }
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messenger_profile?access_token={PAGE_ACCESS_TOKEN}"
    for i in range(3):  # try 3 times
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
            response.raise_for_status()
            break
        except (requests.exceptions.RequestException, requests.exceptions.ReadTimeout) as e:
            if i == 2:
                logging.error(f"Error setting persistent menu: {e}")
                raise
            time.sleep(5)




# ------------------ Utility Functions ------------------
def download_file(url, destination_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(destination_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    except requests.RequestException as e:
        logging.error(f"Failed to fetch the file from URL {url}. Error: {e}")
        # Handle the error or raise it again based on your application's requirements
        raise

def process_downloaded_file(file_url, destination_path, sender_id):
    try:
        download_file(file_url, destination_path)
        logging.debug(f"File downloaded to {destination_path}")

        # Check if the file was downloaded
        if os.path.exists(destination_path):
            logging.debug(f"File successfully downloaded at {destination_path}")
        else:
            logging.error(f"File not found at {destination_path}")
            return  # Return early, as subsequent code relies on file being present

        # Notify the user about the downloaded file
        send_message(sender_id, f"Received and saved your file at: {destination_path}")

    except Exception as e:
        logging.error(f"Error processing file: {e}")
        send_message(sender_id, "There was an error processing your file. Please try again.")

def send_message(sender_id, text):
    # Check if the message is already in the queue for the sender ID and timestamp
    if not any(msg['sender_id'] == sender_id and msg['timestamp'] == int(time.time()) for msg in message_queue):
        # If not, add the message to the queue
        message_queue.append({'sender_id': sender_id, 'text': text, 'timestamp': int(time.time())})
        # Your existing code to send the message
        message_data = {'recipient': {'id': sender_id}, 'message': {'text': text}}
        url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        try:
            response = requests.post(url, json=message_data)
            response.raise_for_status()
            logging.debug(f"Sent message and received response: {response.text}")
        except requests.RequestException as e:
            logging.error(f"Error sending message: {e}")
            if 'response' in locals() or 'response' in globals():
                logging.error(f"Response: {response.text}")
            else:
                logging.error("No response object available.")

def handle_postback(messaging):
    sender_id = messaging['sender']['id']
    payload = messaging['postback']['payload']

    if payload == 'GET_STARTED_PAYLOAD':
        welcome_message = (
            "Welcome to our printing service! How can we assist you today?\n"
            "You can check the menu on the right side for available options.\n\n"
        )
        send_message(sender_id, welcome_message)

        
    elif payload == 'GET_INSTRUCTION':
        instruction_message = (
            "Here's how you process your order:\n"
            "1. Click on 'Upload Your Order Queries' to begin the upload process.\n"
            "2. Select the file(s) you want to print from your device.\n"
            "3. Specify the number of copies and choose color preferences (if applicable).\n"
            "4. Add any special instructions or preferences for your order.\n"
            "5. Review the order details and confirm when prompted.\n"
            "6. You'll receive updates on your order status and any further instructions.\n\n"
            "**Note:** Once you confirm your order, it cannot be cancelled. Please review your order details carefully before confirming.\n\n"
            "**Important:** We provide printing services for finished files. Content creation or writing services are not offered."
        )
        send_message(sender_id, instruction_message)

        
    elif payload == 'GET_RULES':     
        rules_message = (
            "Rules for File Upload:\n"
            "1. We only accept PDF and DOCX file formats for printing.\n"
            "2. Make sure your files are correctly formatted to avoid printing errors.\n"
            "3. If you have specific requirements, let us know in the additional instructions.\n"
            "4. Ensure your files are clear and readable for optimal printing results.\n\n"
            "**Note:** Once you confirm your order, it cannot be cancelled. Please review your order details carefully before confirming.\n\n"
            "**Important:** We provide printing services for finished files. Content creation or writing services are not offered."
        )
        send_message(sender_id, rules_message)

        
    elif payload == 'SERVICES_PRICES':
        try:
            with open('paper_types.txt', 'r') as f:
                services_message = f.read()

            if services_message:
                send_message(sender_id, services_message)
            else:
                send_message(sender_id, "Sorry, the services information is currently unavailable.")
        except FileNotFoundError:
            send_message(sender_id, "Sorry, the services information file is missing.")
        except Exception as e:
            send_message(sender_id, f"An error occurred while fetching services information: {str(e)}")

    elif payload == 'UPLOAD_FILE':
        if sender_id in users_order_data:
            send_message(sender_id, "You've already initiated an upload. Please upload one file at a time or cancel the process if you wish to start over.")
            return
        
        users_order_data[sender_id] = {'upload_started': True, 'files': []}
        send_message(sender_id, "You can upload the file now.")
        threading.Timer(TIMEOUT, handle_upload_timeout, args=(sender_id,)).start()

    elif payload == 'BUSINESS_LOCATION':
        # Load the Google Maps link from the file
        with open('google_maps_link.txt', 'r') as f:
            link = f.read().strip()
            
        business_info_message = (
            "**Our business is located at the following address:**\n"
            "Sampaguita St, Santa Cruz, Laguna\n\n"
            "**You can find us on Google Maps:** " + link
        )
        send_message(sender_id, business_info_message)
  
    else:
        logging.warning(f"Unhandled postback payload: {payload}")

def handle_upload_timeout(sender_id):
    user_data = users_order_data.get(sender_id, {})
    if user_data.get('upload_started', False):
        # Additional context or information about the file check
        file_check_message = "Checking..."

        # You can customize the message based on the specific use case
        send_message(sender_id, file_check_message) 
     
def ask_for_copies(sender_id):
    message_text = "How many copies would you like?"
    quick_replies = [
        {'content_type': 'text', 'title': '1', 'payload': 'COPIES_1'},
        {'content_type': 'text', 'title': '2', 'payload': 'COPIES_2'},
        {'content_type': 'text', 'title': '3', 'payload': 'COPIES_3'},
        {'content_type': 'text', 'title': '4', 'payload': 'COPIES_4'},
        {'content_type': 'text', 'title': '6', 'payload': 'COPIES_5'},
        {'content_type': 'text', 'title': '8', 'payload': 'COPIES_5'},
        {'content_type': 'text', 'title': '10', 'payload': 'COPIES_10'},

    ]
    send_quick_reply(sender_id, message_text, quick_replies)

def ask_for_color(sender_id):
    message_text = "What is Your Color Preferences ?"
    quick_replies = [
        {'content_type': 'text', 'title': 'Colored', 'payload': 'COLOR_YES'},
        {'content_type': 'text', 'title': 'Black & White', 'payload': 'COLOR_NO'}
    ]
    send_quick_reply(sender_id, message_text, quick_replies)

def ask_for_instructions(sender_id):
    instruction_prompt = "Do you have any specific instructions for your order? " \
                        "If there are no instructions, simply type 'none'."

    send_message(sender_id, instruction_prompt)

def confirm_order(sender_id):
    files_to_process = users_order_data[sender_id].get('files_to_process', [])
    copies = users_order_data[sender_id].get('copies', 0)
    color = users_order_data[sender_id].get('color', 'Not specified')
    instructions = users_order_data[sender_id].get('instructions', 'None')

    file_names = ', '.join([file['name'] for file in files_to_process])

    confirmation_msg = (
        "Order Details:\n"
        f"Files: {file_names}\n"
        f"Copies: {copies}\n"
        f"Color: {color}\n"
        f"Instructions: {instructions}\n"
        "Please confirm the above details.\n\n"
        "**Note:** Once confirmed, your order cannot be canceled. Please review the details carefully."
    )
    ask_for_order_confirmation(sender_id, confirmation_msg)

def send_quick_reply(sender_id, message_text, quick_replies):
    message_data = {
        'recipient': {'id': sender_id},
        'message': {
            'text': message_text,
            'quick_replies': quick_replies
        }
    }
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    try:
        response = requests.post(url, json=message_data)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error sending quick reply: {e}")

def process_message(messaging):
    if 'quick_reply' in messaging.get('message', {}):
        handle_quick_reply(messaging)

def handle_quick_reply(messaging):
    sender_id = messaging['sender']['id']
    payload = messaging['message']['quick_reply']['payload']

    if payload.startswith('COPIES_'):
        num_copies = payload.split('_')[1]
        ask_for_color(sender_id)
    elif payload in ['COLOR_YES', 'COLOR_NO']:
        is_color = payload == 'COLOR_YES'
        send_message(sender_id, f"The file will be printed in {'color' if is_color else 'black & white'}.")
        ask_for_instructions(sender_id)  # Ask for instructions after color choice
    elif payload == 'CONFIRM_ORDER':
        check_file_types(sender_id)
    else:
        send_message(sender_id, "Sorry, I didn't understand that. Please try again.")

  
def is_valid_response(response, valid_options):
    return response.lower() in [option.lower() for option in valid_options]

def list_files_for_selection(sender_id):
    file_list_text = "You've uploaded the following Document :\n"
    for idx, file_info in enumerate(users_order_data[sender_id]['files'], 1):
        file_list_text += f"{idx}. {file_info['name']}\n"
    file_list_text += "Please select a file number to process, or type 'All' to batch process."
    send_message(sender_id, file_list_text)
    
def ask_for_order_confirmation(sender_id, message_text):
    quick_replies = [
        {'content_type': 'text', 'title': 'Confirm', 'payload': 'CONFIRM_ORDER'},
        {'content_type': 'text', 'title': 'Cancel', 'payload': 'CANCEL_ORDER'}
    ]
    send_quick_reply(sender_id, message_text, quick_replies)

def check_upload_status(sender_id):
    if users_order_data.get(sender_id, {}).get('upload_started', False) and not users_order_data.get(sender_id, {}).get('files', []):
        del users_order_data[sender_id]['upload_started']  # remove the upload_started marker
        send_message(sender_id, "You didn't upload a file. Please start the process again if you wish to upload.")

def send_quick_reply_with_options(sender_id, message_text, options):
    """Send a message with quick reply options."""
    quick_replies = [{'content_type': 'text', 'title': title, 'payload': payload} for title, payload in options]
    send_quick_reply(sender_id, message_text, quick_replies)

def check_file_types(sender_id):
    files_to_process = users_order_data[sender_id]['files_to_process']
    allowed_file_types = ['.pdf', '.docx', '.xlsx', '.png', '.jpg']

    for file in files_to_process:
        file_name = file['name']
        file_extension = os.path.splitext(file_name)[1].lower()  # Convert to lowercase

        print(f"File Name: {file_name}, File Extension: {file_extension}")

        if file_extension not in allowed_file_types:
            send_message(sender_id, f"Sorry, we only accept PDF, DOCX, XLSX, PNG, and JPG file formats for printing. Please upload a valid file.")
            reset_order(sender_id)
            return
    confirm_order(sender_id)


    
def reset_order(sender_id):
    if sender_id in users_order_data:
        del users_order_data[sender_id]
    send_message(sender_id, "Your order process has been reset. Please start a new order.")

def create_connection():
    try:
        return sqlite3.connect(DATABASE_NAME)
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")

        raise

def create_orders_table():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            sender_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            copies INTEGER NOT NULL,
            color TEXT NOT NULL,
            instructions TEXT,
            order_status TEXT DEFAULT 'Pending',
            archived TEXT DEFAULT 'No',
            date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating orders table: {e}")
    finally:
        cursor.close()
        conn.close()

def save_order(sender_id, file_name, copies, color, instructions):
    try:
        # Fetch user profile information from the Facebook Graph API
        user_profile = get_user_profile(sender_id)
        user_name = user_profile.get('first_name', 'Unknown') + ' ' + user_profile.get('last_name', 'Unknown')  # Combine first and last name

        conn = create_connection()
        cursor = conn.cursor()
        current_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute(
            "INSERT INTO orders (sender_id, user_name, file_name, copies, color, instructions, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sender_id, user_name, file_name, copies, color, instructions, current_date)
        )

        conn.commit()
    except sqlite3.Error as e:
        print(f"Error saving order to the database: {e}")
    finally:
        cursor.close()
        conn.close()

create_orders_table()

def get_user_profile(sender_id):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{sender_id}?fields=first_name,last_name&access_token={PAGE_ACCESS_TOKEN}"
    response = requests.get(url)
    user_profile = response.json()
    return user_profile

def file_upload_timer_expired(sender_id):
    uploaded_files = users_order_data[sender_id].get('files', [])
    valid_extensions = ['pdf', 'docx', 'xlsx', 'png', 'jpg']
    valid_files = [file for file in uploaded_files if file['name'].lower().endswith(tuple(valid_extensions))]

    if valid_files:
        users_order_data[sender_id]['files_to_process'] = [valid_files[0]]
        users_order_data[sender_id]['stage'] = 'ask_copies'
        ask_for_copies(sender_id)
    else:
        valid_extensions_str = ', '.join(valid_extensions)
        error_message = f"You didn't upload a valid file. Please upload a file with one of the following extensions: {valid_extensions_str}."
        send_message(sender_id, error_message)
        reset_order(sender_id)

def overwrite_existing_file(sender_id):
    current_upload = users_order_data[sender_id]['current_upload']
    existing_files = users_order_data[sender_id].get('files', [])
    for idx, f in enumerate(existing_files):
        if f['name'] == current_upload['name']:
            existing_files[idx] = current_upload
            break
    users_order_data[sender_id]['files'] = existing_files
    del users_order_data[sender_id]['current_upload']
    send_message(sender_id, "File overwritten successfully!")

def keep_both_files(sender_id):
    current_upload = users_order_data[sender_id]['current_upload']
    existing_files = users_order_data[sender_id].get('files', [])
    existing_files.append(current_upload)
    users_order_data[sender_id]['files'] = existing_files
    del users_order_data[sender_id]['current_upload']
    send_message(sender_id, "Both files are kept!")

if __name__ == '__main__':
    if not os.path.exists("downloaded_files"):
        os.makedirs("downloaded_files")
    set_get_started_button()
    set_persistent_menu()
    app.run(debug=False)