import streamlit as st
import sqlite3
from hashlib import sha256
import pandas as pd
import google.generativeai as genai
import os
import subprocess
from urllib.parse import urlencode

# Check for the google-generativeai package
output = subprocess.run(["pip", "show", "google-generativeai"], capture_output=True, text=True)
print(output.stdout)

# Set page configuration
st.set_page_config(layout="wide", page_title="SQL Query Assistant", page_icon="🔍")

# Enhanced styling with more modern look
st.markdown(
    """
    <style>
        /* Main Theme Colors */
        :root {
            --primary: #7B68EE;
            --secondary: #6A5ACD;
            --background: #F8F9FA;
            --card-bg: #FFFFFF;
            --text: #333333;
            --accent: #FF6B6B;
            --success: #4CAF50;
            --warning: #FFC107;
            --error: #F44336;
        }
        
        /* Global Styles */
        .stApp {
            background-color: var(--background);
            color: var(--text);
        }
        
        h1, h2, h3 {
            color: var(--primary);
            font-weight: 600;
        }
        
        /* Sidebar Styling */
        .stSidebar {
            background-color: var(--card-bg);
            border-right: 1px solid #E0E0E0;
            padding: 2rem 1rem;
        }
        
        /* Button Styling */
        .stButton button {
            background-color: var(--primary);
            color: white;
            font-weight: 500;
            border-radius: 6px;
            border: none;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }
        
        .stButton button:hover {
            background-color: var(--secondary);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Card Styling for Content Areas */
        .card {
            background-color: var(--card-bg);
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
        }
        
        /* SQL Query Display */
        .sql-query {
            background-color: #282c34;
            color: #abb2bf;
            font-family: 'Courier New', monospace;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid var(--primary);
        }
        
        /* Table Styling */
        .dataframe {
            border-collapse: collapse;
            width: 100%;
            border: none;
            font-size: 14px;
        }
        
        .dataframe th {
            background-color: var(--primary);
            color: white;
            padding: 10px;
            text-align: left;
        }
        
        .dataframe td {
            padding: 8px 10px;
            border-bottom: 1px solid #E0E0E0;
        }
        
        .dataframe tr:nth-child(even) {
            background-color: #F5F7FF;
        }
        
        /* Form Fields */
        input, textarea, select {
            border-radius: 6px !important;
            border: 1px solid #E0E0E0 !important;
        }
        
        /* Status Messages */
        .success-msg {
            color: var(--success);
            padding: 10px;
            border-radius: 6px;
            background: rgba(76, 175, 80, 0.1);
            border-left: 4px solid var(--success);
        }
        
        .error-msg {
            color: var(--error);
            padding: 10px;
            border-radius: 6px;
            background: rgba(244, 67, 54, 0.1);
            border-left: 4px solid var(--error);
        }
        
        .info-msg {
            color: var(--primary);
            padding: 10px;
            border-radius: 6px;
            background: rgba(123, 104, 238, 0.1);
            border-left: 4px solid var(--primary);
        }
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 6px 6px 0 0;
            color: var(--text);
            font-weight: 500;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: transparent;
            border-bottom: 2px solid var(--primary);
            color: var(--primary);
        }
        
        /* Add hover effect */
        .stTabs [data-baseweb="tab"]:hover {
            color: var(--primary);
        }
        
        /* Section Headers */
        .section-header {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #E0E0E0;
        }
        
        .section-header svg {
            margin-right: 0.5rem;
            color: var(--primary);
        }
        
        /* Animation for success messages */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .animated {
            animation: fadeIn 0.5s ease-in-out;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 1rem;
            font-size: 0.8rem;
            color: #999;
            margin-top: 2rem;
            border-top: 1px solid #E0E0E0;
        }
    </style>
    """,
    unsafe_allow_html=True
)

#############################################
# 1) USER AUTHENTICATION SETUP              #
#############################################
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            db_path TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return sha256(password.encode()).hexdigest()

