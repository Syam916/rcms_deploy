# lib.py
import mysql.connector
from mysql.connector import Error
import logging
from dateutil.relativedelta import relativedelta
import os
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime
from flask_mail import Message
from flask_mail import Mail
 
 
# Database configuration
# Database configuration
def get_db_connection():
    """Establishes a database connection using the configured parameters."""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="rcms"
        )
        if conn.is_connected():
            print("Successfully connected to the database")
        return conn  # Note that we are not returning the cursor here
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL Platform: {e}")
        return None
   
def get_factory_ids():
    conn = get_db_connection()
    factory_ids = []
    if conn is not None:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT factory_id FROM factory_master")
            factory_ids = cursor.fetchall()
        except Error as e:
            print(f"Failed to query factory IDs: {e}")
        finally:
            cursor.close()
            conn.close()
    return factory_ids
 
def get_users(factory_id):
    """Fetches user details for a specific factory from the database."""
    conn = get_db_connection()
    users = []
    if conn is not None:
        cursor = conn.cursor()
        try:
            query = "SELECT user_id, user_name FROM users WHERE factory_id = %s"
            cursor.execute(query, (factory_id,))
            users = cursor.fetchall()
        except Error as e:
            logging.error(f"Failed to query users: {e}")
        finally:
            cursor.close()
            conn.close()
    return users
 
def get_regulations(factory_id):
    """Fetches regulation IDs for a specific factory from the database."""
    conn = get_db_connection()
    regulations = []
    if conn:
        cursor = conn.cursor()
        try:
            query = "SELECT regulation_id FROM factory_regulation WHERE factory_id = %s"
            cursor.execute(query, (factory_id,))
            results = cursor.fetchall()
            regulations = [row[0] for row in results]
        except Error as e:
            logging.error(f"Failed to query regulation IDs: {e}")
        finally:
            cursor.close()
            conn.close()
    return regulations
 
 
def get_regulation_name(regulation_id):
    """Fetches the regulation name for a given regulation ID."""
    conn = get_db_connection()
    if conn is not None:
        cursor = conn.cursor()
        try:
            query = "SELECT regulation_name FROM regulation_master WHERE regulation_id = %s"
            cursor.execute(query, (regulation_id,))
            result = cursor.fetchone()
            if result:
                return {'regulation_name': result[0]}
            else:
                return {'regulation_name': None}
        except Error as e:
            logging.error(f"Failed to query regulation name: {e}")
            return {'regulation_name': None}
        finally:
            cursor.close()
            conn.close()
    else:
        return {'regulation_name': None}
   
def get_category_type(regulation_id):
    """Fetches the category type for a given regulation ID."""
    conn = get_db_connection()
    if conn is not None:
        cursor = conn.cursor()
        try:
            query = """
                SELECT c.category_type
                FROM regulation_master r
                JOIN category c ON r.category_id = c.category_id
                WHERE r.regulation_id = %s
            """
            cursor.execute(query, (regulation_id,))
            result = cursor.fetchone()
            if result:
                return {'category_type': result[0]}
            else:
                return {'category_type': None}
        except Error as e:
            logging.error(f"Failed to query category type: {e}")
            return {'category_type': None}
        finally:
            cursor.close()
            conn.close()
    else:
        return {'category_type': None}
   
def get_activities(regulation_id):
    """Fetches activities for a given regulation ID."""
    conn = get_db_connection()
    activities = []
    if conn is not None:
        cursor = conn.cursor()
        try:
            query = "SELECT activity_id, activity, critical_noncritical, ews FROM regulation_checklist WHERE regulation_id = %s"
            cursor.execute(query, (regulation_id,))
            activities = cursor.fetchall()
        except Error as e:
            logging.error(f"Failed to query activities, critical/noncritical status, and EWS: {e}")
        finally:
            cursor.close()
            conn.close()
    return [{'activity_id': act[0], 'activity': act[1], 'critical_noncritical': act[2], 'ews': act[3]} for act in activities]
 
