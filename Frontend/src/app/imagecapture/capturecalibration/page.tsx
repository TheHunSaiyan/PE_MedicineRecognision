"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import { Typography, FormControlLabel, Radio } from '@mui/material';
import ProtectedRoute from '../../../../components/ProtectedRoute';

interface LedParameters{
  upper_led: number;
  side_led: number;
}

const CameraApp: React.FC = () => {
  const [imageUrl, setImageUrl] = useState<string>('');
  const [captureTime, setCaptureTime] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const [isLiveFeedActive, setIsLiveFeedActive] = useState(false);
  const [captureCount, setCaptureCount] = useState<number>(0);

  const [isHolding, setIsHolding] = useState(false);
  const [holdTimer, setHoldTimer] = useState<NodeJS.Timeout | null>(null);
  const [lastCapturedImage, setLastCapturedImage] = useState<string | null>(null);
  const [showLastImage, setShowLastImage] = useState(false);
  const [selectedLamp, setSelectedLamp] = useState<'upper_led' | 'side_led' | 'none'>('none');
  const [Parameters, setParameters] = useState<LedParameters>({
    upper_led: 0,
    side_led: 0
  })

const handleHoldStart = () => {
    setShowLastImage(true);
  };

  const handleHoldEnd = () => {
    setShowLastImage(false);
  };

  useEffect(() => {
        setIsMounted(true);
        const fetchSettings = async () => {
        try {
          const response = await fetch('http://localhost:2076/led_settings');
          if (!response.ok) {
            throw new Error('Failed to fetch led settings');
          }
          const data = await response.json();
          console.log("Received data:", data); 
          setParameters(data);
        } catch (error) {
          console.error('Error fetching settings:', error);
        } finally {
          setIsLoading(false);
        }
      };
        fetchSettings();
        return () => setIsMounted(false);
      }, []);

  const debounce = (func: (...args: any[]) => void, delay: number) => {
  let timeoutId: NodeJS.Timeout;
  return (...args: any[]) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};


const formatTimestamp = (date: Date): string => {
  const pad = (num: number) => num.toString().padStart(2, '0');
  
  return [
    date.getFullYear(),
    '-',
    pad(date.getMonth() + 1),
    '-',
    pad(date.getDate()),
    '_',
    pad(date.getHours()),
    '-',
    pad(date.getMinutes())
  ].join('');
};


  const [pageLoadTime] = useState(() => formatTimestamp(new Date()));

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
      const imageUrl = `${apiUrl}/captured-images/${data.filename}`;
      setImageUrl(imageUrl);
      setCaptureTime(new Date().toLocaleTimeString());

      const fileExtension = data.filename.split('.').pop();
      const newFilename = `${pageLoadTime}_${captureCount}.${fileExtension}`;
      setLastCapturedImage(newFilename);
      
      const downloadResponse = await fetch(imageUrl);
      const blob = await downloadResponse.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = newFilename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      setCaptureCount(prev => prev +1)
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

  const handleLampChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const lamp = event.target.value as 'upper_led' | 'side_led' | 'none';
    setSelectedLamp(lamp);

    const params: LedParameters = {
    upper_led: lamp === 'upper_led' ? Parameters.upper_led : 0,
    side_led: lamp === 'side_led' ? Parameters.side_led : 0
  };

    sendLedUpdate(params);
  };

  const sendLedUpdate = debounce(async (params: LedParameters) => {
  try {
    const response = await fetch('http://localhost:2076/led_control', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });
     if (!response.ok) {
      throw new Error('Failed to update LED settings');
    }
  } catch (error) {
    console.error('Error updating LED settings:', error);
  }
}, 2000);

  return (
    <ProtectedRoute>
    <div className="camera-container" style={{ padding: '20px', height: '100vh'}}>
      <br></br>
      <div style={{alignItems: 'center', justifyContent: 'center', display: 'flex'}}>
      <Button 
          variant="contained"
          size= "large"
          onClick={captureImage}
          onMouseDown={handleHoldStart}
          onMouseUp={handleHoldEnd}
          onMouseLeave={handleHoldEnd}
          onTouchStart={handleHoldStart}
          onTouchEnd={handleHoldEnd}
          disabled={isLoading || !isLiveFeedActive}
          className="capture-button"
          style={{ marginRight: '20px' }}
        >
          {isLoading ? 'Capturing...' : 'Capture Image'}

          {showLastImage && lastCapturedImage && (
          <span style={{
            position: 'absolute',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(0,0,0,0.8)',
            color: 'white',
            padding: '6px 12px',
            borderRadius: '4px',
            fontSize: '0.875rem',
            whiteSpace: 'nowrap',
            marginBottom: '8px',
            zIndex: 1
          }}>
            Last: {lastCapturedImage}
          </span>
        )}
        </Button>
       <Button 
          variant="contained"
          size='large'
          color={isLiveFeedActive ? 'secondary' : 'primary'}
          onClick={toggleLiveFeed}
        >
          {isLiveFeedActive ? 'Stop Live Feed' : 'Start Live Feed'}
        </Button>
        </div>
      
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
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <FormControlLabel
          control={
            <Radio
              checked={selectedLamp === 'upper_led'}
              onChange={handleLampChange}
              value="upper_led"
              name="lamp-selection"
            />
          }
          label="Upper Lamp"
        />
        <FormControlLabel
          control={
            <Radio
              checked={selectedLamp === 'side_led'}
              onChange={handleLampChange}
              value="side_led"
              name="lamp-selection"
            />
          }
          label="Side Lamp"
        />
        <FormControlLabel
          control={
            <Radio
              checked={selectedLamp === 'none'}
              onChange={handleLampChange}
              value="none"
              name="lamp-selection"
            />
          }
          label="None"
        />
      </div>
      <br></br>
       <Link href="/imagecapture" passHref>
            <Button variant="contained">
              Back to Image Capture Page
            </Button>
          </Link>
    </div>
    </ProtectedRoute>
  );
};

export default CameraApp;