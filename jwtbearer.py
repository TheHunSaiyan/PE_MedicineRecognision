from Manager.session_manager import SessionManager
import jwt
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from Config.config import AppConfig

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.session_manager = SessionManager()

    async def __call__(self, request: Request):
        session_id = request.cookies.get("session_id")
        if session_id:
            session_data = self.session_manager.validate_session(session_id)
            if session_data:
                request.state.user_id = session_data.get("user_id")
                request.state.role = session_data.get("role")
                return session_data
        
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Invalid authentication scheme."
                )
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Invalid token or expired token."
                )
            return credentials.credentials
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Invalid authorization code."
            )

    def verify_jwt(self, jwtoken: str) -> bool:
        try:
            payload = jwt.decode(
                jwtoken, 
                AppConfig.JWT_SECRET_KEY, 
                algorithms=[AppConfig.JWT_ALGORITHM]
            )
            return True
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Token expired."
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Invalid token."
            )