from flask import  render_template, request, redirect, url_for, flash, jsonify, session
import mysql.connector
from flask_mail import  Message
import smtplib
import random
import bcrypt
import re,time
from mysql.connector import Error
from datetime import datetime
from flask import Flask
from flask_mail import Mail
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration for Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')


mail = Mail(app)


from python_functions.DB.db import *

# Route to serve the popup page
def get_popup_main():
    """Render and return the popup page."""
    return render_template('popup.html')

# Route to handle login (assuming logic will be added here in the future)


# Function to generate a One-Time Password (OTP)
def generate_otp():
    """Generate a 6-digit OTP.

    Returns:
        str: A random 6-digit OTP as a string.
    """
    return str(random.randint(100000, 999999))

# ---------------------------------------------------------
# Forgot Password Functions
# ---------------------------------------------------------

def send_mail(to, subject, body):
    """Send an email using Flask-Mail.

    Args:
        to (str): Recipient's email address.
        subject (str): Subject of the email.
        body (str): Body of the email.

    Returns:
        bool: True if email sent successfully, False otherwise.
    """
    try:
        msg = Message(subject, recipients=[to])
        msg.body = body
        mail.send(msg)
        print("Email sent successfully.")  # Log success
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_otp_via_email(email, otp):
    """Send OTP to a specified email address using SMTP.

    Args:
        email (str): Recipient's email address.
        otp (str): OTP to send in the email.

    Returns:
        bool: True if OTP sent successfully, False otherwise.
    """
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_email = "vardaan.rcms@gmail.com"
        smtp_password = "aynlltagpthlzqgd"  # Use environment variables for security

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            message = f"Subject: Password Reset OTP\n\nYour OTP for password reset is {otp}."
            server.sendmail(smtp_email, email, message)
            print("OTP email sent successfully.")
            return True
    except Exception as e:
        print(f"Failed to send OTP: {e}")
        return False

# Utility function to validate password strength
def is_valid_password(password):
    """Check if the password meets strength criteria.

    Criteria:
    - At least 8 characters
    - Contains uppercase and lowercase letters
    - Contains digits
    - Contains special characters

    Args:
        password (str): Password to validate.

    Returns:
        bool: True if password is strong, False otherwise.
    """
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c in "@$!%*?&" for c in password):
        return False
    return True




# Route to handle the forgot password process
def forgot_password_main():
    """Main function to handle the forgot password workflow.
    
    This function covers three steps:
    1. Request OTP: Sends an OTP to the user's registered email.
    2. Verification: Verifies the OTP entered by the user.
    3. Reset: Resets the password if OTP verification is successful.
    
    Returns:
        Rendered template with status messages for each step in the process.
    """
    conn, cursor = connect_to_database()

    # Retrieve user ID from the form
    user_id = request.form.get('user_id')
    print(f"Received user_id: {user_id}")
    email = ''

    # Retrieve current step and OTP verification status
    step = request.form.get('step', 'request_otp')
    otp_verified = session.get('otp_verified', False)

    if step == 'request_otp':
        print('Request OTP step entered')
        
        # Fetch user's email from the database
        query = "SELECT email_id FROM users WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()

        if not user:
            return render_template('Global/forgot_password.html', alert_type="error", alert_msg="Invalid User ID.", otp_verified=False, otp="")

        email = user['email_id']
        session['user_id'] = user_id
        session['email_id'] = email

        # Generate and store OTP in session
        otp = generate_otp()
        session['otp'] = otp
        session['otp_time'] = time.time()  # Store time for OTP expiration

        # Send OTP via email
        send_otp_via_email(email, otp)
        return render_template('Global/forgot_password.html', alert_type="success", alert_msg="OTP sent.", otp_verified=False, otp="", email=email)

    elif step == 'verification':
        print('OTP Verification step entered')
        
        # OTP verification step
        otp_input = request.form.get('otp')

        # Check if the OTP has expired (valid for 10 minutes)
        if time.time() - session['otp_time'] > 600:
            return render_template('Global/forgot_password.html', alert_type="error", alert_msg="OTP expired. Please request a new OTP.", otp_verified=False, otp="", email=email)

        # Verify OTP
        if otp_input == session.get('otp'):
            session['otp_verified'] = True
            return render_template('Global/forgot_password.html', alert_type="success", alert_msg="OTP verified.", otp_verified=True, otp=otp_input, email=email)
        else:
            return render_template('Global/forgot_password.html', alert_type="error", alert_msg="Invalid OTP.", otp_verified=False, otp=otp_input, email=email)

    elif step == 'reset':
        print('Password Reset step entered')
        
        # Ensure OTP was verified before password reset
        if not otp_verified:
            return render_template('Global/forgot_password.html', alert_type="error", alert_msg="Please verify OTP before resetting password.", otp_verified=False, email=email)

        # Handle password reset
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            return render_template('Global/forgot_password.html', alert_type="error", alert_msg="Passwords do not match.", otp_verified=True, otp=session.get('otp'), email=email)

        if not is_valid_password(new_password):
            return render_template('Global/forgot_password.html', alert_type="error", alert_msg="Password must be 8 characters long, contain uppercase, lowercase, digits, and special characters.", otp_verified=True, otp=session.get('otp'), email=email)

        # Hash the new password and update it in the database
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        user_id = session.get('user_id')

        query = "UPDATE users SET password = %s WHERE user_id = %s"
        cursor.execute(query, (hashed_password, user_id))
        conn.commit()

        # Clear OTP and session data after password reset
        session.pop('otp', None)
        session.pop('otp_time', None)
        session.pop('otp_verified', None)

        return render_template('Global/forgot_password.html', alert_type="success", alert_msg="Password reset successfully!", otp_verified=False, otp="", email=email)

#-----------------------------------------------------------------Country Codes-----------------------------------------------------------------------------
# Fetching country codes from the database
def fetch_country_codes():
    """Retrieve country codes from the database.

    This function fetches country codes for different countries
    from the country_codes table in the database.

    Returns:
        list: List of dictionaries with 'country' and 'country_code' keys.
    """
    conn, cursor = connect_to_database()
    cursor.execute("SELECT country, country_code FROM country_codes")
    country_codes = cursor.fetchall()
    cursor.close()
    conn.close()
    return country_codes
