"use client";

import React, { useState, useEffect } from 'react';
import { Typography, Paper, Box, TextField, Alert, FormControlLabel, Checkbox, Radio, LinearProgress } from '@mui/material';
import Button from '@mui/material/Button';
import Link from 'next/link';

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
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [selectedMode, setSelectedMode] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressInfo, setProgressInfo] = useState({
      progress: 0,
      processed: 0,
      total: 0
    });

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
          setError(err instanceof Error ? err.message : 'An unknown error occurred');
        } finally {
          setLoading(false);
        }
      };
  
      fetchDataAvailability();
    }, []);

    const handleModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
          const lamp = event.target.value as 'Consumer' | 'Reference';
          setSelectedMode(lamp);
        };

    const startSplit = async () => {
    if (selectedMode === '') {
      setError(`You must choose a mode!`);
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:2076/start_stream_images', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(selectedMode)
      });

      if (!response.ok) {
        throw new Error('Failed to start dataset split');
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsProcessing(false);
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
                  control={<Checkbox checked={availability.mask_images} disabled />}
                  label="Masks"
                /><br></br>
                <FormControlLabel
                  control={<Checkbox checked={availability.split} disabled />}
                  label="Split Consumer/Reference"
                />
                <br></br>
                <FormControlLabel
                  control={<Checkbox checked={availability.background_changed} disabled />}
                  label="Background Changed"
                />
              </>
            )}
          </div>
          <div style={{ flex: '1 1 66%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <h1 style={{ fontSize: '40px', fontWeight: 'bold' }}>Create Stream Images</h1>

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
              <br></br>
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