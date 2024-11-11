from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import mysql.connector
from datetime import datetime
from flask_mail import Message
from app_2 import mail
from dotenv import load_dotenv
 
from python_functions.DB.db import connect_to_database
# Function to show pop-up messages
def pop_up_alert(message_type, message):
    return {
        'message_type': message_type,  # 'success' or 'error'
        'message': message
    }
 
# Function to redirect with a pop-up message
def pop_up_redirect(message_type, message, redirect_url):
    return {
        'message_type': message_type,
        'message': message,
        'redirect': url_for(redirect_url)
    }
 
 
def get_regulations_user():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))  # Redirect to login if not logged in
 
    conn, cur = connect_to_database()
    if conn is None or cur is None:
        return jsonify({"error": "Database connection failed"}), 500
 
    # Fetch all regulations with their status, due_on dates, and review_end_date
    query = """
        SELECT e.activity_id, e.regulation_id, r.regulation_name, a.activity,
               e.due_on, e.status, e.review_end_date, e.preparation_responsibility, e.review_responsibility
        FROM entity_regulation_tasks e
        JOIN regulation_master r ON e.regulation_id = r.regulation_id
        JOIN activity_master a ON e.activity_id = a.activity_id AND e.regulation_id = a.regulation_id
        ORDER BY e.due_on ASC;
    """
    cur.execute(query)
    regulations = cur.fetchall()
    cur.close()
    conn.close()
 
    # Format due_on and review_end_date to strings in dd-mm-yyyy format
    for regulation in regulations:
        regulation['due_on'] = regulation['due_on'].strftime('%d-%m-%Y')
        if regulation['review_end_date']:
            regulation['review_end_date'] = regulation['review_end_date'].strftime('%d-%m-%Y')
        # Log each task's status and review_end_date for debugging
        print(f"Task: {regulation['activity']}, Status: {regulation['status']}, Review End Date: {regulation.get('review_end_date')}")
 
    # Categorize the regulations
    due_this_month = []
    delayed = []
    in_progress = []
    completed = []
 
    current_date = datetime.now().date()
 
    for regulation in regulations:
        # Parse due_on to a date object for comparison
        due_on = datetime.strptime(regulation['due_on'], '%d-%m-%Y').date()
        status = regulation['status']
        review_end_date = regulation.get('review_end_date')
        # Parse review_end_date to a date object if it exists
        review_end_date = datetime.strptime(review_end_date, '%d-%m-%Y').date() if review_end_date else None
 
        # Add regulation to appropriate category based on status
        if status == "Yet to Start":
            if due_on >= current_date:
                due_this_month.append(regulation)
            else:
                delayed.append(regulation)
        elif status == "WIP":
            if due_on > current_date:
                in_progress.append(regulation)
            else:
                regulation['overdue'] = True
                in_progress.append(regulation)
        elif status == "Completed":
            # Only add completed tasks with a filled review_end_date to the completed category
            if review_end_date:
                completed.append(regulation)
            else:
                # If no review_end_date, treat it as incomplete for review purposes
                in_progress.append(regulation)
 
 
    input(completed)
 
    # Render the regulations into separate tables in the HTML
    return render_template('user/entity_user.html',
                           due_this_month=due_this_month,
                           delayed=delayed,
                           in_progress=in_progress,
                           completed=completed,
                           user_id=user_id)
 
 
