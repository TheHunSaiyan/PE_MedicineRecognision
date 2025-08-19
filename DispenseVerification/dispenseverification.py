import os

from fastapi import HTTPException, status

from Controllers.camera_controller import CameraController
from Controllers.led_controller import LEDController
from Logger.logger import logger
from Manager.verification_manager import VerificationManager


class DispenseVerification:
    def __init__(self, camera: CameraController, led: LEDController):
        """
        Initialize the Dispense Verification system.
        Sets up the camera and LED controllers and prepares the verification
        manager for pill dispensing validation operations.

        Args:
            camera (CameraController): Controller instance for camera operations.
            led (LEDController): Controller instance for LED lighting control.

        Returns:
            None
        """
        self.camera = camera
        self.led = led
        self.verification_manager = VerificationManager(camera, led)
        self.initialized = False

    async def initialization(self):
        """
        Initialize the verification system components.

        Args:
            None

        Returns:
            dict: Dictionary containing initialization status and message.
        """
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
        """
        Analyze the dispensing environment for proper verification conditions.

        Args:
            holder_id (str): Identifier for the medication holder being verified.

        Returns:
            dict: Dictionary containing environment analysis results.
        """
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
