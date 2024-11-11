import dash
from dash import dcc, html
from dash.dependencies import Input, Output,State
import dash_table
import plotly.express as px
import pandas as pd
import mysql.connector
from datetime import datetime
from flask import Flask
# from python_functions.db import connect_to_database
# Database connection using mysql.connector
from mysql.connector import Error
import mysql.connector

def connect_to_database():
    try:
        conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="rcms"
    )
        cursor = conn.cursor(dictionary=True)  # This returns query results as dictionaries
        return conn, cursor
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None, None


# Function to fetch and process data from MySQL database


import mysql.connector
import pandas as pd

# Function to get entire dataset without filtering by entity_id
def get_entire_data():
    # Establishing a connection to the database
    conn,cursor=connect_to_database()
    # Query 1: Fetch entire data from final_rcms_data table
    query_final_rcms_data = """
    SELECT 
        entity_id, 
        start_date, 
        end_date, 
        criticality, 
        due_on, 
        status, 
        internal_external, 
        mandatory_optional,
        activity_id,
        regulation_id
    FROM entity_regulation_tasks
    """
    df_final_rcms_data = pd.read_sql(query_final_rcms_data, conn)
    print(f"Rows in final_rcms_data: {df_final_rcms_data.shape[0]}")

    # Query 2: Fetch data from entity_master table (no filtering needed)
    query_entity_master = """
    SELECT DISTINCT
        entity_id, 
        entity_name AS Entity
    FROM entity_master
    """
    df_entity_master = pd.read_sql(query_entity_master, conn)
    print(f"Rows in entity_master: {df_entity_master.shape[0]}")

    # Query 3: Fetch data from regulation_master table (no filtering needed)
    query_regulation_master = """
    SELECT DISTINCT
        regulation_id, 
        category_id,
        regulation_name
    FROM regulation_master
    """
    df_regulation_master = pd.read_sql(query_regulation_master, conn)
    print(f"Rows in regulation_master: {df_regulation_master.shape[0]}")

    # Query 4: Fetch data from category table (no filtering needed)
    query_category = """
    SELECT DISTINCT
        category_id, 
        category_type AS Category
    FROM category
    """
    df_category = pd.read_sql(query_category, conn)
    print(f"Rows in category: {df_category.shape[0]}")

    # Query 5: Fetch data from activity_master table
    query_activity_master = """
    SELECT DISTINCT
        activity_id, 
        activity AS Task
    FROM activity_master
    """
    df_activity_master = pd.read_sql(query_activity_master, conn)

    df_merged = pd.merge(df_final_rcms_data, df_entity_master, on='entity_id', how='left')

    df_merged = pd.merge(df_merged, df_regulation_master, on='regulation_id', how='left')

    df_merged = pd.merge(df_merged, df_category, on='category_id', how='left')

    df_activity_master_unique = df_activity_master.drop_duplicates(subset=['activity_id'])

    df_merged = pd.merge(df_merged, df_activity_master_unique, on='activity_id', how='left')
    output_file_path = 'final_rcms_data_output_entire_dataset.xlsx'
    df_merged.to_excel(output_file_path, index=False)

    conn.close()


    return df_merged





import plotly.graph_objects as go
def create_donut_chart(value, total, color):
    fig = go.Figure(go.Pie(
        values=[0, total],  # Start with an empty pie (0 for the value part)
        hole=0.7,  # Thin donut
        marker=dict(colors=[color, '#E0E0E0']),  # Color the value and make the rest gray
        textinfo='none',  # Hide text in pie chart
        direction='clockwise',  # Fill starting from the right
        showlegend=False  # No legends
    ))

    # Animation properties to make the donut fill automatically
    fig.update_traces(
        values=[value, total - value],  # Actual values to fill
        selector=dict(type='pie')
    )

    fig.update_layout(
        annotations=[dict(text=str(value), x=0.5, y=0.5, font_size=15, showarrow=False)],  # Center number
        margin=dict(l=0, r=20, t=0, b=0),  # Remove margins
        height=85,  # Height of the chart
        width=105,  # Width of the chart
        showlegend=False,  # No legend
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot background
    )

    # Add an automatic animation that runs on page load
    fig.update_layout(
        transition=dict(duration=1000, easing='cubic-in-out'),  # Animation duration and easing
    )

    return fig











def fetch_and_process_data_from_mysql():
    
    # Query the database
    # query = """SELECT Entity, start_date, end_date, criticality, Category, 
    # Task, due_date, status, `internal/external`,`mandatory/optional` FROM final_rcms_data"""
    # df = pd.read_sql(query, conn)
    # Assuming you already fetched the entire data
    df = get_entire_data()

    # Since the dates are already in the correct `DATE` format, pandas should automatically handle them.
    # We don't need to specify a format, just ensure they're in datetime format
    df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
    df['end_date'] = pd.to_datetime(df['end_date'], errors='coerce')
    df['due_on'] = pd.to_datetime(df['due_on'], errors='coerce')

    # Check for any NaT values in the date columns after conversion
    print(f"NaT values in 'start_date': {df['start_date'].isna().sum()}")
    print(f"NaT values in 'end_date': {df['end_date'].isna().sum()}")
    print(f"NaT values in 'due_on': {df['due_on'].isna().sum()}")

    current_date = pd.Timestamp(datetime.today().date())

    # Apply the logic to determine the calculated status based on the dates
    def classify_status(row):
        try:
            # If 'due_on' is NaT, return 'Unknown - Missing due date'
            if pd.isnull(row['due_on']):
                return 'Unknown - Missing due date'
            
            # Handle the various cases
            if row['due_on'] > current_date and row['status'] == "Yet to Start":
                return 'Yet to Start'
            elif row['due_on'] <= current_date and row['status'] == "Yet to Start":
                return 'Yet to Start with Delay'
            elif pd.isnull(row['end_date']) and row['due_on'] > current_date and row['status'] == "WIP":
                return 'WIP with Delay'
            elif pd.isnull(row['end_date']) and row['due_on'] <= current_date and row['status'] == "WIP":
                return 'WIP'
            elif not pd.isnull(row['end_date']) and row['due_on'] >= row['end_date'] and row['status'] == "Completed":
                return 'Completed'
            elif not pd.isnull(row['end_date']) and row['due_on'] < row['end_date'] and row['status'] == "Completed":
                return 'Completed with Delay'
            else:
                # Debugging output if it falls into the "Unknown" category
                # print("Debugging row:")
                # print(f"start_date: {row['start_date']}")
                # print(f"end_date: {row['end_date']}")
                # print(f"due_on: {row['due_on']}")
                # print(f"status: {row['status']}")
                # print(f"current_date: {current_date}")
                # print('---------------------------------------------------------------')
                return 'Unknown'
        except Exception as e:
            # Catch any exceptions to avoid script failure
            print(f"Error processing row: {e}")
            return 'Error'

    # Apply the classification function to the DataFrame
    df['calculated_status'] = df.apply(classify_status, axis=1)

    # View the resulting DataFrame
    print(df[['start_date', 'due_on', 'end_date', 'status', 'calculated_status']])
    
    df['start_date'] = df['start_date'].dt.strftime('%d/%m/%Y')
    df['end_date'] = df['end_date'].dt.strftime('%d/%m/%Y')
    df['due_on'] = df['due_on'].dt.strftime('%d/%m/%Y')


    df['due_on'] = pd.to_datetime(df['due_on'], format='%d/%m/%Y', errors='coerce')





    
    return df




