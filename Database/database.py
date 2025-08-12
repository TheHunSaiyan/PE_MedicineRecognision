import sqlite3

from typing import Optional

from Models.roles import Role
from Models.user import User

class Database:
    def __init__(self, db_name: str = "medicinerecognition.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()
        
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            role_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL,
            FOREIGN KEY (role) REFERENCES roles(name)
        )
        """)
        
        for role in Role:
            cursor.execute(
                "INSERT OR IGNORE INTO roles (name) VALUES (?)",
                (role.value,)
            )
        
        self.conn.commit()

    async def add_user(self, user_data: dict) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO users 
            (first_name, last_name, email, hashed_password, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_data["first_name"],
                user_data["last_name"],
                user_data["email"],
                user_data["hashed_password"],
                user_data["role"]
            )
        )
        self.conn.commit()
        return cursor.lastrowid

    async def get_user(self, user_id: int) -> Optional[User]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return User(
                user_id=row[0],
                first_name=row[1],
                last_name=row[2],
                email=row[3],
                hashed_password=row[4],
                role=Role(row[5])
            )
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        if row:
            return User(
                user_id=row[0],
                first_name=row[1],
                last_name=row[2],
                email=row[3],
                hashed_password=row[4],
                role=Role(row[5])
            )
        return None
    
    async def get_all_users(self) -> list[User]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        return [
            User(
                user_id=row[0],
                first_name=row[1],
                last_name=row[2],
                email=row[3],
                hashed_password=row[4],
                role=Role(row[5])
            ) for row in rows
        ]
        
    async def update_user(self, user_data: dict) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE users 
            SET first_name = ?, last_name = ?, email = ?, role = ?
            WHERE user_id = ?
            """,
            (
                user_data["first_name"],
                user_data["last_name"],
                user_data["email"],
                user_data["role"],
                user_data["user_id"]
            )
        )
        self.conn.commit()
        return user_data["user_id"]
    
    async def delete_user(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM users WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()