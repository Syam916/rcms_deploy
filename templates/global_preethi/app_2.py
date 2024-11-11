from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import mysql.connector
from mysql.connector import errorcode
from datetime import date, timedelta, datetime
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import smtplib
import random
import bcrypt
import threading
import re
import time
from mysql.connector import Error
from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.relativedelta import relativedelta
from wtforms.validators import DataRequired
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pymysql
import mysql.connector
from google.oauth2.credentials import Credentials
import logging
# from python_functions.lib import  get_regulations,get_frequency_description,create_calendar_event, schedule_calendar_events,send_scheduled_emails,add_calendar_events_from_queue,configure_mail

#from python_functions.global_entity_admin import admin_dashboard
#from python_functions.entity_admin import entity_dashboard_page
#from python_functions.entity_dashboard import *

from python_functions.Global.Global import *


from python_functions.Entity.entity import *

app = Flask(__name__)
app.secret_key = 'your_secret_key'

global_admin_dash_app=admin_dashboard(app)
dash_app_2=entity_dashboard_page(app)

# Database connection using mysql.connector
def connect_to_database():
    try:
        conn = mysql.connector.connect(
        host="rcms-database.cxyo004saqut.us-east-1.rds.amazonaws.com",
        user="Global_Admin",
        password="Globaladmin1",
        database="rcms"
        )
        cursor = conn.cursor(dictionary=True)  # This returns query results as dictionaries
        return conn, cursor
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None, None
    

#---------------------------------------------------------Login Page----------------------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('Global/login.html')

# Route to serve the popup page
@app.route('/get_popup')
def get_popup_main():
        return get_popup_main()

# Route to handle login
@app.route('/login', methods=['GET', 'POST'])
def login():
    return login_main()
#----------------------------------------------------------Forgot Password-----------------------------------------------------------------------------------------
def send_mail(to, subject, body):
    try:
        msg = Message(subject, recipients=[to])
        msg.body = body
        mail.send(msg)
        print("Email sent successfully.")  # Log the success of email sending
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
 
def send_otp_via_email(email, otp):
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_email = "vardaan.rcms@gmail.com"
        smtp_password = "aynlltagpthlzqgd"  # Replace with your actual password or environment variable
 
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            message = f"Subject: Password Reset OTP\n\nYour OTP for password reset is {otp}."
            server.sendmail(smtp_email, email, message)
            print("Email sent successfully.")
            return True
    except Exception as e:
        print(f"Failed to send OTP: {e}")
        return False
 
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    return forgot_password()
 
@app.route('/trigger_forgot_password', methods=['POST'])
def trigger_forgot_password():
    return trigger_forgot_password_main()
    
#-----------------------------------------------------------------Country Codes-----------------------------------------------------------------------------
# Fetching country codes from the database
def fetch_country_codes():
    conn, cursor = connect_to_database()
    cursor = conn.cursor(dictionary=True)  # dictionary=True to get rows as dicts
    cursor.execute("SELECT country, country_code ,country_short FROM country_codes")
    country_codes = cursor.fetchall()
    cursor.close()
    conn.close()
    return country_codes

# -------------------------------------------------------------fetching regulation names--------------------------------------------------------
# Fetching country codes from the database
def fetch_regulation_names():
    conn, cursor = connect_to_database()
    cursor = conn.cursor(dictionary=True)  # dictionary=True to get rows as dicts
    cursor.execute("SELECT regulation_name FROM regulation_master")
    regulation_names = cursor.fetchall()
    cursor.close()
    conn.close()
    return regulation_names

#---------------------------------------------------------------Global Admin---------------------------------------------------------------------------------   
# Route for global admin dashboard
@app.route('/global_admin_dashboard')
def global_admin_dashboard():
    return global_admin_dashboard_main()

#---------------------------------------------------------------Add Category--------------------------------------------------------------------------------
@app.route('/category')
def add_category_global():
    return add_category_main()
 
@app.route('/submit-category', methods=['POST'])
def submit_category_global():
    return submit_category_main()


#--------------------------------------------------------------Delete category-------------------------------------------------------#
@app.route('/display_main_categories')
def display_main_categories():
    return display_categories_main()
    

@app.route('/delete_main_category', methods=['POST'])
def delete_main_category():
    return delete_category_main()
#----------------------------------------------------------------Add Entity---------------------------------------------------------------------------------

@app.route('/entity', methods=['GET'])
def add_entity():
    return add_entity_main()

@app.route('/submit-entity', methods=['POST'])
def submit_entity():
    return submit_entity_main()