global_admin = dash.Dash(__name__,suppress_callback_exceptions=True)



global_admin.layout = html.Div([
        html.Link(
            href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap", 
            rel="stylesheet"
        ),
        # html.H1("Global Admin Dashboard", className="page-title"),

        html.Div([




html.Div([
# Row 1: Split into two sections (side by side)
html.Div([
    # Section 1: Images
    html.Div([
            html.Img(src="assets/Vardaan_RCMS.png", alt="Main Converted Image", className='small-image'),  # Image with alt text
], className="image-container"),

    # Section 2: Heading and Chart
    html.Div([
        html.Span("Total Activities", className="metric-title"),  # Heading
        html.Span(id='total-activities', className='metric-value due'),  # Metric value
        dcc.Graph(id='total-activities-donut', config={'displayModeBar': False}, className='metric-donut'),  # Donut chart
    ], className="heading-chart-container"),
], className="row two-sections", style={
'border': '1px solid #ddd', 
'box-shadow': '0 4px 8px rgba(0, 0, 0, 0.1)', 
'border-radius': '10px', 
'padding': '20px', 
'background-color': 'white',
'width': '270px',  # Fixed width (adjust as needed)
'margin': '0 auto'  # Center the container horizontally
}),
# Row 2: Completed and Completed with Delay
html.Div([
    html.Div([
        html.Span("Completed Activities", className="metric-title"),
        html.Span(id='completed-activities', className='metric-value completed'),
        dcc.Graph(id='completed-activities-donut', config={'displayModeBar': False}, className='metric-donut'),
    ], className="metric-box"),
    html.Div([
        html.Span("Completed with Delay", className="metric-title"),
        html.Span(id='completed-delay-activities', className='metric-value delay'),
        dcc.Graph(id='completed-delay-activities-donut', config={'displayModeBar': False}, className='metric-donut'),
    ], className="metric-box"),
], className="row two-columns"),

# Row 3: WIP and WIP with Delay
html.Div([
    html.Div([
        html.Span("WIP Activities", className="metric-title"),
        html.Span(id='wip-activities', className='metric-value wip'),
        dcc.Graph(id='wip-activities-donut', config={'displayModeBar': False}, className='metric-donut'),
    ], className="metric-box"),
    html.Div([
        html.Span("WIP With Delay", className="metric-title"),
        html.Span(id='wip-activities-delay', className='metric-value wip'),
        dcc.Graph(id='wip-delay-activities-donut', config={'displayModeBar': False}, className='metric-donut'),
    ], className="metric-box"),
], className="row two-columns"),

# Row 4: Yet to Start and Yet to Start with Delay
html.Div([
    html.Div([
        html.Span("Yet to Start", className="metric-title"),
        html.Span(id='yet-to-start-activities', className='metric-value yet-to-start'),
        dcc.Graph(id='yet-to-start-activities-donut', config={'displayModeBar': False}, className='metric-donut'),
    ], className="metric-box"),
    html.Div([
        html.Span("Yet to Start with Delay", className="metric-title"),
        html.Span(id='yet-to-start-delay-activities', className='metric-value yet-to-start-delay'),
        dcc.Graph(id='yet-to-start-delay-activities-donut', config={'displayModeBar': False}, className='metric-donut'),
    ], className="metric-box"),
], className="row two-columns"),

], className="activity-container")



,
# End of Activity Container

            html.Div([  # Data Container
                html.Div([  # Radio Container
                    html.Div([
                        html.Label('All', id='radio-all', n_clicks=0, className='radio-button active'),
                        html.Label('Internal', id='radio-internal', n_clicks=0, className='radio-button'),
                        html.Label('External', id='radio-external', n_clicks=0, className='radio-button'),
                    ], className='radio-container'),

                    html.Div([
                        html.Label('All Time', id='radio-all-time', n_clicks=0, className='radio-button active'),
                        html.Label('Current Month', id='radio-current-month', n_clicks=0, className='radio-button'),
                        html.Label('3 Months', id='radio-3-months', n_clicks=0, className='radio-button'),
                        html.Label('6 Months', id='radio-6-months', n_clicks=0, className='radio-button'),
                        html.Label('Next Month', id='radio-9-months', n_clicks=0, className='radio-button'),
                        html.Label('Next 3 Months', id='radio-1-year', n_clicks=0, className='radio-button'),
                    ], className='radio-container'),

                    html.Div([
                        html.Label('All', id='radio-mandatory-all', n_clicks=0, className='radio-button active'),
                        html.Label('Mandatory', id='radio-mandatory', n_clicks=0, className='radio-button'),
                        html.Label('Optional', id='radio-optional', n_clicks=0, className='radio-button'),
                    ], className='radio-container'),
                ], className="radio-container-wrapper"),  # End of Radio Container

                # First row: Two charts side by side
                    html.Div([
                        dcc.Graph(id='status-distribution-donut', className='chart',style={'margin-left':'0.5%','margin-top':'15px'}),
                        
                        dcc.Graph(id='factory-activities', className='chart',style={'margin-left':'-4%','margin-top':'-75px'}),
                        dcc.Graph(id='status-distribution-bar', className='chart',style={'margin-right':'2%','margin-top':'-65px'}),

                    ], className='charts-container'),

                    # Second row: Third chart and table side by side
                    html.Div([
                        # dcc.Graph(id='status-distribution-bar', className='status-distribution-bar',style={'margin-top':'-50px'}),
                            dcc.Graph(id='monthly-task-line-chart', className='status-distribution-bar', style={'margin-left': '7%', 'margin-top': '-12%'}),

                        html.Div([
                                html.H3("Details", className="table-heading",style={'margin-top':'-70px'}),                            
                                
                                dash_table.DataTable(
                                    id='audit-details-table',
                                    columns=[{'name': col, 'id': col} for col in ['Entity', 'criticality', 'Task', 'calculated_status', 'Count']],
                                                                            data=[],  # Leave it empty initially, will be filled later
                                    sort_action='native',
                                    page_action="none",
                                    style_table={
                                        'height': '200px',
                                        'overflowY': 'scroll',
                                        'overflowX': 'hidden',  # Remove horizontal scrolling
                                        'border': '1px solid #ddd',
                                        'padding': '4px',
                                        'width': '120%',
                                        'background': 'white',
                                        'margin-top': '-10px'  # Make sure the table takes full width
                                    },
                                    style_header={
                                        'backgroundColor': '#1E90FF',  # Sky blue header background to match the image
                                        'fontWeight': 'bold',  # Make header bold
                                        'border': '1px solid black',  # Add black border to header cells
                                        'textAlign': 'center',
                                        'color': 'white',  # Set header text to white for better contrast
                                        'font-family': 'Calibri',
                                    },
                                    style_data={
                                        'border': '1px solid black',  # Add black border to data cells
                                        'textAlign': 'center',
                                        'backgroundColor': 'white',
                                        'whiteSpace': 'normal',  # Enable text wrapping
                                        'height': 'auto',  # Adjust row height based on content
                                        'color': 'black',  # Set row text color to black
                                        'font-family': 'Calibri',  # Set font family to Calibri
                                    },
                                    style_data_conditional=[
                                        {
                                            'if': {'row_index': 'odd'},
                                            'backgroundColor': '#a6d6f3'  # Light grey for odd rows
                                        },
                                        {
                                            'if': {'row_index': 'even'},
                                            'backgroundColor': '#FFFFFF'  # White for even rows
                                        },
                                    ]
                                )

                        ], className='table-container',style={'margin-left':'-20px'})
                    ], className='second-row-container'),  # End of Charts Container

            ], className="data-container")  # End of Data Container

        ], className="main-container"),

        # Adding missing dcc.Store components for callbacks
        dcc.Store(id='selected-internal-external', data='All'),
        dcc.Store(id='selected-time-range', data='All Time'),
        dcc.Store(id='selected-mandatory-optional', data='All'),

        # Adding missing dcc.Interval component for periodic updates
        dcc.Interval(id='interval-component', interval=60 * 10000, n_intervals=0)

    ], className="main-wrapper")



