"use client";

import React, { useState, useEffect } from 'react';
import { Typography, Paper, Box, TextField, Alert, FormControlLabel, Checkbox, Radio, LinearProgress, Snackbar } from '@mui/material';
import Button from '@mui/material/Button';
import Link from 'next/link';
import MuiAlert, { AlertProps } from '@mui/material/Alert';

const AlertComponent = React.forwardRef<HTMLDivElement, AlertProps>(function Alert(
  props,
  ref,
) {
  return <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />;
});

interface DataAvailability {
  images: boolean;
  mask_images: boolean;
  split: boolean;
  background_changed: boolean;
}

const CameraApp: React.FC = () => {
const [availability, setAvailability] = useState<DataAvailability>({
    images: false,
    mask_images: false,
    split: false,
    background_changed: false
  });
  const [loading, setLoading] = useState(true);
  const [availabilityError, setAvailabilityError] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [selectedMode, setSelectedMode] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressInfo, setProgressInfo] = useState({
      progress: 0,
      processed: 0,
      total: 0
    });
    const [snackbarOpen, setSnackbarOpen] = useState(false);

  useEffect(() => {
      const fetchDataAvailability = async () => {
        try {
          const response = await fetch('http://localhost:2076/data_availability_for_stream_images');
          if (!response.ok) {
            throw new Error('Failed to fetch data availability');
          }
          const data = await response.json();
          setAvailability({
            images: data.images,
            mask_images: data.mask_images,
            split: data.split,
            background_changed: data.background_changed
          });
          setSuccess(true);
        } catch (err) {
          setAvailabilityError(err instanceof Error ? err.message : 'An unknown error occurred');
        } finally {
          setLoading(false);
        }
      };
  
      fetchDataAvailability();
    }, []);

    const handleModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      setSelectedMode(event.target.value);
    };

    const startSplit = async () => {
    if (selectedMode === '') {
        setStreamError(`You must choose a mode!`);
        return;
    }

    setIsProcessing(true);
    setStreamError(null);

    try {
        const response = await fetch('http://localhost:2076/start_stream_images', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ mode: selectedMode })
        });

        if (!response.ok) {
            throw new Error('Failed to start stream image creation');
        }
        
    } catch (err) {
        setStreamError(err instanceof Error ? err.message : 'An unknown error occurred');
    }
};

   useEffect(() => {
      let intervalId: NodeJS.Timeout;
  
      if (isProcessing) {
        intervalId = setInterval(async () => {
          try {
            const response = await fetch('http://localhost:2076/get_stream_image_progress');
            if (response.ok) {
              const data = await response.json();
              setProgressInfo({
                progress: data.progress,
                processed: data.processed,
                total: data.total
              });
              setProgress(data.progress);
              
              if (data.progress === 100) {
                clearInterval(intervalId);
                setSnackbarOpen(true)
                setIsProcessing(false);
              }
            }
          } catch (err) {
            console.error('Error fetching progress:', err);
          }
        }, 500);
      }
  
      return () => {
        if (intervalId) clearInterval(intervalId);
      };
    }, [isProcessing]);

    const handleSnackbarClose = (event?: React.SyntheticEvent | Event, reason?: string) => {
        if (reason === 'clickaway') {
          return;
        }
        setSnackbarOpen(false);
      };

  return(
    <div className="camera-container" style={{ padding: '20px', height: '100vh', display: 'flex' }}>
        <div style={{ flex: '1 1 33%' }}>
            <h1>Data availability check:</h1>
            <br />
            {loading ? (
              <Typography>Loading availability status...</Typography>
            ) : availabilityError && success ? (
              <Alert severity="error">{availabilityError}</Alert>
            ) : (
              <>
                <FormControlLabel
                  control={<Checkbox checked={availability.images} disabled />}
                  sx={{
                    '& .MuiSvgIcon-root': {
                      color: availability.images ? '#04e762' : '#ef233c' ,
                      fontSize: 28,
                    },
                  }}
                  label={
                    <span style={{
                      color: availability.images ? '#04e762' : '#ef233c',
                      fontWeight: 'bold'
                    }}>
                      Images
                    </span>
                  }
                />
                <br></br>
                <FormControlLabel
                  control={<Checkbox checked={availability.mask_images} disabled />}
                  sx={{
                    '& .MuiSvgIcon-root': {
                      color: availability.mask_images ? '#04e762' : '#ef233c' ,
                      fontSize: 28,
                    },
                  }}
                  label={
                    <span style={{
                      color: availability.mask_images ? '#04e762' : '#ef233c',
                      fontWeight: 'bold'
                    }}>
                      Masks
                    </span>
                  }
                /><br></br>
                <FormControlLabel
                  control={<Checkbox checked={availability.split} disabled />}
                  sx={{
                    '& .MuiSvgIcon-root': {
                      color: availability.split ? '#04e762' : '#ef233c' ,
                      fontSize: 28,
                    },
                  }}
                  label={
                    <span style={{
                      color: availability.split ? '#04e762' : '#ef233c',
                      fontWeight: 'bold'
                    }}>
                      Split Consumer/Reference
                    </span>
                  }
                />
                <br></br>
                <FormControlLabel
                  control={<Checkbox checked={availability.background_changed} disabled />}
                  sx={{
                    '& .MuiSvgIcon-root': {
                      color: availability.background_changed ? '#04e762' : '#ef233c' ,
                      fontSize: 28,
                    },
                  }}
                  label={
                    <span style={{
                      color: availability.background_changed ? '#04e762' : '#ef233c',
                      fontWeight: 'bold'
                    }}>
                      Background Changed
                    </span>
                  }
                />
              </>
            )}
          </div>
          <div style={{ flex: '1 1 33%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <h1 style={{ fontSize: '40px', fontWeight: 'bold' }}>Create Stream Images</h1>
            <div>
            {streamError && <Alert severity="warning" style={{ marginBottom: '20px' }}>{streamError}</Alert>}
            <FormControlLabel
                control={
                  <Radio
                    checked={selectedMode === 'consumer'}
                    onChange={handleModeChange}
                    value="consumer"
                    name="lamp-selection"
                  />
                }
                label="Consumer"
              />
              <FormControlLabel
                control={
                  <Radio
                    checked={selectedMode === 'reference'}
                    onChange={handleModeChange}
                    value="reference"
                    name="lamp-selection"
                  />
                }
                label="Reference"
              />
              </div>
              <br></br>
              <Button 
                variant="contained" 
                color="primary" 
                onClick={startSplit}
                style={{ marginTop: '20px' }}
                disabled={isProcessing && selectedMode==''}
              >
                {isProcessing ? 'Processing...' : 'Start'}
              </Button>
              <div>
                <br></br>
              </div>
              <LinearProgress variant="determinate" value={progress} style={{width: '100%'}} />
                  {progress > 0 && progress < 100 && (
                    <Typography variant="body2" style={{ marginTop: '10px' }}>
                      Creating Stream images... {progress}% ({progressInfo.processed}/{progressInfo.total} files)
                    </Typography>
                  )}
                  {progress === 100 && (
                    <Typography variant="body2" style={{ marginTop: '10px' }}>
                      Stream Images created successfully! ({progressInfo.total} files processed)
                    </Typography>
                  )}
          </div>
          <div style={{ flex: '1 1 33%' }}></div>
          <div style={{
        position: 'absolute',
        left: '20px',
        bottom: '20px'
      }}>
        <Link href="/datapreparation" passHref>
          <Button variant="contained">
            Back to Data Preparation Page
          </Button>
        </Link>
        </div>
        <Snackbar 
          open={snackbarOpen} 
          autoHideDuration={6000} 
          onClose={handleSnackbarClose}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
          <AlertComponent onClose={handleSnackbarClose} severity="success" sx={{ width: '100%' }}>
            Stream images successfully created!
          </AlertComponent>
        </Snackbar>
    </div>
  );


};

export default CameraApp;