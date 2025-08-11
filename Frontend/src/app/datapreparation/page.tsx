"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import ProtectedRoute from '../../../components/ProtectedRoute';

const CameraApp: React.FC = () => {


  return (
    <ProtectedRoute>
    <div className="camera-container" style={{
        position: 'absolute', left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)'
    }}>
    <div style={{ textAlign: 'center', marginBottom: '20px'}}>
      <h1 style={{ fontSize:'40px' }}>Medicine Recognision</h1>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <br></br>
      <Link href="/datapreparation/remapannotation" passHref>
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
          Remap Annotation IDs
        </Button>
      </Link>
      <Link href="/datapreparation/splitdataset" passHref>
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
          Split Dataset
        </Button>
      </Link>
      <br></br>
      <Link href="/datapreparation/augmentimages" passHref>
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
          Augment Images
        </Button>
      </Link>
      <br></br>
      <Link href="/datapreparation/createstreamimages" passHref>
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
          Create Stream Images
        </Button>
      </Link>
      <Link href="/datapreparation/kfoldsort" passHref>
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
          K-fold Sort
        </Button>
      </Link>
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