def add_months(start_year, start_month, months_to_add):
    """
    Add months to a given year and month, adjusting the year if the month exceeds 12.
    
    :param start_year: The initial year (integer)
    :param start_month: The initial month (integer, 1-12)
    :param months_to_add: Number of months to add (integer)
    :return: A tuple (new_year, new_month)
    """
    # Calculate the new month and adjust the year if necessary
    new_month = start_month + months_to_add
    new_year = start_year + (new_month - 1) // 12  # Adjust the year based on months exceeding 12
    new_month = (new_month - 1) % 12 + 1  # Adjust month to stay within 1-12

    print(new_year,new_month)
    
    return new_year, new_month

def filter_by_date_range(df, selected_range):
    today = datetime.today()

    # Convert 'start_date' to datetime format to ensure proper filtering
    # print(len(df['due_on']))
    df['due_on'] = pd.to_datetime(df['due_on'], format='%d/%m/%Y', errors='coerce')
    # print(df['due_on'])

    # Extract the month and year from 'start_date'
    df['start_month'] = df['due_on'].dt.month
    df['start_year'] = df['due_on'].dt.year
    # print(df['start_month'])


    # Get current month and year
    current_month = today.month
    current_year = today.year
    # print(current_month,current_year)

    # Filter based on the selected range
    if selected_range == 'Current Month':
        # Return only the rows where the month and year match the current month and year
        df=df[(df['start_month'] == current_month)]
        print(current_month)
        print(df)
        return df

    elif selected_range == '3 Months':
        # Filter for the current month and the previous 2 months
        start_period = today - pd.DateOffset(months=2)  # Get the month and year from 2 months ago
        return df[(df['due_on'] >= pd.Timestamp(start_period.year, start_period.month, 1)) &
                (df['due_on'] <= pd.Timestamp(current_year, current_month, 1))]

    elif selected_range == '6 Months':
        # Filter for the current month and the previous 5 months
        start_period = today - pd.DateOffset(months=5)  # Get the month and year from 5 months ago
        return df[(df['due_on'] >= pd.Timestamp(start_period.year, start_period.month, 1)) &
                (df['due_on'] <= pd.Timestamp(current_year, current_month, 1))]

    elif selected_range == 'Coming Month':
    # Get the first day of the next month
        next_month = today + pd.DateOffset(months=1)

        # Set the start and end of the next month
        start_period = pd.Timestamp(next_month.year, next_month.month, 1)  # First day of the next month
        end_period = pd.Timestamp(next_month.year, next_month.month + 1, 1) - pd.DateOffset(days=1)  # Last day of the next month

        # Filter the DataFrame for dates in the next month
        return df[(df['due_on'] >= start_period) & (df['due_on'] <= end_period)]

    elif selected_range == 'Coming 3 Months':
        next_month = today + pd.DateOffset(months=1)

        # Set the start date to the first day of the next month
        start_period = pd.Timestamp(next_month.year, next_month.month, 1) 
        print(start_period) # First day of the next month

        # Calculate the new year and month by adding 2 additional months to next_month
        new_year, new_month = add_months(next_month.year, next_month.month, 3)

        # Set the end date to the last day of the third month
        end_period = pd.Timestamp(new_year, new_month + 1, 1) - pd.DateOffset(days=1)  # Last day of the third month

        # Filter the DataFrame for dates in the next 3 months
        return df[(df['due_on'] >= start_period) & (df['due_on'] <= end_period)]


    elif selected_range == 'All Time':
        # If "All Time" is selected, return the entire DataFrame
        return df

    else:
        # If the selection does not match any expected range, return the entire DataFrame
        return df

    return df






