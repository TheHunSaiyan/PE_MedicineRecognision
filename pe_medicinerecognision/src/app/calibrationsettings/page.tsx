"use client";

import React, { useState, useRef, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import { Typography, Paper, Box, TextField, Alert } from '@mui/material';
import LinearProgress from '@mui/material/LinearProgress';

interface CameraCalibrationParams {
  chess_row: number;
  chess_col: number;
  square_size: number;
  error_threshold: number;
}

const CameraApp: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [calibrationParams, setCalibrationParams] = useState<CameraCalibrationParams>({
    chess_row: 7,
    chess_col: 6,
    square_size: 10,
    error_threshold: 0.5
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingParams, setLoadingParams] = useState<boolean>(true);
  const [progress, setProgress] = useState<number>(0);

  useEffect(() => {
    const loadCalibrationParams = async () => {
      try {
        setLoadingParams(true);
        const response = await fetch('http://localhost:2076/camera_calibration_parameters');
        
        if (response.ok) {
          const data = await response.json();
          setCalibrationParams(data);
          setError(null);
        } else if (response.status === 404) {
          setError('No saved calibration parameters found. Using default values.');
        } else {
          const errorData = await response.json();
          setError(`Failed to load parameters: ${errorData.detail || 'Unknown error'}`);
        }
      } catch (err) {
        setError(`Error loading parameters: ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setLoadingParams(false);
      }
    };

    loadCalibrationParams();
  }, []);

  const handleParamChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setCalibrationParams(prev => ({
      ...prev,
      [name]: Number(value)
    }));
  };

  const saveCalibrationParams = async () => {
    setIsProcessing(true);
    setUploadStatus('Saving calibration parameters...');
    
    try {
      const response = await fetch('http://localhost:2076/camera_calibration_parameters', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(calibrationParams),
      });

      if (response.ok) {
        setUploadStatus('Calibration parameters saved successfully!');
      } else {
        const errorData = await response.json();
        setUploadStatus(`Failed to save parameters: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      setUploadStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      const filesArray = Array.from(files);
      setSelectedFiles(filesArray);
      setUploadStatus(`Selected ${filesArray.length} calibration images. Ready to process.`);
      setProgress(prev => prev + 25);
    }
  };

 const handleStartCalibration = async () => {
  if (selectedFiles.length === 0) {
    setUploadStatus('Please select calibration images first');
    return;
  }

  setIsProcessing(true);
  setUploadStatus('Processing calibration images...');

  try {
    const formData = new FormData();
    selectedFiles.forEach(file => {
      formData.append('files', file);
    });

    const response = await fetch('http://localhost:2076/upload_calibration_images', {
      method: 'POST',
      body: formData,
    });

    if (response.ok) {
      const contentDisposition = response.headers.get('content-disposition');
      let filename = 'camera_calibration_params.npz';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
        }
      }

      const blob = await response.blob();
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      const message = response.headers.get('message') || 'Calibration completed successfully!';
      const reprojectionError = response.headers.get('reprojection-error') || '';
      const sourceImages = response.headers.get('source-images') || '';

      setUploadStatus(`${message} ${reprojectionError ? `(Error: ${reprojectionError})` : ''}`);
    } else {
      try {
        const errorData = await response.json();
        setUploadStatus(`Calibration failed: ${errorData.detail || 'Unknown error'}`);
      } catch {
        setUploadStatus(`Calibration failed: ${response.statusText}`);
      }
    }
    setProgress(prev => prev + 25);
  } catch (error) {
    setUploadStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  } finally {
    setIsProcessing(false);
  }
};

  const clearSelection = () => {
    setSelectedFiles([]);
    setUploadStatus('');
    setProgress(prev => prev - 25);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="camera-container" style={{ padding: '20px', height: '100vh', display: 'flex' }}>
      <div style={{ flex: 1 }}>
        <div>
          <Typography id="selection" gutterBottom>File Selection</Typography>
          <input
            type="file"
            id="folder-upload"
            ref={fileInputRef}
            webkitdirectory=""
            directory=""
            multiple
            onChange={handleFileSelection}
            style={{ display: 'none' }}
            disabled={isProcessing}
          />
          <label htmlFor="folder-upload">
            <Button 
              variant='contained' 
              style={{ marginBottom: '20px', marginRight: '10px' }}
              component="span"
              disabled={isProcessing}
            >
              Select Calibration Images
            </Button>
          </label>
          {selectedFiles.length > 0 && (
            <Button 
              variant='outlined' 
              style={{ marginBottom: '20px' }}
              onClick={clearSelection}
              disabled={isProcessing}
            >
              Clear Selection
            </Button>
          )}
          <br />
          <Button 
            variant='contained' 
            style={{ marginBottom: '20px' }}
            disabled={isProcessing}
          >
            Select Camera Matrix File
          </Button>
          <br />
          <Button 
            variant='contained' 
            style={{ marginBottom: '20px' }}
            disabled={isProcessing}
          >
            Select New Camera Matrix File
          </Button>
        </div>
        <br />
        <div>
          <Typography id="operations" gutterBottom>Operations</Typography>
          <Button 
            variant='contained' 
            style={{ marginBottom: '20px' }}
            onClick={handleStartCalibration}
            disabled={selectedFiles.length === 0 || isProcessing}
          >
            {isProcessing ? 'Processing...' : 'Start Calibration'}
          </Button>
          <br />
          <Button 
            variant='contained' 
            style={{ marginBottom: '20px' }}
            disabled={true}
          >
            Generate New Camera Matrix
          </Button>
          <br />
          <Button 
            variant='contained' 
            style={{ marginBottom: '20px' }}
            disabled={true} 
          >
            Undistort Calibration Images
          </Button>
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Typography id="status" gutterBottom>Status</Typography>
        <LinearProgress variant="determinate" value={progress} />
        {uploadStatus && (
          <Typography variant="body2" style={{ marginTop: '10px' }}>
            {uploadStatus}
          </Typography>
        )}
        <div>
          <br />
        </div>
        <Paper elevation={3} style={{ padding: '20px', marginBottom: '20px' }}>
          <Typography variant="h6" gutterBottom>Calibration Parameters</Typography>
          {error && <Alert severity="warning" style={{ marginBottom: '20px' }}>{error}</Alert>}
          <Box component="form" noValidate autoComplete="off">
            <TextField
              fullWidth
              margin="normal"
              label="Chessboard Rows"
              name="chess_row"
              type="number"
              value={calibrationParams.chess_row}
              onChange={handleParamChange}
              inputProps={{ min: 2 }}
            />
            <TextField
              fullWidth
              margin="normal"
              label="Chessboard Columns"
              name="chess_col"
              type="number"
              value={calibrationParams.chess_col}
              onChange={handleParamChange}
              inputProps={{ min: 2 }}
            />
            <TextField
              fullWidth
              margin="normal"
              label="Square Size"
              name="square_size"
              type="number"
              value={calibrationParams.square_size}
              onChange={handleParamChange}
              inputProps={{ step: "0.1", min: 0.1 }}
            />
            <TextField
              fullWidth
              margin="normal"
              label="Error Threshold"
              name="error_threshold"
              type="number"
              value={calibrationParams.error_threshold}
              onChange={handleParamChange}
              inputProps={{ step: "0.01", min: 0, max: 1 }}
            />
            <Button 
              variant="contained" 
              color="primary" 
              onClick={saveCalibrationParams}
              style={{ marginTop: '20px' }}
              disabled={isProcessing}
            >
              Save Parameters
            </Button>
          </Box>
        </Paper>
      </div>
      <div style={{
        position: 'absolute',
        left: '20px',
        bottom: '20px'
      }}>
        <Link href="/" passHref>
          <Button variant="contained">
            Back to the Main Page
          </Button>
        </Link>
      </div>
    </div>
  );
};

export default CameraApp;