
from fastapi import HTTPException, status

class UserManager():
    def __init__(self, database):
        self.database = database
        
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
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        if not user.verify_password(password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect password"
            )
        
        return {
            "status": "success",
            "user_id": user.user_id,
            "role": user.role.value
        }
        
    async def get_all_users(self):
        users = await self.database.get_all_users()
        if not users:
            raise HTTPException(
                status_code=404,
                detail="No users found"
            )
        return users