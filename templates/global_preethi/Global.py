from flask import  render_template, request, redirect, url_for, flash, jsonify, session
import mysql.connector
from flask_mail import  Message
import smtplib
import random
import bcrypt
import re
from mysql.connector import Error

from flask import Flask
from flask_mail import Mail

app = Flask(__name__)
# Configuration for Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'vardaan.rcms@gmail.com'
app.config['MAIL_PASSWORD'] = 'aynlltagpthlzqgd'  # Consider using environment variables for security
app.config['MAIL_DEFAULT_SENDER'] = 'vardaan.rcms@gmail.com'
mail = Mail(app)


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


# Route to serve the popup page

def get_popup_main():
    return render_template('popup.html')

# Route to handle login

def login_main():
    print('Entered login')
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        # Connect to the database
        conn, cursor = connect_to_database()

        if conn is None or cursor is None:
            flash('Database connection failed', 'error')
            return redirect(url_for('index'))

        try:
            # Query to get the user details based on user_id
            query = "SELECT * FROM users WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()
            # print(user)
            # input(user)

            if user:
                print(f"Fetched user data: {user}")  # Debugging output

                # Verify the password
                if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                    # Initialize session variables
                    session['user_id'] = user['user_id']
                    session['entity_id'] = user.get('entity_id')
                    session['user_name'] = user.get('user_name')

                    # Debugging output to ensure session variables are set
                    print(f"Session user_id: {session['user_id']}")
                    print(f"Session factory_id: {session['entity_id']}")
                    print(f"Session user_name: {session['user_name']}")

                    #flash('login_main successful!', 'success')

                    # Role-based redirection
                    if user['role'] == 'Global':
                        print("Redirecting to global admin page")
                        return redirect(url_for('global_admin_dashboard'))

                    elif user['role'] == 'Admin':
                        print("Redirecting to admin dashboard")
                        return redirect(url_for('entity_admin_dashboard'))

                    elif user['role'] == 'User':
                        print("Redirecting to user dashboard")
                        return redirect(url_for('entity_dashboard', factory_id=user['factory_id']))
                else:
                    flash('Invalid credentials, please try again.', 'error')
            else:
                flash('User not found.', 'error')

        except Exception as e:
            print(f'An error occurred: {str(e)}', 'error')
            flash(f'An error occurred: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

    # If the request method is GET or if authentication fails, render the login page
    return render_template('Global/login.html')
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
 

def forgot_password_main():
    if request.method == 'POST':
        step = request.form.get('step', 'verification')
 
        if step == 'verification':
            user_id = session.get('user_id')
            entered_otp = request.form['otp']
           
            # Debugging - print the stored and entered OTPs
            print(f"Stored OTP: {session.get('otp')}, Entered OTP: {entered_otp}")
 
            if 'otp' in session and session['otp'] == int(entered_otp):
                flash('OTP verified successfully. You can now reset your password.')
                return render_template('Global/forgot_password.html', step='reset')
            else:
                flash('Invalid OTP. Please try again.')
                return redirect(url_for('forgot_password'))
 
        elif step == 'reset':
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
 
            if new_password != confirm_password:
                flash('Passwords do not match. Please try again.')
                return render_template('Global/forgot_password.html', step='reset')
 
            # Hash the new password and update it in the database
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
 
            conn, cursor = connect_to_database()
            if conn is None or cursor is None:
                flash('Database connection failed!', 'error')
                return redirect(url_for('forgot_password'))
 
            cursor.execute("UPDATE users SET password = %s WHERE user_id = %s",
                           (hashed_password.decode('utf-8'), session['user_id']))
            conn.commit()
            cursor.close()
            conn.close()
 
            flash('Your password has been reset successfully.')
            session.pop('otp', None)
            session.pop('user_id', None)
            return redirect(url_for('login_main'))
 
    return render_template('Global/forgot_password.html', step='verification')
 

def trigger_forgot_password_main():
    # Get the user_id from the form
    user_id = request.form.get('user_id')
   
    if not user_id:
        flash('User ID is required', 'error')
        return redirect(url_for('login_main'))
 
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        flash('Database connection failed!', 'error')
        return redirect(url_for('login_main'))
 
    # Fetch the email associated with the user_id
    cursor.execute("SELECT email_id FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
 
    if user:
        # Generate and store OTP
        otp = random.randint(100000, 999999)
        session['otp'] = otp
        session['user_id'] = user_id
       
        # Send OTP via email
        email_sent = send_otp_via_email(user['email_id'], otp)
        if email_sent:
            flash(f'An OTP has been sent to {user["email_id"]}. Please enter it below.', 'success')
        else:
            flash('Failed to send OTP. Please try again.', 'error')
       
        cursor.close()
        conn.close()
        return redirect(url_for('forgot_password'))
    else:
        flash('User ID not found. Please try again.', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('login_main_main'))
    
#-----------------------------------------------------------------Country Codes-----------------------------------------------------------------------------
# Fetching country codes from the database
def fetch_country_codes():
    conn, cursor = connect_to_database()
    cursor = conn.cursor(dictionary=True)  # dictionary=True to get rows as dicts
    cursor.execute("SELECT country, country_code  FROM country_codes")
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

def global_admin_dashboard_main():
    return render_template('Global/new_dashboard.html')

#---------------------------------------------------------------Add Category--------------------------------------------------------------------------------

def add_category_main():
    return render_template('Global/add_category.html')
 

def submit_category_main():
    conn, cursor = connect_to_database()
    error_message = None
    success_message = None
 
    if conn is not None:
        cursor = conn.cursor()
        try:
            category_type = request.form.get('categoryType')
            remarks = request.form.get('remarks')
 
            # Check if the category type already exists in the database
            cursor.execute("SELECT COUNT(*) FROM category WHERE category_type = %s", (category_type,))
            if cursor.fetchone()[0] > 0:
                error_message = "Category already exists! Please use a different category type."
            else:
                # Insert the category data into the database
                cursor.execute("""
                    INSERT INTO category (category_type, remarks)
                    VALUES (%s, %s)
                """, (category_type, remarks))
                conn.commit()
 
                success_message = f"Category successfully added with ID {cursor.lastrowid}."
 
        except mysql.connector.IntegrityError as e:
            error_message = "Failed to submit category data due to integrity error."
        except Exception as e:
            print(f"Failed to submit form data: {e}")
            error_message = "Error processing your request."
        finally:
            cursor.close()
            conn.close()
    else:
        error_message = "Failed to connect to the database."
 
    return render_template('Global/add_category.html', error_message=error_message, success_message=success_message)
#-------------------------------------------Delete Category----------------------------------------------------------#
def display_categories_main():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        return "Error connecting to the database."

    try:
        # Fetch specific columns, including remarks
        cursor.execute("SELECT category_id, category_type, Remarks FROM category")
        categories = cursor.fetchall()
        
        # Print the categories to check if remarks are fetched
        print(categories)  # Debugging: check the data structure and whether remarks are fetched
        # Fetching session data
        entity_id = session.get('entity_id')
        user_id = session.get('user_id')

        return render_template('Global/delete_category.html', categories=categories,entity_id=entity_id, user_id=user_id)
    finally:
        cursor.close()
        conn.close()

def delete_category_main():
    category_ids = request.form.getlist('category_ids')
    if category_ids:
        conn, cursor = connect_to_database()
        if conn is None or cursor is None:
            return "Error connecting to the database."
        
        try:
            format_strings = ','.join(['%s'] * len(category_ids))
            cursor.execute(f"DELETE FROM category WHERE category_id IN ({format_strings})", category_ids)
            conn.commit()
            return redirect('/display_main_categories?deleted=true')  # Redirect with query parameter after successful deletion
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            flash("An error occurred while deleting the categories.")
        finally:
            cursor.close()
            conn.close()
    else:
        flash("No category selected for deletion.")
    
    return redirect('/display_main_categories')
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
    error_message = None
    success_message = None

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
    category = request.form.get('category')
    adminEmail = request.form.get('adminEmail')
    adminPassword = request.form.get('adminPassword')
    selected_regulations = request.form.get('selected_regulations')  # Get the selected regulations

    # input(selected_regulations)

    # Hash the admin password
    hashed_password = bcrypt.hashpw(adminPassword.encode('utf-8'), bcrypt.gensalt())

    # Validate required fields
    if not (adminEmail and adminPassword and entity_name and location and state and country and pincode and contact_name and country_code and contact_phno and category):
        error_message = "Some required fields are missing"
        return render_template('Global/add_entity.html', error_message=error_message, country_codes=fetch_country_codes())

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
                error_message = "Factory name already exists! Please use a different name."
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
                               country, pincode, contact_phno, alternate_contact, category, contact_name, alternate_contact_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (factory_id, entity_name, location, state, country, pincode, full_contact_phno, full_alternate_contact_phno, category, contact_name, alternate_contact_name))
                
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
                    INSERT INTO users (user_id, user_name, address, mobile_no, email_id, password, factory_id, role)
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

                success_message = f"Entity successfully added with ID {factory_id}."

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

    return render_template('Global/add_entity.html', error_message=error_message, success_message=success_message, country_codes=fetch_country_codes())

#--------------------------------------------------------Modify Entity----------------------------------------------------------------------------------------
def update_entity_page_main():
    # Render the HTML form for updating an entity
    return render_template('Global/update_entity.html')

def get_entities_main():
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        return jsonify({'error': 'Database connection error'}), 500
    
    cursor.execute("SELECT entity_id, entity_name FROM entity_master")
    entities = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(entities)

def get_entity_details_main(entity_id):
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        return jsonify({'error': 'Database connection error'}), 500

    cursor.execute("""
        SELECT entity_id, entity_name, location, contact_phno, alternate_contact, description,
               country, contact_name, alternate_contact_name, state, pincode
        FROM entity_master
        WHERE entity_id = %s
    """, (entity_id,))
    entity_details = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify(entity_details)

def update_entity_main():
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        return jsonify({'error': 'Database connection error'}), 500

    # Fetch the form data
    entity_id = request.form.get('entity_id')
    location = request.form.get('location')
    contact_phno = request.form.get('contact_phno')
    alternate_contact = request.form.get('alternate_contact')
    description = request.form.get('description')
    country = request.form.get('country')
    contact_name = request.form.get('contact_name')
    alternate_contact_name = request.form.get('alternate_contact_name')
    state = request.form.get('state')
    pincode = request.form.get('pincode')

    # Update the entity details in the database
    try:
        query = """
            UPDATE entity_master
            SET location = %s, contact_phno = %s, alternate_contact = %s, description = %s,
                country = %s, contact_name = %s, alternate_contact_name = %s, state = %s, pincode = %s
            WHERE entity_id = %s
        """
        cursor.execute(query, (location, contact_phno, alternate_contact, description, country, contact_name, alternate_contact_name, state, pincode, entity_id))
        conn.commit()

        return jsonify({'message': 'Entity updated successfully'})
    except mysql.connector.Error as err:
        print(f"Error updating entity: {err}")
        return jsonify({'error': 'Failed to update entity in the database'}), 500
    finally:
        cursor.close()
        conn.close()
#---------------------------------------------------Delete Entity------------------------------------------------------------------
def delete_entity_page_main():
    return render_template('Global/delete_entity.html')

def get_entities_main():
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        return jsonify({'error': 'Database connection error'}), 500
    
    cursor.execute("SELECT entity_id, entity_name FROM entity_master")
    entities = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(entities)

def get_entity_details_for_delete_main(entity_id):
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        return jsonify({'error': 'Database connection error'}), 500

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

def delete_entity_main():
    entity_id = request.form.get('entity_id')
    
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        return jsonify({'error': 'Database connection error'}), 500

    # First, check if the entity exists
    cursor.execute("SELECT * FROM entity_master WHERE entity_id = %s", (entity_id,))
    entity = cursor.fetchone()

    if not entity:
        return jsonify({'error': 'Entity does not exist'}), 404

    # If entity exists, proceed to delete
    try:
        cursor.execute("DELETE FROM entity_master WHERE entity_id = %s", (entity_id,))
        conn.commit()
        return jsonify({'message': 'Entity deleted successfully'})
    except mysql.connector.Error as err:
        print(f"Error deleting entity: {err}")
        return jsonify({'error': 'Failed to delete entity from the database'}), 500
    finally:
        cursor.close()
        conn.close()
#-------------------------------------------------------------Add Regulation-------------------------------------------------------------------------------

def add_regulation_global_main():
    categories = get_categories()  # This should trigger the print statements
    return render_template('Global/add_regulation.html', categories=categories)


def submit_regulation_main():
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


                # query="""

                #     INSERT INTO entity_regulation 
                #     (entity_id,regulation_id) VALUES(%s,%s)
                #     """
                # cursor.execute(query,(factory_id,regulation_id))
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
    return render_template('Global/add_regulation.html', error_message=error_message, success_message=success_message, categories=categories)

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
    # Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')

    # Establish connection to database
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        flash('Database connection error', 'error')
        return redirect(url_for('edit_main_regulation_page'))

    try:
        # Query to fetch all regulations for the given entity_id from the entity_regulation and regulation_master tables
        query = """
            SELECT regulation_id, regulation_name
            FROM regulation_master
        """
        cursor.execute(query)
        regulations = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f'Error fetching regulations: {str(err)}', 'error')
        regulations = []
    finally:
        cursor.close()
        conn.close()

    # Render the template with the list of regulations for the given entity
    return render_template('Global/update_regulations.html', regulations=regulations, entity_id=entity_id, user_id=user_id)

