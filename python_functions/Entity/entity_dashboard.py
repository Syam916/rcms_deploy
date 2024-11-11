from flask import Flask, render_template, session, redirect, url_for, flash, request
import pymysql
from datetime import date, timedelta, datetime
import mysql.connector
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management
 
# Database connection
def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="rcms"
    )
    return conn
 
# Example login route to simulate user login
@app.route('/login/<user_id>')
def login(user_id):
    # For testing, set a factory_id as well (you can modify this as per your logic)
    session['user_id'] = user_id  # Store user ID in session
    session['factory_id'] = 'some_factory_id'  # Replace 'some_factory_id' with real logic to fetch factory_id
 
    # Redirect to the dashboard
    return redirect(url_for('dashboard', factory_id=session['factory_id']))
 
 
# Dashboard route
@app.route('/dashboard/<factory_id>')
def dashboard(factory_id):
 
    if 'factory_id' not in session:
        session['factory_id'] = factory_id
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login', user_id='default_user'))
 
    user_id = session['user_id']
    factory_id = session['factory_id']
 
    connection = get_db_connection()
    cursor = connection.cursor()
 
    # Corrected query to fetch status along with other details
    query = """
        SELECT fram.regulation_id, rm.regulation_name, fram.due_on,
               fram.preparation_responsibility, fram.review_responsibility, fram.status
        FROM factory_regulation_activity_master fram
        JOIN regulation_master rm ON fram.regulation_id = rm.regulation_id
        WHERE fram.factory_id = %s
        AND (fram.preparation_responsibility = %s OR fram.review_responsibility = %s)
    """
    cursor.execute(query, (factory_id, user_id, user_id))
    regulations = cursor.fetchall()
 
    # Prepare the data for the frontend
    delayed = []
    in_progress = []
    due_this_month = []
    completed = []
 
    today = date.today()
    first_day_of_month = today.replace(day=1)
    last_day_of_month = (today.replace(month=today.month + 1, day=1) - timedelta(days=1)) if today.month < 12 else date(today.year, 12, 31)
    one_month_ago = today - timedelta(days=30)
 
    # Categorize the regulations based on their status and due_on date
    for regulation in regulations:
        due_on = regulation['due_on']
        regulation_data = {
            'regulation_id': regulation['regulation_id'],
            'regulation_name': regulation['regulation_name'],
            'due_on': regulation['due_on'],
            'responsibility_type': 'Preparation' if regulation['preparation_responsibility'] == user_id else 'Review'
        }
 
        # Add status-based categorization
        if regulation['status'] == 'Completed':
            completed.append(regulation_data)
        elif regulation['status'] == 'WIP':
            in_progress.append(regulation_data)
        elif regulation['status'] == 'Yet to start' and one_month_ago <= regulation['due_on'] < today:
            delayed.append(regulation_data)
        elif first_day_of_month <= regulation['due_on'] <= last_day_of_month:
            due_this_month.append(regulation_data)
 
    cursor.close()
    connection.close()
 
    # Pass the categorized data to the template
    return render_template('dashboard.html',
                           delayed=delayed,
                           in_progress=in_progress,
                           due_this_month=due_this_month,
                           completed=completed,
                           user_id=user_id,
                           factory_id=factory_id)
 
# Function to generate the audit_id
def generate_audit_id(factory_id, regulation_id, activity_id):
    date_time_str = datetime.now().strftime("%Y%m%d%H%M%S")
    audit_id = f"{factory_id}_{regulation_id}_{activity_id}_{date_time_str}"
    return audit_id
 
# Route to display activities for a specific regulation and due_on date
@app.route('/regulation/<regulation_id>')
def view_regulation(regulation_id):
    due_on = request.args.get('due_on')
    factory_id = session.get('factory_id')
    user_id = session.get('user_id')
 
    connection = get_db_connection()
    cursor = connection.cursor()
 
    # Fetch activities related to the regulation and filter by due_on
    # Modify the activity_query to fetch 'activity' along with 'activity_description'
    activity_query = """
        SELECT rc.activity_id, rc.activity, rc.activity_description
        FROM regulation_checklist rc
        JOIN factory_regulation_activity_master fram
        ON rc.regulation_id = fram.regulation_id AND rc.activity_id = fram.activity_id
        WHERE rc.regulation_id = %s
        AND fram.due_on = %s
        AND (fram.preparation_responsibility = %s OR fram.review_responsibility = %s)
    """
 
    cursor.execute(activity_query, (regulation_id, due_on, user_id, user_id))
    activities = cursor.fetchall()
 
    # Fetch previously submitted data (if any)
    audit_query = """
        SELECT activity_id, status, remarks, attachment
        FROM factory_audit_details
        WHERE audit_id LIKE %s AND due_on = %s
    """
    audit_id_pattern = f"{factory_id}_{regulation_id}_%"  # audit_id pattern
    cursor.execute(audit_query, (audit_id_pattern, due_on))
    responses = cursor.fetchall()
 
    # Convert responses into a dictionary for easier lookup
    responses_dict = {resp['activity_id']: resp for resp in responses}
 
    cursor.close()
    connection.close()
 
    # Render the regulation_activity.html template with activities and responses
    return render_template('regulation_activity.html',
                           regulation_id=regulation_id,
                           activities=activities,
                           responses=responses_dict,
                           due_on=due_on)
 
 
@app.route('/submit_activity', methods=['POST'])
def submit_activity():
    factory_id = session['factory_id']  # Assuming factory_id is stored in session
    user_id = session['user_id']  # Assuming user_id is stored in session (preparation responsibility)
    regulation_id = request.form['regulation_id']
    activity_id = request.form['activity_id']
    remarks = request.form.get(f'remarks_{activity_id}')
    status = request.form.get(f'status_{activity_id}')
    file = request.files.get(f'file_{activity_id}')
    due_on = request.form.get('due_on')  # Get due_on from the form
 
    # Generate the audit_id based on the factory_id, regulation_id, and activity_id
    audit_id = generate_audit_id(factory_id, regulation_id, activity_id)
 
    # Handle the file upload (optional)
    file_path = None
    if file and file.filename != '':
        file_path = f"uploads/{file.filename}"  # Path to save the file (You can change this)
        file.save(file_path)
 
    # Determine the start_date and end_date based on status
    start_date = datetime.now() if status in ['WIP', 'Completed'] else None
    end_date = datetime.now() if status == 'Completed' else None
 
    # Insert data into the factory_audit_details table
    connection = get_db_connection()
    cursor = connection.cursor()
 
    # SQL to insert or update the factory_audit_details table
    audit_query = """
        INSERT INTO factory_audit_details (audit_id, activity_id, status, Remarks, Attachment, prepared_by, start_date, end_date, due_on)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        status = VALUES(status), Remarks = VALUES(Remarks), Attachment = VALUES(Attachment), start_date = VALUES(start_date), end_date = VALUES(end_date), due_on = VALUES(due_on)
    """
    cursor.execute(audit_query, (audit_id, activity_id, status, remarks, file_path, user_id, start_date, end_date, due_on))
 
    # SQL to update the status in factory_regulation_activity_master
    update_query = """
        UPDATE factory_regulation_activity_master
        SET status = %s
        WHERE regulation_id = %s AND activity_id = %s AND due_on = %s
    """
    cursor.execute(update_query, (status, regulation_id, activity_id, due_on))
 
    connection.commit()
    cursor.close()
    connection.close()
 
    flash('Activity submitted successfully!', 'success')
    return redirect(url_for('view_regulation', regulation_id=regulation_id, due_on=due_on))
 
 
if __name__ == '__main__':
    app.run(debug=True)