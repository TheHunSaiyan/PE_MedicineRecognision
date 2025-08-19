import jwt

from datetime import datetime, timedelta
from fastapi import HTTPException, status, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from Config.config import AppConfig
from Logger.logger import logger
from Manager.session_manager import SessionManager
from Models.user import User


class UserManager():
    def __init__(self, database):
        """
        Initialize the UserManager with database and session dependencies.

        Args:
            database: Database connection or ORM instance for user data access.

        Returns:
            None
        """
        self.database = database
        self.session_manager = SessionManager()
        self.security = HTTPBearer()

    async def login(self, data: dict):
        """
        Authenticate user credentials and create a session.

        Args:
             data (dict): Dictionary containing email and password

        Returns:
            dict: Authentication response.
        """
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
        """
        Generate a JWT token for authenticated user.

        Args:
            user (User): Authenticated user object.

        Returns:
            str: Encoded JWT token containing user claims.
        """
        payload = {
            "sub": str(user.user_id),
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(minutes=AppConfig.JWT_EXPIRE_MINUTES)
        }
        return jwt.encode(payload, AppConfig.JWT_SECRET_KEY, algorithm=AppConfig.JWT_ALGORITHM)

    async def get_all_users(self):
        """
        Retrieve all users from the database.

        Args:
            None

        Returns:
            list: List of User objects representing all registered users.
        """
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
        """
        Delete a user by their ID.

        Args:
            user_id (str): Unique identifier of the user to delete.

        Returns:
            dict: Operation result.
        """
        user = await self.database.get_user(user_id)
        if not user:
            logger.info(
                f"User has already been deleted successfully: {user_id}")
            return {"status": "success", "message": "User has already been deleted successfully"}

        await self.database.delete_user(user_id)
        logger.info(f"User deleted successfully: {user_id}")
        return {"status": "success", "message": "User deleted successfully"}

    async def update_user(self, data: dict):
        """
        Update user information.

        Args:
            data (dict): Dictionary containing user data

        Returns:
            dict: Operation result.
        """
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
        """
        Create a new user account.

        Args:
            data (dict): Dictionary containing user data

        Returns:
            dict: Operation result.
        """
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