#--------------------------------Update entity-----------------------------------------------------------------------------------
# Route to render the update_entity.html page
@app.route('/update_entity_page')
def update_entity_page():
    return update_entity_page_main()

# Fetching all entities for the dropdown
@app.route('/get_entities', methods=['GET'])
def get_entities():
    return get_entities_main()
    
# Fetching entity details based on entity_id
@app.route('/get_entity_details/<entity_id>', methods=['GET'])
def get_entity_details(entity_id):
    return get_entity_details_main(entity_id)
    
# Updating the entity details
@app.route('/update_entity', methods=['POST'])
def update_entity():
    return update_entity_main()

#-----------------------------------------------------Delete Entity----------------------------------------------------------------------------------------
# Route to render the delete_entity.html page
@app.route('/delete_entity_page')
def delete_entity_page():
    return delete_entity_page_main()

# Fetching all entities for the dropdown
@app.route('/view_entities', methods=['GET'])
def view_entities():
    return get_entities_main()

# Fetching entity details based on entity_id (for deletion confirmation)
@app.route('/get_entity_details_for_delete/<entity_id>', methods=['GET'])
def get_entity_details_for_delete(entity_id):
    return get_entity_details_for_delete_main(entity_id)
    
# Route to delete an entity
@app.route('/delete_entity', methods=['POST'])
def delete_entity():
    return delete_entity_main()
    
#-------------------------------------------------------------Add Regulation-------------------------------------------------------------------------------
@app.route('/regulations')
def add_regulation_global():
    return add_regulation_global_main()


@app.route('/add-regulation', methods=['POST'])
def submit_regulation_main():
    return submit_regulation_main()

# ---------------------------Add entity regulation---------------------------------------------------------------------
@app.route('/add_entity_regulation')
def add_entity_regulation():
    categories = get_categories()  # This should trigger the print statements
    return render_template('entity/add_entity_regulation.html', categories=categories)

 
@app.route('/add_entity_regulation', methods=['POST'])
def submit_entity_regulation():
    factory_id=session['factory_id']
    regulation_name = request.form['regulationName']
    category_id = request.form['categoryID']
    regulatory_body = request.form['regulatoryBody']
    internal_external = request.form['internalExternal']
    national_international = request.form['nationalInternational']
    mandatory_optional = request.form['mandatoryOptional']
    effective_from = request.form['effectiveFrom']
    obsolete_current = request.form['obsoleteCurrent']
 
    conn, cursor = connect_to_database()
    error_message = None
    success_message = None
 
    if conn is not None:
        cursor = conn.cursor()
        try:
            # Check if the regulation name already exists
            cursor.execute("SELECT COUNT(*) FROM regulation_master WHERE regulation_name = %s", (regulation_name,))
            exists = cursor.fetchone()[0]
 
            if exists:
                error_message = f"Regulation with name '{regulation_name}' already exists."
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


                query="""

                    INSERT INTO entity_regulation 
                    (entity_id,regulation_id) VALUES(%s,%s)
                    """
                cursor.execute(query,(factory_id,regulation_id))
                conn.commit()
                success_message = f"Regulation successfully added with ID {regulation_id}."
        except Error as e:
            print(f"Failed to insert regulation: {e}")
            error_message = f"Failed to add regulation: {e}"
        finally:
            cursor.close()
            conn.close()
    else:
        error_message = "Failed to connect to the database."
 
    categories = get_categories()
    return render_template('Entity/add_entity_regulation.html', error_message=error_message, success_message=success_message, categories=categories)



