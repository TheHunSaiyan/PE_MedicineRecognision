"use client";

import React, { useState, useEffect } from 'react';
import { Button, TextField, Switch, FormControlLabel, Typography, Paper, CircularProgress, Grid, Container, Slider} from '@mui/material';
import Link from 'next/link';

interface CameraParameters {
  brightness: number;
  contrast: number;
  saturation: number;
  white_balance_automatic: boolean;
  white_balance_temperature: number;
  sharpness: number;
  auto_exposure: number;
  exposure_time_absolute: number;
  exposure_dynamic_framerate: boolean;
}

const defaultParameters: CameraParameters = {
  brightness: 0,
  contrast: 32,
  saturation: 60,
  white_balance_automatic: false,
  white_balance_temperature: 4600,
  sharpness: 2,
  auto_exposure: 1,
  exposure_time_absolute: 157,
  exposure_dynamic_framerate: false,
};

const CameraSettingsForm: React.FC = () => {
  const [parameters, setParameters] = useState<CameraParameters>(defaultParameters);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState('');
  const [isMounted, setIsMounted] = useState(false);
  
    useEffect(() => {
      setIsMounted(true);
      const fetchSettings = async () => {
      try {
        const response = await fetch('http://localhost:2076/camera_settings');
        if (!response.ok) {
          throw new Error('Failed to fetch camera settings');
        }
        const data = await response.json();
        console.log("Received data:", data); 
        setParameters(data);
      } catch (error) {
        console.error('Error fetching settings:', error);
        setSubmitMessage(error instanceof Error ? error.message : 'Failed to load settings');
        setTimeout(() => setSubmitMessage(''), 3000);
      } finally {
        setIsLoading(false);
      }
    };
      fetchSettings();
      return () => setIsMounted(false);
    }, []);

     const handleSliderChange = (name: keyof CameraParameters) => (event: Event, newValue: number | number[]) => {
    setParameters(prev => ({
      ...prev,
      [name]: newValue as number
    }));
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setParameters(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : Number(value)
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!parameters) return;
    setIsSubmitting(true);
    
    try {
      const response = await fetch('http://localhost:2076/calibrate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(parameters),
      });

      if (!response.ok) {
        throw new Error('Failed to update camera settings');
      }

      setSubmitMessage('Camera settings updated successfully!');
    } catch (error) {
      setSubmitMessage(error instanceof Error ? error.message : 'An error occurred');
    } finally {
      setIsSubmitting(false);
      setTimeout(() => setSubmitMessage(''), 3000);
    }
  };

  const resetToDefaults = () => {
    setParameters(defaultParameters);
  };

    if (isLoading) {
    return (
      <Paper elevation={3} style={{ 
        padding: '20px', 
        margin: '20px 0',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '200px'
      }}>
        <CircularProgress />
        <Typography variant="body1" style={{ marginTop: '16px' }}>
          Loading camera settings...
        </Typography>
      </Paper>
    );
  }

