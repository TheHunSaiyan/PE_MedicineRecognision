from fastapi.security import HTTPBearer
from Manager.session_manager import SessionManager
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Response
from fastapi.responses import JSONResponse

from Config.config import AppConfig
from Logger.logger import logger
from Models.user import User

class UserManager():
    def __init__(self, database):
        self.database = database
        self.session_manager = SessionManager()
        self.security = HTTPBearer()
        
    async def login(self, data: dict):
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            raise HTTPException(
                status_code=400,
                detail="Email and password are required"
            )
        
        user = await self.database.get_user_by_email(email)
        
        if not user:
            logger.error(f"User not found: {email}")
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        if not user.verify_password(password):
            logger.error(f"Incorrect password for user: {email}")
            raise HTTPException(
                status_code=401,
                detail="Incorrect password"
            )
            
        session_id = self.session_manager.create_session(
            user_id=str(user.user_id),
            role=user.role.value,
            expires_in=AppConfig.SESSION_EXPIRE_SECONDS
        )
        
        token = self._generate_jwt_token(user)
        
        logger.info(f"User {email} logged in successfully")
        
        return {
            "status": "success",
            "user_id": user.user_id,
            "role": user.role.value
        }
        
    def _generate_jwt_token(self, user):
        payload = {
            "sub": str(user.user_id),
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(minutes=AppConfig.JWT_EXPIRE_MINUTES)
        }
        return jwt.encode(payload, AppConfig.JWT_SECRET_KEY, algorithm=AppConfig.JWT_ALGORITHM)
        
    async def get_all_users(self):
        users = await self.database.get_all_users()
        if not users:
            logger.warning("No users found in the database")
            raise HTTPException(
                status_code=404,
                detail="No users found"
            )
        logger.info(f"Retrieved {len(users)} users from the database")
        return users
    
    async def delete_user(self, user_id: str):
        user = await self.database.get_user(user_id)
        if not user:
            logger.info(f"User has already been deleted successfully: {user_id}")
            return {"status": "success", "message": "User has already been deleted successfully"}
        
        await self.database.delete_user(user_id)
        logger.info(f"User deleted successfully: {user_id}")
        return {"status": "success", "message": "User deleted successfully"}
    
    async def update_user(self, data: dict):
        user = await self.database.get_user(data.get("user_id"))
        if not user:
            logger.error(f"User not found for update: {data.get("user_id")}")
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        updated_user_id = await self.database.update_user(data)
        updated_user = await self.database.get_user(updated_user_id)
        logger.info(f"User updated successfully: {data.get("user_id")}")
        return {"status": "success", "user": updated_user}
       
    async def create_user(self, data: dict):
        email = data.get("email")
        password = data.get("password")
        role = data.get("role", "user")
        
        if not email or not password:
            logger.error("Email and password are required for user creation")
            raise HTTPException(
                status_code=400,
                detail="Email and password are required"
            )
        
        existing_user = await self.database.get_user_by_email(email)
        if existing_user:
            logger.error(f"User with email {email} already exists")
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )
        
        user_data = {
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "email": email,
            "hashed_password": User.hash_password(password),
            "role": role
        }
        user_id = await self.database.add_user(user_data)
        new_user = User(
            user_id=user_id,
            **user_data
        )
        
        logger.info(f"User created successfully: {new_user.user_id}")
        return {"status": "success", "user": new_user}