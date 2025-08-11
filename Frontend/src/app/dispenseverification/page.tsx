"use client";

import React, { useState, useEffect, useRef } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import { Box, Checkbox, FormControl, FormControlLabel, InputLabel, MenuItem, Select, Typography } from '@mui/material';
import ProtectedRoute from '../../../components/ProtectedRoute';

const CameraApp: React.FC = () => {
  const [language, setLanguage] = useState('hu');
  const [isInitializing, setIsInitializing] = useState(true);
  const [initializationError, setInitializationError] = useState<string | null>(null);
  const [environmentStatus, setEnvironmentStatus] = useState<boolean | null>(null);
  const [environmentMessage, setEnvironmentMessage] = useState<string>('');
  const [isCheckingEnvironment, setIsCheckingEnvironment] = useState(false);

  const translations = {
    en: {
      title: "Pill Dispense Verification",
      checkEnvironment: "Check Environment",
      selectRecipe: "Select Recipe",
      status: "Status:",
      recipe: "Recipe",
      recipeLabel: "Recipe",
      predictionLabel: "Prediction",
      morning: "Morning",
      noon: "Noon",
      night: "Night",
      midnight: "Midnight",
      pillName: "Pill Name",
      count: "Count",
      referenceImage: "Reference Image",
      result: "Result: -",
      verifyDispense: "Verify Dispense",
      mainPage: "Main Page",
      language: "Language",
      initializing: "Initializing...",
      initializationError: "Error during incicialization!"
    },
    hu: {
      title: "Gyógyszeradagolás ellenőrzése",
      checkEnvironment: "Munkaterület ellenőrzése",
      selectRecipe: "Recept kiválasztása",
      status: "Állapot",
      recipe: "Recept",
      recipeLabel: "Recept",
      predictionLabel: "Előrejelzés",
      morning: "Reggel",
      noon: "Délben",
      night: "Este",
      midnight: "Éjfél",
      pillName: "Gyógyszer neve",
      count: "Darabszám",
      referenceImage: "Referenciakép",
      result: "Eredmény: -",
      verifyDispense: "Adagolás ellenőrzése",
      mainPage: "Főmenü",
      language: "Nyelv",
      initializing: "Inicializálás...",
      initializationError: "Hiba inicianilázás közben!"
    }
  };

  const t = translations[language as keyof typeof translations];

  const handleLanguageChange = (event: any) => {
    setLanguage(event.target.value);
  };

  useEffect(() => {
    const initializeApp = async () => {
      try {
        setIsInitializing(true);
        setInitializationError(null);
        
        const response = await fetch('http://localhost:2076/initialization', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error(`Initialization failed with status ${response.status}`);
        }

      } catch (error) {
        console.error('Initialization error:', error);
        setInitializationError(error instanceof Error ? error.message : 'Initialization failed');
      } finally {
        setIsInitializing(false);
      }
    };

    initializeApp();
  }, []);

  const checkEnvironment = async () => {
    try {
      setIsCheckingEnvironment(true);
      setEnvironmentMessage('');
      
      const response = await fetch('http://localhost:2076/check_environment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          holder_id: "123456789"
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Environment check failed');
      }

      setEnvironmentStatus(data.status);
      setEnvironmentMessage(data.message);
    } catch (error) {
      console.error('Environment check error:', error);
      setEnvironmentStatus(false);
      setEnvironmentMessage(error instanceof Error ? error.message : 'Environment check failed');
    } finally {
      setIsCheckingEnvironment(false);
    }
  };

  if (isInitializing) {
    return (
      <div className="camera-container" style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '24px'
      }}>
        {t.initializing}
      </div>
    );
  }

  if (initializationError) {
    return (
      <div className="camera-container" style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        gap: '20px'
      }}>
        <div style={{ fontSize: '24px', color: 'red' }}>{t.initializationError}</div>
        <Button 
          variant="contained" 
          onClick={() => window.location.reload()}
        >
          {language === 'hu' ? 'Frissítés' : 'Refresh'}
        </Button>
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div className="camera-container" style={{
        padding: '20px',
        width: '100vw',
        boxSizing: 'border-box',
        minHeight: '100vh',
        position: 'relative'
      }}>
        <div style={{ position: 'absolute', right: '20px', top: '20px' }}>
          <FormControl size="small" variant="outlined">
            <InputLabel>{t.language}</InputLabel>
            <Select
              value={language}
              onChange={handleLanguageChange}
              label="Language"
              style={{ minWidth: '120px' }}
            >
              <MenuItem value="en">🇺🇸 EN</MenuItem>
              <MenuItem value="hu">🇭🇺 HU</MenuItem>
            </Select>
          </FormControl>
        </div>
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <h1 style={{ fontSize: '40px', margin: 0 }}>{t.title}</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '30px', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Button 
              variant="contained" 
              onClick={checkEnvironment} 
              disabled={isCheckingEnvironment}>
              {isCheckingEnvironment ? 
                (language === 'hu' ? 'Ellenőrzés...' : 'Checking...') : 
                t.checkEnvironment}
            </Button>
            <FormControlLabel
              control={<Checkbox checked={false} disabled />}
              sx={{
                '& .MuiSvgIcon-root': {
                  color: false ? '#04e762' : '#ef233c',
                  fontSize: 28,
                },
              }}
              label={
                <span style={{
                  color: false ? '#04e762' : '#ef233c',
                  fontWeight: 'bold'
                }}>
                  {t.status}
                </span>
              }
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Button variant="contained">{t.selectRecipe}</Button>
            <FormControlLabel
              control={<Checkbox checked={false} disabled />}
              sx={{
                '& .MuiSvgIcon-root': {
                  color: false ? '#04e762' : '#ef233c',
                  fontSize: 28,
                },
              }}
              label={
                <span style={{
                  color: false ? '#04e762' : '#ef233c',
                  fontWeight: 'bold'
                }}>
                  {t.recipe}
                </span>
              }
            />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
          <Box sx={{ gridColumn: '1' }}>
            <Typography variant='h6' gutterBottom>{t.morning}</Typography>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.recipeLabel}</Typography>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <TableContainer component={Paper} style={{ minHeight: '200px' }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.predictionLabel}</Typography>
            </div>
              <TableContainer component={Paper} style={{ minHeight: '200px' }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </div>
            <Typography gutterBottom style={{ marginTop: '10px' }}>{t.result}</Typography>
          </Box>
          <Box sx={{ gridColumn: '2' }}>
            <Typography variant='h6' gutterBottom>{t.noon}</Typography>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.recipeLabel}</Typography>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <TableContainer component={Paper} style={{ minHeight: '200px' }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.predictionLabel}</Typography>
            </div>
              <TableContainer component={Paper} style={{ minHeight: '200px' }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </div>
            <Typography gutterBottom style={{ marginTop: '10px' }}>{t.result}</Typography>
          </Box>
          <Box sx={{ gridColumn: '3' }}>
            <Typography variant='h6' gutterBottom>{t.night}</Typography>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.recipeLabel}</Typography>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <TableContainer component={Paper} style={{ minHeight: '200px' }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.predictionLabel}</Typography>
            </div>
              <TableContainer component={Paper} style={{ minHeight: '200px' }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </div>
            <Typography gutterBottom style={{ marginTop: '10px' }}>{t.result}</Typography>
          </Box>
          <Box sx={{ gridColumn: '4' }}>
            <Typography variant='h6' gutterBottom>{t.midnight}</Typography>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.recipeLabel}</Typography>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <TableContainer component={Paper} style={{ minHeight: '200px' }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.predictionLabel}</Typography>
            </div>
              <TableContainer component={Paper} style={{ minHeight: '200px' }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                      <TableCell align="right"></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </div>
            <Typography gutterBottom style={{ marginTop: '10px' }}>{t.result}</Typography>
          </Box>
        </div>

        <div style={{
          position: 'fixed',
          left: '20px',
          bottom: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}>
          <Button variant="contained">{t.verifyDispense}</Button>
          <Link href="/mainpage" passHref>
            <Button variant="contained">{t.mainPage}</Button>
          </Link>
        </div>
      </div>
    </ProtectedRoute>
  );
};

export default CameraApp;