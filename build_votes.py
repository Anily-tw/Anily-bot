#!/bin/env python3
import os
import mysql.connector
from datetime import timedelta

BASE_DIR = os.path.join(os.getenv('ANILY_DDRACE_ROOT'), "types")

def connect_db():
    return mysql.connector.connect(
        host=os.getenv("ANILY_DDRACE_DB_HOST"),
        database=os.getenv("ANILY_DDRACE_DB_SCHEME"),
        user=os.getenv("ANILY_DDRACE_DB_USER"),
        password=os.getenv("ANILY_DDRACE_DB_PASS")
    )

def get_categories(cursor):
    cursor.execute("SELECT DISTINCT Server as category_name FROM record_maps")
    return cursor.fetchall()

def get_maps_for_category(cursor, category_name):
    query = "SELECT m.Map, m.Mapper, m.Points, m.Stars, COUNT(r.Time) AS Finishes, NVL(ROUND(AVG(r.Time)), 0) AS Average FROM record_maps AS m LEFT JOIN record_race AS r ON r.Map = m.Map WHERE m.Server = %s GROUP BY m.Map ORDER BY m.Mapper, m.Map"
    cursor.execute(query, (category_name,))
    return cursor.fetchall()

def create_category_folder(category_name):
    category_path = os.path.join(BASE_DIR, category_name)
    if not os.path.exists(category_path):
        os.makedirs(category_path)
    return category_path

def write_votes_file(category, category_path, maps):
    votes_file_path = os.path.join(category_path, 'votes.cfg')
    with open(votes_file_path, 'w') as file:
        file.write(f'sv_server_type "{category} maps"\n')
        if category == 'test':
            file.write(f'add_vote "Hot reload map" "hot_reload"\n')
        file.write(f'add_vote " " "info"\n')

        prev_mapper = None
        for map_details in maps:
            map_name, mapper, points, stars, finishes, average_seconds = map_details

            if prev_mapper != mapper and prev_mapper != None:
                file.write(f'add_vote " " "info"\n')

            file.write(f'add_vote "⌈ {map_name} by {mapper} | {stars}/5★ {points}✦" "sv_reset_file types/{category}/flexreset.cfg; change_map \\"{category}/{map_name}\\""\n')
            file.write(f'add_vote "⌊ {finishes} ⚑ | {timedelta(seconds=average_seconds)} ◷" "info"\n')
            
            prev_mapper = mapper

def gen_votes(categories, cursor):
    for category in categories:
        category_name = category[0]
        print(f"Processing category: {category_name}")

        category_path = create_category_folder(category_name)
        maps = get_maps_for_category(cursor, category_name)

        write_votes_file(category_name, category_path, maps)

def main():
    db = connect_db()
    cursor = db.cursor()

    categories = get_categories(cursor)

    gen_votes(categories, db)

    cursor.close()
    db.close()

if __name__ == "__main__":
    main()
