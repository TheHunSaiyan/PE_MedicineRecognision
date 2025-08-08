"use client";

import React, { useState, useEffect } from 'react';
import {Button, Paper, FormControlLabel, Radio, TextField, FormControl, InputLabel, Select, MenuItem, Checkbox, LinearProgress, Typography, Snackbar} from '@mui/material';
import Link from 'next/link';
import MuiAlert, { AlertProps } from '@mui/material/Alert';
import ProtectedRoute from '../../../../components/ProtectedRoute';

const AlertComponent = React.forwardRef<HTMLDivElement, AlertProps>(function Alert(
  props,
  ref,
) {
  return <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />;
});

const CameraApp: React.FC = () => {
const [foldMode, setfoldMode] = useState('');
const[foldNumber, setfoldNumber] = useState(1);
const [selectedFold, setSelectedFold] = useState('fold1');
const [erase, setErase] = useState(false);
const [isProcessing, setIsProcessing] = useState(false);
const [error, setError] = useState<string | null>(null);
const [progress, setProgress] = useState(0);
const [progressInfo, setProgressInfo] = useState({
    progress: 0,
    processed: 0,
    total: 0
  });
const [snackbarOpen, setSnackbarOpen] = useState(false);
const [foldDataLoaded, setFoldDataLoaded] = useState(false);

  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (isProcessing) {
      interval = setInterval(async () => {
        const response = await fetch('http://localhost:2076/get_sort_process');
        const data = await response.json();
        setProgress(data.progress);
        setProgressInfo(data);
        if (data.progress >= 100) {
          setIsProcessing(false);
          setSnackbarOpen(true)
          clearInterval(interval);
        }
      }, 1000);
    }

    return () => clearInterval(interval);
  }, [isProcessing]);

const handleModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setfoldMode(event.target.value);
    setFoldDataLoaded(false);
  };

const handleNumberChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    let newNumber = Number(event.target.value);
    if (newNumber < 1) newNumber = 1;
    if (newNumber > 10) newNumber = 10;
    setfoldNumber(newNumber);
    if (parseInt(selectedFold.replace('fold', '')) > newNumber) {
      setSelectedFold('fold1');
    }
    setFoldDataLoaded(false);
  };

  const handleFoldChange = (event: any) => {
    setSelectedFold(event.target.value);
  };

   const getFold = async () => {
    if (foldMode === '') {
      setError(`You must choose a fold mode!`);
      return;
    }

    setIsProcessing(true);
    setError(null);
    setFoldDataLoaded(false);

    try {
      const response = await fetch('http://localhost:2076/get_fold', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          load: foldMode === 'exists',
          num_folds: foldNumber
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get fold data');
      }

      const data = await response.json();
      setfoldNumber(data.num_folds)
      
      setFoldDataLoaded(true);
    } catch (err) {
      setIsProcessing(false);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsProcessing(false);
    }
  };

  const foldOptions = Array.from({ length: foldNumber }, (_, i) => `fold${i + 1}`);

  const startSorting = async () => {
    if (foldMode === '') {
      setError(`You must choose a fold mode!`);
      return;
    }

    setIsProcessing(true);
    setError(null);
    setProgress(0);
    setProgressInfo({ progress: 0, processed: 0, total: 0 });

    try {
      const response = await fetch('http://localhost:2076/start_sort', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: foldMode,
          num_folds: foldNumber,
          selected_fold: selectedFold,
          erase: erase
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start sorting process');
      }
    } catch (err) {
      setIsProcessing(false);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    }
  };

  const handleSnackbarClose = (event?: React.SyntheticEvent | Event, reason?: string) => {
      if (reason === 'clickaway') {
        return;
      }
      setSnackbarOpen(false);
    };


    return (
      <ProtectedRoute>
    <div className="camera-container" style={{
        position: 'absolute', left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)'
    }}>
    <div style={{ 
        textAlign: 'center', 
        marginBottom: '20px',
        width: '33.33%',
        minWidth: '300px',
        margin: '0 auto'}}>
            <br></br>
      <h1 style={{ fontSize:'40px' }}>K-Fold Sort</h1>
      <br></br>
      <Paper elevation={3} sx={{ 
      p: 3,
      display: 'flex',
      flexDirection: 'column',
      width: '100%',
      boxSizing: 'border-box'
    }}>
         <FormControlLabel
             control={
               <Radio
                 checked={foldMode === 'exists'}
                 onChange={handleModeChange}
                 value="exists"
                 name="fold"
               />
             }
             label="Load existing folds"
           />
           <br></br>
           <FormControlLabel
             control={
               <Radio
                 checked={foldMode === 'new'}
                 onChange={handleModeChange}
                 value="new"
                 name="fold"
               />
             }
             label="Generate new folds"
           />
           <br></br>
           <TextField
            label="Fold Number"
            type="number"
            value={foldNumber}
            onChange={handleNumberChange}
            inputProps={{ 
              min: 1,
              max: 10,
              step: 1
            }}
            sx={{ mt: 2 }}
            error={foldNumber < 1 || foldNumber > 10}
            helperText={foldNumber < 1 || foldNumber > 10 ? "Must be between 1 and 10" : ""}
          />
          <Button 
                variant="contained" 
                color="primary" 
                onClick={getFold}
                style={{ marginTop: '20px' }}
                disabled={isProcessing && foldMode==''}
              >
                {isProcessing ? 'Processing...' : 'Fold Load/Generate'}
              </Button>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Select Fold</InputLabel>
            <Select
              value={selectedFold}
              label="Select Fold"
              onChange={handleFoldChange}
              disabled={!foldDataLoaded || isProcessing}
            >
              {foldOptions.map((fold) => (
                <MenuItem key={fold} value={fold}>{fold}</MenuItem>
              ))}
            </Select>
          </FormControl>
            <Button 
                variant="contained" 
                color="primary" 
                onClick={startSorting}
                style={{ marginTop: '20px' }}
                disabled={!foldDataLoaded || isProcessing}
              >
                {isProcessing ? 'Processing...' : 'Start'}
              </Button>
              <div>
                <br></br>
              </div>
             {error && (
            <Typography color="error" variant="body2" sx={{ mt: 1 }}>
              {error}
            </Typography>
          )}

          <LinearProgress variant="determinate" value={progress} sx={{ mt: 2 }} />
          {progress > 0 && progress < 100 && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Sorting images... {progress}% ({progressInfo.processed}/{progressInfo.total})
            </Typography>
          )}
          {progress === 100 && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Images sorted successfully! ({progressInfo.total} files processed)
            </Typography>
          )}
    </Paper>
      </div>
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
            K-Fold sort successfully!
          </AlertComponent>
        </Snackbar>
    </div>
    </ProtectedRoute>
  );

};

export default CameraApp;