def get_filtered_tasks_user():
    filter_option = request.args.get('filter', 'current')
    user_id = session.get('user_id')


    print('this function is triggering /////')
 
    conn, cur = connect_to_database()
    if conn is None or cur is None:
        return jsonify({"error": "Database connection failed"}), 500
 
    # SQL query based on filter selection
    if filter_option == 'current':
        query = """
            SELECT e.activity_id, e.regulation_id, r.regulation_name, a.activity, e.due_on, e.status, e.preparation_responsibility, e.review_end_date, e.review_responsibility, e.criticality
            FROM entity_regulation_tasks e
            JOIN regulation_master r ON e.regulation_id = r.regulation_id
            JOIN activity_master a ON e.activity_id = a.activity_id AND e.regulation_id = a.regulation_id
            WHERE (e.preparation_responsibility = %s OR e.review_responsibility = %s)
            AND MONTH(e.due_on) = MONTH(CURRENT_DATE)
            AND YEAR(e.due_on) = YEAR(CURRENT_DATE)
            ORDER BY e.regulation_id ASC, e.activity_id ASC, e.due_on ASC;
        """
    elif filter_option == 'last':
        query = """
            SELECT e.activity_id, e.regulation_id, r.regulation_name, a.activity, e.due_on, e.status, e.preparation_responsibility, e.review_responsibility, e.criticality
            FROM entity_regulation_tasks e
            JOIN regulation_master r ON e.regulation_id = r.regulation_id
            JOIN activity_master a ON e.activity_id = a.activity_id AND e.regulation_id = a.regulation_id
            WHERE (e.preparation_responsibility = %s OR e.review_responsibility = %s)
            AND e.due_on BETWEEN
                LAST_DAY(CURRENT_DATE - INTERVAL 1 MONTH) + INTERVAL 1 DAY - INTERVAL 1 MONTH
                AND LAST_DAY(CURRENT_DATE - INTERVAL 1 MONTH)
            ORDER BY e.regulation_id ASC, e.activity_id ASC, e.due_on ASC;
        """
    elif filter_option == 'next':
        query = """
            SELECT e.activity_id, e.regulation_id, r.regulation_name, a.activity, e.due_on, e.status, e.preparation_responsibility, e.review_responsibility, e.criticality
            FROM entity_regulation_tasks e
            JOIN regulation_master r ON e.regulation_id = r.regulation_id
            JOIN activity_master a ON e.activity_id = a.activity_id AND e.regulation_id = a.regulation_id
            WHERE (e.preparation_responsibility = %s OR e.review_responsibility = %s)
            AND e.due_on BETWEEN
                LAST_DAY(CURRENT_DATE) + INTERVAL 1 DAY
                AND LAST_DAY(CURRENT_DATE + INTERVAL 1 MONTH)
            ORDER BY e.regulation_id ASC, e.activity_id ASC, e.due_on ASC;
        """
    else:
        return jsonify({"error": "Invalid filter option"}), 400
 
    # Now that the query is defined, execute it
    cur.execute(query, (user_id, user_id))
    tasks = cur.fetchall()
 
    # Format the `due_on` date as DD/MM/YYYY
    for task in tasks:
        task['due_on'] = task['due_on'].strftime('%d/%m/%Y')
 
    cur.close()
    conn.close()
 
    return jsonify(tasks)
 
def view_activity_user(activity_id):
    regulation_id = request.args.get('regulation_id')
    role = request.args.get('role')
    due_on = request.args.get('due_on')
    user_id = session.get('user_id')
 
    if not regulation_id or not due_on:
        return jsonify({"error": "regulation_id and due_on are required"}), 400
 
    conn, cur = connect_to_database()
    cur_activity = None
 
    if conn is None or cur is None:
        return jsonify({"error": "Database connection failed"}), 500
 
    try:
        responsibility_column = 'preparation_responsibility' if role == 'preparation' else 'review_responsibility'
 
        prep_status_query = f"""
            SELECT status, remarks
            FROM entity_regulation_tasks
            WHERE activity_id = %s AND regulation_id = %s AND {responsibility_column} = %s AND due_on = %s
        """
        cur.execute(prep_status_query, (activity_id, regulation_id, user_id, due_on))
        task_progress = cur.fetchone()
        cur.fetchall()
 
        if not task_progress:
            return jsonify({"error": "No task found for the given activity and due date"}), 404
 
        status = task_progress.get('status')
        remarks = task_progress.get('remarks', '')
 
        if role == 'review' and status != 'Completed':
            return jsonify({"error": "Cannot review until preparation is completed."}), 403
 
        cur_activity = conn.cursor(dictionary=True)
        activity_query = """
            SELECT a.activity_id, a.activity, a.activity_description, r.regulation_name, a.mandatory_optional, e.documentupload_yes_no
            FROM activity_master a
            JOIN regulation_master r ON a.regulation_id = r.regulation_id
            JOIN entity_regulation_tasks e ON a.activity_id = e.activity_id AND a.regulation_id = e.regulation_id
            WHERE a.regulation_id = %s AND a.activity_id = %s AND e.due_on = %s
        """
        cur_activity.execute(activity_query, (regulation_id, activity_id, due_on))
        activity = cur_activity.fetchone()
 
        if not activity:
            return jsonify({"error": "No activity found with the given details"}), 404
 
        is_mandatory = 'M' in activity['mandatory_optional']
        document_upload_required = activity['documentupload_yes_no'] == 'Y'
 
        if role == 'review':
            review_start_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            update_review_query = """
                UPDATE entity_regulation_tasks
                SET review_start_date = %s
                WHERE activity_id = %s AND regulation_id = %s AND due_on = %s
            """
            cur.execute(update_review_query, (review_start_date, activity_id, regulation_id, due_on))
            conn.commit()
 
        current_date = datetime.now().date()
        return render_template(
            'user/activity_details.html',
            activity=activity,
            role=role,
            is_mandatory=is_mandatory,
            document_upload_required=document_upload_required,
            regulation_id=regulation_id,
            user_id=user_id,
            entity_id=session.get('entity_id'),
            due_on=due_on,
            current_date=current_date,
            status=status,
            remarks=remarks
        )
 
    except mysql.connector.Error as e:
        print(f"MySQL Error: {e}")
        return jsonify({"error": "Database operation failed"}), 500
 
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred."}), 500
 
    finally:
        try:
            if cur:
                cur.close()
            if cur_activity:
                cur_activity.close()
        except mysql.connector.Error as e:
            print(f"Error while closing cursor: {e}")
        if conn:
            conn.close()
 
