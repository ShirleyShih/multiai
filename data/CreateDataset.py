import mysql.connector
from dbconfig import db_config # connect to dbconfig.py

con = mysql.connector.connect(**db_config)
cursor = con.cursor()

# Create table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS member (
        id bigint primary key auto_increment,
        name varchar(255) not null,
        email varchar(255) not null,
        password varchar(255) not null
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation (
        id bigint primary key auto_increment,
        memberid bigint not null,
        conversation_id varchar(255) unique key not null,
        title varchar(255) not null
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS request (
        id bigint primary key auto_increment,
        conversation_id varchar(255) not null,
        request_id varchar(255) unique key not null,
        request_text varchar(10000) not null,
        date varchar(255) not null,
        time varchar(255) not null,
        FOREIGN KEY (conversation_id) REFERENCES conversation(conversation_id) 
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS response_openai (
        id bigint primary key auto_increment,
        request_id varchar(255) not null,
        response_text varchar(10000) not null,
        FOREIGN KEY (request_id) REFERENCES request(request_id) 
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS response_gemini (
        id bigint primary key auto_increment,
        request_id varchar(255) not null,
        response_text varchar(10000) not null,
        FOREIGN KEY (request_id) REFERENCES request(request_id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS response_claude (
        id bigint primary key auto_increment,
        request_id varchar(255) not null,
        response_text varchar(10000) not null,
        FOREIGN KEY (request_id) REFERENCES request(request_id)
    )
""")

# cursor.execute("delete from attractions")
con.commit()
cursor.close()