"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';

const CameraApp: React.FC = () => {
  const [imageUrl, setImageUrl] = useState<string>('');
  const [captureTime, setCaptureTime] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const [isLiveFeedActive, setIsLiveFeedActive] = useState(false);

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

  const toggleLiveFeed = () => {
    setIsLiveFeedActive(!isLiveFeedActive);
  };

  return (
    <div className="camera-container" style={{ padding: '20px', height: '100vh'}}>
      <br></br>
      <Button 
          variant="contained"
          onClick={captureImage} 
          disabled={isLoading || !isLiveFeedActive}
          className="capture-button"
          style={{ marginRight: '20px' }}
        >
          {isLoading ? 'Capturing...' : 'Capture Image'}
        </Button>

       <Button 
          variant="contained"
          color={isLiveFeedActive ? 'secondary' : 'primary'}
          onClick={toggleLiveFeed}
        >
          {isLiveFeedActive ? 'Stop Live Feed' : 'Start Live Feed'}
        </Button>
      
      {error && <div className="error-message">{error}</div>}
      
      <div style={{ 
        display: 'flex', 
        gap: '20px', 
        marginTop: '20px',
        flexWrap: 'wrap'
      }}>
        <div style={{ 
          flex: 1,
          minWidth: '300px',
          border: '1px solid #ddd',
          padding: '10px',
          borderRadius: '8px'
        }}>
          <h2>Captured Image</h2>
          {imageUrl && isMounted ? (
            <div className="image-preview">
              <img 
                src={imageUrl} 
                alt="Captured" 
                onError={() => isMounted && setError('Failed to load image')}
                key={imageUrl}
                style={{ width: '100%', maxWidth: '640px', border: '1px solid #ccc' }}
              />
              {captureTime && <p>Captured at: {captureTime}</p>}
            </div>
          ) : (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              height: '480px',
              backgroundColor: '#f5f5f5',
              color: '#666'
            }}>
              No image captured yet
            </div>
          )}
        </div>
        
        <div style={{ 
          flex: 1,
          minWidth: '300px',
          border: '1px solid #ddd',
          padding: '10px',
          borderRadius: '8px'
        }}>
          <h2>Live Video Feed</h2>
          {isMounted && isLiveFeedActive ? (
            <img
              src="http://localhost:2076/video_feed"
              alt="Live Camera Feed"
              style={{ width: '100%', maxWidth: '640px', border: '1px solid #ccc' }}
            />
          ) : (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              height: '480px',
              backgroundColor: '#f5f5f5',
              color: '#666'
            }}>
              Live feed is inactive
            </div>
          )}
        </div>
      </div>
      <br></br>
       <Link href="/" passHref>
            <Button variant="contained">
              Back to the Main Page
            </Button>
          </Link>
    </div>
  );
};

export default CameraApp;