def send_email_reviewer(to_email, subject, body, is_html=False):
    msg = Message(subject, recipients=[to_email])
   
    if is_html:
        msg.html = body  # Use HTML content if it's passed as HTML
    else:
        msg.body = body  # Default to plain text
 
    try:
        mail.send(msg)
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
 
def submit_activity_user():
    # Extract form data
    activity_id = request.form['activity_id']
    regulation_id = request.form['regulation_id']
    role = request.form['role']
    due_on = request.form['due_on']
    remarks = request.form.get('remarks', '')  # Default to an empty string if not provided
    status = request.form.get('status', 'Completed')  # Set default to 'Completed' for review role
    review_remarks = request.form.get('review_comments', '')  # Default to an empty string if not provided
    document_link = request.form.get('document_link', '')  # Link to the document
 
    # Connect to the database
    conn, cur = connect_to_database()
    if conn is None or cur is None:
        print("Error: Unable to connect to the database.")
        return jsonify({"error": "Database connection failed"}), 500
 
    try:
        # For preparation responsibility
        if role == 'preparation':
            # Set start and end dates based on status
            start_date = None
            end_date = None
            if status == 'WIP':
                start_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            elif status == 'Completed':
                end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
 
            # Update query for preparation responsibility with document_link saved in `upload`
            query = """
                UPDATE entity_regulation_tasks
                SET remarks = %s, status = %s, upload = %s,
                    start_date = COALESCE(start_date, %s), end_date = %s
                WHERE activity_id = %s AND regulation_id = %s AND due_on = %s
            """
            cur.execute(query, (remarks, status, document_link, start_date, end_date, activity_id, regulation_id, due_on))
 
        # For review responsibility
        elif role == 'review':
            review_end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
 
            # Ensure status remains 'Completed' for review responsibility
            query = """
                UPDATE entity_regulation_tasks
                SET review_remarks = %s, review_upload = %s, review_end_date = %s, status = 'Completed'
                WHERE activity_id = %s AND regulation_id = %s AND due_on = %s
            """
            cur.execute(query, (review_remarks, document_link, review_end_date, activity_id, regulation_id, due_on))
 
        # Commit the transaction to save changes
        conn.commit()
        print("Data committed successfully")
 
    except mysql.connector.Error as db_error:
        print(f"Database error: {db_error}")
        conn.rollback()  # Rollback the transaction on error
        return jsonify({"error": "Database operation failed."}), 500
 
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()  # Rollback on any other exception
 
    finally:
        # Close the cursor and connection
        cur.close()
        conn.close()
 
    return jsonify({"success": True, "message": "Activity submitted successfully."})
 
 
def entity_user_main():
    user_id = session.get('user_id')
    entity_id = session.get('entity_id')
 
    if not user_id or not entity_id:
        return redirect(url_for('index'))  # Redirect to login page if not logged in
   
    return render_template('user/entity_user.html', user_id=user_id, entity_id=entity_id)
 
def entity_admin():
    user_id = session.get('user_id')
    entity_id = session.get('entity_id')
 
    if not user_id or not entity_id:
        return redirect(url_for('index'))
 
    return render_template('user/entity_admin.html', user_id=user_id, entity_id=entity_id)
 
def global_admin():
    user_id = session.get('user_id')
    entity_id = session.get('entity_id')
 
    if not user_id or not entity_id:
        return redirect(url_for('index'))
 
    return render_template('user/global_admin.html', user_id=user_id, entity_id=entity_id)