# --------------------------------------manage entity regulations---------------------------------------------------------------------
@app.route('/manage_entity_regulation')
def manage_entity_regulation():
    conn, cursor = connect_to_database()
    cursor.execute("SELECT regulation_name FROM regulation_master")
    regulations = [row['regulation_name'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    return render_template('entity/manage_entity_regulation.html', regulations=regulations)



# --------------------------------------------------manage_entity_submit_regulation---------------------------------------------------------------------------------------
 
@app.route('/manage_entity_submit_regulation', methods=['POST'])
def manage_entity_submit_regulation():
    conn, cursor = connect_to_database()
    error_message = None
    success_message = None
    factory_id=session['factory_id']

    # Capture form data


    
   
    selected_regulations = request.form.get('selected_regulations')  # Get the selected regulations


    
    # Validate required fields
    if not selected_regulations:
        error_message = "you have select atleast one regulation"
        return render_template('Entity/manage_entity_regulation.html', error_message=error_message)

    if conn is not None:
        cursor = conn.cursor()
        try:

   
            # Handle selected regulations
            selected_regulations = request.form.get('selected_regulations')  # Get the selected regulations as a string
            regulation_names = [reg.strip() for reg in selected_regulations.split(',')]  # Split and clean the regulation names


            for regulation_name in regulation_names:
                # Get the regulation_id from regulation_master table
                cursor.execute("SELECT regulation_id FROM regulation_master WHERE regulation_name = %s", (regulation_name,))
                regulation_id = cursor.fetchone()

                if regulation_id:
                    regulation_id = regulation_id[0]  # Get the regulation_id

                    print('regulation name is',regulation_name,'-------------------',regulation_id)

                    # Get the count of mandatory and optional activities from regulation_checklist table
                    cursor.execute("""
                        SELECT COUNT(*) FROM regulation_checklist WHERE regulation_id = %s AND mandatory_optional = 'M'
                    """, (regulation_id,))
                    mandatory_activities = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT COUNT(*) FROM regulation_checklist WHERE regulation_id = %s AND mandatory_optional = 'O'
                    """, (regulation_id,))
                    optional_activities = cursor.fetchone()[0]

                    # Insert into factory_regulation table with factory_id, regulation_id, mandatory_activities, and optional_activities
                    cursor.execute("""
                        INSERT INTO factory_regulation (factory_id, regulation_id, mandatory_activities, optional_activities)
                        VALUES (%s, %s, %s, %s)
                    """, (factory_id, regulation_id, mandatory_activities, optional_activities))
                else:
                    print(f"Regulation '{regulation_name}' not found in regulation_master.")
 
                

                conn.commit()

                success_message = f"Regulations successfully added in {factory_id}."

        except mysql.connector.IntegrityError as e:
            error_message = f"Failed to submit entity data! MySQL Error: {str(e)}"
            print(error_message)

        except Exception as e:
            error_message = f"An error occurred while processing your request: {str(e)}"
            print(error_message)
        finally:
            cursor.close()
            conn.close()
    else:
        error_message = "Failed to connect to the database."

    return render_template('Entity/manage_entity_regulation.html', error_message=error_message, success_message=success_message, country_codes=fetch_country_codes())




#-------------------------------------------Update regulation----------------------------------------------------------#
# Route to serve the edit regulation page
@app.route('/edit_main_regulation_page', methods=['GET'])
def edit_main_regulation_page():
    return edit_regulation_page_main()
    
# Route to fetch regulation details
@app.route('/fetch_main_regulation', methods=['POST'])
def fetch_main_regulation():
    return fetch_regulation_main()
    
# Route to update regulation details
@app.route('/update_main_regulation', methods=['POST'])
def update_main_regulation():
    return update_regulation_main()

#----------------------------------------------------Delete regulations----------------------------------------------------------#
# Route to serve the delete regulations page
@app.route('/delete_main_regulations_page')
def delete_main_regulations_page():
    return delete_regulations_page_main()
    
# Route to fetch categories for the dropdown
@app.route('/fetch_main_categories')
def fetch_main_categories():
    return fetch_categories_main()
   
# Route to fetch regulations based on category_id and entity_id
@app.route('/load_main_regulations/<category_id>', methods=['GET'])
def load_main_regulations(category_id):
    return load_regulations_main(category_id)

# Route to delete regulations
@app.route('/delete_main_regulations', methods=['POST'])
def delete_main_regulations():
    return delete_regulations_main()

#--------------------------------------------------------------Add Activity--------------------------------------------------------------------------
@app.route('/activity')
def add_activity_global():
    return add_activity_main()

@app.route('/checklists/get-regulation-id/<regulation_name>')
def get_regulation_id(regulation_name):
    conn, cursor = connect_to_database()
    if conn is not None:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT regulation_id FROM regulation_master WHERE regulation_name = %s", (regulation_name,))
            result = cursor.fetchone()
            return jsonify({'regulation_id': result[0] if result else ''})
        except Error as e:
            print(f"Failed to query regulation ID: {e}")
            return jsonify({'regulation_id': ''})
        finally:
            cursor.close()
            conn.close()
    return jsonify({'regulation_id': ''})
 
@app.route('/submit-checklist', methods=['POST'])
def submit_checklist():
    return submit_checklist_main()
#-------------------------------------------------Update activity----------------------------------------------------------------------------#
@app.route('/update_main_activities_page')
def update_main_activities_page():
    return update_activities_page_main()
    
@app.route('/update_main_activities_page/populate_main_activities/<regulation_id>')
def populate_main_activities(regulation_id):
    return populate_activities_main(regulation_id)
    
@app.route('/update_main_activities_page/get_main_activity_details/<regulation_id>/<activity_id>')
def get_main_activity_details(regulation_id, activity_id):
    return get_activity_details_entity(regulation_id,activity_id)
    
@app.route('/update_main_activity', methods=['POST'])
def update_main_activity():
    return update_activity_main()

#-----------------------------------------Delete Activity----------------------------------------------------------------------------------------
# Route to render the delete activities page (HTML template)
@app.route('/delete_main_activities_page')
def delete_main_activities_page():
    return delete_activities_page_main()
    
# Route to load regulations directly without categories
@app.route('/populate_main_regulations', methods=['GET'])
def populate_main_regulations():
    return populate_regulations_main()
    
# Route to fetch activities based on regulation_id
@app.route('/load_main_activities/<regulation_id>', methods=['GET'])
def load_main_activities(regulation_id):
    return load_activities_main(regulation_id)
    
# Route to delete activities
@app.route('/delete_main_activities', methods=['POST'])
def delete_main_activities():
    return delete_activities_main()











#---------------------------------------------------------------Entity Admin--------------------------------------------------------------------------------   
# Route for entity admin dashboard
@app.route('/entity_admin_dashboard')
def entity_admin_dashboard():
    return entity_admin_dashboard_entity()

    
#--------------------------------------------------------------------Add User--------------------------------------------------------------------------------
@app.route('/admin/add_entity_user', methods=['GET', 'POST'])
def add_entity_user():
    return add_user_entity()
    
#--------------------------------------------------------------Update User----------------------------------------------------------------------------
# Route to fetch user details based on user_id
@app.route('/load_entity_user/<user_id>', methods=['GET'])
def load_entity_user(user_id):
    return load_user_entity(user_id)

# Route to update user details
@app.route('/update_entity_user', methods=['POST'])
def update_entity_user():
    return update_user_entity()
    
# Route to render the update user template
@app.route('/update_entity_user_page')
def update_entity_user_page():
    return update_user_page_entity()
    
#-------------------------------------------------------------------Delete User----------------------------------------------------------------
# Route to fetch user details based on user_id
@app.route('/fetch_entity_user/<user_id>', methods=['GET'])
def fetch_entity_user(user_id):
    return fetch_user_entity(user_id)

# Route to delete user
@app.route('/delete_entity_user', methods=['POST'])
def delete_entity_user():
    return delete_user_entity()

# Route to render the delete user template
@app.route('/delete_entity_user_page')
def delete_entity_user_page():
    return delete_user_page_entity()
    
#---------------------------------------------------------------Add Category--------------------------------------------------------------------------------
@app.route('/category')
def add_entity_category():
    return add_category_entity()
 
@app.route('/submit_entity_category', methods=['POST'])
def submit_entity_category():
    return submit_category_entity()
    
#--------------------------------------------------------------Delete Category---------------------------------------------------------------------------------
# Make 'enumerate' available in the template context
@app.context_processor
def utility_processor():
    return dict(enumerate=enumerate)

@app.route('/display_entity_categories')
def display_entity_categories():
    return display_categories_entity()
    

@app.route('/delete_entity_category', methods=['POST'])
def delete_entity_category():
    return delete_category_entity()
    
#-------------------------------------------------------------Add Regulation-------------------------------------------------------------------------------
# @app.route('/regulations')
# def add_entity_regulation():
#     return add_regulation_entity()
     
# @app.route('/add-regulation', methods=['POST'])
# def submit_entity_regulation():
#     return submit_regulation_entity()
    
#---------------------------------------------------------Update regulation--------------------------------------------------------
# Route to serve the edit regulation page
@app.route('/edit_entity_regulation_page', methods=['GET'])
def edit_entity_regulation_page():
    return edit_regulation_page_entity()
    
# Route to fetch regulation details
@app.route('/fetch_entity_regulation', methods=['POST'])
def fetch_entity_regulation():
    return fetch_regulation_entity()
    
# Route to update regulation details
@app.route('/update_entity_regulation', methods=['POST'])
def update_entity_regulation():
    return update_regulation_entity()
    
#-----------------------------------------------------------Delete Regulation----------------------------------------------
# Route to serve the delete regulations page
@app.route('/delete_entity_regulations_page')
def delete_entity_regulations_page():
    return delete_regulations_page_entity()
    
# Route to fetch categories for the dropdown
@app.route('/fetch_entity_categories')
def fetch_entity_categories():
    return fetch_categories_entity()
   
# Route to fetch regulations based on category_id and entity_id
@app.route('/load_entity_regulations/<category_id>', methods=['GET'])
def load_entity_regulations(category_id):
    return load_regulations_entity(category_id)

# Route to delete regulations
@app.route('/delete_entity_regulations', methods=['POST'])
def delete_entity_regulations():
    return delete_regulations_entity()
    
#--------------------------------------------------------------Add Activity--------------------------------------------------------------------------
@app.route('/activity')
def add_entity_activity():
    return add_activity_entity()
    
@app.route('/checklists/get_entity_regulation_id/<regulation_name>')
def get_entity_regulation_id(regulation_name):
    return get_regulation_id_entity(regulation_name)
 
@app.route('/submit_entity_checklist', methods=['POST'])
def submit_entity_checklist():
    return submit_checklist_entity()
    
#---------------------------------------------------------Modify Activity-----------------------------------------------------------------
@app.route('/update_entity_activities_page')
def update_entity_activities_page():
    return update_activities_page_entity()
    
@app.route('/update_entity_activities_page/populate_entity_activities/<regulation_id>')
def populate_entity_activities(regulation_id):
    return populate_activities_entity(regulation_id)
    
@app.route('/update_entity_activities_page/get_entity_activity_details/<regulation_id>/<activity_id>')
def get_entity_activity_details(regulation_id, activity_id):
    return get_activity_details_entity(regulation_id,activity_id)
    
@app.route('/update_entity_activity', methods=['POST'])
def update_entity_activity():
    return update_activity_entity()
    
#-------------------------------------------------------------Delete Activity-------------------------------------------------------------
# Route to render the delete activities page (HTML template)
@app.route('/delete_entity_activities_page')
def delete_entity_activities_page():
    return delete_activities_page_entity()
    
# Route to load regulations directly without categories
@app.route('/populate_entity_regulations', methods=['GET'])
def populate_entity_regulations():
    return populate_regulations_entity()
    
# Route to fetch activities based on regulation_id
@app.route('/load_entity_activities/<regulation_id>', methods=['GET'])
def load_entity_activities(regulation_id):
    return load_activities_entity(regulation_id)
    
# Route to delete activities
@app.route('/delete_entity_activities', methods=['POST'])
def delete_entity_activities():
    return delete_activities_entity()
    
#----------------------------------------------------------------Add Holiday--------------------------------------------------------------------------------
@app.route('/add-holiday', methods=['GET', 'POST'])
def add_holiday():
    return add_holiday_entity()
    
#----------------------------------------------------------Delete Holiday-----------------------------------------------------------------------
# Route to render the delete holidays page
@app.route('/delete_holidays_page')
def delete_holidays_page():
    return delete_holidays_page_entity()
    
# Route to fetch holidays
@app.route('/fetch_holidays')
def fetch_holidays():
    return fetch_holidays_entity()

# Route to delete holidays
@app.route('/delete_holidays', methods=['POST'])
def delete_holidays():
    return delete_holidays_entity()
    
#----------------------------------------------------------------Assign Task--------------------------------------------------------------------------------
mail = configure_mail(app)

@app.route('/admin/assign_task')
def assign_task():
    return assign_task_entity()
 
@app.route('/admin/assign_task/get-users/<entity_id>')
def users(entity_id):
    return users_entity(entity_id)

@app.route('/admin/assign_task/get-regulations')
def fetch_regulations():
    return fetch_regulation_entity()
 
@app.route('/admin/assign_task/get-regulations/<entity_id>')
def regulations(entity_id):
    return regulations_entity(entity_id)
 
@app.route('/admin/assign_task/get-regulation-name/<regulation_id>')
def regulation_name(regulation_id):
    return regulation_name_entity(regulation_id)
 
@app.route('/admin/assign_task/get-category-type/<regulation_id>')
def category_type(regulation_id):
    return category_type_entity(regulation_id)
    
@app.route('/admin/assign_task/get-activities/<regulation_id>')
def activities(regulation_id):
    return activities_entity(regulation_id)
    
@app.route('/admin/assign_task/get-frequency/<regulation_id>/<activity_id>')
def frequency(regulation_id, activity_id):
    return frequency_entity(regulation_id,activity_id)
    
@app.route('/admin/assign_task/get-due-on/<regulation_id>/<activity_id>')
def due_on(regulation_id, activity_id):
    return due_on_entity(regulation_id,activity_id)
    
@app.route('/submit-form', methods=['POST'])
def submit_form():
    return submit_form_entity()
 
#---------------------------------------------------------------Reassign Task------------------------------------------------------------------------------- 
@app.route('/reassign', methods=['GET', 'POST'])
def reassign():
    return reassign_entity()
    
@app.route('/logout')
def logout():
    return logout_entity()


if __name__ == '__main__':
    try:
        app.run(debug=True, use_reloader=False)
    finally:
        scheduler.shutdown()
