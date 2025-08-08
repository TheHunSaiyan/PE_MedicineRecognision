"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { useAuth } from '../../../contexts/AuthContext';

const CameraApp: React.FC = () => {
  const { logout } = useAuth();


  return (
    <ProtectedRoute>
    <div className="camera-container" style={{
        position: 'absolute', left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)'
    }}>
      <Button 
        color="error"
        variant="contained"
        onClick={logout}
        sx={{ ml: 2 }}
        style={{ position: 'absolute', top: '20px', right: '20px' }}
      >
        Logout
      </Button>
    <div style={{ textAlign: 'center', marginBottom: '20px'}}>
      <h1 style={{ fontSize:'40px' }}>Medicine Recognision</h1>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <br></br>
      <Link href="/imagecapture" passHref>
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
          Image Capture
        </Button>
      </Link>
      <br></br>
      <Link href="/datapreparation" passHref>
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
          Data Preparation
        </Button>
      </Link>
      <br></br>
      <Link href="/dispenseverification" passHref>
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
          Dispense Verification
        </Button>
      </Link>
      </div>
    </div>
    </ProtectedRoute>
  );
};

export default CameraApp;