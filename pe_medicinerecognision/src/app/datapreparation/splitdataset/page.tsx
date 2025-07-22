"use client";

import React, { useState, useEffect } from 'react';
import { Typography, Paper, Box, TextField, Alert, FormControlLabel, Checkbox } from '@mui/material';
import Button from '@mui/material/Button';
import Link from 'next/link';
import LinearProgress from '@mui/material/LinearProgress';
import InputAdornment from '@mui/material/InputAdornment';

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
  const [error, setError] = useState<string | null>(null);
  const [splitParams, setSplitParams] = useState<SplitParams>({
    train: 70,
    val: 20,
    test: 10,
    segregated: false
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [success, setSuccess] = useState(false);

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
      setError(`Split percentages must sum to 100% (current sum: ${total}%)`);
      return;
    }

    if(splitParams.train == 0 || splitParams.val == 0 || splitParams.test == 0){
        setError("Values can't be 0.")
        return;
    }

    setIsProcessing(true);
    setError(null);
    setProgress(0);

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
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsProcessing(false);
    }
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
            <h1 style={{ fontSize: '40px', fontWeight: 'bold' }}>Split Dataset</h1>
            <br></br>
            <FormControlLabel
          control={<Checkbox 
            checked={splitParams.segregated} 
            onChange={handleCheckboxChange}
            name="segregated"
          />}
          label="Enable Segregated Split"
        />
              <br></br>
              <Paper elevation={3} style={{ padding: '20px', marginBottom: '20px' }}>
          <Typography variant="h6" gutterBottom>Split Ratios</Typography>
          {error && <Alert severity="warning" style={{ marginBottom: '20px' }}>{error}</Alert>}
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
            <Box sx={{ display: 'flex', justifyContent: 'center', marginTop: '20px' }}>
            <Button 
                variant="contained" 
                color="primary" 
                onClick={startSplit}
                style={{ marginTop: '20px' }}
                disabled={isProcessing}
              >
                {isProcessing ? 'Processing...' : 'Start'}
              </Button>
            </Box>
          </Box>
            </Paper>
            <br></br>
            <LinearProgress variant="determinate" value={progress} style={{width: '100%'}} />
        {progress > 0 && progress < 100 && (
          <Typography variant="body2" style={{ marginTop: '10px' }}>
            Splitting dataset... {progress}%
          </Typography>
        )}
        {progress === 100 && (
          <Typography variant="body2" style={{ marginTop: '10px' }}>
            Dataset split completed successfully!
          </Typography>
        )}
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
    </div>
);

};

export default CameraApp;