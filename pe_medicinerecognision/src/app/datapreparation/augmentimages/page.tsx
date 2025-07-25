"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Typography, Paper, Box, TextField, Alert, FormControlLabel, Checkbox, Snackbar } from '@mui/material';
import Button from '@mui/material/Button';
import Link from 'next/link';
import InputAdornment from '@mui/material/InputAdornment';
import MuiAlert, { AlertProps } from '@mui/material/Alert';
import LinearProgress from '@mui/material/LinearProgress';

const AlertComponent = React.forwardRef<HTMLDivElement, AlertProps>(function Alert(
  props,
  ref,
) {
  return <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />;
});

interface DataAvailability {
  images: boolean;
  segmentation_labels: boolean;
  mask_images: boolean;
}

interface Augmentation {
    white_balance: boolean;
    blur: boolean;
    brightness: boolean;
    rotate: boolean;
    shift: boolean;
    zoom: boolean;
    change_background: boolean;
    qr_code: boolean;
    augmentation_per_image: number;
}

interface ProgressData {
    current: number;
    total: number;
    progress: number;
    status: string;
}

const CameraApp: React.FC = () => {
const [availability, setAvailability] = useState<DataAvailability>({
    images: false,
    segmentation_labels: false,
    mask_images: false
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [augmentation, setAugmentation] = useState<Augmentation>({
    white_balance: false,
    blur: false,
    brightness: false,
    rotate: false,
    shift: false,
    zoom: false,
    change_background: false,
    qr_code: true,
    augmentation_per_image: 1
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [progress, setProgress] = useState<ProgressData>({
    current: 0,
    total: 0,
    progress: 0,
    status: 'Idle'
  });
 const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const fetchDataAvailability = async () => {
      try {
        const response = await fetch('http://localhost:2076/data_availability');
        if (!response.ok) {
          throw new Error('Failed to fetch data availability');
        }
        const data = await response.json();
        setAvailability({
          images: data.images,
          segmentation_labels: data.segmentation_labels,
          mask_images: data.mask_images
        });
        setSuccess(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchDataAvailability();
  }, []);

const handleAugmentationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setAugmentation(prev => ({
      ...prev,
      [name]: checked
    }));
  };

  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setAugmentation(prev => ({
      ...prev,
      [name]: parseInt(value, 10)
    }));
  };

  const handleSnackbarClose = (event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    setSnackbarOpen(false);
  };

 const checkProgress = async () => {
  try {
    const response = await fetch('http://localhost:2076/get_augmentation_progress');
    if (!response.ok) {
      throw new Error('Failed to fetch progress');
    }

    const data = await response.json();
    console.log("Progress data:", data);
    setProgress(data);

    if (data.total > 0 && data.current >= data.total) {
      setIsProcessing(false);
      setSnackbarOpen(true);
      return;
    }

    progressIntervalRef.current = setTimeout(checkProgress, 500);
  } catch (err) {
    console.error('Error during progress polling:', err);
    setError('Error checking progress');
    setIsProcessing(false);
  }
};



  const startAugmentation = () => {
  setError(null);
  setIsProcessing(true);

  setProgress({
    current: 0,
    total: 0,
    progress: 0,
    status: 'Starting...',
  });

  checkProgress();

  fetch('http://localhost:2076/start_augmentation', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(augmentation),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error('Failed to start augmentation');
      }
      return response.json();
    })
    .then((data) => {
      console.log("Augmentation finished:", data);
    })
    .catch((err) => {
      console.error('Error starting augmentation:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      setIsProcessing(false);
    });
};




return (
    <div className="camera-container" style={{ padding: '20px', height: '100vh', display: 'flex' }}>
        <div style={{ flex: '1 1 33%' }}>
        <h1>Data availability check:</h1>
        <br />
        {loading ? (
          <Typography>Loading availability status...</Typography>
        ) : error && success ? (
          <Alert severity="error">{error}</Alert>
        ) : (
          <>
            <FormControlLabel
              control={<Checkbox checked={availability.images} disabled />}
              label="Images"
            />
            <br></br>
            <FormControlLabel
              control={<Checkbox checked={availability.segmentation_labels} disabled />}
              label="Segmentation Labels"
            />
            <br></br>
            <FormControlLabel
              control={<Checkbox checked={availability.mask_images} disabled />}
              label="Masks"
            />
          </>
        )}
      </div>
         <div style={{ flex: '1 1 66%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <h1 style={{ fontSize: '40px', fontWeight: 'bold' }}>Augmentation</h1>
            <Paper elevation={3} style={{ padding: '20px', marginBottom: '20px', width: '100vh' }}>
                      <Typography variant="h6" gutterBottom>Augmentation methods</Typography>
                      {error && <Alert severity="warning" style={{ marginBottom: '20px' }}>{error}</Alert>}
                      <Box component="form" noValidate autoComplete="off">
                        <FormControlLabel
                           control={<Checkbox 
                             name="white_balance"
                             checked={augmentation.white_balance}
                             onChange={handleAugmentationChange}
                           />}
                           label="White Balance"
                         />
                         <br></br>
                         <FormControlLabel
                           control={<Checkbox 
                             name="blur"
                             checked={augmentation.blur}
                             onChange={handleAugmentationChange}
                           />}
                           label="Blur"
                         />
                         <br></br>
                         <FormControlLabel
                           control={<Checkbox 
                             name="brightness"
                             checked={augmentation.brightness}
                             onChange={handleAugmentationChange}
                           />}
                           label="Brightness"
                         />
                         <br></br>
                         <FormControlLabel
                           control={<Checkbox 
                             name="rotate"
                             checked={augmentation.rotate}
                             onChange={handleAugmentationChange}
                           />}
                           label="Rotate"
                         />
                         <br></br>
                         <FormControlLabel
                           control={<Checkbox 
                             name="shift"
                             checked={augmentation.shift}
                             onChange={handleAugmentationChange}
                           />}
                           label="Shift"
                         />
                         <br></br>
                         <FormControlLabel
                           control={<Checkbox 
                             name="zoom"
                             checked={augmentation.zoom}
                             onChange={handleAugmentationChange}
                           />}
                           label="Zoom"
                         />
                         <br></br>
                         <FormControlLabel
                           control={<Checkbox 
                             name="change_background"
                             checked={augmentation.change_background}
                             onChange={handleAugmentationChange}
                           />}
                           label="Change Background"
                         />
                         <br></br>
                         <FormControlLabel
                           control={<Checkbox 
                             name="qr_code"
                             checked={augmentation.qr_code}
                             onChange={handleAugmentationChange}
                           />}
                           label="QR Code"
                         />
                         <br></br>
                         <TextField
                           fullWidth
                           margin="normal"
                           label="Augmentation per image"
                           name="augmentation_per_image"
                           type="number"
                           value={augmentation.augmentation_per_image}
                           onChange={handleNumberChange}
                           inputProps={{ min: 1, max: 100 }}
                           InputProps={{
                             endAdornment: <InputAdornment position="end">times</InputAdornment>,
                           }}
                         />
                         <Box sx={{ display: 'flex', justifyContent: 'center', marginTop: '20px' }}>
                           <Button 
                             variant="contained" 
                             color="primary" 
                             onClick={startAugmentation}
                             style={{ marginTop: '20px' }}
                             disabled={isProcessing}
                           >
                             {isProcessing ? 'Processing...' : 'Start Augmentation'}
                           </Button>
                           {isProcessing && (
                              <>
                                <LinearProgress 
                                  variant="determinate" 
                                  value={progress.progress} 
                                  style={{ width: '100%' }} 
                                />
                                <Typography variant="body2" style={{ marginTop: '10px' }}>
                                  {progress.status}: {progress.current}/{progress.total} images processed ({Math.round(progress.progress)}%)
                                </Typography>
                              </>
                            )}
                         </Box>
                      </Box>
                      </Paper>
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
          Augmentation finished successfully!
        </AlertComponent>
      </Snackbar>
    </div>
);

};

export default CameraApp;