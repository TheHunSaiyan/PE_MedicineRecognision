"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import { Typography } from '@mui/material';
import LinearProgress, { LinearProgressProps } from '@mui/material/LinearProgress';


const CameraApp: React.FC = () => {

  return (
    <div className="camera-container" style={{ padding: '20px', height: '100vh', display: 'flex' }}>
      <div style={{ flex: 1}}>
      <div>
      <Typography id="selection" gutterBottom>File Selection</Typography>
        <Button variant='contained' style={{ marginBottom: '20px' }}>
            Select Calibration Images
        </Button>
        <br></br>
        <Button variant='contained' style={{ marginBottom: '20px' }}>
            Select Camera Matrix File
        </Button>
        <br></br>
        <Button variant='contained' style={{ marginBottom: '20px' }}>
            Select New Camera Matrix File
        </Button>
      </div>
      <br></br>
      <div>
      <Typography id="selection" gutterBottom>Operations</Typography>
        <Button variant='contained' style={{ marginBottom: '20px' }}>
            Start Calibration
        </Button>
        <br></br>
        <Button variant='contained' style={{ marginBottom: '20px' }}>
            Generate New Camera Matrix
        </Button>
        <br></br>
        <Button variant='contained' style={{ marginBottom: '20px' }}>
            Undistort Calibration Images
        </Button>
      </div>
      </div>
      <div style={{ flex: 1, display: 'flex'}}>
        Status
        <LinearProgress variant="determinate" value={50}/>
      </div>
      <br></br>
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