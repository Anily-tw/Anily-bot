import os
import mysql.connector
from mysql.connector import Error
import shutil

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

async def save_map_file(map_file, map_path):
    await map_file.save(map_path)

def move_file_on_error(source_path, destination_folder):
    try:
        shutil.copy2(source_path, destination_folder)
        os.remove(source_path)
    except OSError as e:
        return f"Error moving map file: {e}"
    return f"Map file '{source_path}' moved to {destination_folder}."

def insert_map_into_db(map_name, category, points, stars, mapper, release_date):
    try:
        connection = mysql.connector.connect(
            host=os.getenv("ANILY_DDRACE_DB_HOST", "localhost"),
            database=os.getenv("ANILY_DDRACE_DB_SCHEME", "teeworlds"),
            user=os.getenv("ANILY_DDRACE_DB_USER", "teeworlds"),
            password=os.getenv("ANILY_DDRACE_DB_PASS", "bigSuperPass")
        )

        if connection.is_connected():
            cursor = connection.cursor()
            sql_insert_query = """INSERT INTO record_maps (Map, Server, Points, Stars, Mapper, Timestamp)
                                  VALUES (%s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql_insert_query, (map_name, category, points, stars, mapper, release_date))
            connection.commit()
            return None, connection, cursor
    except Error as e:
        return e, None, None
    return None, None, None

def close_db_connection(connection, cursor):
    if connection and connection.is_connected():
        cursor.close()
        connection.close()
        return "MySQL connection closed."
    return None
