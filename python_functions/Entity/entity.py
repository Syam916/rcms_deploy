from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import mysql.connector
from datetime import  datetime
import os
from flask_mail import Mail, Message
import smtplib
import traceback
import bcrypt
import re
from mysql.connector import Error
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.relativedelta import relativedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import mysql.connector
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

from python_functions.Entity.lib_functions import *


from python_functions.DB.db import connect_to_database

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


def entity_admin_dashboard_main():
    # Pass entity_id to Dash when rendering the page
      # Call your Dash app with entity_id
      entity_id2=session['entity_id']
      print("The Entity ID 2 is", entity_id2)
      return render_template('entity/entity_admin.html', factory_id=entity_id2)

#---------------------------------------------------------------------------------------------
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


#---------------------------------------------------Add user---------------------------------------------------------------------------------------------------------#
def add_user_entity():
    success_message = None
    error_message = None

    # Fetching session data
    user_entity_id = session.get('entity_id')
    user_user_id = session.get('user_id')

    # Initialize form data
    form_data = {
        'user_id': '',
        'user_name': '',
        'address': '',
        'mobile_no': '',
        'email_id': '',
        'password': '',
        'role': 'User'  # Default role if needed
    }

    if request.method == 'POST':
        form_data['user_id'] = request.form['user_id'].strip()
        form_data['user_name'] = request.form['user_name'].strip()
        form_data['address'] = request.form['address'].strip()
        form_data['mobile_no'] = request.form['mobile_no'].strip()
        form_data['email_id'] = request.form['email_id'].strip()
        password = request.form['password']
        form_data['role'] = request.form['role'].strip()  # Get the role from the form

        # Validate email format
        if not validate_email(form_data['email_id']):
            error_message = 'Invalid email format. Please enter a valid email address.'
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)  # Log the error
            return render_template('entity/add_user.html', error_message=error_message,
                                   user_entity_id=user_entity_id, user_user_id=user_user_id,
                                   form_data=form_data)

        # Validate password strength
        if not validate_password(password):
            error_message = ('Password must be at least 8 characters long, contain at least one uppercase letter, '
                             'one lowercase letter, one number, and one special character.')
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)  # Log the error
            return render_template('entity/add_user.html', error_message=error_message,
                                   user_entity_id=user_entity_id, user_user_id=user_user_id,
                                   form_data=form_data)

        # Validate mobile number
        if not validate_mobile_number(form_data['mobile_no']):
            error_message = 'Mobile number must be exactly 10 digits.'
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)  # Log the error
            return render_template('entity/add_user.html', error_message=error_message,
                                   user_entity_id=user_entity_id, user_user_id=user_user_id,
                                   form_data=form_data)

        # Hash the password before saving it
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Connect to the database
        conn, cursor = connect_to_database()
        if conn is None or cursor is None:
            error_message = 'Database connection failed!'
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)  # Log the error
            return render_template('entity/add_user.html', error_message=error_message,
                                   user_entity_id=user_entity_id, user_user_id=user_user_id,
                                   form_data=form_data)

        try:
            # Check if the user_id already exists in the same entity_id
            cursor.execute("SELECT * FROM users WHERE user_id = %s AND entity_id = %s", 
                           (form_data['user_id'], user_entity_id))
            existing_user = cursor.fetchone()

            if existing_user:
                error_message = 'User ID already exists in this entity. Please choose a different User ID.'
                log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)  # Log the error
            else:
                # Insert the new user into the database
                cursor.execute(""" 
                    INSERT INTO users (user_id, user_name, address, mobile_no, email_id, password, entity_id, role)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (form_data['user_id'], form_data['user_name'], form_data['address'], 
                      form_data['mobile_no'], form_data['email_id'], 
                      hashed_password.decode('utf-8'), user_entity_id, form_data['role']))

                conn.commit()

                # Log the successful addition of the user
                log_func(datetime.now().date(), datetime.now().time(), 'ADD', 'User added successfully')

                # Send email notification to the user
                msg = Message(
                    "Welcome to Regulatory Compliance Management System",
                    sender="vardaan.rcms@gmail.com",
                    recipients=[form_data['email_id']]
                )
                msg.body = (f"Dear {form_data['user_name']},\n\n"
                            f"You have been added to the system with the following credentials:\n\n"
                            f"User ID: {form_data['user_id']}\n"
                            f"Password: {password}\n"
                            f"Factory ID: {user_entity_id}\n"
                            f"Role: {form_data['role']}\n\n"
                            f"Please log in and change your password as soon as possible.\n\n"
                            f"Best regards,\n"
                            f"Your Factory ID: {user_entity_id}")
                mail.send(msg)

                success_message = 'User added successfully! An email has been sent to the user.'
                # Clear the form by resetting form_data
                form_data = {key: '' for key in form_data}  # Clear all fields

        except mysql.connector.Error as err:
            error_message = f'Failed to add user: {err}'
            conn.rollback()
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)  # Log the error
        finally:
            cursor.close()
            conn.close()

    return render_template('entity/add_user.html', user_entity_id=user_entity_id, user_user_id=user_user_id,
                           success_message=success_message, error_message=error_message,
                           form_data=form_data)

def validate_email(email):
    # Regex for validating an Email
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def validate_password(password):
    # Check for password strength
    password_regex = (r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
    return re.match(password_regex, password) is not None

def validate_mobile_number(mobile_no):
    # Check if mobile number is exactly 10 digits
    return re.match(r'^\d{10}$', mobile_no) is not None



#------------------------------------------------------Update User----------------------------------------------------------------------------------
def load_user_entity(user_id):
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = 'Database connection error'
        log_func(datetime.now().date(), datetime.now().time(), 'MODIFY', error_message)  # Log the error
        return jsonify({'error': error_message}), 500

    try:
        # Fetch user details based on user_id and entity_id from the session
        cursor.execute("SELECT user_id, entity_id, user_name, address, mobile_no, email_id, role "
                       "FROM users WHERE user_id = %s AND entity_id = %s", 
                       (user_id, session['entity_id']))
        user = cursor.fetchone()
        
        if user:
            return jsonify(user)
        else:
            error_message = 'User not found in this entity'
            log_func(datetime.now().date(), datetime.now().time(), 'MODIFY', error_message)  # Log the error
            return jsonify({'error': error_message}), 404
    finally:
        cursor.close()
        conn.close()

def update_user_entity():
    # Fetch user input and trim spaces
    user_id = request.form['user_id'].strip()
    
    # Validate that user_id is provided
    if not user_id:
        error_message = 'User ID is required.'
        log_func(datetime.now().date(), datetime.now().time(), 'MODIFY', error_message)  # Log the error
        return jsonify({'error': error_message}), 400

    user_name = request.form['user_name'].strip()
    address = request.form['address'].strip()
    mobile_no = request.form['mobile_no'].strip()
    email_id = request.form['email_id'].strip()

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = 'Database connection error'
        log_func(datetime.now().date(), datetime.now().time(), 'MODIFY', error_message)  # Log the error
        return jsonify({'error': error_message}), 500

    try:
        # Fetch the current user data for checking if the user exists
        cursor.execute("SELECT user_name, address, mobile_no, email_id FROM users WHERE user_id = %s AND entity_id = %s", 
                       (user_id, session['entity_id']))
        existing_user = cursor.fetchone()

        # Check if the user exists
        if existing_user is None:
            error_message = 'User not found in this entity'
            log_func(datetime.now().date(), datetime.now().time(), 'MODIFY', error_message)  # Log the error
            return jsonify({'error': error_message}), 404

        # Validate mobile number and email
        if not is_valid_mobile_no(mobile_no):
            error_message = 'Invalid mobile number format'
            log_func(datetime.now().date(), datetime.now().time(), 'MODIFY', error_message)  # Log the error
            return jsonify({'error': error_message}), 400

        if not is_valid_email(email_id):
            error_message = 'Invalid email address format'
            log_func(datetime.now().date(), datetime.now().time(), 'MODIFY', error_message)  # Log the error
            return jsonify({'error': error_message}), 400

        # Check for changes
        modified_fields = []
        if existing_user['user_name'] != user_name:
            modified_fields.append(f"user_name: {user_name}")
        if existing_user['address'] != address:
            modified_fields.append(f"address: {address}")
        if existing_user['mobile_no'] != mobile_no:
            modified_fields.append(f"mobile_no: {mobile_no}")
        if existing_user['email_id'] != email_id:
            modified_fields.append(f"email_id: {email_id}")

        # Execute update if there are any changes
        if modified_fields:
            cursor.execute(""" 
                UPDATE users 
                SET user_name = %s, address = %s, mobile_no = %s, email_id = %s 
                WHERE user_id = %s AND entity_id = %s
            """, (user_name, address, mobile_no, email_id, user_id, session['entity_id']))
            conn.commit()

            log_func(datetime.now().date(), datetime.now().time(), 'MODIFY', 'User updated successfully!')
            return jsonify({'message': 'User updated successfully!'}), 200
        else:
            return jsonify({'message': 'No changes made to user.'}), 200  # Handle case where no changes were made

    except mysql.connector.Error as err:
        error_message = str(err)
        log_func(datetime.now().date(), datetime.now().time(), 'MODIFY', error_message)  # Log the error
        return jsonify({'error': error_message}), 500
    finally:
        cursor.close()
        conn.close()


def update_user_page_entity():
    # Fetching session data
    user_entity_id = session.get('entity_id')
    user_user_id = session.get('user_id')
    log_func(datetime.now().date(), datetime.now().time(), 'LOAD', 'Update user page accessed')
    return render_template('entity/update_user.html', user_entity_id=user_entity_id, user_user_id=user_user_id)

def is_valid_mobile_no(mobile_no):
    # Define a regex pattern for validating mobile numbers
    pattern = re.compile(r'^\d{10}$')  # Adjust the pattern as needed
    return pattern.match(mobile_no)

def is_valid_email(email):
    # Define a regex pattern for validating email addresses
    pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return pattern.match(email)

#------------------------------------------------------Delete user------------------------------------------------------------------------------------------------------
def fetch_user_entity(user_id):
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = 'Database connection error'
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
        return jsonify({'error': error_message}), 500

    try:
        # Fetch the user details based on user_id and entity_id from the session
        cursor.execute("SELECT user_id, entity_id, user_name, address, mobile_no, email_id, role "
                       "FROM users WHERE user_id = %s AND entity_id = %s", 
                       (user_id, session['entity_id']))
        user = cursor.fetchone()
        
        if user:
            return jsonify(user)
        else:
            error_message = 'User not found in this entity'
            log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
            return jsonify({'error': error_message}), 404
    finally:
        cursor.close()
        conn.close()

def delete_user_entity():
    user_id = request.form['user_id'].strip()  # Trim spaces
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = 'Database connection error'
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
        return jsonify({'error': error_message}), 500

    try:
        # Fetching the user details before deletion for logging, based on user_id and entity_id
        cursor.execute("SELECT user_name FROM users WHERE user_id = %s AND entity_id = %s", 
                       (user_id, session['entity_id']))
        existing_user = cursor.fetchone()

        if existing_user is None:
            error_message = 'User not found in this entity'
            log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
            return jsonify({'error': error_message}), 404

        # Proceed to delete the user
        cursor.execute("DELETE FROM users WHERE user_id = %s AND entity_id = %s", 
                       (user_id, session['entity_id']))
        conn.commit()

        # Log the successful deletion
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', 'User deleted successfully!')

        return jsonify({'message': 'User deleted successfully!'}), 200
    except mysql.connector.Error as err:
        error_message = str(err)
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
        return jsonify({'error': error_message}), 500
    finally:
        cursor.close()
        conn.close()

def delete_user_page_entity():
    # Fetching session data
    user_entity_id = session.get('entity_id')
    user_user_id = session.get('user_id')
    log_func(datetime.now().date(), datetime.now().time(), 'DELETE', 'Delete user page accessed')  # Log page access
    return render_template('entity/delete_user.html', user_entity_id=user_entity_id, user_user_id=user_user_id)

#--------------------------------------------------------Add category-------------------------------------------------------------------------------------------------#
def add_category_entity():
    # Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')

    # Log the access to the add category page
    log_func(datetime.now().date(), datetime.now().time(), 'ADD', 'Add category page accessed')

    # Pass the session data to the template
    return render_template('entity/add_category_entity.html', entity_id=entity_id, user_id=user_id)

def submit_category_entity():
    conn, cursor = connect_to_database()
    error_message = None
    success_message = None

    # Fetching session data
    user_id = session.get('user_id')
    if conn is not None:
        try:
            category_type = request.form.get('categoryType').strip()
            remarks = request.form.get('remarks').strip()

            # Check if the category type already exists in the database
            cursor.execute("SELECT COUNT(*) as count FROM category WHERE category_type = %s", (category_type,))
            result = cursor.fetchone()

            # Use the key 'count' to get the count of categories
            if result['count'] > 0:
                error_message = "Category already exists! Please use a different category type."
                log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)
            else:
                # Insert the category data into the database
                cursor.execute("""
                    INSERT INTO category (category_type, remarks)
                    VALUES (%s, %s)
                """, (category_type, remarks))
                conn.commit()

                success_message = f"Category successfully added with ID {cursor.lastrowid}."
                log_func(datetime.now().date(), datetime.now().time(), 'ADD', success_message)

        except mysql.connector.IntegrityError as e:
            error_message = "Failed to submit category data due to integrity error."
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)
        except mysql.connector.Error as e:
            error_message = f"Database error occurred: {str(e)}"  # Capture detailed database error
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)
            print(f"Failed to submit form data: {error_message}")  # Log the error to console
        except Exception as e:
            # Log the complete traceback for better diagnosis
            error_message = f"Unexpected error occurred: {str(e)}"  # Capture any other unexpected error
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)
            print(f"Failed to submit form data: {error_message}")  # Log the error to console
            print(traceback.format_exc())  # Print the full traceback to the console
        finally:
            cursor.close()
            conn.close()
    else:
        error_message = "Failed to connect to the database."
        log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)

    # Fetching session data again
    entity_id = session.get('entity_id')

    return render_template('entity/add_category_entity.html', error_message=error_message, success_message=success_message, entity_id=entity_id, user_id=user_id)

#---------------------------------------------------------Delete category------------------------------------------------------------------------------------------------------
def display_categories_entity():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = "Error connecting to the database."
        user_id = session.get('user_id')
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
        return error_message

    try:
        # Fetch specific columns, including remarks
        cursor.execute("SELECT category_id, category_type, Remarks FROM category")
        categories = cursor.fetchall()
        
        # Print the categories to check if remarks are fetched
        print(categories)  # Debugging: check the data structure and whether remarks are fetched
        
        # Fetching session data
        entity_id = session.get('entity_id')
        user_id = session.get('user_id')

        # Log the successful display of categories
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', 'Categories displayed successfully')

        return render_template('entity/delete_category.html', categories=categories, entity_id=entity_id, user_id=user_id)
    finally:
        cursor.close()
        conn.close()

def delete_category_entity():
    category_ids = request.form.getlist('category_ids')

    if category_ids:
        conn, cursor = connect_to_database()
        if conn is None or cursor is None:
            error_message = "Error connecting to the database."
            log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
            return error_message
        
        try:
            format_strings = ','.join(['%s'] * len(category_ids))
            cursor.execute(f"DELETE FROM category WHERE category_id IN ({format_strings})", category_ids)
            conn.commit()

            # Log successful deletion
            log_func(datetime.now().date(), datetime.now().time(), 'DELETE', 'Categories deleted successfully')
            
            return redirect('/display_entity_categories?deleted=true')  # Redirect with query parameter after successful deletion
        except mysql.connector.Error as err:
            error_message = f"Error: {err}"
            log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
            print(f"Error: {err}")
            flash("An error occurred while deleting the categories.")
        finally:
            cursor.close()
            conn.close()
    else:
        error_message = "No category selected for deletion."
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
        flash(error_message)
    
    return redirect('/display_entity_categories')

#---------------------------------------------------Add Regulation---------------------------------------------------------------------------------------------------------------------------
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

#-----------------------------------------------------Update regulation--------------------------------------------------------------------------------------------------------------------------------------
def edit_regulation_page_entity():
    # Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')

    # Establish connection to database
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = 'Database connection error'
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', error_message)  # Log the error
        flash(error_message, 'error')
        return redirect(url_for('edit_entity_regulation_page'))

    try:
        # Query to fetch all regulations for the given entity_id from the entity_regulation and regulation_master tables
        query = """
            SELECT rm.regulation_id, rm.regulation_name
            FROM regulation_master rm
            INNER JOIN entity_regulation er ON rm.regulation_id = er.regulation_id
            WHERE er.entity_id = %s
        """
        cursor.execute(query, (entity_id,))
        regulations = cursor.fetchall()
        
        # Log the successful retrieval of regulations
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', 'Regulations displayed successfully')
    except mysql.connector.Error as err:
        error_message = f'Error fetching regulations: {str(err)}'
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', error_message)  # Log the error
        flash(error_message, 'error')
        regulations = []
    finally:
        cursor.close()
        conn.close()

    # Render the template with the list of regulations for the given entity
    return render_template('entity/update_regulations.html', regulations=regulations, entity_id=entity_id, user_id=user_id)

def fetch_regulation_entity():
    regulation_name = request.form.get('regulation_name').strip()  # Trim spaces

    # Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')
 
    # Connect to the database
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = 'Database connection error'
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', error_message)  # Log the error
        flash(error_message, 'error')
        return redirect(url_for('edit_entity_regulation_page'))

    try:
        # Fetch the details of the selected regulation
        query = """
            SELECT rm.*
            FROM regulation_master rm
            INNER JOIN entity_regulation er ON rm.regulation_id = er.regulation_id
            WHERE LOWER(rm.regulation_name) = LOWER(%s) AND er.entity_id = %s
        """
        cursor.execute(query, (regulation_name, entity_id))
        regulation = cursor.fetchone()

        if not regulation:
            flash('No regulation found', 'error')
            log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', 'No regulation found')
            return redirect(url_for('edit_entity_regulation_page'))

        # Fetch all regulations to display in the dropdown
        cursor.execute("""
            SELECT rm.regulation_name
            FROM regulation_master rm
            INNER JOIN entity_regulation er ON rm.regulation_id = er.regulation_id
            WHERE er.entity_id = %s
        """, (entity_id,))
        regulations = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    # Pass selected_regulation and all regulations to the template
    return render_template('entity/update_regulations.html', 
                           regulation=regulation, 
                           entity_id=entity_id, 
                           user_id=user_id, 
                           regulations=regulations, 
                           selected_regulation=regulation_name)


def update_regulation_entity():
    # Get data from the form using `request.form`
    regulation_id = request.form.get('regulation_id')
    regulatory_body = request.form.get('regulatory_body')
    internal_external = request.form.get('internal_external')
    national_international = request.form.get('national_international')
    mandatory_optional = request.form.get('mandatory_optional')
    obsolete_current = request.form.get('obsolete_current')

    if not regulation_id:
        error_message = 'Missing regulation ID'
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', error_message)  # Log the error
        flash(error_message, 'error')
        return redirect(url_for('edit_entity_regulation_page'))

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = 'Database connection error'
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', error_message)  # Log the error
        flash(error_message, 'error')
        return redirect(url_for('edit_entity_regulation_page'))

    try:
        # Fetch current values for logging previous values
        cursor.execute("""
            SELECT regulatory_body, internal_external, national_international, mandatory_optional, obsolete_current 
            FROM regulation_master 
            WHERE regulation_id = %s
        """, (regulation_id,))
        
        current_values = cursor.fetchone()

        if current_values:
            query = """
                UPDATE regulation_master
                SET regulatory_body = %s,
                    internal_external = %s,
                    national_international = %s,
                    mandatory_optional = %s,
                    obsolete_current = %s
                WHERE regulation_id = %s
            """
            cursor.execute(query, (regulatory_body, internal_external, national_international, mandatory_optional, obsolete_current, regulation_id))
            conn.commit()

            success_message = 'Regulation updated successfully!'
            log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', success_message)  # Log the update success
            flash(success_message, 'success')
            return redirect(url_for('edit_entity_regulation_page'))
        else:
            error_message = 'Regulation not found for updating.'
            log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', error_message)  # Log the error
            flash(error_message, 'error')

    except mysql.connector.Error as err:
        error_message = f'Error updating regulation: {str(err)}'
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', error_message)  # Log the error
        flash(error_message, 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('edit_entity_regulation_page'))

#-------------------------------------------------Delete regulation-------------------------------------------------------------------------------------------------

def delete_regulations_page_entity():
    # Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')

    # Log the action of accessing the delete regulations page
    log_func(datetime.now().date(), datetime.now().time(), 'DELETE', 'Accessed delete regulations page.')
    
    return render_template('entity/delete_regulations.html', entity_id=entity_id, user_id=user_id)

def fetch_categories_entity():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = 'Database connection error'
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
        return jsonify({'error': error_message}), 500
    
    try:
        cursor.execute("SELECT category_id, category_type FROM category")
        categories = cursor.fetchall()
        # Log successful fetching of categories
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', 'Fetched categories successfully.')
        return jsonify(categories)
    except Exception as e:
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', str(e))  # Log the error
        return jsonify({'error': 'Failed to fetch categories'}), 500
    finally:
        cursor.close()
        conn.close()

def load_regulations_entity(category_id):
    # Fetch entity_id from the session
    entity_id = session.get('entity_id')
    
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = 'Database connection error'
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
        return jsonify({'error': error_message}), 500

    try:
        query = """
            SELECT rm.regulation_id, rm.regulation_name, rm.regulatory_body
            FROM regulation_master rm
            INNER JOIN entity_regulation er ON rm.regulation_id = er.regulation_id
            WHERE rm.category_id = %s AND er.entity_id = %s
        """
        cursor.execute(query, (category_id, entity_id))
        regulations = cursor.fetchall()

        # Log successful loading of regulations
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', f'Loaded regulations for category_id: {category_id}.')
        return jsonify(regulations)
    except Exception as e:
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', str(e))  # Log the error
        return jsonify({'error': 'Failed to load regulations'}), 500
    finally:
        cursor.close()
        conn.close()

def delete_regulations_entity():
    regulation_ids = request.form.getlist('regulation_ids')
    if not regulation_ids:
        error_message = 'No regulations selected'
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
        return jsonify({'error': error_message}), 400

    # Fetch entity_id from the session
    entity_id = session.get('entity_id')

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        error_message = 'Database connection error'
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
        return jsonify({'error': error_message}), 500

    try:
        # Retrieve previous values before deletion
        format_strings = ','.join(['%s'] * len(regulation_ids))
        query = f"""
            SELECT rm.regulation_id, rm.regulation_name, rm.regulatory_body
            FROM regulation_master rm
            INNER JOIN entity_regulation er ON rm.regulation_id = er.regulation_id
            WHERE rm.regulation_id IN ({format_strings}) AND er.entity_id = %s
        """
        cursor.execute(query, (*regulation_ids, entity_id))
        # First, delete from activity_master that references these regulations
        delete_activity_query = f"""
            DELETE FROM activity_master
            WHERE regulation_id IN ({format_strings})
        """
        cursor.execute(delete_activity_query, (*regulation_ids,))

        # Next, delete from entity_regulation
        delete_entity_regulation_query = f"""
            DELETE FROM entity_regulation
            WHERE regulation_id IN ({format_strings}) AND entity_id = %s
        """
        cursor.execute(delete_entity_regulation_query, (*regulation_ids, entity_id))

        # Finally, delete from regulation_master
        delete_regulation_query = f"""
            DELETE FROM regulation_master
            WHERE regulation_id IN ({format_strings})
        """
        cursor.execute(delete_regulation_query, (*regulation_ids,))
        conn.commit()
        
        success_message = 'Selected regulations deleted successfully!'
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', success_message)  # Log the deletion success
        return jsonify({'message': success_message})

    except Exception as e:
        error_message = f'Failed to delete regulations: {str(e)}'
        log_func(datetime.now().date(), datetime.now().time(), 'DELETE', error_message)  # Log the error
        print(f"Error during regulation deletion: {error_message}")  # Added debug print
        return jsonify({'error': error_message}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
#-------------------------------------------------------------------------------------------------------------------------------------------------------------

#----------------------------------Add Activity--------------------------------------------------------------------------#
def add_activity_entity():
    conn, cursor = connect_to_database()
    regulations = []
    entity_id = session.get('entity_id')  # Fetching the entity_id from session

    if conn is not None:
        cursor = conn.cursor()
        try:
            # Fetch regulation ID and name filtered by entity_id using JOIN
            cursor.execute("""
                SELECT rm.regulation_id, rm.regulation_name 
                FROM regulation_master rm
                JOIN entity_regulation er ON rm.regulation_id = er.regulation_id
                WHERE er.entity_id = %s
            """, (entity_id,))
            regulations = cursor.fetchall()
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', 'Fetched regulations for adding activity.')  # Log the fetching of regulations
        except Error as e:
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', str(e))  # Log the error
            print(f"Failed to query regulations: {e}")
        finally:
            cursor.close()
            conn.close()

    # Fetching user_id from session
    user_id = session.get('user_id')
    
    return render_template('entity/add_activity_entity.html', regulations=regulations, entity_id=entity_id, user_id=user_id)

def get_regulation_id_entity(entity_id, regulation_name):
    conn, cursor = connect_to_database()
    if conn is not None:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT rm.regulation_id 
                FROM regulation_master rm
                JOIN entity_regulation er ON rm.regulation_id = er.regulation_id
                WHERE er.entity_id = %s AND rm.regulation_name = %s
            """, (entity_id, regulation_name))
            result = cursor.fetchone()
            regulation_id = result[0] if result else ''
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', f'Retrieved regulation ID: {regulation_id} for regulation name: {regulation_name}')
            return jsonify({'regulation_id': regulation_id})
        except Error as e:
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', str(e))  # Log the error
            print(f"Failed to query regulation ID: {e}")
            return jsonify({'regulation_id': ''})
        finally:
            cursor.close()
            conn.close()
    return jsonify({'regulation_id': ''})