# -------------------------------------------------------------fetching regulation names--------------------------------------------------------
# Fetching regulation names from the database
def fetch_regulation_names():
    """Retrieve regulation names from the regulation_master table.

    This function connects to the database, retrieves all regulation names,
    and returns them as a list of dictionaries.

    Returns:
        list: List of dictionaries with 'regulation_name' as a key.
    """
    conn, cursor = connect_to_database()
    cursor.execute("SELECT regulation_name FROM regulation_master")
    regulation_names = cursor.fetchall()
    cursor.close()
    conn.close()
    return regulation_names


# --------------------------------------------------------------Global Admin---------------------------------------------------------------------------------   
def log_func(date, time, action, remarks):
    """
    Logs user actions (add, delete, modify) in the log_files table.

    Parameters:
    - date: The current date when the action occurred.
    - time: The current time when the action occurred.
    - action: 'ADD', 'DELETE', 'MODIFY' (the type of action performed).
    - remarks: Any remarks about the attempt, e.g., 'User added successfully'.
    """
    # Connect to the database
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        print("Failed to connect to the database for logging.")
        return

    # Create the log entry
    log_entry_query = """
    INSERT INTO log_files (date, time, action, remarks)
    VALUES (%s, %s, %s, %s)
    """
    
    log_entry_data = (date, time, action, remarks)

    # Add the log entry to the database and commit the changes
    try:
        cursor.execute(log_entry_query, log_entry_data)
        conn.commit()  # Commit the transaction
        print(f"Log entry successfully saved for action: {action}")
    except mysql.connector.Error as e:
        conn.rollback()  # Rollback if there's an error
        print(f"Error saving log entry for action: {action}. Error: {e}")
    finally:
        cursor.close()  # Close the cursor
        conn.close()    # Close the connection

# Route for global admin dashboard

def global_admin_dashboard_main():
    
    return render_template('Global/new_dashboard.html')

#---------------------------------------------------------------Add Category--------------------------------------------------------------------------------
from flask import render_template, request, session
from datetime import datetime
import mysql.connector

def add_category_main():
    """Render the add category page with current session entity and user IDs.

    Returns:
        Rendered HTML template for the add category page with entity and user IDs.
    """
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
    return render_template('Global/add_category.html', entity_id=entity_id, user_id=user_id)

def submit_category_main():
    """Handle the submission of a new category to the database.

    This function checks if the category type already exists. If not, it inserts
    the new category, logs the action, and returns a success message. If it exists
    or fails, an error message is displayed.

    Returns:
        Rendered HTML template with success or error messages based on the submission outcome.
    """
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
    error_type, remarks = None, None  # Initialize to ensure defined

    conn, cursor = connect_to_database()
    if conn is None:
        error_type, remarks = get_message_by_code("RCMS_E033")  # Connection error
        return render_template('Global/add_category.html', entity_id=entity_id, user_id=user_id, error_type=error_type, remarks=remarks)

    try:
        category_type = request.form.get('categoryType')
        category_remarks = request.form.get('remarks')

        # Check if the category type already exists in the database
        cursor.execute("SELECT COUNT(*) FROM category WHERE category_type = %s", (category_type,))
        if cursor.fetchone()[0] > 0:
            error_type, remarks = get_message_by_code("RCMS_E030")  # Duplicate category
        else:
            # Insert the new category into the database
            cursor.execute("INSERT INTO category (category_type, remarks) VALUES (%s, %s)", (category_type, category_remarks))
            conn.commit()
            error_type, remarks = get_message_by_code("RCMS_S008")  # Success message

    except mysql.connector.IntegrityError:
        error_type, remarks = get_message_by_code("RCMS_E032")  # Integrity error

    except Exception as e:
        print(f"Failed to submit form data: {e}")
        error_type, remarks = get_message_by_code("RCMS_E033")  # General error

    finally:
        cursor.close()
        conn.close()

    # Log the outcome of the action
    log_func(datetime.now().date(), datetime.now().time(), 'ADD', remarks)
    return render_template('Global/add_category.html', entity_id=entity_id, user_id=user_id, error_type=error_type, remarks=remarks)

#-----------------------------------------------------Delete Category----------------------------------------------------------#
def display_categories_main():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_type,remarks=get_message_by_code("RCMS_E035")
        return remarks

    try:
        # Fetch specific columns, including remarks
        cursor.execute("SELECT category_id, category_type, Remarks FROM category")
        categories = cursor.fetchall()

        # Fetching session data
        entity_id = session.get('entity_id')
        user_id = session.get('user_id')

        return render_template('Global/delete_category.html', categories=categories, entity_id=entity_id, user_id=user_id)
    finally:
        cursor.close()
        conn.close()

from flask import request, session, redirect, url_for, render_template, flash
import mysql.connector

def delete_category_main():
    category_ids = request.form.getlist('category_ids')
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'N/A')

    if not category_ids:
        # No categories selected for deletion
        error_type,remarks=get_message_by_code("RCMS_E036")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_category.html', error_type=error_type,remarks=remarks)

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_type,remarks=get_message_by_code("RCMS_E037")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_category.html', error_type=error_type,remarks=remarks)

    try:
        # Delete selected categories
        format_strings = ','.join(['%s'] * len(category_ids))
        cursor.execute(f"DELETE FROM category WHERE category_id IN ({format_strings})", category_ids)
        conn.commit()

        error_type,remarks=get_message_by_code("RCMS_S009")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_category.html',error_type=error_type,remarks=remarks )
    except mysql.connector.Error as err:
        # Handle database errors
        error_type,remarks=get_message_by_code("RCMS_E038")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_category.html', error_type=error_type,remarks=remarks)
    finally:
        cursor.close()
        conn.close()



#----------------------------------------------------------------Add Entity---------------------------------------------------------------------------------


