"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { ROLES } from '../../../constans/roles';

const CameraApp: React.FC = () => {


  return (
    <ProtectedRoute allowedRoles={[ROLES.ADMIN, ROLES.TECHNICIAN]}>
    <div className="camera-container" style={{
        position: 'absolute', left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)'
    }}>
    <div style={{ textAlign: 'center', marginBottom: '20px'}}>
      <h1 style={{ fontSize:'40px' }}>Medicine Recognision</h1>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <br></br>
      <Link href="/imagecapture/camerasettings" passHref>
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
      <Link href="/imagecapture/capturecalibration" passHref>
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
          Capture Calibration Images
        </Button>
      </Link>
      <br></br>
      <Link href="/imagecapture/calibrationsettings" passHref>
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
          Camera Calibration
        </Button>
      </Link>
      <br></br>
      <Link href="/imagecapture/capture" passHref>
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
      <br></br>
      <Link href="/mainpage" passHref>
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
          Main Page
        </Button>
      </Link>
      </div>
    </div>
    </ProtectedRoute>
  );
};

export default CameraApp;