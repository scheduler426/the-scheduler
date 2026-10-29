import duckdb


file = duckdb.connect("group.duckdb")

file.execute("""
    CREATE TABLE IF NOT EXISTS group 
    (
        groupID INTEGER PRIMARY KEY
        groupName VARCHAR NOT NULL
        description VARCHAR
    );
    
    """)

file.execute("""
    CREATE TABLE IF NOT EXISTS groupRoster 
    (
        groupID INTEGER NOT NULL
        userID INTEGER NOT NULL

        PRIMARY KEY (groupID, userID),
        FOREIGN KEY (groupID) REFERENCES groups(groupID)
    );
    
    """)

file.execute("""
    CREATE TABLE IF NOT EXISTS scheduledMeetings
    ( 
        meetingID INTEGER PRIMARY KEY,
        groupID INTEGER NOT NULL
        meetingDate DATE,
        meetingTime TIME,

        FOREIGN KEY (groupID) REFERENCES groups(groupID)
    );
    
    """)

file.execute("""
    CREATE TABLE IF NOT EXISTS groupFiles(
        fileID INTEGER PRIMARY KEY,
        groupID INTEGER NOT NULL,
        fileName VARCHAR,
        filePath VARCHAR,

        FOREIGN KEY (groupID) REFERENCES groups(groupID)
    );
    """)

print("SUCCESS TEST")

file.close()