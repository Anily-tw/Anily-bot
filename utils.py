import os
import json
import mysql.connector
from mysql.connector import Error
import shutil
import paramiko

def load_config(config_file):
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config

def upload_map_to_servers(servers, local_map_path, remote_map_path_relative):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for server in servers:
        private_key = paramiko.RSAKey.from_private_key_file(server['pkey_path'])
        ssh.connect(server['ip'], port=server['port'], username=server['username'], pkey=private_key, password=server['password'])
        sftp = ssh.open_sftp()
        sftp.put(local_map_path, os.path.join(server['maps_path'], remote_map_path_relative))
        sftp.close()
        ssh.close()

def upload_bans_to_servers(servers, local_bans_path, remote_bans_path_relative):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for server in servers:
        private_key = paramiko.RSAKey.from_private_key_file(server['pkey_path'])
        ssh.connect(server['ip'], port=server['port'], username=server['username'], pkey=private_key, password=server['password'])
        sftp = ssh.open_sftp()
        sftp.put(local_bans_path, os.path.join(server['bans_path'], remote_bans_path_relative))
        sftp.close()
        ssh.close()

def run_command_servers(servers, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for server in servers:
        private_key = paramiko.RSAKey.from_private_key_file(server['pkey_path'])
        ssh.connect(server['ip'], port=server['port'], username=server['username'], pkey=private_key, password=server['password'])
        ssh.exec_command(command)
        ssh.close()

def run_execute_all_servers(servers, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for server in servers:
        private_key = paramiko.RSAKey.from_private_key_file(server['pkey_path'])
        ssh.connect(server['ip'], port=server['port'], username=server['username'], pkey=private_key, password=server['password'])
        ssh.exec_command(f"{server['execute_all']} {command}")
        ssh.close()

def run_build_votes_servers(servers):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for server in servers:
        private_key = paramiko.RSAKey.from_private_key_file(server['pkey_path'])
        ssh.connect(server['ip'], port=server['port'], username=server['username'], pkey=private_key, password=server['password'])
        ssh.exec_command(server['build_votes'])
        ssh.close()

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def file_exists(path):
    return os.path.exists(path)

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
