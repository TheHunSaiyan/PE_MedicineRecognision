"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Typography, Paper, Box, TextField, Alert, FormControlLabel, Checkbox, Snackbar } from '@mui/material';
import Button from '@mui/material/Button';
import Link from 'next/link';
import LinearProgress from '@mui/material/LinearProgress';
import ProtectedRoute from '../../../../components/ProtectedRoute';
import { ROLES } from '../../../../constans/roles';

const CameraApp: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [progressInfo, setProgressInfo] = useState({
    progress: 0,
    processed: 0,
    total: 0
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [filesSelected, setFilesSelected] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFolderSelection = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) {
      setFilesSelected(false);
      return;
    }
    const txtFiles = Array.from(files).filter(file => 
      file.name.toLowerCase().endsWith('.txt')
    );

    if (txtFiles.length > 0) {
      setSelectedFiles(txtFiles);
      setFilesSelected(true);
    } else {
      setFilesSelected(false);
      alert('No .txt files found in the selected folder');
    }
  };

  const startRemap = async () => {
    if (!filesSelected || isProcessing) return;
    
    setIsProcessing(true);
    setProgress(0);
    
    try {
      const formData = new FormData();
      selectedFiles.forEach(file => {
        formData.append('files', file);
      });

      const response = await fetch('http://localhost:2076/start_remap_annotation', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to start remap process');
      }

      const intervalId = setInterval(async () => {
        try {
          const progressResponse = await fetch('http://localhost:2076/get_remap_annotation_progress');
          if (!progressResponse.ok) {
            throw new Error('Failed to get progress');
          }
          const progressData = await progressResponse.json();
          
          setProgressInfo({
            progress: progressData.progress,
            processed: progressData.processed,
            total: progressData.total
          });
          
          setProgress(progressData.progress);
          
          if (progressData.progress >= 100) {
            clearInterval(intervalId);
            setIsProcessing(false);
          }
        } catch (error) {
          console.error('Error fetching progress:', error);
          clearInterval(intervalId);
          setIsProcessing(false);
        }
      }, 500);

    } catch (error) {
      console.error('Error starting remap:', error);
      setIsProcessing(false);
    }
  };

  const handleFolderButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.setAttribute('webkitdirectory', '');
      fileInputRef.current.setAttribute('directory', '');
      fileInputRef.current.setAttribute('multiple', '');
      fileInputRef.current.click();
    }
  };

  return (
    <ProtectedRoute allowedRoles={[ROLES.ADMIN, ROLES.TECHNICIAN]}>
    <div className="camera-container" style={{ padding: '20px', height: '100vh', display: 'flex' }}>
      <div style={{ 
        textAlign: 'center', 
        marginBottom: '20px',
        width: '33.33%',
        minWidth: '300px',
        margin: '0 auto'}}>
        <br></br>
        <h1 style={{ fontSize:'40px' }}>Remap Annotation IDs</h1>
        <br></br>
        <input
          id="folder-upload"
          type="file"
          ref={fileInputRef}
          accept=".txt"
          onChange={handleFolderSelection}
          style={{ display: 'none' }}
          disabled={isProcessing}
        />
        <label htmlFor="folder-upload">
          <Button 
            variant='contained' 
            style={{ marginBottom: '20px', marginRight: '10px' }}
            onClick={handleFolderButtonClick}
            disabled={isProcessing}
          >
            Select Annotation Files
          </Button>
        </label>
        <br></br>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={startRemap}
          style={{ marginTop: '20px', marginBottom: '20px' }}
          disabled={!filesSelected || isProcessing}
        >
          {isProcessing ? 'Processing...' : 'Start'}
        </Button>
        <br></br>
        <LinearProgress variant="determinate" value={progress} style={{width: '100%'}} />
        {progress > 0 && progress < 100 && (
          <Typography variant="body2" style={{ marginTop: '10px' }}>
            Remapping annotations... {progress}% ({progressInfo.processed}/{progressInfo.total} files)
          </Typography>
        )}
        {progress === 100 && (
          <Typography variant="body2" style={{ marginTop: '10px' }}>
            Annotation remapping completed successfully! ({progressInfo.total} files processed)
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
    </ProtectedRoute>
  );
};

export default CameraApp;