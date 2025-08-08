"use client";

import React, { useState, useEffect } from 'react';
import { Button, Input, Switch, FormControlLabel, Typography, Paper, CircularProgress, Grid, Container, Slider, Radio} from '@mui/material';
import Link from 'next/link';
import ProtectedRoute from '../../../../components/ProtectedRoute';

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

interface LedParameters {
  upper_led: number;
  side_led: number;
}

const defaultLedParameters: LedParameters = {
  upper_led: 50,
  side_led: 50
};

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
 const [ledParams, setLedParams] = useState<LedParameters>(defaultLedParameters);
const [ledIntensity, setLedIntensity] = useState<number>(defaultLedParameters.upper_led);
const [selectedLamp, setSelectedLamp] = useState<'upper_led' | 'side_led'>('upper_led');
  
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

const debounce = (func: (...args: any[]) => void, delay: number) => {
  let timeoutId: NodeJS.Timeout;
  return (...args: any[]) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};

  const sendUpdate = debounce(async (params: CameraParameters) => {
  try {
    const response = await fetch('http://localhost:2076/calibrate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      throw new Error('Failed to update camera settings');
    }
  } catch (error) {
    console.error('Error updating settings:', error);
  }
}, 300);

const handleInputChange = (name: keyof CameraParameters) => (event: React.ChangeEvent<HTMLInputElement>) => {
  const value = Number(event.target.value);
  if (isNaN(value)) return;
  
  const updatedParams = {
    ...parameters,
    [name]: value
  };
  setParameters(updatedParams);
  sendUpdate(updatedParams);
};

     const handleSliderChange = (name: keyof CameraParameters) => (event: Event, newValue: number | number[]) => {
  const updatedParams = {
    ...parameters,
    [name]: newValue as number
  };
  setParameters(updatedParams);
  sendUpdate(updatedParams);
};

const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  const { name, value, type, checked } = e.target;
  const updatedParams = {
    ...parameters,
    [name]: type === 'checkbox' ? checked : Number(value)
  };
  setParameters(updatedParams);
  sendUpdate(updatedParams);
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

 const handleUpload = async () => {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  
  input.onchange = async (e: Event) => {
    const target = e.target as HTMLInputElement;
    const file = target.files?.[0];
    
    if (!file) return;
    
    try {
      setIsLoading(true);
      const reader = new FileReader();
      
      reader.onload = (event) => {
        try {
          const result = event.target?.result;
          if (typeof result === 'string') {
            const jsonData = JSON.parse(result) as CameraParameters;
            
            if (typeof jsonData.brightness !== 'number' || 
                typeof jsonData.contrast !== 'number' ||
                typeof jsonData.saturation !== 'number' ||
                typeof jsonData.white_balance_automatic !== 'boolean' ||
                typeof jsonData.white_balance_temperature !== 'number' ||
                typeof jsonData.sharpness !== 'number' ||
                typeof jsonData.exposure_time_absolute !== 'number') {
              throw new Error('Invalid JSON format: Missing required camera parameters');
            }
            
            setParameters(jsonData);
            setSubmitMessage('Parameters loaded successfully!');
          }
        } catch (error) {
          console.error('Error parsing JSON:', error);
          setSubmitMessage(error instanceof Error ? error.message : 'Invalid JSON file');
        } finally {
          setIsLoading(false);
          setTimeout(() => setSubmitMessage(''), 3000);
        }
      };
      
      reader.onerror = () => {
        setSubmitMessage('Error reading file');
        setIsLoading(false);
        setTimeout(() => setSubmitMessage(''), 3000);
      };
      
      reader.readAsText(file);
    } catch (error) {
      console.error('Error handling file upload:', error);
      setSubmitMessage(error instanceof Error ? error.message : 'Failed to upload file');
      setIsLoading(false);
      setTimeout(() => setSubmitMessage(''), 3000);
    }
  };
  
  input.click();
};

const handleSave = () => {
  try {
    const jsonString = JSON.stringify(parameters, null, 2);
    
    const blob = new Blob([jsonString], { type: 'application/json' });
    
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `camera_settings_${new Date().toISOString().slice(0, 10)}.json`;
    
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 0);
    
    setSubmitMessage('Parameters saved successfully!');
    setTimeout(() => setSubmitMessage(''), 3000);
  } catch (error) {
    console.error('Error saving parameters:', error);
    setSubmitMessage('Failed to save parameters');
    setTimeout(() => setSubmitMessage(''), 3000);
  }
};

const handleLedIntensityChange = (event: Event, newValue: number | number[]) => {
  const value = newValue as number;
  setLedIntensity(value);
  
  const updatedLedParams = {
    ...ledParams,
    [selectedLamp]: value
  };
  
  setLedParams(updatedLedParams);
  sendLedUpdate(updatedLedParams);
};

