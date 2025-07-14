"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';

const CameraApp: React.FC = () => {


  return (
    <div className="camera-container" style={{
        position: 'absolute', left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)'
    }}>
    <div style={{ textAlign: 'center', marginBottom: '20px'}}>
      <h1 style={{ fontSize:'40px' }}>Medicine Recognision</h1>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <br></br>
      <Link href="/camerasettings" passHref>
        <Button variant="contained" style={{ marginLeft: '10px', marginBottom:'20px' }}  sx={{
    width: {
      xs: '100%',
      sm: 'auto',
    },
    minWidth: 400,
    height: 80,
    padding: '0 32px',
    fontSize: '20px',
    borderRadius: '8px',
    boxShadow: 3
  }}>
          Camera Settings
        </Button>
      </Link>
      <br></br>
      <Link href="/calibrationsettings" passHref>
        <Button variant="contained" style={{ marginLeft: '10px' , marginBottom:'20px' }} sx={{
    width: {
      xs: '100%',
      sm: 'auto',
    },
    minWidth: 400,
    height: 80,
    padding: '0 32px',
    fontSize: '20px',
    borderRadius: '8px',
    boxShadow: 3
  }}>
          Calibration Settings
        </Button>
      </Link>
      <br></br>
      <Link href="/calibration" passHref>
        <Button variant="contained" style={{ marginLeft: '10px' , marginBottom:'20px' }} sx={{
    width: {
      xs: '100%',
      sm: 'auto',
    },
    minWidth: 400,
    height: 80,
    padding: '0 32px',
    fontSize: '20px',
    borderRadius: '8px',
    boxShadow: 3
  }}>
          Calibration
        </Button>
      </Link>
      <br></br>
      <Link href="/capture" passHref>
        <Button variant="contained" style={{ marginLeft: '10px' , marginBottom:'20px' }} sx={{
    width: {
      xs: '100%',
      sm: 'auto',
    },
    minWidth: 400,
    height: 80,
    padding: '0 32px',
    fontSize: '20px',
    borderRadius: '8px',
    boxShadow: 3
  }}>
          Capture Pill Images
        </Button>
      </Link>
      </div>
    </div>
  );
};

export default CameraApp;