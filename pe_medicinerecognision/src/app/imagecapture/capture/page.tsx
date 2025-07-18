"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import Select from 'react-select'
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';

interface Medication {
  id: number;
  name: string;
}

interface SelectOption {
  value: string;
  label: string;
}

const CameraApp: React.FC = () => {
const [imageUrl, setImageUrl] = useState<string>('');
  const [captureTime, setCaptureTime] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const [isLiveFeedActive, setIsLiveFeedActive] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [pillsOptions, setPillsOptions] = useState<SelectOption[]>([]);
  const [isLoadingPills, setIsLoadingPills] = useState<boolean>(true);
  const [selectedLamp, setSelectedLamp] = useState('');
  const [selectedPillSide, setSelectedPillSide] = useState('');
  const [isClient, setIsClient] = useState(false);
  const [filePath, setFilePath] = useState('');
  const [snackbarOpen, setSnackbarOpen] = useState(false);
const [snackbarMessage, setSnackbarMessage] = useState('');
const [snackbarSeverity, setSnackbarSeverity] = useState<'error' | 'warning' | 'info' | 'success'>('error');

const showMessage = (message: string, severity: 'error' | 'warning' | 'info' | 'success' = 'error') => {
  setSnackbarMessage(message);
  setSnackbarSeverity(severity);
  setSnackbarOpen(true);
};

  useEffect(() => {
    setIsMounted(true);
    setIsClient(true);

    const fetchPills = async () => {
      try {
        const response = await fetch('http://localhost:2076/pills');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const pillsData = await response.json();
        const options = pillsData.medications.map((medication: Medication) => ({
          value: medication.name,
          label: medication.id.toString() + '. ' + formatMedicationName(medication.name)
        }));
        
        setPillsOptions(options);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load pills data');
      } finally {
        setIsLoadingPills(false);
      }
    };
    
    fetchPills();

    return () => setIsMounted(false);
  }, []);

const formatMedicationName = (name: string): string => {
  return name
    .split('_')
    .map((word, index, array) => {
      let formatted = word.charAt(0).toUpperCase() + word.slice(1);
      
      if (index < array.length - 1) {
        const currentIsNumber = !isNaN(Number(word));
        const nextIsNumber = !isNaN(Number(array[index + 1]));
        
        if (currentIsNumber && nextIsNumber) {
          formatted += ',';
        } else {
          formatted += ' ';
        }
      }
      return formatted;
    })
    .join('');
};
  const captureImage = async () => {
  if (!isMounted || !selectedOption) {
    showMessage('Please select a pill before capturing');
    return;
  }
  if (!selectedLamp) {
    showMessage('Please select a lamp position before capturing');
    return;
  }
  if (!selectedPillSide) {
    showMessage('Please select a pill side before capturing');
    return;
  }

  setIsLoading(true);
  setError(null);
  
  try {
    const apiUrl = 'http://localhost:2076';
    const response = await fetch(`${apiUrl}/capture_pill`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        pill_name: selectedOption,
        lamp_position: selectedLamp,
        pill_side: selectedPillSide
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (data.status === 'success' && data.filename) {
      setImageUrl(`${apiUrl}/captured-images/${data.filename}`);
      setCaptureTime(new Date().toLocaleTimeString());
      setFilePath(data.filename)
    } else {
      throw new Error(data.error || 'Failed to capture image');
    }
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Unknown error occurred');
    showMessage(err instanceof Error ? err.message : 'Unknown error occurred');
  } finally {
    setIsLoading(false);
  }
};

  const toggleLiveFeed = () => {
  if (!selectedOption && !isLiveFeedActive) {
    showMessage('Please select a pill before starting the live feed');
    return;
  }
  setIsLiveFeedActive(!isLiveFeedActive);
};

  const handleLampChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      setSelectedLamp(event.target.value);
    };

  const handlePillSideChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      setSelectedPillSide(event.target.value);
    };

  return (
    <div className="camera-container" style={{ padding: '20px', height: '100vh' }}>
      { isClient && (
     <Select<SelectOption>
        options={pillsOptions}
        isLoading={isLoadingPills}
        onChange={(selected) => {
          setSelectedOption(selected?.label ?? null);
        }}
        value={pillsOptions.find(option => option.value === selectedOption)}
        placeholder={isLoadingPills ? "Loading pills..." : "Select a pill"}
        styles={{
          control: (base) => ({
            ...base,
            marginBottom: '20px'
          }),
          option: (base) => ({
            ...base,
            color: 'black'
          }),
        }}
      />)}
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

        <label style={{ marginLeft: '20px', marginRight: '10px' }}>
          <input
            type="radio"
            name="lampSelection"
            value="upperLamp"
            checked={selectedLamp === 'upperLamp'}
            onChange={handleLampChange}
          />
          Upper Lamp
        </label>

        <label style={{ marginRight: '10px' }}>
          <input
            type="radio"
            name="lampSelection"
            value="sideLamp"
            checked={selectedLamp === 'sideLamp'}
            onChange={handleLampChange}
          />
          Side Lamp
        </label>
        <label style={{ marginRight: '10px', marginLeft: '20px' }}>
          <input
            type="radio"
            name="pillSideSelection"
            value="topSide"
            checked={selectedPillSide=== 'topSide'}
            onChange={handlePillSideChange}
          />
          Top Side
        </label>

        <label style={{ marginRight: '10px' }}>
          <input
            type="radio"
            name="pillSideSelection"
            value="bottomSide"
            checked={selectedPillSide === 'bottomSide'}
            onChange={handlePillSideChange}
          />
          Bottom Side
        </label>
      
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
              {filePath && <p>File Path: {filePath}</p>}
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
       <Link href="/imagecapture" passHref>
            <Button variant="contained">
              Back to Image Capture Page
            </Button>
          </Link>

          <Snackbar
  open={snackbarOpen}
  autoHideDuration={6000}
  onClose={() => setSnackbarOpen(false)}
  anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
>
  <Alert 
    onClose={() => setSnackbarOpen(false)} 
    severity={snackbarSeverity}
    sx={{ width: '100%' }}
  >
    {snackbarMessage}
  </Alert>
</Snackbar>
    </div>
  );
};

export default CameraApp;