def get_frequency(regulation_id, activity_id):
    """Fetches the frequency for a given regulation ID and activity ID."""
    conn = get_db_connection()
    if conn is not None:
        cursor = conn.cursor()
        try:
            query = """
                SELECT frequency
                FROM regulation_checklist
                WHERE regulation_id = %s AND activity_id = %s
            """
            cursor.execute(query, (regulation_id, activity_id))
            result = cursor.fetchone()
            if result:
                logging.info(f"Frequency fetched: {result[0]}")  # Debugging
                return {'frequency': result[0]}  # Ensure 26 for fortnight is sent
            else:
                return {'frequency': None}
        except Error as e:
            logging.error(f"Failed to query frequency: {e}")
            return {'frequency': None}
        finally:
            cursor.close()
            conn.close()
    else:
        return {'frequency': None}
   
# Define the task frequency description based on the frequency value
def get_frequency_description(frequency):
    if frequency == 52:  # Weekly (52 times a year)
        return "This is a weekly occurring task."
    elif frequency == 12:  # Monthly (12 times a year)
        return "This is a monthly occurring task."
    elif frequency == 4:  # Quarterly (4 times a year)
        return "This is a quarterly occurring task."
    elif frequency == 2:  # Half-yearly (2 times a year)
        return "This is a half-yearly occurring task."
    elif frequency == 1:  # Annually (1 time a year)
        return "This is an annual task."
    elif frequency == 3:  # Once in 4 months
        return "This is a once-in-four-months task."
    elif frequency == 26:  # 26 times a year
        return "This is a fortnightly occurring task."
    elif frequency == 365:  # 26 times a year
        return "This is a daily task."
    elif frequency == 0:  # Only once
        return "This is a one time task."
    elif frequency == 6:  # 6 times a year
        return "This is a once-in-two-months task."
    else:
        return "This is a custom frequency task."
    
 # This will allow you to use date.today() to get the current date
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

# Your get_due_on function and other code follows here...

   
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

def get_due_on(regulation_id, activity_id):
    """Generates and adjusts upcoming due dates for a regulation activity, including holiday checking."""
    conn = get_db_connection()
    if conn is not None:
        cursor = conn.cursor()
        try:
            query = """
                SELECT frequency_timeline, frequency
                FROM regulation_checklist
                WHERE regulation_id = %s AND activity_id = %s
            """
            cursor.execute(query, (regulation_id, activity_id))
            result = cursor.fetchone()
            if result:
                frequency_timeline, frequency = result
                current_date = datetime.today().date()
                end_of_next_year = datetime(current_date.year + 1, 12, 31).date()

                due_dates = []
                due_on = frequency_timeline
                while due_on <= end_of_next_year:
                    # Collect due dates
                    due_dates.append(due_on)
                    # Calculate next due date based on frequency
                    if frequency == 52:  # Weekly
                        due_on += relativedelta(weeks=1)
                    elif frequency == 12:  # Monthly
                        due_on += relativedelta(months=1)
                    elif frequency == 4:  # Quarterly
                        due_on += relativedelta(months=3)
                    elif frequency == 2:  # Half-yearly
                        due_on += relativedelta(months=6)
                    elif frequency == 1:  # Annually
                        due_on += relativedelta(years=1)
                    elif frequency == 3:  # Once in 4 months
                        due_on += relativedelta(months=4)
                    elif frequency == 26:  # Fortnightly
                        due_on += relativedelta(weeks=2)
                    elif frequency == 365:  # Daily
                        due_on += relativedelta(days=1)
                    elif frequency == 6:  # Once in 2 months
                        due_on += relativedelta(months=2)

                # Adjust due dates for holidays
                adjusted_due_dates = adjust_due_dates_with_holidays(cursor,due_dates)

                return {'due_on': [date.strftime('%Y-%m-%d') for date in adjusted_due_dates]}
            else:
                return {'due_on': None}
        except Error as e:
            logging.error(f"Failed to query due_on date: {e}")
            return {'due_on': None}
        finally:
            cursor.close()
            conn.close()
    else:
        return {'due_on': None}


def adjust_due_dates_with_holidays(cursor,due_dates):
    """Adjusts each due date individually by checking for holidays."""
    adjusted_due_dates = []
    
    for due_date in due_dates:
        while True:
            # Check if the due_date is a holiday
            cursor.execute("SELECT COUNT(*) FROM holiday_master WHERE Holiday_Date = %s", (due_date,))
            is_holiday = cursor.fetchone()[0]
            if is_holiday:
                # If it's a holiday, adjust the due date by moving it to the next day
                due_date = due_date + relativedelta(days=1)
            else:
                # If it's not a holiday, add the due date to the adjusted list
                adjusted_due_dates.append(due_date)
                break

    return adjusted_due_dates


 