def fetch_regulation_main():
    regulation_name = request.form.get('regulation_name')

    # Fetching session data
    entity_id = session.get('entity_id')

    # Convert the input to lowercase for case-insensitive search
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        flash('Database connection error', 'error')
        return redirect(url_for('edit_main_regulation_page'))

    try:
        # Query to fetch regulation details based on regulation_name and entity_id
        query = """
            SELECT rm.*
            FROM regulation_master rm
            WHERE LOWER(rm.regulation_name) = LOWER(%s)
        """
        cursor.execute(query, (regulation_name,))
        regulation = cursor.fetchone()
    except mysql.connector.Error as err:
        flash(f'Error fetching regulation: {str(err)}', 'error')
        regulation = None
    finally:
        cursor.close()
        conn.close()

    if not regulation:
        flash('No regulation found', 'error')
        return redirect(url_for('edit_main_regulation_page'))

    # Fetching session data for rendering
    user_id = session.get('user_id')

    return render_template('Global/update_regulations.html', regulation=regulation, entity_id=entity_id, user_id=user_id)

def update_regulation_main():
    # Get data from the form using `request.form`
    regulation_id = request.form.get('regulation_id')
    regulatory_body = request.form.get('regulatory_body')
    internal_external = request.form.get('internal_external')
    national_international = request.form.get('national_international')
    mandatory_optional = request.form.get('mandatory_optional')
    obsolete_current = request.form.get('obsolete_current')

    if not regulation_id:
        flash('Missing regulation ID', 'error')
        return redirect(url_for('edit_main_regulation_page'))

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        flash('Database connection error', 'error')
        return redirect(url_for('edit_main_regulation_page'))

    try:
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

        flash('Regulation updated successfully!', 'success')
        return redirect(url_for('edit_main_regulation_page'))
    except mysql.connector.Error as err:
        flash(f'Error updating regulation: {str(err)}', 'error')
        return redirect(url_for('edit_main_regulation_page'))
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
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        cursor.execute("SELECT category_id, category_type FROM category")
        categories = cursor.fetchall()
        return jsonify(categories)
    finally:
        cursor.close()
        conn.close()

