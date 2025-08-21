import jwt

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from Config.config import AppConfig
from Manager.session_manager import SessionManager


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        """
        Initialize the JWTBearer authentication handler.

        Args:
            auto_error (bool, optional): Whether to automatically raise errors
                                        on authentication failure.
                                        Defaults to True.

        Returns:
            None
        """
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.session_manager = SessionManager()

    async def __call__(self, request: Request):
        """
        Authenticate incoming request using session or JWT token.

        Args:
            request (Request): FastAPI request object.

        Returns:
            Union[dict, str]: Session data if session authentication succeeds,
                             JWT token if token authentication succeeds.
        """
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
        """
        Verify the validity of a JWT token.

        Args:
            jwtoken (str): JWT token string to validate.

        Returns:
            bool: True if token is valid and not expired.
        """
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
