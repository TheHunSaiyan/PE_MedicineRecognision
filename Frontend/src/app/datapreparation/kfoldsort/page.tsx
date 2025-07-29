"use client";

import React, { useState, useEffect } from 'react';
import {Button, Paper, FormControlLabel, Radio, TextField, FormControl, InputLabel, Select, MenuItem, Checkbox, LinearProgress, Typography} from '@mui/material';
import Link from 'next/link';

const CameraApp: React.FC = () => {
const [foldMode, setfoldMode] = useState('');
const[foldNumber, setfoldNumber] = useState(0);
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

const handleModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      setfoldMode(event.target.value);
    };

const handleNumberChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newNumber = Number(event.target.value);
    setfoldNumber(newNumber);
    if (parseInt(selectedFold.replace('fold', '')) > newNumber) {
      setSelectedFold('fold1');
    }
  };

  const handleFoldChange = (event: any) => {
    setSelectedFold(event.target.value);
  };

  const foldOptions = Array.from({ length: foldNumber }, (_, i) => `fold${i + 1}`);

  const startSorting = async () => {
    if (foldMode === '') {
        setError(`You must choose a fold mode!`);
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
            body: JSON.stringify({ mode: foldMode })
        });

        if (!response.ok) {
            throw new Error('Failed to start stream image creation');
        }
        
    } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
    }
};

    return (
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
                 checked={foldMode === 'exist'}
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
              step: 1
            }}
            sx={{ mt: 2 }}
          />
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Select Fold</InputLabel>
            <Select
              value={selectedFold}
              label="Select Fold"
              onChange={handleFoldChange}
            >
              {foldOptions.map((fold) => (
                <MenuItem key={fold} value={fold}>{fold}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControlLabel
                control={<Checkbox/>}
                label="Erase existing folds"
              />
            <Button 
                variant="contained" 
                color="primary" 
                onClick={startSorting}
                style={{ marginTop: '20px' }}
                disabled={isProcessing && foldMode==''}
              >
                {isProcessing ? 'Processing...' : 'Start'}
              </Button>
              <div>
                <br></br>
              </div>
              <LinearProgress variant="determinate" value={progress} style={{width: '100%'}} />
                  {progress > 0 && progress < 100 && (
                    <Typography variant="body2" style={{ marginTop: '10px' }}>
                      Creating Stream images... {progress}% ({progressInfo.processed}/{progressInfo.total} files)
                    </Typography>
                  )}
                  {progress === 100 && (
                    <Typography variant="body2" style={{ marginTop: '10px' }}>
                      Stream Images created successfully! ({progressInfo.total} files processed)
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
    </div>
  );

};

export default CameraApp;