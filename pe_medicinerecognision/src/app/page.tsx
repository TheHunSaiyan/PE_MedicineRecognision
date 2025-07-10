"use client";

import React, { useState, useEffect } from 'react';

const CameraApp: React.FC = () => {
  const [imageUrl, setImageUrl] = useState<string>('');
  const [captureTime, setCaptureTime] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  const captureImage = async () => {
    if (!isMounted) return;
    
    setIsLoading(true);
    setError(null);
    
     try {
    const apiUrl = 'http://localhost:2076';
    const response = await fetch(`${apiUrl}/capture`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (data.status === 'success' && data.filename) {
      setImageUrl(`${apiUrl}/captured-images/${data.filename}`);
      setCaptureTime(new Date().toLocaleTimeString());
    } else {
      throw new Error(data.error || 'Failed to capture image');
    }
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Unknown error occurred');
  } finally {
    setIsLoading(false);
  }
  };

  return (
    <div className="camera-container">
      <h1>Camera Capture</h1>
      
      <button 
        onClick={captureImage} 
        disabled={isLoading}
        className="capture-button"
      >
        {isLoading ? 'Capturing...' : 'Capture Image'}
      </button>
      
      {error && <div className="error-message">{error}</div>}
      
      {imageUrl && isMounted && (
        <div className="image-preview">
          <img 
            src={imageUrl} 
            alt="Captured" 
            onError={() => isMounted && setError('Failed to load image')}
            key={imageUrl} // Force re-render when URL changes
          />
          {captureTime && <p>Captured at: {captureTime}</p>}
        </div>
      )}
    </div>
  );
};

export default CameraApp;