def configure_mail(app):
    """Configure the Flask-Mail settings and return a Mail object."""
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USERNAME'] = 'vardaan.rcms@gmail.com'
    app.config['MAIL_PASSWORD'] = 'aynlltagpthlzqgd'
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']
   
    mail = Mail(app)
    return mail  
 
# Google API credentials file paths
CREDENTIALS_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']
 
def get_credentials():
    """Retrieve or refresh Google Calendar API credentials."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
   
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
       
        # Save the credentials for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
   
    return creds
 
def create_calendar_event(subject, date, to_email, content):
    """Creates a calendar event in Google Calendar for the given email."""
    try:
        creds = get_credentials()
        service = build('calendar', 'v3', credentials=creds)
 
        event = {
            'summary': subject,
            'description': content,
            'start': {'dateTime': date.strftime('%Y-%m-%dT09:00:00'), 'timeZone': 'Europe/London'},
            'end': {'dateTime': date.strftime('%Y-%m-%dT10:00:00'), 'timeZone': 'Europe/London'},
            'attendees': [{'email': to_email}],
        }
 
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        logging.info(f"Calendar event created for {to_email}: {event_result.get('htmlLink')}")
    except Exception as e:
        logging.error(f"Failed to create calendar event: {e}")
        raise
 
def schedule_calendar_events(activity_name, due_on, assignee_email, reviewer_email):
    """Schedules calendar events for both assignee and reviewer."""
    for recipient in [(assignee_email, "Assignee"), (reviewer_email, "Reviewer")]:
        email, role = recipient
        try:
            create_calendar_event(activity_name, due_on, email, f"Task: {activity_name} is due on {due_on.strftime('%Y-%m-%d')} ({role})")
            print(f"Scheduled calendar event for {role}: {email} on {due_on.strftime('%Y-%m-%d')}")
        except Exception as e:
            print(f"Failed to schedule calendar event for {role}: {email} on {due_on.strftime('%Y-%m-%d')} - {e}")
 
def send_scheduled_emails(app, mail, get_db_connection):
    """Function to send scheduled emails."""
    with app.app_context():  # Push the application context
        conn = get_db_connection()
        if conn is not None:
            cursor = conn.cursor()
            try:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("""
                    SELECT s_no, message_des, email_id
                    FROM message_queue
                    WHERE date <= %s AND time <= %s AND status IN ('Scheduled', 'Added to Calendar')
                """, (current_time[:10], current_time[11:]))
 
                messages = cursor.fetchall()
 
                for msg in messages:
                    s_no, message_des, email_id = msg
                    try:
                        email_message = Message(subject="Scheduled Reminder", recipients=[email_id], body=message_des)
                        mail.send(email_message)
                        print(f"Scheduled email sent to {email_id}")
                        cursor.execute("UPDATE message_queue SET status = 'Sent' WHERE s_no = %s", (s_no,))
                        conn.commit()
                    except Exception as e:
                        print(f"Failed to send scheduled email: {e}")
 
            except Error as e:
                print(f"Failed to fetch scheduled messages: {e}")
            finally:
                cursor.close()
                conn.close()
 
def add_calendar_events_from_queue(get_db_connection, create_calendar_event):
    """Function to add calendar events from the message queue."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT s_no, message_des, email_id, date FROM message_queue WHERE status = 'Scheduled'")
            messages = cursor.fetchall()
            for msg in messages:
                s_no, message_des, email_id, due_date = msg
 
                # Since due_date is already a date object (no need to convert)
                due_date_time = due_date  # Directly use due_date since it's a 'date' object
 
                try:
                    # Create a calendar event using the due_date (date object)
                    create_calendar_event("Reminder: " + message_des, due_date_time, email_id, message_des)
                    cursor.execute("UPDATE message_queue SET status = 'Added to Calendar' WHERE s_no = %s", (s_no,))
                    conn.commit()
                    logging.info(f"Added to Calendar and updated status for message {s_no}")
                except Exception as e:
                    logging.error(f"Failed to create calendar event for message {s_no}: {e}")
        except Error as e:
            logging.error(f"Database error: {e}")
        finally:
            cursor.close()
            conn.close()