const handleLampChange = (event: React.ChangeEvent<HTMLInputElement>) => {
  const lamp = event.target.value as 'upper_led' | 'side_led';
  setSelectedLamp(lamp);
  setLedIntensity(ledParams[lamp]);
};

const sendLedUpdate = debounce(async (params: LedParameters) => {
  try {
    const response = await fetch('http://localhost:2076/led_control', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });
     if (!response.ok) {
      throw new Error('Failed to update LED settings');
    }
  } catch (error) {
    console.error('Error updating LED settings:', error);
  }
}, 2000);

  const handleBlur = (name: keyof CameraParameters, min: number, max: number) => (event: React.FocusEvent<HTMLInputElement>) => {
  const value = Number(event.target.value);
  if (isNaN(value)) {
    event.target.value = parameters[name].toString();
    return;
  }

  const clampedValue = Math.min(max, Math.max(min, value));
  
  const updatedParams = {
    ...parameters,
    [name]: clampedValue
  };
  
  setParameters(updatedParams);
  sendUpdate(updatedParams);
};

  return (
    <ProtectedRoute>
    <div className="camera-container" style={{minHeight: '100vh', display: 'flex',
  flexDirection: 'column'}}>
    <Container maxWidth="xl" sx={{
    padding: '20px 0',
    minHeight: '100%'
  }}>
      <Grid container spacing={3} sx={{ height: 'calc(100vh-64px)' }}>
       <Grid item xs={12} md={6} style={{ display: 'flex', flexDirection: 'column' }}>
    <Paper elevation={3} sx={{ 
      p: 2,
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      minHeight: 0,
      overflow: 'auto'
    }}>
      <Typography variant="h5" gutterBottom>Camera Settings</Typography>
        <div style={{
          gap: '16px',
          marginBottom: '20px'
        }}>
          <div>
            <Typography id="brightness-slider" gutterBottom>Brightness</Typography>
            <div style={{ display: 'flex' }}>
                  <Slider
                    value={parameters.brightness}
                    onChange={handleSliderChange('brightness')}
                    aria-labelledby="brightness-slider"
                    min={-64}
                    max={64}
                    valueLabelDisplay="auto"
                  />
                  <Input
      value={parameters.brightness}
      size="small"
      onChange={handleInputChange('brightness')}
      onBlur={handleBlur('brightness', -64, 64)}
      inputProps={{
        step: 1,
        min: -64,
        max: 64,
        type: 'number',
        'aria-labelledby': 'brightness-slider',
      }}
      sx={{ width: '80px' }}

      style={{ marginLeft: '20px' }}
    />
    </div>
          </div>
          <div>
             <Typography id="contrast-slider" gutterBottom>Contrast</Typography>
             <div style={{ display: 'flex' }}>
                  <Slider
                    value={parameters.contrast}
                    onChange={handleSliderChange('contrast')}
                    aria-labelledby="contrast-slider"
                    min={0}
                    max={64}
                    valueLabelDisplay="auto"
                  /><Input
      value={parameters.contrast}
      size="small"
      onChange={handleInputChange('contrast')}
      onBlur={handleBlur('contrast', 0, 64)}
      inputProps={{
        step: 1,
        min: 0,
        max: 64,
        type: 'number',
        'aria-labelledby': 'contrast-slider',
      }}
      sx={{ width: '80px' }}

      style={{ marginLeft: '20px' }}
    />
                </div>
          </div>
          <div>
            <Typography id="saturation-slider" gutterBottom>Saturation</Typography>
             <div style={{ display: 'flex' }}>
                  <Slider
                    value={parameters.saturation}
                    onChange={handleSliderChange('saturation')}
                    aria-labelledby="saturation-slider"
                    min={0}
                    max={128}
                    valueLabelDisplay="auto"
                  />
                  <Input
      value={parameters.saturation}
      size="small"
      onChange={handleInputChange('saturation')}
      onBlur={handleBlur('saturation', 0, 128)}
      inputProps={{
        step: 1,
        min: 0,
        max: 128,
        type: 'number',
        'aria-labelledby': 'saturation-slider',
      }}
      sx={{ width: '80px' }}

      style={{ marginLeft: '20px' }}
    />
    </div>
          </div>
          <div>
             <Typography id="sharpness-slider" gutterBottom>Sharpness</Typography>
              <div style={{ display: 'flex' }}>
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
                  <Input
      value={parameters.sharpness}
      size="small"
      onChange={handleInputChange('sharpness')}
      onBlur={handleBlur('sharpness', 0, 6)}
      inputProps={{
        step: 1,
        min: 0,
        max: 6,
        type: 'number',
        'aria-labelledby': 'sharpness-slider',
      }}
      sx={{ width: '80px' }}

      style={{ marginLeft: '20px' }}
    />
    </div>
          </div>
        </div>

        <div>
          <Typography variant="subtitle1" gutterBottom>White Balance</Typography>
          <div style={{
            gap: '16px',
            alignItems: 'center',
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
              <div style={{ display: 'flex' }}>
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
                    <Input
      disabled={parameters.white_balance_automatic}
      value={parameters.white_balance_temperature}
      size="small"
      onChange={handleInputChange('white_balance_temperature')}
      onBlur={handleBlur('white_balance_temperature', 2800, 6500)}
      inputProps={{
        step: 100,
        min: 2800,
        max: 6500,
        type: 'number',
        'aria-labelledby': 'white_balance_temperature-slider',
      }}
      sx={{ width: '80px' }}

      style={{ marginLeft: '20px' }}
    />
    </div>
            </div>
          </div>
        </div>

        <div>
          <Typography variant="subtitle1" gutterBottom>Exposure</Typography>
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '16px',
            marginBottom: '16px'
          }}>
            <div style={{ flex: '1 1 300px' }}>
              <Typography id="exposure-time-slider" gutterBottom>Exposure Time Absolute</Typography>
              <div style={{ display: 'flex' }}>
                    <Slider
                      value={parameters.exposure_time_absolute}
                      onChange={handleSliderChange('exposure_time_absolute')}
                      aria-labelledby="exposure-time-slider"
                      min={1}
                      max={5000}
                      step={100}
                      valueLabelDisplay="auto"
                    />
                    <Input
      value={parameters.exposure_time_absolute}
      size="small"
      onChange={handleInputChange('exposure_time_absolute')}
      onBlur={handleBlur('exposure_time_absolute', 1, 5000)}
      inputProps={{
        step: 100,
        min: 1,
        max: 5000,
        type: 'number',
        'aria-labelledby': 'exposure_time_absolute-slider',
      }}
      sx={{ width: '80px' }}

      style={{ marginLeft: '20px' }}
    />
    </div>
            </div>
          </div>
          <Typography variant="h5" gutterBottom>Lamps</Typography>
        <div style={{
          minWidth: '300px',
          padding: '10px',
        }}>
        <div>
           <div>
            <FormControlLabel
              control={
                <Radio
                  checked={selectedLamp === 'upper_led'}
                  onChange={handleLampChange}
                  value="upper_led"
                  name="lamp-selection"
                />
              }
              label="Upper Lamp"
            />
            <FormControlLabel
              control={
                <Radio
                  checked={selectedLamp === 'side_led'}
                  onChange={handleLampChange}
                  value="side_led"
                  name="lamp-selection"
                />
              }
              label="Side Lamp"
            />
          </div>
    </div>

        <Typography id="led-slider" gutterBottom>
          {selectedLamp === 'upper_led' ? 'Upper' : 'Side'} Lamp Intensity
        </Typography>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <Slider
            value={ledIntensity}
            onChange={handleLedIntensityChange}
            aria-labelledby="led-slider"
            min={30}
            max={180}
            step={1}
            valueLabelDisplay="auto"
            sx={{ flex: 1 }}
          />
          <Input
            value={ledIntensity}
            size="small"
            onChange={(e) => {
              const value = Number(e.target.value);
              if (!isNaN(value)) {
                handleLedIntensityChange(e as any, value);
              }
            }}
            onBlur={(e) => {
              const value = Number(e.target.value);
              const clampedValue = Math.min(100, Math.max(0, isNaN(value) ? ledIntensity : value));
              handleLedIntensityChange(e as any, clampedValue);
            }}
            inputProps={{
              step: 1,
              min: 0,
              max: 100,
              type: 'number',
            }}
            sx={{ width: '80px' }}
          />
        </div>
        </div>
        </div>
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column',
          gap: '10px', 
          marginTop: '20px'
        }}>
           <div style={{ display: 'flex', gap: '10px' }}>
          <Button
            variant="contained"
            onClick={handleUpload}
            >
              Upload Parameters
            </Button>

            <Button
            variant="contained"
            onClick={handleSave}
            >
              Save Parameters
            </Button>
             <Button
            variant="outlined"
            onClick={resetToDefaults}
            >
              Reset to Defaults
            </Button>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
          <Link href="/imagecapture" passHref>
            <Button variant="contained">
              Back to Image Capture Page
            </Button>
          </Link>
          </div>
        </div>

        {submitMessage && (
          <Typography color={submitMessage.includes('success') ? 'success' : 'error'} style={{ marginTop: '10px' }}>
            {submitMessage}
          </Typography>
        )}
    </Paper>
    </Grid>
    
    <Grid item xs={12} md={6} style={{ display: 'flex', flexDirection: 'column' }}>
      <Paper elevation={3} sx={{ 
      p: 2,
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      minHeight: 0
    }}>
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
        <br></br>
        </Paper>
        </Grid>
    </Grid>
    </Container>
    </div>
    </ProtectedRoute>
  );
};

export default CameraSettingsForm;