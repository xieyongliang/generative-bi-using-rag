import json

import streamlit as st
from dotenv import load_dotenv
from nlq.business.connection import ConnectionManagement
from nlq.data_access.database import RelationDatabase
from utils.logging import getLogger
from utils.navigation import make_sidebar

logger = getLogger()
# global variables

db_type_mapping = {
    'mysql': 'MySQL',
    'postgresql': 'PostgreSQL',
    'redshift': 'Redshift',
    'starrocks': 'StarRocks',
    'clickhouse': 'Clickhouse',
    'hive': 'Hive',
    'athena': 'Athena',
    'bigquery': 'BigQuery'
}


# global functions
def index_of_db_type(db_type):
    index = 0
    for k, v in db_type_mapping.items():
        if k == db_type:
            return index
        index += 1


def new_connection_clicked():
    st.session_state.new_connection_mode = True
    st.session_state.update_connection_mode = False
    st.session_state.current_conn_name = None


def test_connection_view(db_type, user, password, host, port, db_name):
    if st.button('Test Connection'):
        if RelationDatabase.test_connection(db_type, user, password, host, port, db_name):
            st.success(f"Connected successfully!")
        else:
            st.error(f"Failed to connect!")


# Main logic
def main():
    load_dotenv()

    st.set_page_config(page_title="Data Connection Management")
    make_sidebar()

    if 'new_connection_mode' not in st.session_state:
        st.session_state['new_connection_mode'] = False

    if 'update_connection_mode' not in st.session_state:
        st.session_state['update_connection_mode'] = False

    if 'current_connection' not in st.session_state:
        st.session_state['current_connection'] = None

    with st.sidebar:
        st.title("Data Connection Management")
        st.selectbox("My database connection", ConnectionManagement.get_all_connections(),
                     index=None,
                     placeholder="Please database connection...", key='current_conn_name')
        if st.session_state.current_conn_name:
            st.session_state.current_connection = ConnectionManagement.get_conn_config_by_name(
                st.session_state.current_conn_name)
            st.session_state.update_connection_mode = True
            st.session_state.new_connection_mode = False

        st.button('Create new...', on_click=new_connection_clicked)

    if st.session_state.new_connection_mode:
        st.subheader("New Database Connection")
        connection_name = st.text_input("Database Connection Name")
        db_type = st.selectbox("Database type", db_type_mapping.values(), index=0)  # Add more options as needed
        db_type = db_type.lower()  # Convert to lowercase for matching with db_mapping keys
        if db_type == 'athena':
            st.info("Please enter S3 staging directory in the database name field. You can leave other fields empty. Please also make sure that IAM role is able to access Athena and S3.")

        if db_type == "bigquery":
            host = st.text_input("Enter host")
            password = st.text_area("Credentials Info", height=200,  placeholder="Paste your credentials info here")
            # credentials_info = json.loads(credentials_info)
            port = ""
            user = ""
            db_name = ""
            comment = st.text_input("Enter comment")
            test_connection_view(db_type, user, password, host, port, db_name)
            if st.button('Add Connection', type='primary'):
                ConnectionManagement.add_connection(connection_name, db_type, host, port, user, password, db_name, comment)
                st.success(f"{connection_name} added successfully!")
                st.session_state.new_connection_mode = False

        else:
            host = st.text_input("Enter host")
            port = st.text_input("Enter port")
            user = st.text_input("Enter username")
            password = st.text_input("Enter password", type="password")
            db_name = st.text_input("Enter database name")
            comment = st.text_input("Enter comment")

            test_connection_view(db_type, user, password, host, port, db_name)

            if st.button('Add Connection', type='primary'):
                if db_name == '':
                    st.error("Database name is required!")
                else:
                    ConnectionManagement.add_connection(connection_name, db_type, host, port, user, password, db_name, comment)
                    st.success(f"{connection_name} added successfully!")
                    st.session_state.new_connection_mode = False

    elif st.session_state.update_connection_mode:
        st.subheader("Update Database Connection")
        current_conn = st.session_state.current_connection
        connection_name = st.text_input("Database Connection Name", current_conn.conn_name, disabled=True)
        db_type = st.selectbox("Database type", db_type_mapping.values(), index=index_of_db_type(current_conn.db_type),
                               disabled=True)  # Add more options as needed
        db_type = db_type.lower()  # Convert to lowercase for matching with db_mapping keys
        if db_type == 'athena':
            st.info("Please enter S3 staging directory in the database name field. You can leave other fields empty. Please also make sure that IAM role is able to access Athena and S3.")
        host = st.text_input("Enter host", current_conn.db_host)
        port = st.text_input("Enter port", current_conn.db_port)
        user = st.text_input("Enter username", current_conn.db_user)
        password = st.text_input("Enter password", type="password", value=current_conn.db_pwd)
        db_name = st.text_input("Enter database name", current_conn.db_name)
        comment = st.text_input("Enter comment", current_conn.comment)

        test_connection_view(db_type, user, password, host, port, db_name)

        if st.button('Update Connection', type='primary'):
            ConnectionManagement.update_connection(connection_name, db_type, host, port, user, password, db_name,
                                                   comment)
            st.success(f"{connection_name} updated successfully!")

        if st.button('Delete Connection'):
            ConnectionManagement.delete_connection(connection_name)
            st.success(f"{connection_name} deleted successfully!")
            st.session_state.current_connection = None

        st.session_state.update_connection_mode = False

    else:
        st.subheader("Data Connection Management")
        st.info('Please select connection in the left sidebar.')


if __name__ == '__main__':
    main()
