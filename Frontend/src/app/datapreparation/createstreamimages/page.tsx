"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Typography, Paper, Box, TextField, Alert, FormControlLabel, Checkbox, Radio, LinearProgress, Snackbar } from '@mui/material';
import Button from '@mui/material/Button';
import Link from 'next/link';
import MuiAlert, { AlertProps } from '@mui/material/Alert';
import { closeSnackbar, SnackbarProvider } from 'notistack';
import { useSnackbar } from 'notistack';
import ProtectedRoute from '../../../../components/ProtectedRoute';
import { ROLES } from '../../../../constans/roles';

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
  const [availabilitySuccess, setAvailabilitySuccess] = useState(false)
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
  const { enqueueSnackbar } = useSnackbar();
  const [dataSuccess, setDataSuccess] = useState(false);
  const [modeSelected, setModeSelected] = useState(false);
  const [stopEnabled, setStopEnabled] = useState(false);

  const stopStream = async () => {
  try {
    const response = await fetch('http://localhost:2076/stop_stream_image', {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to stop stream image process');
    }

    const result = await response.json();
    if (result.status === 'success') {
      setIsProcessing(false);
      setStopEnabled(false);
      setProgress(0);
      enqueueSnackbar('Process stopped successfully and output directories cleared', { 
        variant: 'info',
        autoHideDuration: 10000
      });
    } else {
      enqueueSnackbar(result.message, { 
        variant: 'warning',
        autoHideDuration: 10000
      });
    }
  } catch (error) {
    console.error('Error stopping stream image process:', error);
    enqueueSnackbar('Error stopping process', { 
      variant: 'error',
      autoHideDuration: 10000
    });
  }
};

  const handleMissingData = async (currentData: DataAvailability) => {
    try {
      console.log(currentData);
      if (!currentData.split && currentData.images && currentData.mask_images) {
        enqueueSnackbar("Images haven't been sorted by Consumer/Reference. Starting it now", { 
          variant: 'info',
          autoHideDuration: 10000
        });
        const response = await fetch('http://localhost:2076/split_consumer_reference', {
          method: 'POST'
        });
        if (!response.ok) {
          throw new Error('Failed to split consumer reference');
        }
        enqueueSnackbar('Consumer/Reference split completed successfully!', { 
          variant: 'success',
          autoHideDuration: 10000
        });
      }
      if (!currentData.background_changed && currentData.images && currentData.mask_images) {
        enqueueSnackbar("Image backgrounds haven't been removed yet. Starting it now", { 
          variant: 'info',
          autoHideDuration: 10000
        });
        const response = await fetch('http://localhost:2076/change_background', {
          method: 'POST'
        });
        if (!response.ok) {
          throw new Error('Failed to change background');
        }
        enqueueSnackbar('Background change completed successfully!', { 
          variant: 'success',
          autoHideDuration: 10000
        });
      }
    } catch (err) {
      setAvailabilityError(err instanceof Error ? err.message : 'An unknown error occurred');
    }
  };

  useEffect(() => {
    const fetchDataAvailability = async () => {
      try {
        const response = await fetch('http://localhost:2076/data_availability_for_stream_images');
        if (!response.ok) {
          throw new Error('Failed to fetch data availability');
        }
        const data = await response.json();
        
        setAvailability(data);
        
        if (!data.split || !data.background_changed) {
          await handleMissingData(data);
          
          const newResponse = await fetch('http://localhost:2076/data_availability_for_stream_images');
          const newData = await newResponse.json();
          setAvailability(newData);
        }
        
        setSuccess(true);
        setDataSuccess(true);
      } catch (err) {
        setAvailabilityError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchDataAvailability();
  }, []);

    const handleModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      setModeSelected(true);
      setSelectedMode(event.target.value);
    };

    const startSplit = async () => {
    if (selectedMode === '') {
        setStreamError(`You must choose a mode!`);
        return;
    }

    setIsProcessing(true);
    setStopEnabled(true);
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
        setStopEnabled(false);
        setIsProcessing(false);
        setStreamError(err instanceof Error ? err.message : 'An unknown error occurred');
    }
};

useEffect(() => {
  if (progress >= 100) {
    setStopEnabled(false);
  }
}, [progress]);

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
                enqueueSnackbar('Stream images successfully created!', { 
                variant: 'success',
                autoHideDuration: 10000
              });
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

  return(
    <ProtectedRoute allowedRoles={[ROLES.ADMIN, ROLES.TECHNICIAN]}>
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
              <div style={{display: 'flex', marginTop: '20px', marginLeft: '10px', flexDirection: 'column' }}>
              <Button 
                variant="contained" 
                color="primary" 
                onClick={startSplit}
                style={{ flex: '1', marginBottom: '20px' }}
                disabled={isProcessing || !(modeSelected) || !(dataSuccess)}
              >
                {isProcessing && availabilitySuccess ? 'Processing...' : 'Start'}
              </Button>
              <br></br>
              <Button 
                variant="contained" 
                color="error" 
                onClick={stopStream}
                style={{ flex:'1' }}
                disabled={!stopEnabled}
              >
                Stop
              </Button>
              </div>
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
    </div>
    </ProtectedRoute>
  );


};

const CameraAppWithSnackbar = () => (
  <SnackbarProvider 
    maxSnack={6} 
    autoHideDuration={10000} 
    anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
    preventDuplicate
    action={(snackbarId) => (
    <button 
      onClick={() => closeSnackbar(snackbarId)}
      style={{ color: 'white', background: 'transparent', border: 'none' }}
    >
      ✕
    </button>
  )}
  >
    <CameraApp />
  </SnackbarProvider>
);

export default CameraAppWithSnackbar;