def add_entity_main():
    country_codes = fetch_country_codes()
 
   
    # Fetch regulation names from the database
    conn, cursor = connect_to_database()
    cursor.execute("SELECT regulation_name FROM regulation_master")
    regulations = [row['regulation_name'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
 
    return render_template('Global/add_entity.html', country_codes=country_codes, regulations=regulations)
 
 
def submit_entity_main():
    conn, cursor = connect_to_database()
    cursor.execute("SELECT regulation_name FROM regulation_master")
    regulations = [row['regulation_name'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    print('entered submit entity')
 
    conn, cursor = connect_to_database()

 
    # Capture form data
    entity_name = request.form.get('entityName')
    location = request.form.get('location')
    state = request.form.get('state')
    country = request.form.get('country')
    pincode = request.form.get('pincode')
 
    contact_name = request.form.get('contactName')
    country_code = request.form.get('country_code')
    contact_phno = request.form.get('contactPhno')
    alternate_contact_name = request.form.get('alternate_contactName')
    alt_country_code = request.form.get('alt_country_code')
    alternate_contact_phno = request.form.get('alternate_contactPhno')
    description = request.form.get('description')
    adminEmail = request.form.get('adminEmail')
    adminPassword = request.form.get('adminPassword')
    selected_regulations = request.form.get('selected_regulations')  # Get the selected regulations
 
    # input(selected_regulations)
    print(f"Entity Name: {entity_name}, Location: {location}, ...")
    # Hash the admin password
    hashed_password = bcrypt.hashpw(adminPassword.encode('utf-8'), bcrypt.gensalt())
 
    # Validate required fields
    if not (adminEmail and adminPassword and entity_name and location and state and country and description and pincode and contact_name  and contact_phno):
       
        print(adminEmail,adminPassword, entity_name , location , state , country , pincode , contact_name , country_code , contact_phno)
        error_type,remarks=get_message_by_code("RCMS_E003")
        log_func(datetime.now().date(), datetime.now().time(), 'ADD', remarks)
        return render_template('Global/add_entity.html', error_type=error_type,remarks=remarks, country_codes=fetch_country_codes())
   
    import re
    print(f"Pincode: {pincode}")  # Debugging print statement
    if not pincode or not re.match(r'^\d{6}$', pincode):
        error_type,remarks=get_message_by_code("RCMS_E004")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/add_entity.html', error_type=error_type,remarks=remarks, country_codes=fetch_country_codes())
 
 
    if not re.match(r'^\d{10}$', contact_phno):  # Validate contact number (10 digits)
        error_type,remarks=get_message_by_code("RCMS_E005")
        log_func(datetime.now().date(), datetime.now().time(), 'ADD', remarks)
        return render_template('Global/add_entity.html', error_type=error_type,remarks=remarks, country_codes=fetch_country_codes())
 
    if alternate_contact_phno and not re.match(r'^\d{10}$', alternate_contact_phno):  # Validate alternate contact number if provided
        error_type,remarks=get_message_by_code("RCMS_E006")
        log_func(datetime.now().date(), datetime.now().time(), 'ADD', remarks)
        return render_template('Global/add_entity.html', error_type=error_type,remarks=remarks, country_codes=fetch_country_codes())
 
    # Updated password validation to include special character requirement
    if len(adminPassword) < 8:
        # or not re.search(r'[A-Za-z]', adminPassword)  # Must contain at least one letter
        # or not re.search(r'[0-9]', adminPassword)     # Must contain at least one digit
        # or not re.search(r'[A-Z]', adminPassword)     # Must contain at least one uppercase letter
        # or not re.search(r'[!@#$%^&*(),.?":{}|<>]', adminPassword)):  # Must contain at least one special character
        error_type,remarks=get_message_by_code("RCMS_E007")
        log_func(datetime.now().date(), datetime.now().time(), 'ADD', remarks)
        return render_template('Global/add_entity.html', error_type=error_type,remarks=remarks, country_codes=fetch_country_codes())
 
 
    # Combine country code and phone numbers
    full_contact_phno = country_code + contact_phno
    print(full_contact_phno)
    full_alternate_contact_phno = alt_country_code + alternate_contact_phno if alternate_contact_phno else None
 
    if conn is not None:
        cursor = conn.cursor()
        try:
            # Check if the factory name already exists
            cursor.execute("SELECT COUNT(*) FROM entity_master WHERE entity_name = %s", (entity_name,))
            count = cursor.fetchone()[0]
 
            if count > 0:
                error_type,remarks=get_message_by_code("RCMS_E008")
                log_func(datetime.now().date(), datetime.now().time(), 'ADD', remarks)
            else:
                # Generate factory_id based on the first 4 letters of the factory name
                prefix = entity_name[:4].upper()
 
                # Check if there are existing factory IDs with the same prefix
                cursor.execute("""
                    SELECT entity_id FROM entity_master WHERE entity_id LIKE %s ORDER BY entity_id DESC LIMIT 1
                """, (prefix + '%',))
                last_id = cursor.fetchone()
 
                if last_id:
                    # Extract the digit part using regex to ensure only the number is captured
                    import re
                    last_num = re.search(r'\d+$', last_id[0])
                    new_num = int(last_num.group()) + 1 if last_num else 1
                else:
                    new_num = 1
 
                factory_id = f"{prefix}{new_num:03}"  # Format the digit part with leading zeros
 
                # Insert the factory data into the database
                cursor.execute("""
                    INSERT INTO entity_master (entity_id, entity_name, location, state,
                               country, pincode, contact_phno, alternate_contact, description, contact_name, alternate_contact_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (factory_id, entity_name, location, state, country, pincode, full_contact_phno, full_alternate_contact_phno, description, contact_name, alternate_contact_name))
               
                conn.commit()
 
                # Send email notification to the user with their credentials and factory_id
                msg = Message(
                    "Welcome to Regulatory Compliance Management System",
                    sender="vardaan.rcms@gmail.com",
                    recipients=[adminEmail]
                )
 
                msg.body = (f"Dear {contact_name},\n\n"
                            f"You have been added to the system with the following credentials:\n\n"
                            f"User ID: {contact_name}\n"
                            f"Password: {adminPassword}\n"
                            f"Factory ID: {factory_id}\n\n"
                            f"Please log in and change your password as soon as possible.\n\n"
                            f"Best regards,\n"
                            f"Your Factory ID: {factory_id}")
                mail.send(msg)
 
                cursor.execute("""
                    INSERT INTO users (user_id, user_name, address, mobile_no, email_id, password, entity_id, role)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (contact_name, contact_name, location, contact_phno, adminEmail, hashed_password, factory_id, 'Admin'))
 
 
 
                # Handle selected regulations
                selected_regulations = request.form.get('selected_regulations')  # Get the selected regulations as a string
                regulation_names = [reg.strip() for reg in selected_regulations.split(',')]  # Split and clean the regulation names
 
 
                for regulation_name in regulation_names:
                    # Get the regulation_id from regulation_master table
                    cursor.execute("SELECT regulation_id FROM regulation_master WHERE regulation_name = %s", (regulation_name,))
                    regulation_id = cursor.fetchone()
 
                    if regulation_id:
                        regulation_id = regulation_id[0]  # Get the regulation_id
 
                        # Get the count of mandatory and optional activities from activity_master table
                        cursor.execute("""
                            SELECT COUNT(*) FROM activity_master WHERE regulation_id = %s AND mandatory_optional = 'M'
                        """, (regulation_id,))
                        mandatory_activities = cursor.fetchone()[0]
 
                        cursor.execute("""
                            SELECT COUNT(*) FROM activity_master WHERE regulation_id = %s AND mandatory_optional = 'O'
                        """, (regulation_id,))
                        optional_activities = cursor.fetchone()[0]
 
                        # Insert into factory_regulation table with factory_id, regulation_id, mandatory_activities, and optional_activities
                        cursor.execute("""
                            INSERT INTO entity_regulation (entity_id, regulation_id, mandatory_activities, optional_activities)
                            VALUES (%s, %s, %s, %s)
                        """, (factory_id, regulation_id, mandatory_activities, optional_activities))
                    else:
                        print(f"Regulation '{regulation_name}' not found in regulation_master.")
 
               
 
                conn.commit()
                error_type,remarks=get_message_by_code("RCMS_S002")
                log_func(datetime.now().date(), datetime.now().time(), 'ADD', remarks)
               
 
 
        except mysql.connector.IntegrityError as e:
            error_type,remarks=get_message_by_code("RCMS_E008")
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', remarks)
            print(remarks)
 
        except Exception as e:
            error_type,remarks=get_message_by_code("RCMS_E009")
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', remarks)
            print(remarks)
        finally:
            cursor.close()
            conn.close()
    else:
        error_type,remarks=get_message_by_code("RCMS_E010")
        log_func(datetime.now().date(), datetime.now().time(), 'ADD', remarks)
 
    return render_template('Global/add_entity.html', error_type=error_type,remarks=remarks, country_codes=fetch_country_codes())
#--------------------------------------------------------Modify Entity----------------------------------------------------------------------------------------
def update_entity_page_main():
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
    # Render the HTML form for updating an entity
    return render_template('Global/update_entity.html',entity_id=entity_id, user_id=user_id)

def get_entities_main():
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        error_type,remarks=get_message_by_code("RCMS_E011")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return jsonify({'error': remarks}), 500
    
    try:
        cursor.execute("SELECT entity_id, entity_name FROM entity_master")
        entities = cursor.fetchall()

        
        return jsonify(entities)
    except Exception as e:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE','Failed to fetch entities')
        return jsonify({'error': 'Failed to fetch entities'}), 500
    finally:
        cursor.close()
        conn.close()

def get_entity_details_main(entity_id):
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        error_type,remarks=get_message_by_code("RCMS_E011")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE',remarks)
        return jsonify({'error': remarks}), 500
    try:
        cursor.execute(""" 
            SELECT entity_id, entity_name, location, contact_phno, alternate_contact, description,
                   country, contact_name, alternate_contact_name, state, pincode 
            FROM entity_master 
            WHERE entity_id = %s 
        """, (entity_id,))
        entity_details = cursor.fetchone()

        

        return jsonify(entity_details)
    except Exception as e:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE',remarks)
        return jsonify({'error': 'Failed to fetch entity details'}), 500
    finally:
        cursor.close()
        conn.close()

def update_entity_main():
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        error_type,remarks=get_message_by_code("RCMS_E011")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_entity.html', error_type=error_type,remarks=remarks)

    # Fetch the form data
    entity_id = request.form.get('entity_id')
    # location = request.form.get('location')
    contact_phno = request.form.get('contact_phno')
    alternate_contact = request.form.get('alternate_contact')
    description = request.form.get('description')
    country = request.form.get('country')
    contact_name = request.form.get('contact_name')
    alternate_contact_name = request.form.get('alternate_contact_name')
    state = request.form.get('state')
    pincode = request.form.get('pincode')

    # Validation checks
    import re
    if not pincode or not re.match(r'^\d{6}$', pincode):
        error_type,remarks=get_message_by_code("RCMS_E012")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_entity.html', error_type=error_type,remarks=remarks)

    if not re.match(r'^\+\d{1,3}\d{10}$', contact_phno):
        error_type,remarks=get_message_by_code("RCMS_E013")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_entity.html', error_type=error_type,remarks=remarks)

    if alternate_contact and not re.match(r'^\+\d{1,3}\d{10}$', alternate_contact):
        error_type,remarks=get_message_by_code("RCMS_E014")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_entity.html', error_type=error_type,remarks=remarks)

    try:
        # Fetch previous entity details (fetch all results to avoid "unread result" issue)
        cursor.execute("SELECT * FROM entity_master WHERE entity_id = %s", (entity_id,))
        cursor.fetchall()  # Ensures any previous query results are fully read

        # Update the entity details in the database
        query = """
            UPDATE entity_master
            SET  contact_phno = %s, alternate_contact = %s, description = %s,
                country = %s, contact_name = %s, alternate_contact_name = %s, state = %s, pincode = %s
            WHERE entity_id = %s
        """
        cursor.execute(query, ( contact_phno, alternate_contact, description, country, contact_name, alternate_contact_name, state, pincode, entity_id))
        conn.commit()

        error_type,remarks=get_message_by_code("RCMS_S003")
        print('changed')
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)

        return render_template('Global/update_entity.html', error_type=error_type,remarks=remarks)
    except mysql.connector.Error as err:
        error_type,remarks=get_message_by_code("RCMS_E015")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_entity.html', error_type=error_type,remarks=remarks)
    finally:
        cursor.close()
        conn.close()


#---------------------------------------------------Delete Entity------------------------------------------------------------------
def delete_entity_page_main():
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
    return render_template('Global/delete_entity.html',entity_id=entity_id, user_id=user_id)

def get_entities_main():
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        error_type,remarks=get_message_by_code("RCMS_E011")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE',remarks)
        return jsonify({'error': remarks}), 500
    
    cursor.execute("SELECT entity_id, entity_name FROM entity_master")
    entities = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(entities)

def get_entity_details_for_delete_main(entity_id):
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        error_type,remarks=get_message_by_code("RCMS_E011")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE',remarks)
        return jsonify({'error': remarks}), 500
    cursor.execute("""
        SELECT entity_id, entity_name, location, contact_phno, alternate_contact, description,
               country, contact_name, alternate_contact_name, state, pincode
        FROM entity_master
        WHERE entity_id = %s
    """, (entity_id,))
    entity_details = cursor.fetchone()
    cursor.close()
    conn.close()

    if not entity_details:
        return jsonify({'error': 'Entity does not exist'}), 404
    return jsonify(entity_details)

from flask import render_template, request
from datetime import datetime

def delete_entity_main():
    entity_id = request.form.get('entity_id')
    
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        error_type,remarks=get_message_by_code("RCMS_E011")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_entity.html', error_type=error_type,remarks=remarks)

    # First, check if the entity exists
    cursor.execute("SELECT * FROM entity_master WHERE entity_id = %s", (entity_id,))
    entity = cursor.fetchone()

    if not entity:
        error_type,remarks=get_message_by_code("RCMS_E016")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_entity.html', error_type=error_type,remarks=remarks)

    # If entity exists, proceed to delete
    try:
        cursor.execute("DELETE FROM entity_master WHERE entity_id = %s", (entity_id,))
        conn.commit()
        error_type,remarks=get_message_by_code("RCMS_S004")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_entity.html', error_type=error_type,remarks=remarks)
    except mysql.connector.Error as err:
        error_type,remarks=get_message_by_code("RCMS_E017")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_entity.html', error_type=error_type,remarks=remarks)
    finally:
        cursor.close()
        conn.close()

#-------------------------------------------------------------Add Regulation-------------------------------------------------------------------------------

def add_regulation_global_main():
    categories = get_categories()  # This should trigger the print statements
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
    return render_template('Global/add_regulation.html', entity_id=entity_id, user_id=user_id,categories=categories)


def submit_regulation_main():
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
    factory_id = session['entity_id']
    regulation_name = request.form['regulationName']
    category_id = request.form['categoryID']
    regulatory_body = request.form['regulatoryBody']
    internal_external = request.form['internalExternal']
    national_international = request.form['nationalInternational']
    mandatory_optional = request.form['mandatoryOptional']
    effective_from = request.form['effectiveFrom']
    obsolete_current = request.form['obsoleteCurrent']

    conn, cursor = connect_to_database()
    
    

    if conn is not None:
        cursor = conn.cursor()
        try:
            # Check if the regulation name already exists
            cursor.execute("SELECT COUNT(*) FROM regulation_master WHERE regulation_name = %s", (regulation_name,))
            exists = cursor.fetchone()[0]

            if exists:
                error_type,remarks=get_message_by_code("RCMS_E018")
                log_func(datetime.now().date(), datetime.now().time(), 'ADD',remarks)
            else:
                # Generate regulation_id based on the first 4 letters of the regulation name
                prefix = regulation_name[:4].upper()

                # Check if there are existing regulation IDs with the same prefix
                cursor.execute(""" 
                    SELECT regulation_id FROM regulation_master WHERE regulation_id LIKE %s ORDER BY regulation_id DESC LIMIT 1
                """, (prefix + '%',))
                last_id = cursor.fetchone()

                if last_id:
                    last_num = re.search(r'\d+$', last_id[0])
                    new_num = int(last_num.group()) + 1 if last_num else 1
                else:
                    new_num = 1

                regulation_id = f"{prefix}{new_num:03}"  # Format the digit part with leading zeros

                # Insert the regulation data into the database
                query = """
                    INSERT INTO regulation_master
                    (regulation_id, regulation_name, category_id, regulatory_body, internal_external,
                    national_international, mandatory_optional, effective_from, obsolete_current)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    regulation_id, regulation_name, category_id, regulatory_body,
                    internal_external, national_international, mandatory_optional,
                    effective_from, obsolete_current
                ))

                conn.commit()
                error_type,remarks=get_message_by_code("RCMS_S005")
                log_func(datetime.now().date(), datetime.now().time(), 'ADD',remarks)
                return render_template('Global/add_regulation.html',entity_id=entity_id, user_id=user_id, error_type=error_type,remarks=remarks)

        except Error as e:
            print(f"Failed to insert regulation: {e}")
            error_type,remarks=get_message_by_code("RCMS_E019")
            log_func(datetime.now().date(), datetime.now().time(), 'ADD',remarks)
        finally:
            cursor.close()
            conn.close()
    else:
        error_type,remarks=get_message_by_code("RCMS_E020")
        log_func(datetime.now().date(), datetime.now().time(), 'ADD',remarks)
    categories = get_categories()
    
    return render_template('Global/add_regulation.html',entity_id=entity_id, user_id=user_id, error_type=error_type,remarks=remarks, categories=categories)

# -----------------------------------------------------------------------------------------------------------------------------------------
def get_categories():

    print("get_categories() function is called", flush=True)
    conn, cursor = connect_to_database()
    categories = []
    if conn is not None:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT category_id, category_type FROM category ORDER BY category_type ASC")
            categories = cursor.fetchall()
            print("Categories fetched and sorted:", categories, flush=True)  # Immediate output
        except Error as e:
            print(f"Failed to query categories: {e}", flush=True)
        finally:
            cursor.close()
            conn.close()
    return categories

#--------------------------------------------------Update regulations------------------------------------------------------------------#
def edit_regulation_page_main():
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_type,remarks=get_message_by_code("RCMS_E021")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE',remarks)
        return render_template('Global/update_regulations.html', error_type=error_type,remarks=remarks)

    try:
        query = """
            SELECT regulation_id, regulation_name
            FROM regulation_master
        """
        cursor.execute(query)
        regulations = cursor.fetchall()
    except mysql.connector.Error as err:
        regulations = []
    finally:
        cursor.close()
        conn.close()

    return render_template('Global/update_regulations.html', 
                           regulations=regulations, 
                           entity_id=entity_id, 
                           user_id=user_id)


def fetch_regulation_main():
    regulation_name = request.form.get('regulation_name')
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_type,remarks=get_message_by_code("RCMS_E021")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE',remarks)
        return render_template('Global/update_regulations.html', error_type=error_type,remarks=remarks)
    try:
        query = """
            SELECT rm.*
            FROM regulation_master rm
            WHERE LOWER(rm.regulation_name) = LOWER(%s)
        """
        cursor.execute(query, (regulation_name,))
        regulation = cursor.fetchone()

        cursor.execute("SELECT regulation_id, regulation_name FROM regulation_master")
        regulations = cursor.fetchall()
    except mysql.connector.Error as err:
        regulation = None
        regulations = []
    finally:
        cursor.close()
        conn.close()

    if not regulation:
        error_type,remarks=get_message_by_code("RCMS_E022")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_regulations.html', 
                               remarks=remarks, 
                               regulations=regulations, 
                               entity_id=entity_id, 
                               user_id=user_id)
    
    return render_template('Global/update_regulations.html', 
                           regulation=regulation, 
                           regulations=regulations, 
                           entity_id=entity_id, 
                           user_id=user_id)


def update_regulation_main():
    regulation_id = request.form.get('regulation_id')
    regulatory_body = request.form.get('regulatory_body')
    internal_external = request.form.get('internal_external')
    national_international = request.form.get('national_international')
    mandatory_optional = request.form.get('mandatory_optional')
    obsolete_current = request.form.get('obsolete_current')[0].upper()

    if not regulation_id:
        error_type,remarks=get_message_by_code("RCMS_E023")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_regulations.html',error_type=error_type,remarks=remarks)

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_type,remarks=get_message_by_code("RCMS_E021")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_regulations.html', error_type=error_type,remarks=remarks)

    try:
        cursor.execute("""
            UPDATE regulation_master
            SET regulatory_body = %s,
                internal_external = %s,
                national_international = %s,
                mandatory_optional = %s,
                obsolete_current = %s
            WHERE regulation_id = %s
        """, (regulatory_body, internal_external, national_international, mandatory_optional, obsolete_current, regulation_id))
        
        conn.commit()
        error_type,remarks=get_message_by_code("RCMS_S006")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_regulations.html', error_type=error_type,remarks=remarks)
    
    except mysql.connector.Error as err:
        error_type,remarks=get_message_by_code("RCMS_E024")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_regulations.html',error_type=error_type,remarks=remarks)
    
    finally:
        cursor.close()
        conn.close()

#---------------------------------------------------------Delete Regulation-------------------------------------------------------------------------
def delete_regulations_page_main():
    # Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
    
    return render_template('Global/delete_regulations.html', entity_id=entity_id, user_id=user_id)

def fetch_categories_main():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_type,remarks=get_message_by_code("RCMS_E021")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE',remarks)
        return jsonify({'error': remarks}), 500
    
    try:
        cursor.execute("SELECT category_id, category_type FROM category")
        categories = cursor.fetchall()
        
        
        return jsonify(categories)
    except Exception as e:
        error_type,remarks=get_message_by_code("RCMS_E025")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE',remarks)
        return jsonify({'error': remarks}), 500
    finally:
        cursor.close()
        conn.close()

def load_regulations_main(category_id):
    # Fetch entity_id from the session
    entity_id = session.get('entity_id')
    
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_type,remarks=get_message_by_code("RCMS_E021")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return jsonify({'error': remarks}), 500

    try:
        # Modify the query to join with entity_regulation and filter by entity_id
        query = """
            SELECT rm.regulation_id, rm.regulation_name, rm.regulatory_body
            FROM regulation_master rm
            WHERE rm.category_id = %s
        """
        cursor.execute(query, (category_id,))
        regulations = cursor.fetchall()
        return jsonify(regulations)
    
    except Exception as e:
        error_type,remarks=get_message_by_code("RCMS_E026")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return jsonify({'error': remarks}), 500
    finally:
        cursor.close()
        conn.close()

def delete_regulations_main():
    regulation_ids = request.form.getlist('regulation_ids')
    if not regulation_ids:
        error_type,remarks=get_message_by_code("RCMS_E027")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_regulations.html', error_type=error_type,remarks=remarks)

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_type,remarks=get_message_by_code("RCMS_E021")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_regulations.html', error_type=error_type,remarks=remarks)

    try:
        # Check if regulations exist and log previous values
        format_strings = ','.join(['%s'] * len(regulation_ids))
        query = f"""
            SELECT regulation_id FROM regulation_master 
            WHERE regulation_id IN ({format_strings})
        """
        cursor.execute(query, regulation_ids)
        existing_regulations = cursor.fetchall()

        if not existing_regulations:
            error_type,remarks=get_message_by_code("RCMS_E028")
            log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
            return render_template('Global/delete_regulations.html', error_type=error_type,remarks=remarks)

        # Attempt to delete regulations
        delete_query = f"""
            DELETE FROM regulation_master 
            WHERE regulation_id IN ({format_strings})
        """
        cursor.execute(delete_query, regulation_ids)
        conn.commit()

        error_type,remarks=get_message_by_code("RCMS_S007")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_regulations.html', error_type=error_type,remarks=remarks)
    except mysql.connector.Error as e:
        error_type,remarks=get_message_by_code("RCMS_E029")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_regulations.html', error_type=error_type,remarks=remarks)
    finally:
        cursor.close()
        conn.close()

#--------------------------------------------------------------Add Activity--------------------------------------------------------------------------

def add_activity_main():
    conn, cursor = connect_to_database()
    regulations = []
    if conn is not None:
        cursor = conn.cursor()
        try:
            # Fetch both regulation ID and name
            cursor.execute("SELECT regulation_id, regulation_name FROM regulation_master")
            regulations = cursor.fetchall()
        except Error as e:

            log_func(datetime.now().date(), datetime.now().time(), 'ADD',f"Failed to query regulations: {e}")

            print(f"Failed to query regulations: {e}")
        finally:
            cursor.close()
            conn.close()

    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
    return render_template('Global/add_activity.html', entity_id=entity_id, user_id=user_id,regulations=regulations)
 

def get_regulation_id(regulation_name):
    conn, cursor = connect_to_database()
    # user_id = session.get('user_id')
    # user_name = session.get('user_name', 'N/A')  # Use 'N/A' if user_name is not available

    if conn is not None:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT regulation_id FROM regulation_master WHERE regulation_name = %s", (regulation_name,))
            result = cursor.fetchone()
            
            return jsonify({'regulation_id': result[0] if result else ''})
        except Error as e:
            log_func(datetime.now().date(), datetime.now().time(), 'ADD',f"Failed to query regulation ID: {e}")
            print(f"Failed to query regulation ID: {e}")
            return jsonify({'regulation_id': ''})
        finally:
            cursor.close()
            conn.close()
    return jsonify({'regulation_id': ''})
 
def submit_checklist_main():
    regulation_id = request.form['regulationID']
    activity = request.form['activity']
    mandatory_optional = request.form['mandatoryOptional']
    document_upload_yes_no = request.form['documentupload_yes_no']
    frequency = request.form['frequency']
    frequency_timeline = request.form['frequencyTimeline']
    criticality = request.form['criticalNonCritical']
    ews = request.form['EWS']
    activity_description = request.form['activityDescription']

    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
 
    conn, cursor = connect_to_database()
    
    
 
    if conn is not None:
        cursor = conn.cursor()
        try:
            # Check if the activity already exists for the given regulation
            cursor.execute("""
                SELECT COUNT(*) FROM activity_master
                WHERE activity = %s AND regulation_id = %s
            """, (activity, regulation_id))
            if cursor.fetchone()[0] > 0:
                error_type,remarks=get_message_by_code("RCMS_E040")
                log_func(datetime.now().date(), datetime.now().time(), 'ADD',remarks)

            else:
                # If it doesn't exist, insert the new activity
                cursor.execute("SELECT COALESCE(MAX(activity_id) + 1, 1) FROM activity_master WHERE regulation_id = %s", (regulation_id,))
                activity_id = cursor.fetchone()[0]
 
                query = """
                    INSERT INTO activity_master
                    (regulation_id, activity_id, activity, mandatory_optional, documentupload_yes_no,
                    frequency, frequency_timeline, criticality, ews, activity_description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    regulation_id, activity_id, activity, mandatory_optional, document_upload_yes_no,
                    frequency, frequency_timeline, criticality, ews, activity_description
                ))
                conn.commit()
                error_type,remarks=get_message_by_code("RCMS_S010")
                log_func(datetime.now().date(), datetime.now().time(), 'ADD',remarks)

 
        except Error as e:
            print(f"Failed to insert activity: {e}")
            error_type,remarks=get_message_by_code("RCMS_E043")
        finally:
            cursor.close()
            conn.close()
    else:
        error_type,remarks=get_message_by_code("RCMS_E042")
        log_func(datetime.now().date(), datetime.now().time(), 'ADD',remarks)

 
    regulations = send_regulations()
    
    return render_template('Global/add_activity.html', entity_id=entity_id, user_id=user_id,error_type=error_type,remarks=remarks, regulations=regulations)
 
def send_regulations():
    conn, cursor = connect_to_database()
    regulations = []
    if conn is not None:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT regulation_id, regulation_name FROM regulation_master")
            regulations = cursor.fetchall()
        except Error as e:
            print(f"Failed to query regulations: {e}")
        finally:
            cursor.close()
            conn.close()
    return regulations
#--------------------------------------------------Update activity-----------------------------------------------------#
def update_activities_page_main():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE',"Database connection failed")

        return "Database connection failed", 500
    
    # Fetch all regulation_id
    cursor.execute("SELECT DISTINCT regulation_id FROM rcms.activity_master")
    regulations = cursor.fetchall()
    
    cursor.close()
    conn.close()

    #Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
    return render_template('Global/update_activities.html', regulations=regulations,entity_id=entity_id,user_id=user_id)

def populate_activities_main(regulation_id):
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE',"Database connection failed")
        return "Database connection failed", 500
    
    
    # Fetch all activities based on regulation_id
    cursor.execute(f"SELECT activity_id, activity FROM rcms.activity_master WHERE regulation_id='{regulation_id}'")
    activities = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {'activities': activities}

def get_activity_details_main(regulation_id, activity_id):
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE',"Database connection failed")
        return "Database connection failed", 500

    try:
        # Fetch the details of the selected activity based on both regulation_id and activity_id
        cursor.execute("""
            SELECT * FROM rcms.activity_master
            WHERE regulation_id = %s AND activity_id = %s
        """, (regulation_id, activity_id))
        
        # Use fetchone() to retrieve the result
        activity_details = cursor.fetchone()
        print(f"Activity Details: {activity_details}")

        if activity_details:
            return {
                'activity_description': activity_details['activity_description'],
                'criticality': activity_details['criticality'],
                'documentupload_yes_no': activity_details['documentupload_yes_no'],
                'frequency': activity_details['frequency'],
                'frequency_timeline': activity_details['frequency_timeline'].strftime('%Y-%m-%d') if activity_details['frequency_timeline'] else None,  # Format the date properly
                'mandatory_optional': activity_details['mandatory_optional'],
                'ews': activity_details['ews']
            }
        else:
            log_func(datetime.now().date(), datetime.now().time(), 'UPDATE',"No activity found")
            return "No activity found", 404
    except mysql.connector.Error as err:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE',f"Error fetching activity details: {err}")
        return f"Error fetching activity details: {err}", 500
    finally:
        cursor.close()
        conn.close()

def update_activity_main():
    data = request.form
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_type,remarks=get_message_by_code("RCMS_E011")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_activities.html', error_type=error_type,remarks=remarks)

    try:
        # Debugging: print the form data to check what is being passed
        print("Form Data:", data)
        
        # Check if all required fields are present
        required_fields = ['activity_description', 'criticality', 'documentupload_yes_no',
                           'frequency', 'frequency_timeline', 'mandatory_optional', 'ews',
                           'regulation_id', 'activity_id_hidden']
        
        for field in required_fields:
            if field not in data:
                error_type,remarks=get_message_by_code("RCMS_E044")
                return render_template('Global/update_activities.html', error_type=error_type,remarks=remarks)

        # Debugging: print the parameters to be passed in the SQL query
        print("Updating activity with parameters: ",
              data['activity_description'], data['criticality'], data['documentupload_yes_no'],
              data['frequency'], data['frequency_timeline'], data['mandatory_optional'],
              data['ews'], data['regulation_id'], data['activity_id_hidden'])
        
        # Update the activity based on both regulation_id and activity_id to prevent incorrect updates
        cursor.execute("""
            UPDATE rcms.activity_master SET
                activity_description = %s,
                criticality = %s,
                documentupload_yes_no = %s,
                frequency = %s,
                frequency_timeline = %s,
                mandatory_optional = %s,
                ews = %s
            WHERE regulation_id = %s AND activity_id = %s
        """, (data['activity_description'], data['criticality'], data['documentupload_yes_no'],
              data['frequency'], data['frequency_timeline'], data['mandatory_optional'],
              data['ews'], data['regulation_id'], data['activity_id_hidden']))
    
        conn.commit()

        # Fetch updated data to pass to the template
        cursor.execute("SELECT DISTINCT regulation_id FROM rcms.activity_master")
        regulations = cursor.fetchall()

        cursor.execute("SELECT activity_id, activity FROM rcms.activity_master WHERE regulation_id = %s", (data['regulation_id'],))
        activities = cursor.fetchall()

        error_type,remarks=get_message_by_code("RCMS_S011")

        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)

        # Stay on the same page and display a success message
        entity_id = session.get('entity_id')
        user_id = session.get('user_id')
        return render_template('Global/update_activities.html', 
                               regulations=regulations, 
                               activities=activities,
                               entity_id=entity_id, 
                               user_id=user_id,
                               error_type=error_type,remarks=remarks)
    
    except mysql.connector.Error as err:
        error_type,remarks=get_message_by_code("RCMS_E045")
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', remarks)
        return render_template('Global/update_activities.html', error_type=error_type,remarks=remarks)
    
    finally:
        cursor.close()
        conn.close()

# --------------------------------------Delete Activity---------------------------------------------------------
def delete_activities_page_main():
    #Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')

    return render_template('Global/delete_activities.html',entity_id=entity_id, user_id=user_id)  # This renders the delete activities HTML page

def populate_regulations_main():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE','Database connection error')
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        cursor.execute("SELECT regulation_id, regulation_name FROM regulation_master")
        regulations = cursor.fetchall()
        
        return jsonify(regulations)
    except Exception as e:
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE','Failed to fetch regulations')
        return jsonify({'error': 'Failed to fetch regulations'}), 500
    finally:
        cursor.close()
        conn.close()

def load_activities_main(regulation_id):
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        cursor.execute("SELECT activity_id, activity FROM activity_master WHERE regulation_id = %s", (regulation_id,))
        activities = cursor.fetchall()
        
        return jsonify(activities)
    except Exception as e:
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE','Failed to load activities')
        return jsonify({'error': 'Failed to load activities'}), 500
    finally:
        cursor.close()
        conn.close()

def delete_activities_main():
    regulation_id = request.form.get('regulation_id')
    activity_ids = request.form.getlist('activity_ids')
    
    if not regulation_id or not activity_ids:
        error_type,remarks=get_message_by_code("RCMS_E046")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_activities.html', error_type=error_type,remarks=remarks)

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_type,remarks=get_message_by_code("RCMS_E011")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_activities.html', error_type=error_type,remarks=remarks)

    try:
        # Retrieve previous values before deletion
        format_strings = ','.join(['%s'] * len(activity_ids))
        query = f"SELECT * FROM activity_master WHERE regulation_id = %s AND activity_id IN ({format_strings})"
        cursor.execute(query, (regulation_id, *activity_ids))
        
        # Fetch all results to avoid unread result issues
        previous_activities = cursor.fetchall()
        error_type,remarks=get_message_by_code("RCMS_E047")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)

        # Delete only the activities with the specific regulation_id and activity_ids
        query = f"DELETE FROM activity_master WHERE regulation_id = %s AND activity_id IN ({format_strings})"
        cursor.execute(query, (regulation_id, *activity_ids))
        conn.commit()

        error_type,remarks=get_message_by_code("RCMS_S012")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)

        print(error_type,remarks)
        return render_template('Global/delete_activities.html', error_type=error_type,remarks=remarks)
    except Exception as e:
        error_type,remarks=get_message_by_code("RCMS_E048")
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', remarks)
        return render_template('Global/delete_activities.html', error_type=error_type,remarks=remarks)
    finally:
        cursor.close()
        conn.close()