if (!parameters) {
    return (
      <Paper elevation={3} style={{ padding: '20px', textAlign: 'center' }}>
        <CircularProgress />
        <Typography>Loading camera settings...</Typography>
      </Paper>
    );
  }

  return (
    <div className="camera-container" style={{ padding: '20px' }}>
    <Container maxWidth="xl" sx={{ 
      py: 4,
      height: '100vh',
      boxSizing: 'border-box'
    }}>
      <Grid container spacing={3} sx={{ height: '100%' }}>
       <Grid item xs={12} md={6}>
    <Paper elevation={3} style={{ padding: '20px', margin: '20px 0' }}>
      <Typography variant="h5" gutterBottom>Camera Settings</Typography>
      
      <form onSubmit={handleSubmit}>
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '20px'
        }}>
          <div style={{ flex: '1 1 300px' }}>
            <Typography id="brightness-slider" gutterBottom>Brightness</Typography>
                  <Slider
                    value={parameters.brightness}
                    onChange={handleSliderChange('brightness')}
                    aria-labelledby="brightness-slider"
                    min={-64}
                    max={64}
                    valueLabelDisplay="auto"
                  />
          </div>
          <div style={{ flex: '1 1 300px' }}>
             <Typography id="contrast-slider" gutterBottom>Contrast</Typography>
                  <Slider
                    value={parameters.contrast}
                    onChange={handleSliderChange('contrast')}
                    aria-labelledby="contrast-slider"
                    min={0}
                    max={64}
                    valueLabelDisplay="auto"
                  />
          </div>
          <div style={{ flex: '1 1 300px' }}>
            <Typography id="saturation-slider" gutterBottom>Saturation</Typography>
                  <Slider
                    value={parameters.saturation}
                    onChange={handleSliderChange('saturation')}
                    aria-labelledby="saturation-slider"
                    min={0}
                    max={128}
                    valueLabelDisplay="auto"
                  />
          </div>
          <div style={{ flex: '1 1 300px' }}>
             <Typography id="sharpness-slider" gutterBottom>Sharpness</Typography>
                  <Slider
                    value={parameters.sharpness}
                    onChange={handleSliderChange('sharpness')}
                    aria-labelledby="sharpness-slider"
                    min={0}
                    max={6}
                    step={1}
                    marks
                    valueLabelDisplay="auto"
                  />
          </div>
        </div>

        <div style={{ margin: '20px 0' }}>
          <Typography variant="subtitle1" gutterBottom>White Balance</Typography>
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '16px',
            alignItems: 'center',
            marginBottom: '16px'
          }}>
            <FormControlLabel
              control={
                <Switch
                  name="white_balance_automatic"
                  checked={parameters.white_balance_automatic}
                  onChange={handleChange}
                />
              }
              label="Automatic White Balance"
            />
            <div style={{ flex: '1 1 300px' }}>
              <Typography id="white-balance-slider" gutterBottom>White Balance Temperature</Typography>
                    <Slider
                      value={parameters.white_balance_temperature}
                      onChange={handleSliderChange('white_balance_temperature')}
                      aria-labelledby="white-balance-slider"
                      min={2800}
                      max={6500}
                      step={100}
                      valueLabelDisplay="auto"
                      disabled={parameters.white_balance_automatic}
                    />
            </div>
          </div>
        </div>

        <div style={{ margin: '20px 0' }}>
          <Typography variant="subtitle1" gutterBottom>Exposure</Typography>
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '16px',
            marginBottom: '16px'
          }}>
            <div style={{ flex: '1 1 300px' }}>
              <Typography id="exposure-time-slider" gutterBottom>Exposure Time Absolute</Typography>
                    <Slider
                      value={parameters.exposure_time_absolute}
                      onChange={handleSliderChange('exposure_time_absolute')}
                      aria-labelledby="exposure-time-slider"
                      min={1}
                      max={5000}
                      step={100}
                      valueLabelDisplay="auto"
                    />
            </div>
          </div>
        </div>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          gap: '10px', 
          marginTop: '20px'
        }}>
          <div style={{ display: 'flex', gap: '10px' }}>
            <Button
              type="submit"
              variant="contained"
              color="primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Applying...' : 'Apply Settings'}
            </Button>
            <Button
            variant="outlined"
            onClick={resetToDefaults}
            >
              Reset to Defaults
            </Button>
          </div>
  
          <Link href="/" passHref>
            <Button variant="contained">
              Back to the Main Page
            </Button>
          </Link>
        </div>

        {submitMessage && (
          <Typography color={submitMessage.includes('success') ? 'success' : 'error'} style={{ marginTop: '10px' }}>
            {submitMessage}
          </Typography>
        )}
      </form>
    </Paper>
    </Grid>
    
    <Grid item xs={12} md={6}>
      <Paper elevation={3} style={{ padding: '20px', margin: '20px 0' }}>
      <Typography variant="h5" gutterBottom>Live Feed</Typography>
        <div style={{ 
          flex: 1,
          minWidth: '300px',
          border: '1px solid #ddd',
          padding: '10px',
          borderRadius: '8px'
        }}>
          {isMounted && (
            <img
              src="http://localhost:2076/video_feed"
              alt="Live Camera Feed"
              style={{ width: '100%', maxWidth: '640px', border: '1px solid #ccc' }}
            />
          )}
        </div>

        </Paper>
        </Grid>
    </Grid>
    </Container>
    </div>
  );
};

export default CameraSettingsForm;