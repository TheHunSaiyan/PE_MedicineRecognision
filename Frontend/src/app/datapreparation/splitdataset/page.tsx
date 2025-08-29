"use client";

import React, { useState, useEffect } from 'react';
import { Typography, Paper, Box, TextField, Alert, FormControlLabel, Checkbox, Snackbar } from '@mui/material';
import Button from '@mui/material/Button';
import Link from 'next/link';
import LinearProgress from '@mui/material/LinearProgress';
import InputAdornment from '@mui/material/InputAdornment';
import MuiAlert, { AlertProps } from '@mui/material/Alert';
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
  segmentation_labels: boolean;
  mask_images: boolean;
}

interface SplitParams {
  train: number;
  val: number;
  test: number;
  segregated: boolean;
}

const CameraApp: React.FC = () => {
const [availability, setAvailability] = useState<DataAvailability>({
    images: false,
    segmentation_labels: false,
    mask_images: false
  });
  const [loading, setLoading] = useState(true);
  const [availabilityError, setAvailabilityError] = useState<string | null>(null);
  const [splitError, setSplitError] = useState<string | null>(null);
  const [splitParams, setSplitParams] = useState<SplitParams>({
    train: 70,
    val: 20,
    test: 10,
    segregated: false
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [success, setSuccess] = useState(false);
   const [progressInfo, setProgressInfo] = useState({
    progress: 0,
    processed: 0,
    total: 0
  });
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
  if (progress === 100) {
    setSnackbarOpen(true);
    setIsComplete(false);
  }
}, [isComplete, progress]);

  useEffect(() => {
  const fetchDataAvailability = async () => {
    try {
      const response = await fetch('http://localhost:2076/data_availability_for_split');
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
      setAvailabilityError(null);
    } catch (err) {
      setAvailabilityError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  fetchDataAvailability();
}, []);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (isProcessing) {
      intervalId = setInterval(async () => {
        try {
          const response = await fetch('http://localhost:2076/get_split_progress');
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
              setIsProcessing(false);
              setIsComplete(true);
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

  const handleParamChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSplitParams(prev => ({
      ...prev,
      [name]: parseInt(value) || 0
    }));
  };

  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSplitParams(prev => ({
      ...prev,
      segregated: e.target.checked
    }));
  };

  const startSplit = async () => {
  const total = splitParams.train + splitParams.val + splitParams.test;
  if (total !== 100) {
    setSplitError(`Split percentages must sum to 100% (current sum: ${total}%)`);
    return;
  }

  if(splitParams.train == 0 || splitParams.val == 0 || splitParams.test == 0) {
    setSplitError("Values can't be 0.");
    return;
  }

  setIsProcessing(true);
  setSplitError(null);
  setProgress(0);
  setIsComplete(false);
  setSnackbarOpen(false);

  try {
    const response = await fetch('http://localhost:2076/start_split', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(splitParams)
    });

    if (!response.ok) {
      throw new Error('Failed to start dataset split');
    }
    setProgress(100);

  } catch (err) {
    setSplitError(err instanceof Error ? err.message : 'An unknown error occurred');
  } finally {
    setIsProcessing(false);
  }
};

const handleSnackbarClose = (event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    setSnackbarOpen(false);
  };

  const stopSplit = async () => {
  try {
    setSplitError(null);
    const response = await fetch('http://localhost:2076/stop_split', {
      method: 'POST',
    });
    
    const result = await response.json();
    
    if (!response.ok) {
      throw new Error(result.message || 'Failed to stop dataset split');
    }
    
    setProgress(0);
    setIsProcessing(false);
    setProgressInfo({
      progress: 0,
      processed: 0,
      total: 0
    });
    
  } catch (err) {
    setSplitError(err instanceof Error ? err.message : 'An unknown error occurred');
  }
};

return (
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
              control={
                <Checkbox 
                  checked={availability.images} 
                  disabled
                  sx={{
                    '& .MuiSvgIcon-root': {
                      color: availability.images ? '#04e762' : '#ef233c' ,
                      fontSize: 28,
                    },
                  }}
                />
              }
              label={
                <span style={{
                  color: availability.images ? '#04e762' : '#ef233c',
                  fontWeight: 'bold'
                }}>
                  Images
                </span>
              }
              sx={{
                '& .MuiFormControlLabel-label': {
                  color: availability.images ? '#04e762' : '#ef233c',
                  fontWeight: 'bold',
                }
              }}
            />
            <br />
            <FormControlLabel
              control={
                <Checkbox 
                  checked={availability.segmentation_labels} 
                  disabled
                  sx={{
                    '& .MuiSvgIcon-root': {
                      color: availability.segmentation_labels ? '#04e762' : '#ef233c',
                      fontSize: 28,
                    },
                  }}
                />
              }
              label={
                <span style={{
                  color: availability.images ? '#04e762' : '#ef233c',
                  fontWeight: 'bold'
                }}>
                  Segmentation Label
                </span>
              }
              sx={{
                '& .MuiFormControlLabel-label': {
                  color: availability.segmentation_labels ? '#04e762' : '#ef233c',
                  fontWeight: 'bold',
                }
              }}
            />
            <br />
            <FormControlLabel
              control={
                <Checkbox 
                  checked={availability.mask_images} 
                  disabled
                  sx={{
                    '& .MuiSvgIcon-root': {
                      color: availability.mask_images ? '#04e762' : '#ef233c',
                      fontSize: 28,
                    },
                  }}
                />
              }
              label={
                <span style={{
                  color: availability.images ? '#04e762' : '#ef233c',
                  fontWeight: 'bold'
                }}>
                  Masks
                </span>
              }
              sx={{
                '& .MuiFormControlLabel-label': {
                  color: availability.mask_images ? '#04e762' : '#ef233c',
                  fontWeight: 'bold',
                }
              }}
            />
          </>
        )}
      </div>
         <div style={{ flex: '1 1 33%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <h1 style={{ fontSize: '40px', fontWeight: 'bold' }}>Split Dataset</h1>
            <br></br>
              <br></br>
              <Paper elevation={3} style={{ padding: '20px', marginBottom: '20px' }}>
                <FormControlLabel
          control={<Checkbox 
            checked={splitParams.segregated} 
            onChange={handleCheckboxChange}
            name="segregated"
          />}
          label="Enable Segregated Split"
        />
          <Typography variant="h6" gutterBottom>Split Ratios</Typography>
          {splitError && <Alert severity="warning" style={{ marginBottom: '20px' }}>{splitError}</Alert>}
          <Box component="form" noValidate autoComplete="off">
            <TextField
              fullWidth
              margin="normal"
              label="Train %"
              name="train"
              type="number"
              value={splitParams.train}
              onChange={handleParamChange}
              inputProps={{ min: 1, max: 98 }}
              InputProps={{
                endAdornment: <InputAdornment position="end">%</InputAdornment>,
              }}
            />
            <TextField
              fullWidth
              margin="normal"
              label="Val %"
              name="val"
              type="number"
              value={splitParams.val}
              onChange={handleParamChange}
              inputProps={{ min: 1, max: 98 }}
              InputProps={{
                endAdornment: <InputAdornment position="end">%</InputAdornment>,
              }}
            />
            <TextField
              fullWidth
              margin="normal"
              label="Test %"
              name="test"
              type="number"
              value={splitParams.test}
              onChange={handleParamChange}
              inputProps={{ min: 1, max: 98 }}
              InputProps={{
                endAdornment: <InputAdornment position="end">%</InputAdornment>,
              }}
            />
            <Box sx={{ display: 'flex', justifyContent: 'center', marginTop: '20px', flexDirection: 'column' }}>
            <Button 
                variant="contained" 
                color="primary" 
                onClick={startSplit}
                style={{ marginTop: '20px' }}
                disabled={isProcessing || loading}
              >
                {isProcessing ? 'Processing...' : 'Start'}
              </Button>
              <Button 
              variant="contained" 
              color="error" 
              onClick={stopSplit}
              style={{ marginTop: '20px' }}
              disabled={!isProcessing}
            >
              Stop
            </Button>
            </Box>
          </Box>
            </Paper>
            <br></br>
            <LinearProgress variant="determinate" value={progress} style={{width: '100%'}} />
    {progress > 0 && progress < 100 && (
      <Typography variant="body2" style={{ marginTop: '10px' }}>
        Splitting dataset... {progress}% ({progressInfo.processed}/{progressInfo.total} files)
      </Typography>
    )}
    {progress === 100 && (
      <Typography variant="body2" style={{ marginTop: '10px' }}>
        Dataset split completed successfully! ({progressInfo.total} files processed)
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
                  Split was successfull!
                </AlertComponent>
              </Snackbar>
    </div>
    </ProtectedRoute>
);

};

export default CameraApp;