def add_user(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
    conn.commit()
    conn.close()

def verify_user(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_db_path(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT db_path FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else None

def update_user_db_path(username, db_path):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET db_path = ? WHERE username = ?", (db_path, username))
    conn.commit()
    conn.close()

init_db()

# Initialize session state variables
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "show_table_data" not in st.session_state:
    st.session_state["show_table_data"] = False
if "table_edited" not in st.session_state:
    st.session_state["table_edited"] = False

# Sidebar Authentication UI with improved styling
with st.sidebar:
    st.markdown('<div class="section-header"><h2>👤 Account Access</h2></div>', unsafe_allow_html=True)
    
    # Only show logout if logged in
    if st.session_state["logged_in"]:
        if st.button("🚪 Logout", key="logout_btn"):
            st.session_state["logged_in"] = False
            for key in ["username", "db_schema", "db_path", "show_table_data"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        st.markdown(f"<div class='info-msg'>Welcome, <b>{st.session_state.get('username', 'User')}</b>!</div>", 
                    unsafe_allow_html=True)
    else:
        auth_choice = st.radio("Choose an option:", ["Login", "Sign Up"])
        
        with st.form(key="auth_form"):
            st.markdown("#### Enter your credentials")
            username_input = st.text_input("Username", key="username_input")
            password_input = st.text_input("Password", key="password_input", type="password")
            
            submit_text = "Sign Up" if auth_choice == "Sign Up" else "Login"
            submit_button = st.form_submit_button(f"🔐 {submit_text}")
            
            if submit_button:
                if not username_input or not password_input:
                    st.error("Please fill out both fields.")
                elif auth_choice == "Sign Up":
                    try:
                        add_user(username_input, password_input)
                        st.markdown("<div class='success-msg animated'>Account created successfully! Please log in.</div>", 
                                   unsafe_allow_html=True)
                    except sqlite3.IntegrityError:
                        st.markdown("<div class='error-msg animated'>Username already exists. Please choose a different username.</div>", 
                                  unsafe_allow_html=True)
                else:  # Login
                    user = verify_user(username_input, password_input)
                    if user:
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = username_input
                        # Load stored DB path (if any) for this user:
                        stored_path = get_user_db_path(username_input)
                        st.session_state["db_path"] = stored_path
                        st.rerun()
                    else:
                        st.markdown("<div class='error-msg animated'>Invalid username or password.</div>", 
                                  unsafe_allow_html=True)

    # Sidebar Info Section
    st.markdown("---")
    st.markdown("### 📊 App Features")
    st.markdown("""
    - Convert English to SQL queries
    - View & edit database tables
    - Share queries with others
    - Save your database for later use
    """)

#############################################
# 2) MAIN APP: FILE UPLOAD & SQL CONVERSION #
#############################################
if st.session_state["logged_in"]:
    current_user = st.session_state["username"]
    
    st.markdown("<h1 style='text-align: center;'>🔍 SQL Query Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-bottom: 2rem;'>Convert natural language to SQL queries and manage your database</p>", unsafe_allow_html=True)
    
    # Create tabs for different functionality
    tab1, tab2, tab3 = st.tabs(["📁 Database Management", "💬 Query Translator", "✏️ Table Editor"])
    
    with tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📁 Database Connection")
        st.markdown("Upload a database file or use your previously stored database.")
        
        # Use per-user keys for storing DB info
        schema_key = f"db_schema_{current_user}"
        path_key = f"db_path_{current_user}"
        
        # If a stored database exists for this user, ask if they want to use it
        stored_db = st.session_state.get("db_path", None)
        use_stored = False
        
        if stored_db and os.path.exists(stored_db):
            use_stored = st.checkbox("Use stored database", value=True)
            
            if use_stored:
                st.markdown(f"<div class='info-msg'>Using database: <code>{os.path.basename(stored_db)}</code></div>", 
                            unsafe_allow_html=True)
                db_path = stored_db
                st.session_state[path_key] = db_path
                
                # Extract schema from the stored database
                db_schema_dict = {}
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    for table in tables:
                        table_name = table[0]
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        schema_str = f"Table: {table_name}\n"
                        for col in columns:
                            schema_str += f"  - {col[1]} ({col[2]})\n"
                        db_schema_dict[table_name] = schema_str
                    conn.close()
                    st.session_state[schema_key] = db_schema_dict
                except Exception as e:
                    st.error(f"Error extracting schema from stored DB: {e}")
        
        # If not using stored DB, allow file upload to override
        if not use_stored:
            # Clear stored DB info for current user if they choose to upload new
            if "using_new_upload" not in st.session_state:
                st.session_state["using_new_upload"] = False
                
            uploaded_file = st.file_uploader("Upload a .sql, .db, or .sqlite3 file", 
                                          type=["sql", "db", "sqlite3"],
                                          help="Upload your database file to query and manage it")
            
            if uploaded_file is not None:
                st.session_state["using_new_upload"] = True
                for key in [schema_key, path_key]:
                    if key in st.session_state:
                        del st.session_state[key]
                
                db_schema_dict = {}
                db_path = None
                
                ############### SQL CLEANING ###############
                def clean_sql_script(sql_script):
                    cleaned_lines = []
                    for line in sql_script.split("\n"):
                        line = line.strip()
                        if (
                            line.lower().startswith(("use ", "create database", "alter", "drop", "grant", "set ", "delimiter"))
                            or "engine=" in line.lower()
                            or line.startswith("/*!")
                            or line.startswith("--")
                            or line.startswith("#")
                        ):
                            continue
                        line = line.replace("AUTO_INCREMENT", "AUTOINCREMENT")
                        line = line.replace("`", "")
                        cleaned_lines.append(line)
                    return "\n".join(cleaned_lines)
                
                ############### CONVERT .SQL → .DB ###############
                def convert_sql_to_db(sql_file, db_file):
                    try:
                        conn = sqlite3.connect(db_file)
                        cursor = conn.cursor()
                        with open(sql_file, "r", encoding="utf-8") as f:
                            raw_script = f.read()
                        cleaned_script = clean_sql_script(raw_script)
                        statements = cleaned_script.split(";")
                        for stmt in statements:
                            stmt = stmt.strip()
                            if stmt:
                                try:
                                    cursor.execute(stmt)
                                except sqlite3.Error:
                                    pass
                        conn.commit()
                        conn.close()
                        return True
                    except Exception as e:
                        st.error(f"Error converting .sql to .db: {e}")
                        return False
                
                ############### GET DB SCHEMA ###############
                def get_db_schema(db_path):
                    try:
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = cursor.fetchall()
                        schema_dict = {}
                        for table in tables:
                            table_name = table[0]
                            cursor.execute(f"PRAGMA table_info({table_name})")
                            columns = cursor.fetchall()
                            schema_str = f"Table: {table_name}\n"
                            for col in columns:
                                schema_str += f"  - {col[1]} ({col[2]})\n"
                            schema_dict[table_name] = schema_str
                        conn.close()
                        return schema_dict
                    except Exception as e:
                        st.error(f"Error extracting schema: {e}")
                        return {}
                
                local_file_path = os.path.join("./", uploaded_file.name)
                with open(local_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                st.markdown("<div class='success-msg animated'>File uploaded successfully!</div>", 
                           unsafe_allow_html=True)
                
                if uploaded_file.name.endswith(".sql"):
                    temp_db_path = f"converted_database_{current_user}.db"
                    with st.spinner("Converting SQL file to SQLite database..."):
                        if convert_sql_to_db(local_file_path, temp_db_path):
                            db_path = temp_db_path
                            update_user_db_path(current_user, db_path)
                            db_schema_dict = get_db_schema(db_path)
                            st.session_state[schema_key] = db_schema_dict
                            st.session_state[path_key] = db_path
                            st.success("SQL file converted successfully!")
                        else:
                            st.error("Failed to convert .sql file. Please check the SQL syntax.")
                elif uploaded_file.name.endswith((".db", ".sqlite3")):
                    db_path = local_file_path
                    update_user_db_path(current_user, db_path)
                    db_schema_dict = get_db_schema(db_path)
                    st.session_state[schema_key] = db_schema_dict
                    st.session_state[path_key] = db_path
        
        # Display schema in a better format
        if st.session_state.get(schema_key):
            db_schema_dict = st.session_state[schema_key]
            st.markdown("### 📋 Database Schema")
            
            if len(db_schema_dict) == 0:
                st.warning("No tables found in the database.")
            elif len(db_schema_dict) == 1:
                selected_table = list(db_schema_dict.keys())[0]
                st.session_state["selected_table"] = selected_table
                
                # Display schema in a cleaner way
                st.markdown("<div class='sql-query'>", unsafe_allow_html=True)
                st.code(db_schema_dict[selected_table], language="sql")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                table_list = list(db_schema_dict.keys())
                selected_table = st.selectbox("Select a table", table_list, 
                                           help="Choose which table to use for queries and editing")
                st.session_state["selected_table"] = selected_table
                
                # Display schema in a cleaner way
                st.markdown("<div class='sql-query'>", unsafe_allow_html=True)
                st.code(db_schema_dict[selected_table], language="sql")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("No schema extracted. Please upload a valid database file.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💬 English to SQL Translator")
        st.markdown("Type your question in plain English, and I'll convert it to SQL.")

        #############################################
        # 3) NATURAL LANGUAGE → SQL → EXECUTION     #
        #############################################
        def clean_generated_sql(sql_query):
            sql_query = sql_query.strip()
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            sql_query = sql_query.replace("\n", " ").replace("\t", " ")
            return sql_query

        # Add shared query loading
        query_params = st.query_params  # Updated: Replaced st.experimental_get_query_params with st.query_params
        shared_query = query_params.get("query", [None])[0]

        if shared_query:
            st.markdown("<div class='info-msg'>📌 Loaded shared query from link.</div>", unsafe_allow_html=True)
            st.text_area("Shared Query", shared_query, height=100, disabled=True)
            try:
                conn = sqlite3.connect(st.session_state.get("db_path", ""))
                df = pd.read_sql_query(shared_query, conn)
                df = df.drop_duplicates()
                st.subheader("Shared Query Results:")
                st.dataframe(df)
                conn.close()
            except Exception as e:
                st.error(f"Error executing shared SQL: {e}")

        english_query = st.text_area("Enter your English query:", 
                                  placeholder="Example: Show me all employees who work in the sales department",
                                  height=100)

        run_query = st.button("🔍 Convert to SQL", key="run_query_btn")

        if run_query:
            if not english_query.strip():
                st.warning("Please enter a query to convert.")
            elif "selected_table" not in st.session_state:
                st.warning("Please select a table first.")
            else:
                selected_table = st.session_state["selected_table"]
                table_schema = st.session_state[schema_key][selected_table]

                with st.spinner("Converting your query to SQL..."):
                    def generate_sql(nl_query, schema):
                        prompt = f"""
You are a SQL expert. Given the following table schema for '{selected_table}' and a natural language query, generate a valid SQL query that operates solely on that table.
IMPORTANT: Ensure the query returns each row only once. Use DISTINCT if necessary.

Table Schema:
{schema}

Natural Language Query:
{nl_query}

SQL Query:
"""
                        try:
                            genai.configure(api_key="AIzaSyAAHfxYOnX2YckrUj9BPC3VZ29mTo-qnNY")
                            model = genai.GenerativeModel("gemini-2.0-flash")
                            response = model.generate_content(prompt)
                            return response.text.strip() if response and response.text else None
                        except Exception as e:
                            st.error(f"Error with the model generation: {e}")
                            return None

                    sql_output = generate_sql(english_query, table_schema)
                    if sql_output:
                        sql_output = clean_generated_sql(sql_output)
                        if sql_output.lower().startswith("select") and "distinct" not in sql_output.lower():
                            sql_output = sql_output.replace("select", "select distinct", 1)

                        st.markdown("### 📝 Generated SQL Query")
                        st.markdown("<div class='sql-query'>", unsafe_allow_html=True)
                        st.code(sql_output, language="sql")
                        st.markdown("</div>", unsafe_allow_html=True)

                        # Generate shareable link
                        params = urlencode({"query": sql_output})
                        base_url = "https://englishtosqlconverter.streamlit.app/"  # Replace with actual URL
                        share_link = f"{base_url}?{params}"

                        st.markdown(f"<a href='{share_link}' target='_blank' style='text-decoration:none;'>"
                                  f"<div style='display:inline-flex;align-items:center;background:#7B68EE;color:white;padding:10px 15px;border-radius:6px;'>"
                                  f"<span>📤 Share this result</span>"
                                  f"</div></a>", 
                                  unsafe_allow_html=True)

                        try:
                            conn = sqlite3.connect(st.session_state[path_key])
                            df = pd.read_sql_query(sql_output, conn)
                            df = df.drop_duplicates()

                            st.markdown("### 🔍 Query Results")
                            st.dataframe(df, use_container_width=True)

                            # Show row count and download option
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                st.info(f"Results: {len(df)} rows")
                            with col2:
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download Results",
                                    data=csv,
                                    file_name=f"query_results_{selected_table}.csv",
                                    mime="text/csv"
                                )

                            conn.close()
                        except Exception as e:
                            st.error(f"Error executing SQL: {e}")
                    else:
                        st.warning("SQL generation failed. Try rewording your query and try again.")

    #############################################
    # 4) TABLE EDITOR SECTION                   #
    #############################################
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### ✏️ Table Editor")
    st.markdown("View and edit your database table data.")

    # Check if a table is selected
    if "selected_table" in st.session_state:
        selected_table = st.session_state["selected_table"]

        # Button to display the table data
        if st.button("👁️ Show Table Data", key="show_table"):
            st.session_state["show_table_data"] = True

        # Add column section
        add_col_expander = st.expander("Add a new column")
        with add_col_expander:
            col1, col2 = st.columns([3, 1])
            with col1:
                new_column_name = st.text_input("New column name:", key="new_column_name")
            with col2:
                col_type = st.selectbox("Type:", ["TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"])

            if st.button("➕ Add Column", key="add_column_btn"):
                if new_column_name:
                    try:
                        # Connect to the database
                        conn = sqlite3.connect(st.session_state[path_key])
                        cursor = conn.cursor()

                        # Check if the column already exists
                        cursor.execute(f"PRAGMA table_info({selected_table})")
                        columns = cursor.fetchall()
                        column_names = [col[1] for col in columns]

                        if new_column_name in column_names:
                            st.warning(f"Column '{new_column_name}' already exists.")
                        else:
                            # Add the new column
                            cursor.execute(f"ALTER TABLE {selected_table} ADD COLUMN {new_column_name} {col_type}")
                            conn.commit()

                            # Update the schema
                            db_schema_dict = st.session_state[schema_key]
                            cursor.execute(f"PRAGMA table_info({selected_table})")
                            columns = cursor.fetchall()
                            schema_str = f"Table: {selected_table}\n"
                            for col in columns:
                                schema_str += f"  - {col[1]} ({col[2]})\n"
                            db_schema_dict[selected_table] = schema_str
                            st.session_state[schema_key] = db_schema_dict

                            st.markdown("<div class='success-msg animated'>Column added successfully!</div>", 
                                       unsafe_allow_html=True)
                            st.session_state["show_table_data"] = True  # Show table after adding column
                            st.rerun()  # Refresh the page to see the new column
                    except Exception as e:
                        st.error(f"Error adding column: {e}")
                    finally:
                        conn.close()
                else:
                    st.warning("Please enter a column name.")

        # Display table data if the button is clicked
        if st.session_state.get("show_table_data", False):
            try:
                # Connect to the database
                conn = sqlite3.connect(st.session_state[path_key])
                cursor = conn.cursor()

                # Fetch the table data
                df_editable = pd.read_sql_query(f"SELECT * FROM {selected_table}", conn)
                st.dataframe(df_editable, use_container_width=True)

                # Editable DataFrame
                st.markdown("### ✏️ Edit Table Data")
                edited_df = st.data_editor(df_editable, num_rows="dynamic", use_container_width=True)

                # Save changes button
                if st.button("💾 Save Changes", key="save_changes_btn"):
                    try:
                        # Update each row in the table
                        for _, row in edited_df.iterrows():
                            # Construct the UPDATE query
                            set_clause = ", ".join([f"{col} = ?" for col in row.index])
                            where_clause = f"WHERE rowid = {row.name + 1}"  # Use rowid to identify the row
                            update_query = f"UPDATE {selected_table} SET {set_clause} {where_clause}"
                            
                            # Execute the UPDATE query
                            cursor.execute(update_query, tuple(row.values))

                        conn.commit()
                        st.markdown("<div class='success-msg animated'>Changes saved successfully!</div>", 
                                   unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Error saving changes: {e}")
                    finally:
                        conn.close()
            except Exception as e:
                st.error(f"Error loading table data: {e}")
        else:
            st.info("Click 'Show Table Data' to view and edit the table.")

    st.markdown('</div>', unsafe_allow_html=True)
