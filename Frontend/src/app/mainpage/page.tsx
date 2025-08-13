"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { useAuth } from '../../../contexts/AuthContext';
import { ROLES } from '../../../constans/roles';

const CameraApp: React.FC = () => {
  const { logout, userRole } = useAuth();

  const menuItems = [
    {
      path: "/imagecapture",
      label: "Image Capture",
      allowedRoles: [ROLES.ADMIN, ROLES.TECHNICIAN]
    },
    {
      path: "/datapreparation",
      label: "Data Preparation",
      allowedRoles: [ROLES.ADMIN, ROLES.TECHNICIAN]
    },
    {
      path: "/dispenseverification",
      label: "Dispense Verification",
      allowedRoles: [ROLES.ADMIN, ROLES.NURSE, ROLES.DOCTOR, ROLES.TECHNICIAN]
    },
    {
      path: "/usermanagment",
      label: "User Management",
      allowedRoles: [ROLES.ADMIN]
    }
  ];

  const filteredMenuItems = menuItems.filter(item => 
    userRole && item.allowedRoles.includes(userRole)
  );

  return (
    <ProtectedRoute allowedRoles={[ROLES.ADMIN, ROLES.NURSE, ROLES.DOCTOR, ROLES.TECHNICIAN]}>
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
          <h1 style={{ fontSize:'40px' }}>Medicine Recognition</h1>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          {filteredMenuItems.map((item, index) => (
            <React.Fragment key={item.path}>
              <br />
              <Link href={item.path} passHref>
                <Button 
                  variant="contained" 
                  style={{ marginLeft: '10px', marginBottom:'20px' }}  
                  sx={{
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
                  }}
                >
                  {item.label}
                </Button>
              </Link>
            </React.Fragment>
          ))}
        </div>
      </div>
    </ProtectedRoute>
  );
};

export default CameraApp;