@global_admin.callback(
    [Output('selected-internal-external', 'data'),
    Output('selected-time-range', 'data'),
    Output('selected-mandatory-optional', 'data')],
    [Input('radio-all', 'n_clicks'),
    Input('radio-internal', 'n_clicks'),
    Input('radio-external', 'n_clicks'),
    Input('radio-all-time', 'n_clicks'),
    Input('radio-current-month', 'n_clicks'),
    Input('radio-3-months', 'n_clicks'),
    Input('radio-6-months', 'n_clicks'),
    Input('radio-9-months', 'n_clicks'),
    Input('radio-1-year', 'n_clicks'),
    Input('radio-mandatory-all', 'n_clicks'),
    Input('radio-mandatory', 'n_clicks'),
    Input('radio-optional', 'n_clicks')],
    [State('selected-internal-external', 'data'),
    State('selected-time-range', 'data'),
    State('selected-mandatory-optional', 'data')]
)
def update_filters(all_clicks, internal_clicks, 
                external_clicks, all_time_clicks, 
                current_month_clicks, three_months_clicks, 
                six_months_clicks, nine_months_clicks, one_year_clicks, 
                mandatory_all_clicks, mandatory_clicks, optional_clicks, 
                stored_internal, stored_time_range, stored_mandatory):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Set initial filter states based on the stored values
    selected_filter = stored_internal
    selected_time_range = stored_time_range
    selected_mandatory_filter = stored_mandatory

    # Update the state of the filter that was triggered
    if triggered_id == 'radio-internal':
        selected_filter = 'Internal'
    elif triggered_id == 'radio-external':
        selected_filter = 'External'
    elif triggered_id == 'radio-all':
        selected_filter = 'All'

    if triggered_id == 'radio-all-time':
        selected_time_range = 'All Time'
    elif triggered_id == 'radio-current-month':
        selected_time_range = 'Current Month'
    elif triggered_id == 'radio-3-months':
        selected_time_range = '3 Months'
    elif triggered_id == 'radio-6-months':
        selected_time_range = '6 Months'
    elif triggered_id == 'radio-9-months':
        selected_time_range = 'Coming Month'
    elif triggered_id == 'radio-1-year':
        selected_time_range = 'Coming 3 Months'

    if triggered_id == 'radio-mandatory':
        selected_mandatory_filter = 'Mandatory'
    elif triggered_id == 'radio-optional':
        selected_mandatory_filter = 'Optional'
    elif triggered_id == 'radio-mandatory-all':
        selected_mandatory_filter = 'All'

    return selected_filter, selected_time_range, selected_mandatory_filter


@global_admin.callback(
    [Output('radio-all', 'style'),
    Output('radio-internal', 'style'),
    Output('radio-external', 'style'),
    Output('radio-mandatory-all', 'style'),
    Output('radio-mandatory', 'style'),
    Output('radio-optional', 'style'),
    Output('radio-all-time', 'style'),
    Output('radio-current-month', 'style'),
    Output('radio-3-months', 'style'),
    Output('radio-6-months', 'style'),
    Output('radio-9-months', 'style'),
    Output('radio-1-year', 'style')],
    [Input('selected-internal-external', 'data'),
    Input('selected-time-range', 'data'),
    Input('selected-mandatory-optional', 'data')]
)
def update_styles(selected_filter, selected_time_range, selected_mandatory_filter):
    # Dynamic styling based on the current selections
    all_style = {'background-color': '#007bff', 'color': 'white'} if selected_filter == 'All' else {}
    internal_style = {'background-color': '#007bff', 'color': 'white'} if selected_filter == 'Internal' else {}
    external_style = {'background-color': '#007bff', 'color': 'white'} if selected_filter == 'External' else {}

    all_time_style = {'background-color': '#007bff', 'color': 'white'} if selected_time_range == 'All Time' else {}
    current_month_style = {'background-color': '#007bff', 'color': 'white'} if selected_time_range == 'Current Month' else {}
    three_months_style = {'background-color': '#007bff', 'color': 'white'} if selected_time_range == '3 Months' else {}
    six_months_style = {'background-color': '#007bff', 'color': 'white'} if selected_time_range == '6 Months' else {}
    nine_months_style = {'background-color': '#007bff', 'color': 'white'} if selected_time_range == 'Coming Month' else {}
    one_year_style = {'background-color': '#007bff', 'color': 'white'} if selected_time_range == 'Coming 3 Months' else {}

    mandatory_all_style = {'background-color': '#007bff', 'color': 'white'} if selected_mandatory_filter == 'All' else {}
    mandatory_style = {'background-color': '#007bff', 'color': 'white'} if selected_mandatory_filter == 'Mandatory' else {}
    optional_style = {'background-color': '#007bff', 'color': 'white'} if selected_mandatory_filter == 'Optional' else {}

    return (all_style, internal_style, external_style, mandatory_all_style, mandatory_style, optional_style,
            all_time_style, current_month_style, three_months_style, six_months_style, nine_months_style, one_year_style)



# Combined callback to handle multiple radio button selections and filtering
# Combined callback to handle multiple radio button selections and filtering


