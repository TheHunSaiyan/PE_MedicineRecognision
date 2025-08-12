"use client";

import React, { useState, useRef, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import { Typography, Paper, Box, TextField, Alert, FormControlLabel, Checkbox } from '@mui/material';
import LinearProgress from '@mui/material/LinearProgress';
import ProtectedRoute from '../../../../components/ProtectedRoute';
import CloseIcon from '@mui/icons-material/Close';
import { ROLES } from '../../../../constans/roles';

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
  const [calibrationSuccess, setCalibrationSuccess] = useState<boolean>(false);
  const [newMatrixSuccess, setNewMatrixSuccess] = useState<boolean>(false);
  const [undistortSuccess, setUndistortSuccess] = useState<boolean>(false);
  const[enableStartCalibration, setEnableStartCalibration] = useState<boolean>(false);
  const [enableNewMatrix, setEnableNewMatrix] = useState<boolean>(false);
  const [enableUndistort, setEnableUndistort] = useState<boolean>(false);
  const [hasError, setHasError] = useState<boolean>(false);

const resetProgress = () => {
  setProgress(0);
  setCalibrationSuccess(false);
  setNewMatrixSuccess(false);
  setUndistortSuccess(false);
  setUploadStatus('');
  setSelectedFiles([]);
  if (fileInputRef.current) {
    fileInputRef.current.value = '';
  }
  setEnableNewMatrix(false);
  setEnableStartCalibration(false);
  setEnableUndistort(false);
  setHasError(false);
};

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
          setError(`Failed to load parameters: ${errorData.detail || 'Unknown error'}. Please press the reset button.`);
          setHasError(true);
        }
      } catch (err) {
        setError(`Error loading parameters: ${err instanceof Error ? err.message : 'Unknown error'}. Please press the reset button.`);
        setHasError(true);
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
      setEnableStartCalibration(true);
    }
    else {
      resetProgress();
      setUploadStatus('No files selected.');
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

      setCalibrationSuccess(true);
      const message = response.headers.get('message') || 'Calibration completed successfully!';
      const reprojectionError = response.headers.get('reprojection-error') || '';
      const sourceImages = response.headers.get('source-images') || '';

      setUploadStatus(`${message} ${reprojectionError ? `(Error: ${reprojectionError})` : ''}`);
      setProgress(prev => prev + 25);
      setEnableNewMatrix(true);
    } else {
        setHasError(true);
        try {
          const errorData = await response.json();
          setUploadStatus(`Calibration failed: ${errorData.detail || 'Unknown error'}. Please press the reset button.`);
        } catch {
          setCalibrationSuccess(false);
          setUploadStatus(`Calibration failed: ${response.statusText}. Please press the reset button.`);
        }
      }
    } catch (error) {
      setHasError(true);
      setUploadStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}. Please press the reset button.`);
    } finally {
      setIsProcessing(false);
    }
  };

  const clearSelection = () => {
    setSelectedFiles([]);
    setUploadStatus('');
    resetProgress();
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleGenerateNewMatrix = async () => {
  setIsProcessing(true);
  setUploadStatus('Generating new camera matrix...');

  try {
    const response = await fetch('http://localhost:2076/generate_new_matrix_file', {
      method: 'POST',
    });

    if (response.ok) {
      const contentDisposition = response.headers.get('content-disposition');
      let filename = 'undistorted_camera_matrix.npz';
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

      const message = response.headers.get('message') || 'New camera matrix generated successfully!';
      const reprojectionError = response.headers.get('reprojection_error') || '';
      const sourceImages = response.headers.get('source_images') || '';

      setUploadStatus(`${message} ${reprojectionError ? `(Reprojection error: ${reprojectionError})` : ''}`);
      setNewMatrixSuccess(true);
      setProgress(prev => prev + 25);
      setEnableUndistort(true);
    } else {
        setHasError(true);
        try {
          const errorData = await response.json();
          setUploadStatus(`Failed to undistort images: ${errorData.detail || 'Unknown error'}. Please press the reset button.`);
        } catch {
          setUploadStatus(`Failed to undistort images: ${response.statusText}. Please press the reset button.`);
        }
      }
    } catch (error) {
      setHasError(true);
      setUploadStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}. Please press the reset button.`);
    } finally {
      setIsProcessing(false);
    }
  };

const handleUndistortImages = async () => {
  setIsProcessing(true);
  setUploadStatus('Undistorting calibration images...');

  try {
    const response = await fetch('http://localhost:2076/undistort_image', {
      method: 'POST',
    });

    if (response.ok) {

      const message = response.headers.get('message') || 'Images undistorted successfully!';
      const undistortedImagesDir = response.headers.get('undistorted_images_dir') || '';

      setUploadStatus(`${message} ${undistortedImagesDir ? `(Saved to: ${undistortedImagesDir})` : ''}`);
      setUndistortSuccess(true);
      setProgress(prev => prev + 25);
    } else {
      resetProgress();
      try {
        const errorData = await response.json();
        setUploadStatus(`Failed to undistort images: ${errorData.detail || 'Unknown error'}`);
      } catch {
        setUploadStatus(`Failed to undistort images: ${response.statusText}`);
      }
    }
  } catch (error) {
    setUploadStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  } finally {
    setIsProcessing(false);
  }
};

const handleUploadMatrixFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
  const files = event.target.files;
  if (!files || files.length === 0) return;

  setIsProcessing(true);
  setUploadStatus('Uploading camera matrix file...');

  try {
    const formData = new FormData();
    formData.append('file', files[0]);

    const response = await fetch('http://localhost:2076/upload_camera_calibration_npz', {
      method: 'POST',
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      setUploadStatus(`Camera matrix file uploaded successfully: ${data.filename}`);
      setProgress(prev => prev + 50);
      setNewMatrixSuccess(true);
      setEnableNewMatrix(true);
    } else {
      resetProgress();
      const errorData = await response.json();
      setUploadStatus(`Upload failed: ${errorData.detail || 'Unknown error'}`);
    }
  } catch (error) {
    setUploadStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  } finally {
    setIsProcessing(false);
    event.target.value = '';
  }
};

const handleUploadUndistortedMatrix = async (event: React.ChangeEvent<HTMLInputElement>) => {
  const files = event.target.files;
  if (!files || files.length === 0) return;

  setIsProcessing(true);
  setUploadStatus('Uploading undistorted matrix file...');

  try {
    const formData = new FormData();
    formData.append('file', files[0]);

    const response = await fetch('http://localhost:2076/upload_undistorted_npz', {
      method: 'POST',
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      setUploadStatus(`Undistorted matrix file uploaded successfully: ${data.filename}`);
      setProgress(prev => prev + 75);
      setNewMatrixSuccess(true);
      setEnableUndistort(true);
    } else {
      resetProgress();
      const errorData = await response.json();
      setUploadStatus(`Upload failed: ${errorData.detail || 'Unknown error'}`);
    }
  } catch (error) {
    setUploadStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  } finally {
    setIsProcessing(false);
    event.target.value = '';
  }
};

  return (
    <ProtectedRoute allowedRoles={[ROLES.ADMIN, ROLES.TECHNICIAN]}>
    <div className="camera-container" style={{ padding: '20px', height: '100vh', display: 'flex' }}>
      <div style={{ flex: '1 1 33%' }}>
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
          <input
    type="file"
    id="matrix-upload"
    accept=".npz"
    onChange={handleUploadMatrixFile}
    style={{ display: 'none' }}
    disabled={isProcessing}
  />
  <label htmlFor="matrix-upload">
    <Button 
      variant='contained' 
      style={{ marginBottom: '20px' }}
      component="span"
      disabled={isProcessing}
    >
      Select Camera Matrix File
    </Button>
  </label>
          <br />
          <input
  type="file"
  id="undistorted-matrix-upload"
  accept=".npz"
  onChange={handleUploadUndistortedMatrix}
  style={{ display: 'none' }}
  disabled={isProcessing}
/>
<label htmlFor="undistorted-matrix-upload">
  <Button 
    variant='contained' 
    style={{ marginBottom: '20px' }}
    component="span"
    disabled={isProcessing}
  >
    Select New Camera Matrix File
  </Button>
</label>
        </div>
        <br />
        <div>
          <Typography id="operations" gutterBottom>Operations</Typography>
          <Button 
            variant='contained' 
            style={{ marginBottom: '20px' }}
            onClick={handleStartCalibration}
            disabled={!enableStartCalibration || isProcessing}
          >
            {isProcessing ? 'Processing...' : 'Start Calibration'}
          </Button>
          <br />
          <Button 
            variant='contained' 
            style={{ marginBottom: '20px' }}
            disabled={isProcessing || !enableNewMatrix}
            onClick={handleGenerateNewMatrix}
          >
            {isProcessing ? 'Generating...' : 'Generate New Camera Matrix'}
          </Button>
          <br />
          <Button 
            variant='contained' 
            style={{ marginBottom: '20px' }}
            onClick={handleUndistortImages}
            disabled={isProcessing || !enableUndistort}
          >
            {isProcessing ? 'Undistorting...' : 'Undistort Calibration Images'}
          </Button>
        </div>
      </div>
      <div style={{ flex: '1 1 66%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <Typography id="status" gutterBottom>Status</Typography>
          <LinearProgress variant="determinate" value={progress} style={{width: '100%'}} />
          {uploadStatus && (
            <Typography variant="body2" style={{ marginTop: '10px' }}>
              {uploadStatus}
            </Typography>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', width: '100%' }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={progress >= 25 && !hasError}
                  icon={hasError && progress >= 25 ? <CloseIcon color="error" /> : undefined}
                  disabled
                />
              }
              label="Images Selected"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={progress >= 50 && !hasError}
                  icon={hasError && progress >= 50 ? <CloseIcon color="error" /> : undefined}
                  disabled
                />
              }
              label="Calibration Done"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={progress >= 75 && !hasError}
                  icon={hasError && progress >= 75 ? <CloseIcon color="error" /> : undefined}
                  disabled
                />
              }
              label="Matrix Generated"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={progress >= 100 && !hasError}
                  icon={hasError && progress >= 100 ? <CloseIcon color="error" /> : undefined}
                  disabled
                />
              }
              label="Images Undistorted"
            />
          </div>
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
        <Link href="/imagecapture" passHref>
          <Button variant="contained">
            Back to Image Capture Page
          </Button>
        </Link>
        <Button 
          variant="outlined" 
          style={{ marginLeft: '10px' }}
          onClick={resetProgress}
          disabled={isProcessing}
        >
          Reset Progress
        </Button>
      </div>
    </div>
    </ProtectedRoute>
  );
};

export default CameraApp;