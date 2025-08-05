"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import { Box, Checkbox, FormControlLabel, Typography } from '@mui/material';

const CameraApp: React.FC = () => {


  return (
    <div className="camera-container" style={{
        position: 'absolute', left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)'
    }}>
    <div style={{ textAlign: 'center', marginBottom: '20px'}}>
      <h1 style={{ fontSize:'40px' }}>Pill Dispense Verification</h1>
      </div>
      <div style={{ flex: '1 1 33%' }}>
         <Button variant="contained" style={{marginBottom: '20px'}}>
            Check Enviroment
          </Button>
          <FormControlLabel
                            style={{marginLeft: '30px'}}
                            control={<Checkbox checked={false} disabled />}
                            sx={{
                              '& .MuiSvgIcon-root': {
                                color: false ? '#04e762' : '#ef233c' ,
                                fontSize: 28,
                              },
                            }}
                            label={
                              <span style={{
                                color: false ? '#04e762' : '#ef233c',
                                fontWeight: 'bold'
                              }}>
                                Status
                              </span>
                            }
                          />
          <br></br>
           <Button variant="contained">
            Select Recipe
          </Button>
          <FormControlLabel
                            style={{marginLeft: '30px'}}
                            control={<Checkbox checked={false} disabled />}
                            sx={{
                              '& .MuiSvgIcon-root': {
                                color: false ? '#04e762' : '#ef233c' ,
                                fontSize: 28,
                              },
                            }}
                            label={
                              <span style={{
                                color: false ? '#04e762' : '#ef233c',
                                fontWeight: 'bold'
                              }}>
                                Recipe
                              </span>
                            }
                          />
      </div>
      <div style={{ display: 'flex', justifyContent: 'center'}}>
        <Box sx={{ margin: '20px', maxWidth: '800px' }}>
  <Typography  
    variant='h6'
    gutterBottom
  >
    Morning
  </Typography>
      <div style={{display: 'flex', justifyContent: 'center'}}>
        <Typography  
    gutterBottom
  >
    Recipe
  </Typography>
      <TableContainer component={Paper} style={{minHeight: '250px', maxWidth: '300px', margin: '20px'}}>
      <Table sx={{ minWidth: 650 }} aria-label="simple table">
        <TableHead>
          <TableRow>
            <TableCell>Pill Name</TableCell>
            <TableCell align="right">Count</TableCell>
            <TableCell align="right">Reference Image</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
            <TableRow
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    <Typography  
    gutterBottom
  >
    Prediction
  </Typography>
    <TableContainer component={Paper} style={{minHeight: '250px', maxWidth: '300px', margin: '20px'}}>
      <Table sx={{ minWidth: 650 }} aria-label="simple table">
        <TableHead>
          <TableRow>
            <TableCell>Pill Name</TableCell>
            <TableCell align="right">Count</TableCell>
            <TableCell align="right">Reference Image</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
            <TableRow
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    </div>
    </Box>
    <Box sx={{ margin: '20px', maxWidth: '800px' }}>
  <Typography  
    variant='h6'
    gutterBottom
  >
    Noon
  </Typography>
      <div style={{display: 'flex', justifyContent: 'center'}}>
        <Typography  
    gutterBottom
  >
    Recipe
  </Typography>
      <TableContainer component={Paper} style={{minHeight: '250px', maxWidth: '300px', margin: '20px'}}>
      <Table sx={{ minWidth: 650 }} aria-label="simple table">
        <TableHead>
          <TableRow>
            <TableCell>Pill Name</TableCell>
            <TableCell align="right">Count</TableCell>
            <TableCell align="right">Reference Image</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
            <TableRow
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    <Typography  
    gutterBottom
  >
    Prediction
  </Typography>
    <TableContainer component={Paper} style={{minHeight: '250px', maxWidth: '300px', margin: '20px'}}>
      <Table sx={{ minWidth: 650 }} aria-label="simple table">
        <TableHead>
          <TableRow>
            <TableCell>Pill Name</TableCell>
            <TableCell align="right">Count</TableCell>
            <TableCell align="right">Reference Image</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
            <TableRow
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    </div>
    </Box>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center'}}>
      <Box sx={{ margin: '20px', maxWidth: '800px' }}>
  <Typography  
    variant='h6'
    gutterBottom
  >
    Night
  </Typography>
      <div style={{display: 'flex', justifyContent: 'center'}}>
        <Typography  
    gutterBottom
  >
    Recipe
  </Typography>
      <TableContainer component={Paper} style={{minHeight: '250px', maxWidth: '300px', margin: '20px'}}>
      <Table sx={{ minWidth: 650 }} aria-label="simple table">
        <TableHead>
          <TableRow>
            <TableCell>Pill Name</TableCell>
            <TableCell align="right">Count</TableCell>
            <TableCell align="right">Reference Image</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
            <TableRow
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    <Typography  
    gutterBottom
  >
    Prediction
  </Typography>
    <TableContainer component={Paper} style={{minHeight: '250px', maxWidth: '300px', margin: '20px'}}>
      <Table sx={{ minWidth: 650 }} aria-label="simple table">
        <TableHead>
          <TableRow>
            <TableCell>Pill Name</TableCell>
            <TableCell align="right">Count</TableCell>
            <TableCell align="right">Reference Image</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
            <TableRow
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    </div>
    </Box>
    <Box sx={{ margin: '20px', maxWidth: '800px' }}>
  <Typography  
    variant='h6'
    gutterBottom
  >
    Midnight
  </Typography>
      <div style={{display: 'flex', justifyContent: 'center'}}>
        <Typography  
    gutterBottom
  >
    Recipe
  </Typography>
      <TableContainer component={Paper} style={{minHeight: '250px', maxWidth: '300px', margin: '20px'}}>
      <Table sx={{ minWidth: 650 }} aria-label="simple table">
        <TableHead>
          <TableRow>
            <TableCell>Pill Name</TableCell>
            <TableCell align="right">Count</TableCell>
            <TableCell align="right">Reference Image</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
            <TableRow
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    <Typography  
    gutterBottom
  >
    Prediction
  </Typography>
    <TableContainer component={Paper} style={{minHeight: '250px', maxWidth: '300px', margin: '20px'}}>
      <Table sx={{ minWidth: 650 }} aria-label="simple table">
        <TableHead>
          <TableRow>
            <TableCell>Pill Name</TableCell>
            <TableCell align="right">Count</TableCell>
            <TableCell align="right">Reference Image</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
            <TableRow
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    </div>
    </Box>
      </div>
      <div style={{ flex: '1 1 33%' }}></div>
        <div style={{
        position: 'absolute',
        left: '20px',
        bottom: '20px'
      }}>
        <Button variant="contained" style={{marginBottom: '20px'}}>
            Verify Dispense
          </Button>
          <br></br>
        <Link href="/" passHref>
          <Button variant="contained">
            Main Page
          </Button>
        </Link>
        </div>
    </div>
  );
};

export default CameraApp;