def ensure_all_criticality_levels(df, category_column, critical_category_order):
    existing_categories = df[category_column].unique()
    missing_categories = [category for category in critical_category_order if category not in existing_categories]
    
    # Append missing criticality categories with count = 0
    for category in missing_categories:
        for entity in df['Entity'].unique():
            df = pd.concat([df, pd.DataFrame({category_column: [category], 'count': [0], 'Entity': [entity]})])
    
    return df


@global_admin.callback(
[Output('audit-details-table', 'data'),
    Output('audit-details-table', 'columns'),
    Output('total-activities-donut', 'figure'),
    Output('completed-activities-donut', 'figure'),
    Output('completed-delay-activities-donut', 'figure'),
    Output('wip-activities-donut', 'figure'),
Output('wip-delay-activities-donut', 'figure'),
    Output('yet-to-start-activities-donut', 'figure'),
    Output('yet-to-start-delay-activities-donut', 'figure'),
    Output('status-distribution-donut', 'figure'),
    Output('factory-activities', 'figure'),
    Output('status-distribution-bar', 'figure'),
    Output('monthly-task-line-chart', 'figure')],
[Input('factory-activities', 'clickData'),
    Input('monthly-task-line-chart', 'clickData'),
    Input('status-distribution-bar', 'clickData'),
    Input('status-distribution-donut', 'clickData'),
    Input('interval-component', 'n_intervals'),
    Input('selected-internal-external', 'data'),
    Input('selected-time-range', 'data'),
    Input('selected-mandatory-optional', 'data')
    ]
)
def update_dashboard(statusClickData, regulationClickData,criticalityClickData, 
                    donutClickData, n_intervals, selected_filter, 
                    selected_time_range, selected_mandatory_filter):

    color_map = {
        'Completed': '#4CAF50',  # Green
        'Completed with Delay': '#268567',  #  alternate green shade

        'WIP': '#2196F3',  # Blue
        'WIP with Delay': '#F44336',  # Red

        'Yet to Start': '#720e9e',  # Dark Purple
        'Yet to Start with Delay': '#8055cb',  # purple shade
        
        
        
    }


# Get the selected filter values
    
    
    

    
    # Fetch and process data from MySQL
    df= fetch_and_process_data_from_mysql()

    # Apply the internal/external filter
    if selected_filter != 'All':
        # print('the selected filter is ',selected_filter[0])
        df['internal_external'] = df['internal_external'].str.strip().str.lower()
        selected_filter = selected_filter.lower()
        df = df[df['internal_external'] == selected_filter[0]]
    
    # Apply the time filter
    df = filter_by_date_range(df, selected_time_range)
    
    # Apply the mandatory/optional filter
    if selected_mandatory_filter != 'All':
        df['mandatory_optional'] = df['mandatory_optional'].str.strip().str.lower()
        selected_mandatory_filter = selected_mandatory_filter.lower()
        df = df[df['mandatory_optional'] == selected_mandatory_filter[0]]
    # Metrics
    total_activities = len(df)
    completed_activities = len(df[df['calculated_status'] == 'Completed'])
    completed_delay_activities = len(df[df['calculated_status'] == 'Completed with Delay'])
    wip_activities = len(df[df['calculated_status'] == 'WIP'])
    wip_delay_activities = len(df[df['calculated_status'] == 'WIP with Delay'])
    not_started_activities = len(df[df['calculated_status'] == 'Yet to Start'])
    not_started_activities_with_delay = len(df[df['calculated_status'] == 'Yet to Start with Delay'])
    print(not_started_activities)

    category_order = [
    'Completed', 'Yet to Start', 'WIP', 'WIP with Delay', 'Completed with Delay', 'Yet to Start with Delay'



]   
    

    critical_color_map = {
'High': '#D32F2F',  # Dark Red for High criticality
'Medium': '#00c2ff',  # Light Blue for Medium criticality
'Low': '#44ff8a',  # Light Green for Low criticality
}


# Define the fixed category order to ensure constant status order in the legends
    critical_category_order = ['High','Medium','Low'
    ]

    

    

    # Generate donut charts for each metric
    total_activities_donut = create_donut_chart(total_activities, total_activities, '#17a2b8')
    completed_activities_donut = create_donut_chart(completed_activities, total_activities, '#4CAF50')
    completed_delay_donut = create_donut_chart(completed_delay_activities, total_activities, '#268567')
    wip_activities_donut = create_donut_chart(wip_activities, total_activities, '#2196F3')
    wip_delay_donut = create_donut_chart(wip_delay_activities, total_activities, '#F44336')
    yet_to_start_donut = create_donut_chart(not_started_activities, total_activities, '#720e9e')
    yet_to_start_delay_donut = create_donut_chart(not_started_activities_with_delay, total_activities, '#8055CB')







            # Pie Chart: Status Distribution
            # Pie Chart: Status Distribution (Donut) with no background


    df = filter_by_date_range(df, selected_time_range)

    # Group by Entity and Month and count the tasks for each
    df['month'] = df['due_on'].dt.to_period('M')  # Extract month after filtering
    df_monthly_task_count = df.groupby(['Entity', 'month']).size().reset_index(name='task_count')

