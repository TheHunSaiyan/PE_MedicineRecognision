import os
from fastapi import HTTPException, status
from Manager.verification_manager import VerificationManager
from Controllers.camera_controller import CameraController
from Controllers.led_controller import LEDController
from Logger.logger import logger

class DispenseVerification:
    def __init__(self, camera: CameraController, led: LEDController):
        self.camera = camera
        self.led = led
        self.verification_manager = VerificationManager(camera, led)
        self.initialized = False
    
    async def initialization(self):
        try:
            self.initialized = await self.verification_manager.initialize()
            if not self.initialized:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize verification system"
                )
            return {"status": True, "message": "Verification system initialized"}
        except Exception as e:
            logger.error(f"Verification initialization failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Initialization error: {str(e)}"
            )

    async def check_environment(self, holder_id: str):
        if not self.initialized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification system not initialized"
            )
        
        result = await self.verification_manager.analyze_environment(holder_id)
        if not result["status"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        return result
