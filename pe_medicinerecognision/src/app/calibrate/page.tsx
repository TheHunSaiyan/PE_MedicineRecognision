"use client";

import React, { useState, useEffect } from 'react';
import { Button, TextField, Switch, FormControlLabel, Typography, Paper, CircularProgress, Grid, Container} from '@mui/material';
import Link from 'next/link';

interface CameraParameters {
  brightness: number;
  contrast: number;
  saturation: number;
  hue: number;
  white_balance_automatic: boolean;
  gamma: number;
  gain: number;
  power_line_frequency: number;
  white_balance_temperature: number;
  sharpness: number;
  backlight_compensation: number;
  auto_exposure: number;
  exposure_time_absolute: number;
  exposure_dynamic_framerate: boolean;
}

const defaultParameters: CameraParameters = {
  brightness: 0,
  contrast: 32,
  saturation: 60,
  hue: 0,
  white_balance_automatic: false,
  gamma: 100,
  gain: 0,
  power_line_frequency: 1,
  white_balance_temperature: 4600,
  sharpness: 2,
  backlight_compensation: 1,
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
            <TextField
              fullWidth
              label="Brightness"
              name="brightness"
              type="number"
              value={parameters.brightness}
              onChange={handleChange}
              inputProps={{ min: -64, max: 64 }}
            />
          </div>
          <div style={{ flex: '1 1 300px' }}>
            <TextField
              fullWidth
              label="Contrast"
              name="contrast"
              type="number"
              value={parameters.contrast}
              onChange={handleChange}
              inputProps={{ min: 0, max: 64 }}
            />
          </div>
          <div style={{ flex: '1 1 300px' }}>
            <TextField
              fullWidth
              label="Saturation"
              name="saturation"
              type="number"
              value={parameters.saturation}
              onChange={handleChange}
              inputProps={{ min: 0, max: 128 }}
            />
          </div>
          <div style={{ flex: '1 1 300px' }}>
            <TextField
              fullWidth
              label="Hue"
              name="hue"
              type="number"
              value={parameters.hue}
              onChange={handleChange}
              inputProps={{ min: -40, max: 40 }}
            />
          </div>
          <div style={{ flex: '1 1 300px' }}>
            <TextField
              fullWidth
              label="Gamma"
              name="gamma"
              type="number"
              value={parameters.gamma}
              onChange={handleChange}
              inputProps={{ min: 72, max: 500 }}
            />
          </div>
          <div style={{ flex: '1 1 300px' }}>
            <TextField
              fullWidth
              label="Sharpness"
              name="sharpness"
              type="number"
              value={parameters.sharpness}
              onChange={handleChange}
              inputProps={{ min: 0, max: 6 }}
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
              <TextField
                fullWidth
                label="White Balance Temperature"
                name="white_balance_temperature"
                type="number"
                value={parameters.white_balance_temperature}
                onChange={handleChange}
                disabled={parameters.white_balance_automatic}
                inputProps={{ min: 2800, max: 6500 }}
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
              <TextField
                fullWidth
                label="Auto Exposure"
                name="auto_exposure"
                type="number"
                value={parameters.auto_exposure}
                onChange={handleChange}
                inputProps={{ min: 0, max: 3 }}
              />
            </div>
            <div style={{ flex: '1 1 300px' }}>
              <TextField
                fullWidth
                label="Exposure Time Absolute"
                name="exposure_time_absolute"
                type="number"
                value={parameters.exposure_time_absolute}
                onChange={handleChange}
                inputProps={{ min: 1, max: 5000 }}
              />
            </div>
            <div style={{ flex: '1 1 300px', display: 'flex', alignItems: 'center' }}>
              <FormControlLabel
                control={
                  <Switch
                    name="exposure_dynamic_framerate"
                    checked={parameters.exposure_dynamic_framerate}
                    onChange={handleChange}
                  />
                }
                label="Dynamic Framerate"
              />
            </div>
          </div>
        </div>

        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '20px'
        }}>
          <div style={{ flex: '1 1 300px' }}>
            <TextField
              fullWidth
              label="Gain"
              name="gain"
              type="number"
              value={parameters.gain}
              onChange={handleChange}
              inputProps={{ min: 0, max: 100 }}
            />
          </div>
          <div style={{ flex: '1 1 300px' }}>
            <TextField
              fullWidth
              label="Backlight Compensation"
              name="backlight_compensation"
              type="number"
              value={parameters.backlight_compensation}
              onChange={handleChange}
              inputProps={{ min: 0, max: 2 }}
            />
          </div>
          <div style={{ flex: '1 1 300px' }}>
            <TextField
              fullWidth
              label="Power Line Frequency"
              name="power_line_frequency"
              type="number"
              value={parameters.power_line_frequency}
              onChange={handleChange}
              inputProps={{ min: 0, max: 2 }}
            />
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
  );
};

export default CameraSettingsForm;