def submit_checklist_entity():
    regulation_id = request.form['regulationID']
    activity = request.form['activity']
    mandatory_optional = request.form['mandatoryOptional']
    document_upload_yes_no = request.form['documentupload_yes_no']
    frequency = request.form['frequency']
    frequency_timeline = request.form['frequencyTimeline']
    criticality = request.form['criticalNonCritical']
    ews = request.form['ews']
    activity_description = request.form['activityDescription']
 
    conn, cursor = connect_to_database()
    error_message = None
    success_message = None
 
    if conn is not None:
        cursor = conn.cursor()
        try:
            # Check if the activity already exists for the given regulation
            cursor.execute("""
                SELECT COUNT(*) FROM activity_master
                WHERE activity = %s AND regulation_id = %s
            """, (activity, regulation_id))
            if cursor.fetchone()[0] > 0:
                error_message = "Activity already exists for this regulation."
                log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)  # Log the error
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
                success_message = "Activity successfully added."
                log_func(datetime.now().date(), datetime.now().time(), 'ADD', f"Activity successfully added with ID: {activity_id}")

        except Error as e:
            print(f"Failed to insert activity: {e}")
            error_message = "Failed to add checklist item due to a database error."
            log_func(datetime.now().date(), datetime.now().time(), 'ADD', str(e))  # Log the error
        finally:
            cursor.close()
            conn.close()
    else:
        error_message = "Failed to connect to the database."
        log_func(datetime.now().date(), datetime.now().time(), 'ADD', error_message)  # Log the error
 
    # Fetch regulations for the current entity
    entity_id = session.get('entity_id')
    regulations = send_regulations_for_entity(entity_id)
    user_id = session.get('user_id')
    
    return render_template('entity/add_activity_entity.html', error_message=error_message, success_message=success_message, regulations=regulations, entity_id=entity_id, user_id=user_id)