#     # Convert 'month' to string for better visualization
#     df_monthly_task_count['month'] = df_monthly_task_count['month'].astype(str)


    task_count_df = df.groupby(['Entity','entity_id', 'regulation_name']).size().reset_index(name='Task')

    # Create a horizontal stacked bar chart showing regulation task counts by entity
    line_chart = px.bar(
        task_count_df,
        y='entity_id',  # Entities on y-axis
        x='Task',  # Task count on x-axis
        color='regulation_name',  # Regulations color-coded
        labels={'Entity': 'Entity', 'Task Count': 'Task', 'Regulation': 'regulation_name'},  # Axis labels
        orientation='h',  # Horizontal bar graph
        height=400,
        width=600,
    )

    # Update layout to style the chart
    line_chart.update_layout(
        title=None,
        margin=dict(l=20, r=20, t=75, b=75),
        bargap=0.4,
        bargroupgap=0.5,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background (paper)
        # plot_bgcolor='rgba(0,0,0,0)'  # Transparent plot background
    )


    line_chart.update_xaxes(title=None)

            

    status_distribution_donut = px.pie(
        df,
        names='calculated_status',
        hole=0.7,
        height=300,  # Adjust the height to fit better
        width=400,  # Adjust the width to fit better
        category_orders={"calculated_status": category_order},
        color='calculated_status',
        color_discrete_map=color_map
    )

    # Apply custom colors for each calculated status and ensure no labels overlap
    status_distribution_donut.update_traces(
        textinfo='percent+label',  # Show both percentage and label
        textposition='outside',  # Position the text outside the donut chart
        hoverinfo='label+percent',  # Show hover info with label and percentage
        marker=dict(line=dict(color='rgba(0,0,0,0)', width=0))  # Remove the border lines around the segments
    )

    # Remove title, legend, and background
    status_distribution_donut.update_layout(
        title=None,  # No title
        showlegend=False,  # Disable the legend
        margin=dict(l=10, r=120, t=0, b=
                    50),  # Remove all margins
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background (paper)
        plot_bgcolor='rgba(0,0,0,0)'  # Transparent plot area background
    )



    # Bar Chart: Factor-wise Activities by Criticality
    factory_criticality_counts = df.groupby(['Entity', 'criticality']).size().reset_index(name='count')
    factory_criticality_counts = ensure_all_criticality_levels(factory_criticality_counts, 'criticality', critical_category_order)

    status_distribution_bar = px.bar(
        factory_criticality_counts,
        x='Entity',
        y='count',
        color='criticality',
        labels={'Entity': 'Entity', 'count': 'Total Activities'},
        barmode='group',
        height=350,
        width=500,
        category_orders={"criticality": critical_category_order},
        color_discrete_map=critical_color_map
    )

    # Remove title from the bar chart
    status_distribution_bar.update_layout(
        title=None,
        

        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background (paper)
        # plot_bgcolor='rgba(0,0,0,0)' 
    )

    status_distribution_bar.update_layout(
        margin=dict(l=15, r=110, t=50, b=20),  # Adequate margin to prevent label cut-off
        title_x=0.04,  # Center the title horizontally
        title_y=0.95,
        legend_title_text='',
        legend=dict(
            orientation="h",  # Horizontal legend
            yanchor="bottom",
            y=-0.3,  # Positioning the legend below the chart
            xanchor="center",
            x=0.5,
            font=dict(size=9)
        )
    )

    # Bar Chart: Activities by Entity and Status
    factory_status_counts = df.groupby(['Entity', 'calculated_status']).size().reset_index(name='count')

    factory_activities = px.bar(
        factory_status_counts,
        x='Entity',
        y='count',
        color='calculated_status',
        labels={'Entity': 'Entity', 'count': 'Total Activities'},
        barmode='stack',
        height=350,
        width=400,
        category_orders={"calculated_status": category_order},
        color_discrete_map=color_map
    )

    # Additional updates for layout and spacing
    factory_activities.update_layout(
        title=None,  # No title
        showlegend=False,
        bargap=0.4,
        bargroupgap=0.5,
        margin=dict(l=25, r=25, t=50, b=50),
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background (paper)
        # plot_bgcolor='rgba(0,0,0,0)' 
    )

    

    default_data = df[df['calculated_status'].isin(['WIP', 'Completed','Completed with Delay','Yet to Start', 'WIP with Delay', 'Yet to Start with Delay'])]

    # Group the default filtered data
    grouped_data = default_data.groupby(['Entity', 'calculated_status']).size().reset_index(name='Count')


    if  donutClickData:
        clicked_status = donutClickData['points'][0]['label']
        
        # Filter the DataFrame for the clicked status
        filtered_df = df[df['calculated_status'] == clicked_status]

        if statusClickData:
            clicked_factory = statusClickData['points'][0]['x']
            filtered_df = filtered_df[filtered_df['Entity'] == clicked_factory]


            # -----------------------------------------------------------------------------------------------------------------------------------
        elif regulationClickData:
            clicked_regulation = regulationClickData['points'][0]['y']
            count_clicked_regulation = regulationClickData['points'][0]['x']

            factory_filtered_df = filtered_df[filtered_df['Entity'] == clicked_regulation]

            status_counts_df = factory_filtered_df.groupby('regulation_name').size().reset_index(name='count')

            print(status_counts_df)

            matched_status = status_counts_df[status_counts_df['count'] == count_clicked_regulation]['regulation_name'].values[0]

            print(f"Factory: {clicked_regulation}, Status: {matched_status}, Count: {count_clicked_regulation}")

            print(clicked_regulation,'is regulation')
            filtered_df = df[(df['Entity'] == clicked_regulation) &(df['regulation_name'] == matched_status) &(df['calculated_status'] == clicked_status)]


            # --------------------------------------------------------------------------------------------------------------------------------------
        
        # Update the table based on the clicked status
        status_grouped_data = filtered_df.groupby(['Entity', 'calculated_status']).size().reset_index(name='Count')
        
        
        # Update the factory activities chart based on the clicked status
        factory_status_counts = filtered_df.groupby(['Entity', 'calculated_status']).size().reset_index(name='count')
        print(status_grouped_data)
        print(factory_status_counts)


        regulation_status_counts=filtered_df.groupby(['Entity', 'regulation_name']).size().reset_index(name='Task')

        # update critical chart based on the clicked status
        # critical_status_counts = filtered_df.groupby(['Entity', 'criticality', 'calculated_status']).size().reset_index(name='count')
        
        factory_activities = px.bar(
            factory_status_counts,
            x='Entity',
            y='count',
            color='calculated_status',
            title=f"Activities by Entity and {clicked_status}",
            labels={'Entity': 'Entity', 'count': 'Total Activities'},
            barmode='stack',
            color_discrete_map={clicked_status: color_map[clicked_status]}  # Only apply clicked status color
        )

        factory_activities.update_layout(
                margin=dict(l=50, r=50, t=75, b=75),  # Adequate margin to prevent label cut-off
                title_x=0.001,  # Center the title horizontally
                title_y=0.95,
                legend_title_text='',
                legend=dict(
                    orientation="h",  # Horizontal legend
                    yanchor="bottom",
                    y=-0.6,  # Positioning the legend below the chart
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11)
                )
            )

        factory_activities.update_layout(
                bargap=0.1,  # Increase gap between bars within the same group to make them narrower
                bargroupgap=0.7  # Increase gap between groups of bars
            )
        

        critical_status_counts = df.groupby(['Entity', 'criticality', 'calculated_status']).size().reset_index(name='count')
        status_distribution_bar = px.bar(
            critical_status_counts,
            x='Entity',
            y='count',
            color='criticality',
            title=f"Activities by Entity and Criticality for {clicked_status}",
            labels={'Entity': 'Entity', 'count': 'Total Activities'},
            barmode='group',
            category_orders={"criticality": critical_category_order},
            color_discrete_map=critical_color_map
        )

        status_distribution_bar.update_layout(
            margin=dict(l=50, r=50, t=75, b=75),
            title_x=0.001,
            title_y=0.95,
            legend_title_text='',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5,
                font=dict(size=11)
            )
        )

        # Create a horizontal stacked bar chart showing regulation task counts by entity
        line_chart = px.bar(
            regulation_status_counts,
            y='Entity',  # Entities on y-axis
            x='Task',  # Task count on x-axis
            color='regulation_name',  # Regulations color-coded
            labels={'Entity': 'Entity', 'Task Count': 'Task', 'Regulation': 'regulation_name'},  # Axis labels
            orientation='h',  # Horizontal bar graph
            height=400,
            width=600,
        )

        # Update layout to style the chart
        line_chart.update_layout(
            title=None,
            margin=dict(l=20, r=20, t=75, b=75),
            bargap=0.4,
            bargroupgap=0.5,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',  # Transparent background (paper)
            # plot_bgcolor='rgba(0,0,0,0)'  # Transparent plot background
        )

        # Format 'due_on' to 'dd-mon-yyyy' format
        filtered_df['due_on'] = pd.to_datetime(filtered_df['due_on'], format='%d/%m/%Y', errors='coerce')
        filtered_df['due_on'] = filtered_df['due_on'].dt.strftime('%d-%b-%Y')


        columns = [{'name': 'Entity', 'id': 'Entity'},
                    {'name': 'Regulation', 'id': 'regulation_name'},
                {'name': 'Status', 'id': 'calculated_status'},
                {'name': 'Task', 'id': 'Task'},
                {'name': 'due_on', 'id': 'due_on'}]

        # Return table data, columns, and updated metrics
        return (filtered_df[['Entity', 'regulation_name','calculated_status', 'Task','due_on']].to_dict('records'), columns,\
                total_activities_donut, completed_activities_donut, completed_delay_donut, wip_activities_donut,\
    wip_delay_donut , yet_to_start_donut,yet_to_start_delay_donut,\
    status_distribution_donut, \
    factory_activities, status_distribution_bar ,line_chart)




    # If "factory-activities" chart was clicked
    elif statusClickData:
        clicked_factory = statusClickData['points'][0]['x']
        clicked_status = category_order[statusClickData['points'][0]['curveNumber']]
        current_date = pd.Timestamp(datetime.today().date())
        print(current_date)

        entiry_df=df[df['Entity'] == clicked_factory]
        filtered_df = df[((df['Entity'] == clicked_factory) & (df['calculated_status'] == clicked_status) ) & ((df['due_on'] > current_date) )]

        # Format 'due_on' to 'dd-mon-yyyy' format
        filtered_df['due_on'] = pd.to_datetime(filtered_df['due_on'], format='%d/%m/%Y', errors='coerce')
        filtered_df['due_on'] = filtered_df['due_on'].dt.strftime('%d-%b-%Y')

        # Define the columns and return the filtered data
        columns = [{'name': 'Entity', 'id': 'Entity'},
                {'name': 'Category', 'id': 'Category'},
                {'name': 'Task', 'id': 'Task'},
                {'name': 'Status', 'id': 'calculated_status'},
                {'name': 'due_on', 'id': 'due_on'}]
        


        total_activities = len(entiry_df)
        completed_activities = len(entiry_df[entiry_df['calculated_status'] == 'Completed'])
        completed_delay_activities = len(entiry_df[entiry_df['calculated_status'] == 'Completed with Delay'])
        wip_activities = len(entiry_df[entiry_df['calculated_status'] == 'WIP'])
        wip_delay_activities = len(entiry_df[entiry_df['calculated_status'] == 'WIP with Delay'])
        not_started_activities = len(entiry_df[entiry_df['calculated_status'] == 'Yet to Start'])
        not_started_activities_with_delay = len(entiry_df[entiry_df['calculated_status'] == 'Yet to Start with Delay'])
        print(not_started_activities)


        # Generate donut charts for each metric
        total_activities_donut = create_donut_chart(total_activities, total_activities, '#4CAF50')
        completed_activities_donut = create_donut_chart(completed_activities, total_activities, '#4CAF50')
        completed_delay_donut = create_donut_chart(completed_delay_activities, total_activities, '#FF9800')
        wip_activities_donut = create_donut_chart(wip_activities, total_activities, '#007bff')
        wip_delay_donut = create_donut_chart(wip_delay_activities, total_activities, '#F44336')
        yet_to_start_donut = create_donut_chart(not_started_activities, total_activities, '#5C63F2')
        yet_to_start_delay_donut = create_donut_chart(not_started_activities_with_delay, total_activities, '#ffbf00')

        return filtered_df[['Entity', 'Category', 'Task', 'calculated_status','due_on']].to_dict('records'), columns, \
            total_activities_donut, completed_activities_donut, completed_delay_donut, wip_activities_donut,\
    wip_delay_donut , yet_to_start_donut,yet_to_start_delay_donut,\
    status_distribution_donut, \
    factory_activities, status_distribution_bar ,line_chart

        # Inside the main callback function for update_dashboard

    # If "status-distribution-bar" was clicked
    elif criticalityClickData:
        clicked_factory = criticalityClickData['points'][0]['x']
        clicked_criticality = critical_category_order[criticalityClickData['points'][0]['curveNumber']]
        filtered_df = df[(df['Entity'] == clicked_factory) & (df['criticality'] == clicked_criticality)]

        entiry_df = df[(df['Entity'] == clicked_factory) & (df['criticality'] == clicked_criticality)]



        total_activities = len(entiry_df)
        completed_activities = len(entiry_df[entiry_df['calculated_status'] == 'Completed'])
        completed_delay_activities = len(entiry_df[entiry_df['calculated_status'] == 'Completed with Delay'])
        wip_activities = len(entiry_df[entiry_df['calculated_status'] == 'WIP'])
        wip_delay_activities = len(entiry_df[entiry_df['calculated_status'] == 'WIP with Delay'])
        not_started_activities = len(entiry_df[entiry_df['calculated_status'] == 'Yet to Start'])
        not_started_activities_with_delay = len(entiry_df[entiry_df['calculated_status'] == 'Yet to Start with Delay'])
        print(not_started_activities)


        # Generate donut charts for each metric
        total_activities_donut = create_donut_chart(total_activities, total_activities, '#4CAF50')
        completed_activities_donut = create_donut_chart(completed_activities, total_activities, '#4CAF50')
        completed_delay_donut = create_donut_chart(completed_delay_activities, total_activities, '#FF9800')
        wip_activities_donut = create_donut_chart(wip_activities, total_activities, '#007bff')
        wip_delay_donut = create_donut_chart(wip_delay_activities, total_activities, '#F44336')
        yet_to_start_donut = create_donut_chart(not_started_activities, total_activities, '#5C63F2')
        yet_to_start_delay_donut = create_donut_chart(not_started_activities_with_delay, total_activities, '#ffbf00')

        columns = [
            {'name': 'Entity', 'id': 'Entity'},
            {'name': 'Criticality', 'id': 'criticality'},
            {'name': 'Task', 'id': 'Task'},
            {'name': 'Status', 'id': 'calculated_status'}  # Include status in the table
        ]

        return filtered_df[['Entity', 'criticality', 'Task', 'calculated_status']].to_dict('records'), columns, \
            total_activities_donut, completed_activities_donut, completed_delay_donut, wip_activities_donut,\
        wip_delay_donut , yet_to_start_donut,yet_to_start_delay_donut,\
        status_distribution_donut, \
        factory_activities, status_distribution_bar ,line_chart
    
    elif regulationClickData:
        clicked_regulation = regulationClickData['points'][0]['y']
        count_clicked_regulation = regulationClickData['points'][0]['x']

        factory_filtered_df = df[df['entity_id'] == clicked_regulation]

        status_counts_df = factory_filtered_df.groupby(['Entity','regulation_name']).size().reset_index(name='count')
        print('-----------------------------------------------------------------------------------------')
        print(len(status_counts_df))

        matched_status = status_counts_df[status_counts_df['count'] == count_clicked_regulation]['regulation_name'].values[0]

        print(f"Factory: {clicked_regulation}, Status: {matched_status}, Count: {count_clicked_regulation}")

        print(clicked_regulation,'is regulation')
        filtered_df = df[(df['entity_id'] == clicked_regulation) &(df['regulation_name'] == matched_status)]

        entiry_df = df[(df['entity_id'] == clicked_regulation) &(df['regulation_name'] == matched_status)]

        total_activities = len(entiry_df)
        completed_activities = len(entiry_df[entiry_df['calculated_status'] == 'Completed'])
        completed_delay_activities = len(entiry_df[entiry_df['calculated_status'] == 'Completed with Delay'])
        wip_activities = len(entiry_df[entiry_df['calculated_status'] == 'WIP'])
        wip_delay_activities = len(entiry_df[entiry_df['calculated_status'] == 'WIP with Delay'])
        not_started_activities = len(entiry_df[entiry_df['calculated_status'] == 'Yet to Start'])
        not_started_activities_with_delay = len(entiry_df[entiry_df['calculated_status'] == 'Yet to Start with Delay'])
        print(not_started_activities)


        # Generate donut charts for each metric
        total_activities_donut = create_donut_chart(total_activities, total_activities, '#4CAF50')
        completed_activities_donut = create_donut_chart(completed_activities, total_activities, '#4CAF50')
        completed_delay_donut = create_donut_chart(completed_delay_activities, total_activities, '#FF9800')
        wip_activities_donut = create_donut_chart(wip_activities, total_activities, '#007bff')
        wip_delay_donut = create_donut_chart(wip_delay_activities, total_activities, '#F44336')
        yet_to_start_donut = create_donut_chart(not_started_activities, total_activities, '#5C63F2')
        yet_to_start_delay_donut = create_donut_chart(not_started_activities_with_delay, total_activities, '#ffbf00')





        columns = [
            {'name': 'Regulation', 'id': 'regulation_name'},
            {'name': 'Task', 'id': 'Task'},
            {'name': 'Status', 'id': 'calculated_status'}  # Include status in the table
        ]

        return filtered_df[['Entity', 'regulation_name', 'Task', 'calculated_status']].to_dict('records'), columns, \
            total_activities_donut, completed_activities_donut, completed_delay_donut, wip_activities_donut,\
        wip_delay_donut , yet_to_start_donut,yet_to_start_delay_donut,\
        status_distribution_donut, \
        factory_activities, status_distribution_bar ,line_chart


    # Return default values if no specific chart is clicked
    return grouped_data[['Entity', 'calculated_status', 'Count']].to_dict('records'), [
            {'name': 'Entity', 'id': 'Entity'},  
            {'name': 'Status', 'id': 'calculated_status'},
            {'name': 'Count', 'id': 'Count'}], \
        total_activities_donut, completed_activities_donut, completed_delay_donut, wip_activities_donut,\
        wip_delay_donut , yet_to_start_donut,yet_to_start_delay_donut,\
        status_distribution_donut, \
        factory_activities, status_distribution_bar ,line_chart
    




# Run the app
if __name__ == '__main__':
    global_admin.run_server(debug=True)