def load_regulations_main(category_id):
    # Fetch entity_id from the session
    entity_id = session.get('entity_id')
    
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        return jsonify({'error': 'Database connection error'}), 500

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
    finally:
        cursor.close()
        conn.close()

def delete_regulations_main():
    regulation_ids = request.form.getlist('regulation_ids')
    if not regulation_ids:
        return jsonify({'error': 'No regulations selected'}), 400

    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        return jsonify({'error': 'Database connection error'}), 500

    try:
        # Ensure that only regulations associated with the entity_id can be deleted
        format_strings = ','.join(['%s'] * len(regulation_ids))
        query = f"""
            DELETE FROM regulation_master 
            WHERE regulation_id IN ({format_strings})
        """
        cursor.execute(query,regulation_ids)
        conn.commit()
        return jsonify({'message': 'Selected regulations deleted successfully!'})
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
            print(f"Failed to query regulations: {e}")
        finally:
            cursor.close()
            conn.close()
    return render_template('Global/add_activity.html', regulations=regulations)
 

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
            else:
                # If it doesn't exist, insert the new activity
                cursor.execute("SELECT COALESCE(MAX(activity_id) + 1, 1) FROM activity_master WHERE regulation_id = %s", (regulation_id,))
                activity_id = cursor.fetchone()[0]
 
                query = """
                    INSERT INTO activity_master
                    (regulation_id, activity_id, activity, mandatory_optional, documentupload_yes_no,
                    frequency, frequency_timeline, critical_noncritical, ews, activity_description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    regulation_id, activity_id, activity, mandatory_optional, document_upload_yes_no,
                    frequency, frequency_timeline, criticality, ews, activity_description
                ))
                conn.commit()
                success_message = "Activity successfully added."
 
        except Error as e:
            print(f"Failed to insert activity: {e}")
            error_message = "Failed to add checklist item due to a database error."
        finally:
            cursor.close()
            conn.close()
    else:
        error_message = "Failed to connect to the database."
 
    regulations = send_regulations()
    return render_template('Global/add_activity.html', error_message=error_message, success_message=success_message, regulations=regulations)
 
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
            return "No activity found", 404
    except mysql.connector.Error as err:
        return f"Error fetching activity details: {err}", 500
    finally:
        cursor.close()
        conn.close()

def update_activity_main():
    data = request.form
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        return "Database connection failed", 500
    
    try:
        # Debugging: print the form data to check what is being passed
        print("Form Data:", data)
        
        # Check if all required fields are present
        required_fields = ['activity_description', 'criticality', 'documentupload_yes_no',
                           'frequency', 'frequency_timeline', 'mandatory_optional', 'ews',
                           'regulation_id', 'activity_id_hidden']
        
        for field in required_fields:
            if field not in data:
                return f"Missing field: {field}", 400
        
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

        # Stay on the same page and display a success message
        return render_template('Global/update_activities.html', 
                               regulations=regulations, 
                               activities=activities)
    
    except mysql.connector.Error as err:
        return f"Error updating activity: {err}", 500
    finally:
        cursor.close()
        conn.close()
#----------------------------------------------------------Delete Activity---------------------------------------------------------
def delete_activities_page_main():
    #Fetching session data
    entity_id = session.get('entity_id')
    user_id = session.get('user_id')

    return render_template('Global/delete_activities.html',entity_id=entity_id, user_id=user_id)  # This renders the delete activities HTML page

def populate_regulations_main():
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        cursor.execute("SELECT regulation_id, regulation_name FROM regulation_master")
        regulations = cursor.fetchall()
        return jsonify(regulations)
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
    finally:
        cursor.close()
        conn.close()

def delete_activities_main():
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
    finally:
        cursor.close()
        conn.close()