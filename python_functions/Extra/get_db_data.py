import mysql.connector
import pandas as pd

# Function to get entire dataset without filtering by entity_id
def get_entire_data():
    # Establishing a connection to the database
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="rcms"
    )



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
    FROM final_rcms_data
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
        category_id
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

