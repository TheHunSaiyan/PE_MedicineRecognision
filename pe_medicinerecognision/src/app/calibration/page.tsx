"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';

const CameraApp: React.FC = () => {


  return (
    <div className="camera-container" style={{ padding: '20px' }}>
      <h1>Calibration</h1>
       <Link href="/" passHref>
            <Button variant="contained">
              Back to the Main Page
            </Button>
          </Link>
    </div>
  );
};

export default CameraApp;