def send_regulations_for_entity(entity_id):
    conn, cursor = connect_to_database()
    regulations = []
    if conn is not None:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT rm.regulation_id, rm.regulation_name 
                FROM regulation_master rm
                JOIN entity_regulation er ON rm.regulation_id = er.regulation_id
                WHERE er.entity_id = %s
            """, (entity_id,))
            regulations = cursor.fetchall()
        except Error as e:
            print(f"Failed to query regulations: {e}")
        finally:
            cursor.close()
            conn.close()
    return regulations

 #---------------------------------------------------Update activity-----------------------------------------------------------------------------------------------------#
@app.route('/update_activities_page_entity')
def update_activities_page_entity():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        log_func(datetime.now().date(), datetime.now().time(), 'ERROR', "Database connection failed")
        return "Database connection failed", 500

    # Fetch the entity_id from the session
    entity_id = session.get('entity_id')

    # Fetch regulations related to the entity_id from the entity_regulation table
    cursor.execute("""
        SELECT r.regulation_id, r.regulation_name 
        FROM regulation_master r
        JOIN entity_regulation er ON r.regulation_id = er.regulation_id
        WHERE er.entity_id = %s
    """, (entity_id,))
    
    regulations = cursor.fetchall()

    cursor.close()
    conn.close()

    # Fetching user_id from session
    user_id = session.get('user_id')
    log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', 'Accessed update activities page.')
    
    return render_template('entity/update_activities.html', regulations=regulations, entity_id=entity_id, user_id=user_id)

def populate_activities_entity(regulation_id):
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', "Database connection failed")
        return "Database connection failed", 500
    
    try:
        # Fetch all activities based on regulation_id
        cursor.execute("SELECT activity_id, activity FROM activity_master WHERE regulation_id=%s", (regulation_id,))
        activities = cursor.fetchall()
        
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', f'Fetched activities for regulation ID: {regulation_id}.')
    
        return {'activities': activities}
    finally:
        cursor.close()
        conn.close()

def get_activity_details_entity(regulation_id, activity_id):
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', "Database connection failed")
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
            log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', f'Fetched activity details for Activity ID: {activity_id}, Regulation ID: {regulation_id}.')

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
            log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', 'No activity found.')
            return "No activity found", 404
    except mysql.connector.Error as err:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', f"Error fetching activity details: {err}")
        return f"Error fetching activity details: {err}", 500
    finally:
        cursor.close()
        conn.close()

def update_activity_entity():
    # Fetch the entity_id from the session
    entity_id = session.get('entity_id')
    # Fetching user_id from session
    user_id = session.get('user_id')
    data = request.form
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', "Database connection failed")
        return "Database connection failed", 500
    
    try:
        # Check if all required fields are present
        required_fields = ['activity_description', 'criticality', 'documentupload_yes_no',
                           'frequency', 'frequency_timeline', 'mandatory_optional', 'ews',
                           'regulation_id', 'activity_id_hidden', 'entity_id']  # Add entity_id here
        
        for field in required_fields:
            if field not in data:
                log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', f"Missing field: {field}")
                return f"Missing field: {field}", 400

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

        # Fetch updated regulations based on entity_id
        cursor.execute("""
            SELECT r.regulation_id, r.regulation_name 
            FROM regulation_master r
            JOIN entity_regulation er ON r.regulation_id = er.regulation_id
            WHERE er.entity_id = %s
        """, (data['entity_id'],))  # Use the entity_id from the form data
        regulations = cursor.fetchall()

        cursor.execute("SELECT activity_id, activity FROM rcms.activity_master WHERE regulation_id = %s", (data['regulation_id'],))
        activities = cursor.fetchall()

        success_message = "Activity updated successfully!"

        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE','Activity updated successfully!')

        # Stay on the same page and display a success message
        return render_template('entity/update_activities.html', 
                               regulations=regulations, 
                               activities=activities, 
                               success_message=success_message,
                               entity_id=entity_id, user_id=user_id)
    
    except mysql.connector.Error as err:
        log_func(datetime.now().date(), datetime.now().time(), 'UPDATE', 
                 f"Error updating activity: {err}")
        return f"Error updating activity: {err}", 500
    finally:
        cursor.close()
        conn.close()

#-----------------------------------------------------Delete Activity---------------------------------------------------------------------------------------------------------------------------------#
def delete_activities_page_entity():
    # Fetch session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')


    # This renders the delete activities HTML page
    return render_template('entity/delete_activities.html', entity_id=entity_id, user_id=user_id)

def populate_regulations_entity():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        return jsonify({'error': 'Database connection error'}), 500
    
    entity_id = session.get('entity_id')  # Fetch entity_id from session

    try:
        # Fetch regulations specific to the entity_id
        cursor.execute("""
            SELECT r.regulation_id, r.regulation_name 
            FROM regulation_master r
            JOIN entity_regulation er ON r.regulation_id = er.regulation_id
            WHERE er.entity_id = %s
        """, (entity_id,))
        
        regulations = cursor.fetchall()
        
        return jsonify(regulations)
    finally:
        cursor.close()
        conn.close()

def load_activities_entity(regulation_id):
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        # Fetch activities based on regulation_id
        cursor.execute("SELECT activity_id, activity FROM activity_master WHERE regulation_id = %s", (regulation_id,))
        activities = cursor.fetchall()
        
        
        return jsonify(activities)
    finally:
        cursor.close()
        conn.close()

def delete_activities_entity():
    regulation_id = request.form.get('regulation_id')
    activity_ids = request.form.getlist('activity_ids')

    if not regulation_id or not activity_ids:
        return jsonify({'error': 'No activities or regulation selected'}), 400

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        return jsonify({'error': 'Database connection error'}), 500

    try:
        # Delete only the activities with the specific regulation_id and activity_ids
        format_strings = ','.join(['%s'] * len(activity_ids))
        query = f"DELETE FROM activity_master WHERE regulation_id = %s AND activity_id IN ({format_strings})"
        cursor.execute(query, (regulation_id, *activity_ids))
        conn.commit()

        return jsonify({'message': 'Selected activities deleted successfully!'})
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------Add Holiday--------------------------------------------------------------------------------------------------
def add_holiday_entity():
    # Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')

    success_message = None
    error_message = None

    if request.method == 'POST':
        submit_type = request.form.get('submit_type')

        conn, cursor = connect_to_database()
        if conn is None or cursor is None:
            error_message = 'Database connection failed!'
            return render_template('entity/add_holiday.html', error_message=error_message, entity_id=entity_id, user_id=user_id)

        if submit_type == 'multiple':
            holidays = []

            for i in range(12):
                holiday_date = request.form.get(f'holiday_date_{i}')
                description = request.form.get(f'description_{i}')
                if holiday_date and description:
                    holidays.append((holiday_date, description, entity_id))

            if not holidays:
                error_message = 'At least one holiday must be provided!'
                return render_template('entity/add_holiday.html', error_message=error_message, entity_id=entity_id, user_id=user_id)

            try:
                cursor.executemany(""" 
                    INSERT INTO holiday_master (Holiday_Date, Description, entity_id)
                    VALUES (%s, %s, %s)
                """, holidays)
                conn.commit()
                success_message = 'Holidays added successfully!'
                
            except Exception as e:
                conn.rollback()
                error_message = f'Failed to add holidays: {str(e)}'
                

        elif submit_type == 'single':
            holiday_date = request.form.get('holiday_date_single')
            description = request.form.get('description_single')

            if not holiday_date or not description:
                error_message = 'All fields are required!'
               
                return render_template('entity/add_holiday.html', error_message=error_message, entity_id=entity_id, user_id=user_id)

            try:
                cursor.execute("""
                    INSERT INTO holiday_master (Holiday_Date, Description, entity_id)
                    VALUES (%s, %s, %s)
                """, (holiday_date, description, entity_id))
                conn.commit()
                success_message = f'Holiday added successfully! Date: {holiday_date}, Description: {description}'
                
            except Exception as e:
                conn.rollback()
                error_message = f'Failed to add holiday: {str(e)}'
               

        cursor.close()
        conn.close()

        return render_template('entity/add_holiday.html', success_message=success_message, error_message=error_message, entity_id=entity_id, user_id=user_id)


    return render_template('entity/add_holiday.html', entity_id=entity_id, user_id=user_id, success_message=success_message, error_message=error_message)


#----------------------------------------------Delete holidays---------------------------------------------------------------------------

def delete_holidays_page_entity():
    # Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')

    # This renders the delete holidays HTML page
    return render_template('entity/delete_holidays.html', entity_id=entity_id, user_id=user_id)

def fetch_holidays_entity():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
    
        return jsonify({'error': 'Database connection error'}), 500
    
    # Fetching session data
    entity_id = session.get('entity_id')

    try:
        # Fetch holidays only for the current entity_id
        cursor.execute("SELECT `Holiday_Date`, `Description` FROM holiday_master WHERE entity_id = %s", (entity_id,))
        holidays = cursor.fetchall()

        # Format the date to exclude time
        for holiday in holidays:
            holiday['Holiday_Date'] = holiday['Holiday_Date'].strftime("%Y-%m-%d")  # Correct format for MySQL

       

        return jsonify(holidays)
    finally:
        cursor.close()
        conn.close()


def delete_holidays_entity():
    holiday_dates = request.form.getlist('holiday_dates')
    if not holiday_dates:
       
        return jsonify({'error': 'No holidays selected'}), 400

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
      
        return jsonify({'error': 'Database connection error'}), 500

    # Fetching session data
    entity_id = session.get('entity_id')

    try:
        # Convert dates to MySQL acceptable format
        formatted_dates = [datetime.strptime(date, "%Y-%m-%d").date() for date in holiday_dates]
        format_strings = ','.join(['%s'] * len(formatted_dates))
        
        # Delete holidays only for the current entity_id
        cursor.execute(f"DELETE FROM holiday_master WHERE `Holiday_Date` IN ({format_strings}) AND entity_id = %s", (*formatted_dates, entity_id))
        conn.commit()

      

        return jsonify({'message': 'Selected holidays deleted successfully!'})
    except Exception as e:
        
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


#--------------------------------------------------------------------------------------------------------------------------------------------------------

#-----------------------------------------------reassign-------------------------------------------------------------------------------------

def send_email(subject, to_email, content):
    sender_email = "vardaan.rcms@gmail.com"  # Replace with your sender email
    password = "aynlltagpthlzqgd"  # Replace with your app-specific password
 
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = to_email
    message['Subject'] = subject
    message.attach(MIMEText(content, 'plain'))
 
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, password)
    text = message.as_string()
    server.sendmail(sender_email, to_email, text)
    server.quit()
 
# Function to create a Google Calendar event
from google.oauth2.credentials import Credentials  # Ensure this import
 
def ccreate_calendar_event(subject, due_on, to_email):
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
 
    # Check if token file exists
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
 
    # If there are no valid credentials, request authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
 
    # Create the calendar service
    service = build('calendar', 'v3', credentials=creds)
 
    event = {
        'summary': subject,
        'description': f'Task due on {due_on}',
        'start': {
            'dateTime': f'{due_on}T08:00:00',
            'timeZone': 'Europe/London',
        },
        'end': {
            'dateTime': f'{due_on}T09:00:00',
            'timeZone': 'Europe/London',
        },
        'attendees': [
            {'email': to_email},
        ],
    }
 
    # Insert the event into the Google Calendar
    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f'Event created: {event.get("htmlLink")}')

def reassign_entity():
    conn, cursor = connect_to_database()
    cursor = conn.cursor()

    # Fetching task_entity_id from session instead of the form
    task_entity_id = session.get('entity_id')
    task_user_id = session.get('user_id')

    success_message = None  # Initialize success_message
    error_message = None    # Initialize error_message

    if not task_entity_id:
        return "Entity ID not found in session", 400

    # Fetching unique Factory IDs based on task_entity_id
    cursor.execute("SELECT DISTINCT entity_id FROM entity_regulation WHERE entity_id = %s", (task_entity_id,))
    factories = cursor.fetchall()

    # Default empty values for dropdowns that depend on other selections
    regulation_ids = []
    activities = []
    due_dates = []
    users = []

    # Capture values from the form
    assignTo = request.args.get('assignTo', '')
    reviewer = request.args.get('reviewer', '')
    regulation_id = request.args.get('regulationID', '')
    due_on = request.args.get('dueTo', '')  # Capture the selected due date
    user_id = request.args.get('userID', '')  # Capture the selected user ID
    activity_description = request.args.get('activity', '')  # Capture selected activity description

    print(f"Selected Due Date: {due_on}")  # Debugging

    # Fetch users based on the task_entity_id from the session
    if task_entity_id:
        cursor.execute("""
            SELECT user_id, email_id
            FROM users
            WHERE entity_id = %s
        """, (task_entity_id,))
        users = cursor.fetchall()

    # Fetch Reassign To and Review Reassign To User IDs based on task_entity_id
    reassignto = []
    review_reassignto = []
    if task_entity_id:
        cursor.execute("""
            SELECT user_id, email_id
            FROM users
            WHERE entity_id = %s
        """, (task_entity_id,))
        reassignto = cursor.fetchall()

        cursor.execute("""
            SELECT user_id, email_id
            FROM users
            WHERE entity_id = %s
        """, (task_entity_id,))
        review_reassignto = cursor.fetchall()

    # Fetch Regulation IDs based on user_id and preparation_responsibility
    if user_id:
        cursor.execute("""
            SELECT DISTINCT regulation_id
            FROM entity_regulation_tasks
            WHERE preparation_responsibility = %s
        """, (user_id,))
        regulation_ids = cursor.fetchall()

    # Fetch activity descriptions based on selected user_id and regulation_id
    if user_id and regulation_id:
        cursor.execute("""
            SELECT DISTINCT rc.activity_description
            FROM activity_master rc
            INNER JOIN entity_regulation_tasks fram
                ON rc.regulation_id = fram.regulation_id
                AND rc.activity_id = fram.activity_id
            WHERE fram.preparation_responsibility = %s
            AND fram.regulation_id = %s
        """, (user_id, regulation_id))
        activities = cursor.fetchall()

    # Fetch due_on values based on user_id, regulation_id, and activity_description
    if user_id and regulation_id and activity_description:
        cursor.execute("""
            SELECT DISTINCT due_on
            FROM entity_regulation_tasks fram
            INNER JOIN activity_master rc
                ON fram.regulation_id = rc.regulation_id
                AND fram.activity_id = rc.activity_id
            WHERE fram.preparation_responsibility = %s
            AND fram.regulation_id = %s
            AND rc.activity_description = %s
            AND fram.status IN ('Yet to Start', 'WIP')
        """, (user_id, regulation_id, activity_description))
        due_dates = cursor.fetchall()

    # If both assignTo, reviewer, and due_on are provided, perform the update and send emails
    if assignTo and reviewer and due_on:
        # Fetch current values for logging
        cursor.execute("""
            SELECT preparation_responsibility, review_responsibility
            FROM entity_regulation_tasks
            WHERE regulation_id = %s AND due_on = %s
        """, (regulation_id, due_on))
        current_values = cursor.fetchone()

        previous_values = f"Preparation Responsibility: {current_values[0]}, Review Responsibility: {current_values[1]}" if current_values else "N/A"

        try:
            # Update the responsibility in the database
            cursor.execute("""
                UPDATE entity_regulation_tasks
                SET preparation_responsibility = %s, review_responsibility = %s
                WHERE regulation_id = %s AND due_on = %s
            """, (assignTo, reviewer, regulation_id, due_on))
            conn.commit()

           
            # Get email IDs for assignTo and reviewer
            cursor.execute("SELECT email_id FROM users WHERE user_id = %s", (assignTo,))
            assign_to_email = cursor.fetchone()[0]
            cursor.execute("SELECT email_id FROM users WHERE user_id = %s", (reviewer,))
            reviewer_email = cursor.fetchone()[0]

            # Send email to Reassign To and Review Reassign To
            send_email(
                activity_description,
                assign_to_email,
                f"""
                Hello,

                A new task has been reassigned to you.

                Task Name: {activity_description}
                Factory ID: {task_entity_id}
                Regulation ID: {regulation_id}
                Assigned To: {assignTo}
                Reviewer: {reviewer}
                Due On: {due_on}

                Please take the necessary action.

                Regards,
                Your Team
                """
            )

            send_email(
                activity_description,
                reviewer_email,
                f"""
                Hello,

                A task review has been reassigned to you.

                Task Name: {activity_description}
                Factory ID: {task_entity_id}
                Regulation ID: {regulation_id}
                Assigned To: {assignTo}
                Reviewer: {reviewer}
                Due On: {due_on}

                Please take the necessary action.

                Regards,
                Your Team
                """
            )

            # Schedule Google Calendar event
            ccreate_calendar_event("Task Reassigned", due_on, assign_to_email)
            ccreate_calendar_event("Task Review Reassigned", due_on, reviewer_email)

            # Flash a success message
            success_message = 'Task successfully reassigned!'
        except Exception as e:
            error_message = f'Error in reassigning task: {str(e)}'
            

    cursor.close()
    conn.close()

    return render_template(
        'entity/reassign_task.html',
        factories=factories,
        users=users,
        regulations=regulation_ids,
        activities=activities,
        due_dates=due_dates,
        reassignto=reassignto,
        review_reassignto=review_reassignto,
        selected_due_on=due_on,  # Ensure due date is passed back to the template
        success_message=success_message,
        error_message=error_message,
        task_entity_id=task_entity_id,
        task_user_id=task_user_id
    )
#---------------------------------------------------------------------------------------------------------------------------------------------------


#------------------------------------logout------------------------------------------------------------------------------------------------

def logout_entity():
    # Fetch user details from session
    user_id = session.get('user_id')
    user_name = session.get('user_name')

    # Clear the user session
    session.pop('user_id', None)
    session.pop('entity_id', None)
    session.pop('user_name', None)

    # Redirect to the login page
    return redirect(url_for('index'))


#-------------------------------------------Assign task-----------------------------------------------------------------------------------------------------

def assign_task_entity():
    # Fetching session data
    task_entity_id = session.get('entity_id')
    user_id = session.get('user_id')
    
    # Directly pass task_entity_id and user_id from session
    return render_template('entity/assign_task.html', task_entity_id=task_entity_id, user_id=user_id)

def users_entity(entity_id):
    if not entity_id:
        return jsonify([])  # No entity_id provided, return empty list
    
    print(f"Fetching users for entity_id: {entity_id}")  # Debugging message

    try:
        users = get_users(entity_id)  # Make sure this function is properly defined and fetching the data
        if users:
            print(f"Fetched {len(users)} users")  # Debugging message
            return jsonify([{'user_id': user[0], 'user_name': user[1]} for user in users])
        else:
            print("No users found")  # Debugging message
            return jsonify([])
    except Exception as e:
        print(f"Error fetching users: {e}")  # Log the error
        return jsonify([])  # Return an empty list on error

def fetch_regulations_entity():
    task_entity_id = session.get('entity_id')
    if not task_entity_id:
        return jsonify([])  # Return an empty list if entity_id is not in the session

    print(f"Received entity_id from session: {task_entity_id}")  # Debugging statement
    regulations = get_regulations(task_entity_id)
    return jsonify(regulations)

def regulations_entity(entity_id):
    regulations = get_regulations(entity_id)  # Call the function from lib.py
    return jsonify(regulations)

def regulation_name_entity(regulation_id):
    regulation = get_regulation_name(regulation_id)  # Call the function from lib.py
    return jsonify(regulation)

def category_type_entity(regulation_id):
    category = get_category_type(regulation_id)  # Call the function from lib.py
    return jsonify(category)

def activities_entity(regulation_id):
    activities = get_activities(regulation_id)  # Call the function from lib.py
    return jsonify(activities)

def frequency_entity(regulation_id, activity_id):
    frequency = get_frequency(regulation_id, activity_id)  # Call the function from lib.py
    return jsonify(frequency)

def due_on_entity(regulation_id, activity_id):
    due_on = get_due_on(regulation_id, activity_id)  # Call the function from lib.py
    return jsonify(due_on)
 

def adjust_due_dates_with_holidays(cursor, due_dates):
    """Adjusts each due date by checking for weekends and holidays."""
    print("Starting due date adjustment.")  # Debug

    adjusted_due_dates = []
    
    for due_date in due_dates:
        print(f"Checking due date: {due_date}")  # Log current due date being checked
        
        while True:
            try:
                # Check if the due_date is a weekend (Saturday or Sunday)
                if due_date.weekday() == 5:  # Saturday
                    due_date -= relativedelta(days=1)  # Move to Friday
                    print(f"Adjusted due date to {due_date} because it's a Saturday")
                elif due_date.weekday() == 6:  # Sunday
                    due_date -= relativedelta(days=2)  # Move to Friday
                    print(f"Adjusted due date to {due_date} because it's a Sunday")

                # Check if the due_date is a holiday
                cursor.execute("SELECT COUNT(*) as holiday_count FROM holiday_master WHERE Holiday_Date = %s", (due_date,))
                result = cursor.fetchone()
                print(f"SQL Query Result for {due_date}: {result}")  # Debug: print the raw result

                if result is None:
                    raise ValueError(f"No result returned for due_date {due_date}")
                
                # Access the result using the dictionary key
                is_holiday = result['holiday_count']
                print(f"Is {due_date} a holiday? {'Yes' if is_holiday else 'No'}")  # Log result of holiday check

                if is_holiday:
                    # If it's a holiday, adjust the due date by moving it to the previous working day
                    due_date -= relativedelta(days=1)
                    print(f"Adjusted due date to {due_date} because of holiday")
                else:
                    # If it's not a holiday or weekend, add the due date to the adjusted list
                    adjusted_due_dates.append(due_date)
                    break

            except mysql.connector.Error as err:
                print(f"MySQL Error: {err}")
                raise  # Re-raise the error after logging it for deeper inspection
            
            except Exception as e:
                print(f"Error adjusting due dates: {e}")
                raise  # Re-raise the error to get full stack trace

    print(f"Final adjusted due dates: {adjusted_due_dates}")  # Log final adjusted due dates
    return adjusted_due_dates


def submit_form_entity():
    conn, cursor = connect_to_database()
    error_message = None
    success_message = None
 
    # Fetch the task_entity_id from session
    task_entity_id = session.get('entity_id')
    if not task_entity_id:
        error_message = "Entity ID not found in session"
       
        return render_template('Entity/assign_task.html', error_message=error_message)
    user_id = session.get('user_id')
 
    if conn is not None:
        cursor = conn.cursor(dictionary=True)
        try:
            # Step 1: Fetch form data
            factory_id = task_entity_id
            regulation_id = request.form.get('regulationID')
            activity_id = request.form.get('taskName')
            due_on_str = request.form.get('Due_on')
            assign_to = request.form.get('Assign_to')
            reviewer = request.form.get('Reviewer')

            

            # Fetch the regulations for the session entity_id to repopulate after form submission
            regulations = get_regulations(factory_id)

            print(f"Form Data: factory_id={factory_id}, regulation_id={regulation_id}, activity_id={activity_id}, due_on={due_on_str}, assign_to={assign_to}, reviewer={reviewer}")

            # Step 2: Parse due_on date
            try:
                due_on = datetime.strptime(due_on_str, '%Y-%m-%d').date()
                print(f"Parsed due_on: {due_on}")
            except ValueError as e:
                error_message = f"Invalid date format for 'Due_on': {due_on_str}. Error: {str(e)}"
               
                print(error_message)
                return render_template('Entity/assign_task.html', error_message=error_message, regulations=regulations, task_entity_id=task_entity_id, user_id=user_id)
            
            # Step 3: Check if the task already exists for the given entity_id, regulation_id, and activity_id (ignoring due date)
            cursor.execute("""
                SELECT COUNT(*) as task_count FROM entity_regulation_tasks
                WHERE entity_id = %s AND regulation_id = %s AND activity_id = %s
            """, (factory_id, regulation_id, activity_id))
            task_exists = cursor.fetchone()['task_count']

            if task_exists > 0:
                # If any task already exists, return an error message and stop the process
                error_message = "A task for this regulation and activity is already assigned."
                
                print(error_message)
                return render_template('Entity/assign_task.html', error_message=error_message, task_entity_id=task_entity_id, user_id=user_id, regulations=regulations)

            # Step 4: Fetch activity details, including frequency_timeline
            cursor.execute("""
                SELECT activity, frequency_timeline, frequency, ews, criticality, mandatory_optional, documentupload_yes_no
                FROM activity_master
                WHERE activity_id = %s AND regulation_id = %s
            """, (activity_id, regulation_id))

            activity_result = cursor.fetchone()

            if not activity_result:
                error_message = "Failed to fetch activity details."
                
                print(error_message)
                return render_template('Entity/assign_task.html', error_message=error_message, task_entity_id=task_entity_id, user_id=user_id)

            # Assign the values from the fetched result
            activity_name = activity_result['activity']
            frequency_timeline = activity_result['frequency_timeline']
            frequency = activity_result['frequency']
            ews = activity_result['ews']
            criticality = activity_result['criticality']
            mandatory_optional = activity_result['mandatory_optional']
            documentupload_yes_no = activity_result['documentupload_yes_no']

            print(f"Activity details: {activity_name}, Frequency Timeline: {frequency_timeline}, Frequency: {frequency}, EWS: {ews}, Criticality: {criticality}, Mandatory/Optional: {mandatory_optional}")

            # Fetch `internal_external` from `regulation_master` based on `regulation_id`
            cursor.execute("""
                SELECT internal_external FROM regulation_master
                WHERE regulation_id = %s
            """, (regulation_id,))
            regulation_result = cursor.fetchone()

            if not regulation_result:
                error_message = f"Failed to fetch internal/external for regulation_id {regulation_id}."
                
                print(error_message)
                return render_template('Entity/assign_task.html', error_message=error_message, task_entity_id=task_entity_id, user_id=user_id, regulations=regulations)

            internal_external = regulation_result['internal_external']
            print(f"Regulation details: Internal/External = {internal_external}")

            # Step 5: Fetch assignee and reviewer details
            cursor.execute("SELECT email_id, user_name FROM users WHERE user_id = %s", (assign_to,))
            assignee_info = cursor.fetchone()
            cursor.fetchall()  # Consume any unread results
            cursor.execute("SELECT email_id, user_name FROM users WHERE user_id = %s", (reviewer,))
            reviewer_info = cursor.fetchone()
            cursor.fetchall()  # Consume any unread results

            if not assignee_info or not reviewer_info:
                error_message = "Failed to fetch email or name for assignee or reviewer."
               
                print(error_message)
                return render_template('Entity/assign_task.html', error_message=error_message, task_entity_id=task_entity_id, user_id=user_id)

            print(f"Assignee: {assignee_info['user_name']}, Reviewer: {reviewer_info['user_name']}")

            # Step 7: Calculate due dates starting from frequency timeline
            print(f"Frequency timeline: {frequency_timeline}, current date: {datetime.now().date()}")
            current_due_on = frequency_timeline

            # End of the next year limit for due dates
            end_of_next_year = datetime(datetime.now().year + 1, 12, 31).date()

            # List to hold valid due dates
            due_dates = []
            
            # Case 1: If the frequency is 0 (one-time task)
            if frequency == 0:
                # If frequency is 0, we only need the due date to be the frequency_timeline
                due_dates.append(frequency_timeline)
                print(f"Frequency is 0, one-time task. Due date is {frequency_timeline}")

            # Case 2: If the frequency_timeline is in the future and frequency > 0
            elif frequency_timeline >= datetime.now().date():
                due_dates.append(frequency_timeline)
                print(f"First due date based on future frequency timeline: {frequency_timeline}")

            # Case 3: If the frequency_timeline is in the past and frequency > 0
            else:
                # Skip past dates by incrementing based on the frequency
                while current_due_on < datetime.now().date():
                    current_due_on += {
                        52: relativedelta(weeks=1),
                        12: relativedelta(months=1),
                        4: relativedelta(months=3),
                        2: relativedelta(months=6),
                        1: relativedelta(years=1),
                        3: relativedelta(months=4),
                        6: relativedelta(months=2),
                        26: relativedelta(weeks=2),
                        365: relativedelta(days=1)
                    }.get(frequency, relativedelta(years=1))

                # Add the next valid due date
                if current_due_on >= datetime.now().date():
                    due_dates.append(current_due_on)
                    print(f"First valid future due date after skipping past dates: {current_due_on}")

            # Generate subsequent due dates if frequency is > 0
            if frequency > 0:
                iteration_count = 0
                while current_due_on <= end_of_next_year:
                    current_due_on += {
                        52: relativedelta(weeks=1),
                        12: relativedelta(months=1),
                        4: relativedelta(months=3),
                        2: relativedelta(months=6),
                        1: relativedelta(years=1),
                        3: relativedelta(months=4),
                        6: relativedelta(months=2),
                        26: relativedelta(weeks=2),
                        365: relativedelta(days=1)
                    }.get(frequency, relativedelta(years=1))

                    if current_due_on <= end_of_next_year and current_due_on >= datetime.now().date():
                        due_dates.append(current_due_on)
                        print(f"Generated subsequent due date: {current_due_on}")

                    iteration_count += 1
                    if iteration_count > 1000:
                        print("Loop exceeded safe iteration count. Breaking loop to prevent infinite loop.")
                        break

            print("Starting due date adjustment.")
            due_dates = adjust_due_dates_with_holidays(cursor, due_dates)
            print(f"Adjusted due dates: {due_dates}")

            # Step 8: Insert tasks and schedule reminders for each due date
            for adjusted_due_on in due_dates:
                cursor.execute("""
                    INSERT INTO entity_regulation_tasks
                    (entity_id, regulation_id, activity_id, due_on, preparation_responsibility, review_responsibility, 
                     status, ews, criticality, internal_external, mandatory_optional, documentupload_yes_no)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (factory_id, regulation_id, activity_id, adjusted_due_on.strftime('%Y-%m-%d'), assign_to, reviewer, "Yet to Start", ews, criticality, internal_external, mandatory_optional, documentupload_yes_no))
                conn.commit()

                # Schedule reminders
                reminder_date = adjusted_due_on - relativedelta(days=ews) if ews is not None else adjusted_due_on
                cursor.execute("""
                    INSERT INTO message_queue (message_des, date, time, email_id, status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (f"Reminder: The task '{activity_name}' for regulation '{regulation_id}' is due on {adjusted_due_on.strftime('%Y-%m-%d')}.", reminder_date.strftime('%Y-%m-%d'), "09:00:00", assignee_info['email_id'], "Scheduled"))
                cursor.execute("""
                    INSERT INTO message_queue (message_des, date, time, email_id, status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (f"Reminder: The task '{activity_name}' for regulation '{regulation_id}' is due on {adjusted_due_on.strftime('%Y-%m-%d')}.", reminder_date.strftime('%Y-%m-%d'), "09:00:00", reviewer_info['email_id'], "Scheduled"))
                conn.commit()

                # Send the assignment email for the first due date only
                if adjusted_due_on == due_on:
                    text_assigned = f"""
                    Hello,
                    A new task has been assigned to you.
                    Task Name: {activity_name}
                    Factory ID: {factory_id}
                    Regulation ID: {regulation_id}
                    Assigned To: {assignee_info['user_name']}
                    Reviewer: {reviewer_info['user_name']}
                    Due On: {adjusted_due_on.strftime('%Y-%m-%d')}
                    {get_frequency_description(frequency)}

                    Please take the necessary action.
                    Regards, Your Team
                    """
                    msg = Message("New Task Assigned", recipients=[assignee_info['email_id'], reviewer_info['email_id']], body=text_assigned)
                    try:
                        mail.send(msg)
                        print(f"Assignment email sent to {assignee_info['email_id']}, {reviewer_info['email_id']} for task due on {adjusted_due_on.strftime('%Y-%m-%d')}")
                        success_message = f"Task assigned successfully and email sent to {assignee_info['user_name']} and {reviewer_info['user_name']}."
                    except Exception as e:
                        print(f"Failed to send assignment email: {e}")
                        error_message = "Task assigned, but failed to send email notification."

                # Schedule calendar events
                try:
                    schedule_calendar_events(activity_name=activity_name, due_on=adjusted_due_on, assignee_email=assignee_info['email_id'], reviewer_email=reviewer_info['email_id'])
                    print(f"Calendar events scheduled for task: {activity_name}.")
                except Exception as e:
                    print(f"Failed to schedule calendar events: {e}")

                
            success_message = "Tasks created successfully for all due dates."
            print(success_message)

        except mysql.connector.IntegrityError as e:
            print(f"Integrity Error: {str(e)}")
        
            error_message = "Failed to submit form data: " + str(e)

        except Exception as e:
            print(f"Failed to submit form data: {e}")
           

            error_message = "Error processing your request."


        finally:
            cursor.close()
            conn.close()
    else:
      

        error_message = "Failed to connect to the database."

    return render_template('Entity/assign_task.html', error_message=error_message, success_message=success_message, task_entity_id=task_entity_id, user_id=user_id)

# Setting up the scheduler to run `send_scheduled_emails` every minute
scheduler = BackgroundScheduler()
scheduler.add_job(func=lambda: send_scheduled_emails(app, mail, connect_to_database), trigger="interval", seconds=60)
scheduler.add_job(func=lambda: add_calendar_events_from_queue(connect_to_database, create_calendar_event), trigger="interval", seconds=60)
scheduler.start()




 