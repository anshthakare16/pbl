import streamlit as st
import sqlite3
from hashlib import sha256
import pandas as pd
from google import genai
import os

# Set page configuration
st.set_page_config(layout="wide", page_title="English to SQL Translator", page_icon="📊")
# Custom styling
st.markdown(
    """
    <style>
        body {background-color: #000000; color: #FFFFFF;}
        .stSidebar {background-color: #121212; padding: 10px; color: #FFFFFF;}
        .stButton button {background-color: #FFA500; color: white; font-size: 16px; border-radius: 8px;}
        .sql-query {background-color: #1E1E1E; padding: 10px; border-radius: 5px; color: #FFFFFF;}
        .footer {position: fixed; bottom: 0; width: 100%; text-align: center; padding: 10px; font-size: 14px; color: #000000; background-color: transparent;}
        .login-section {color: #FFD700;}
        label {color: #FFD700 !important; font-weight: bold;}
        .main-content {background-color: #FFFFFF; padding: 20px; border-radius: 10px; color: #000000;}
        .query-label {color: #000000 !important; font-weight: normal;}
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

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Sidebar: Logout button if logged in
if st.session_state["logged_in"]:
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        for key in ["username", "db_schema", "db_path"]:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()

auth_choice = st.sidebar.selectbox("Choose Authentication", ["Login", "Sign Up"])
username_input = st.sidebar.text_input("Username", key="username_input")
password_input = st.sidebar.text_input("Password", key="password_input", type="password")

if auth_choice == "Sign Up":
    if st.sidebar.button("Create Account"):
        if username_input and password_input:
            try:
                add_user(username_input, password_input)
                st.sidebar.success("Account created successfully! Please log in.")
            except sqlite3.IntegrityError:
                st.sidebar.error("Username already exists. Please choose a different username.")
        else:
            st.sidebar.warning("Please fill out both fields.")
elif auth_choice == "Login":
    if st.sidebar.button("Login"):
        user = verify_user(username_input, password_input)
        if user:
            st.sidebar.success("Login successful!")
            st.session_state["logged_in"] = True
            st.session_state["username"] = username_input
            # Load stored DB path (if any) for this user:
            stored_path = get_user_db_path(username_input)
            st.session_state["db_path"] = stored_path
        else:
            st.sidebar.error("Invalid username or password.")

#############################################
# 2) MAIN APP: FILE UPLOAD & SQL CONVERSION #
#############################################
if st.session_state["logged_in"]:
    current_user = st.session_state["username"]
    st.write(f"Welcome, {current_user}!")
    st.title("English to SQL Translator")
    st.markdown("Upload a .sql (MySQL dump) or a .db/.sqlite3 (SQLite DB) file. You can also use your stored database if available.")

    # Use per-user keys for storing DB info
    schema_key = f"db_schema_{current_user}"
    path_key = f"db_path_{current_user}"
    
    # If a stored database exists for this user, ask if they want to use it
    stored_db = st.session_state.get("db_path", None)
    use_stored = False
    if stored_db and os.path.exists(stored_db):
        use_stored = st.checkbox("Use stored database", value=True)
        if use_stored:
            db_path = stored_db
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
            except Exception as e:
                st.error(f"Error extracting schema from stored DB: {e}")
            st.session_state[schema_key] = db_schema_dict
            st.session_state[path_key] = db_path
    else:
        use_stored = False

    # If not using stored DB, allow file upload to override
    if not use_stored:
        # Clear stored DB info for current user
        for key in [schema_key, path_key]:
            if key in st.session_state:
                del st.session_state[key]
        uploaded_file = st.file_uploader("Upload a .sql, .db, or .sqlite3 file", type=["sql", "db", "sqlite3"])
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

        if uploaded_file is not None:
            local_file_path = os.path.join("./", uploaded_file.name)
            with open(local_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("File uploaded successfully!")
            if uploaded_file.name.endswith(".sql"):
                temp_db_path = f"converted_database_{current_user}.db"
                if convert_sql_to_db(local_file_path, temp_db_path):
                    db_path = temp_db_path
                    update_user_db_path(current_user, db_path)
                    db_schema_dict = get_db_schema(db_path)
                    st.session_state[schema_key] = db_schema_dict
                    st.session_state[path_key] = db_path
                else:
                    st.error("Failed to convert .sql file. Please check the SQL syntax.")
            elif uploaded_file.name.endswith((".db", ".sqlite3")):
                db_path = local_file_path
                update_user_db_path(current_user, db_path)
                db_schema_dict = get_db_schema(db_path)
                st.session_state[schema_key] = db_schema_dict
                st.session_state[path_key] = db_path

    # Display schema only once:
    selected_table = None
    if st.session_state.get(schema_key):
        db_schema_dict = st.session_state[schema_key]
        if len(db_schema_dict) == 1:
            selected_table = list(db_schema_dict.keys())[0]
            st.text_area("Extracted Database Schema", db_schema_dict[selected_table], height=200, disabled=True)
        else:
            table_list = list(db_schema_dict.keys())
            selected_table = st.selectbox("Select a table to use for queries", table_list)
            st.text_area("Selected Table Schema", db_schema_dict[selected_table], height=150, disabled=True)
    else:
        st.warning("No schema extracted. Please upload a valid database file.")

    #############################################
    # 3) NATURAL LANGUAGE → SQL → EXECUTION     #
    #############################################
    def clean_generated_sql(sql_query):
        sql_query = sql_query.strip()  # Remove leading/trailing spaces
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()  # Remove code block markers
        sql_query = sql_query.replace("\n", " ")  # Ensure query is a single line if necessary
        sql_query = sql_query.replace("\t", " ")  # Remove tabs
        return sql_query


    st.subheader("Enter Your Query")
    english_query = st.text_area("Enter your English query:", height=100)

    if st.button("Convert to SQL"):
        if not english_query.strip():
            st.warning("Please enter a query to convert.")
        else:
            if not selected_table:
                st.warning("Please select a table first.")
            else:
                table_schema = st.session_state[schema_key][selected_table]
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
                        client = genai.Client(api_key="AIzaSyAAHfxYOnX2YckrUj9BPC3VZ29mTo-qnNY")  # Replace with your actual API key
                        response = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=prompt
                        )
                        return response.text.strip()
                    except Exception as e:
                        st.error(f"Error with the model generation: {e}")
                        return None

                sql_output = generate_sql(english_query, table_schema)
                if sql_output:
                    sql_output = clean_generated_sql(sql_output)
                    if sql_output.lower().startswith("select") and "distinct" not in sql_output.lower():
                        sql_output = sql_output.replace("select", "select distinct", 1)
                    st.subheader("Generated SQL Query:")
                    st.code(sql_output)
                    try:
                        conn = sqlite3.connect(st.session_state[path_key])
                        df = pd.read_sql_query(sql_output, conn)
                        df = df.drop_duplicates()
                        st.subheader("Query Results:")
                        st.dataframe(df)
                        conn.close()
                    except Exception as e:
                        st.error(f"Error executing SQL: {e}")
                else:
                    st.warning("SQL generation failed. Try again.")
else:
    st.info("Please log in to access the application.")
