#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/Users/patrickoliver/.music_tagger/cache/artist_cache.db')
cursor = conn.cursor()
cursor.execute('SELECT artist_name, country FROM artist_country LIMIT 5')
for row in cursor.fetchall():
    print(f"{row[0]} -> {row[1]}")
conn.close()