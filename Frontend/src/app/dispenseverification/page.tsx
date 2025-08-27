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
import { Alert, Box, Checkbox, FormControl, FormControlLabel, InputLabel, MenuItem, Select, Snackbar, Typography } from '@mui/material';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { ROLES } from '../../../constans/roles';

interface Medication {
  pill_name: string;
  count: number;
}

interface MedicationsData {
  medications: {
    dispensing_bay_1: Medication[];
    dispensing_bay_2: Medication[];
    dispensing_bay_3: Medication[];
    dispensing_bay_4: Medication[];
  };
}

interface VerificationResult {
  status: boolean;
  bays: {
    bay: string;
    expected: Medication[];
    found: Medication[];
    match: boolean;
  }[];
  verification_passed: boolean;
}

const CameraApp: React.FC = () => {
  const [language, setLanguage] = useState('hu');
  const [isInitializing, setIsInitializing] = useState(true);
  const [initializationError, setInitializationError] = useState<string | null>(null);
  const [environmentStatus, setEnvironmentStatus] = useState<boolean | null>(null);
  const [environmentMessage, setEnvironmentMessage] = useState<string>('');
  const [isCheckingEnvironment, setIsCheckingEnvironment] = useState(false);
  const [recipeSelected, setRecipeSelected] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [medicationsData, setMedicationsData] = useState<MedicationsData | null>(null);
  const [referenceImages, setReferenceImages] = useState<Record<string, any>>({});
  const [isVerifying, setIsVerifying] = useState(false);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);

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
      initializationError: "Error during incicialization!",
      recipeUploadSuccess: "Recipe uploaded successfully!",
      recipeUploadError: "Error uploading recipe: ",
      noFileSelected: "Please select a JSON file first",
      imageUploadSuccess: "Image uploaded successfully!",
      imageUploadError: "Error uploading image: ",
      match: "Match",
      mismatch: "Mismatch"
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
      initializationError: "Hiba inicianilázás közben!",
      recipeUploadSuccess: "Recept sikeresen feltöltve!",
      recipeUploadError: "Hiba a recept feltöltésekor: ",
      noFileSelected: "Kérjük, válasszon ki egy JSON fájlt",
      imageUploadSuccess: "Kép sikeresen feltöltve!",
      imageUploadError: "Hiba a kép feltöltésekor: ",
      match: "Egyezik",
      mismatch: "Nem egyezik"
    }
  };

const recipeRefs = useRef<(HTMLDivElement | null)[]>([]);
const predictionRefs = useRef<(HTMLDivElement | null)[]>([]);
const [labelHeights, setLabelHeights] = useState({ recipe: 0, prediction: 0 });
const [bayHeight, setBayHeight] = useState(0);
const bayRefs = useRef<(HTMLDivElement | null)[]>([]);

useEffect(() => {
  if (bayRefs.current.length > 0) {
    const max = Math.max(...bayRefs.current.map(el => el?.offsetHeight || 0));
    setBayHeight(max);
  }
}, [medicationsData, language, verificationResult]);


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

 const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
  const file = event.target.files?.[0];
  if (!file) return;

  if (file.type !== 'application/json') {
    setSnackbar({
      open: true,
      message: t.recipeUploadError + (language === 'hu' ? 'Csak JSON fájlok engedélyezettek' : 'Only JSON files are allowed'),
      severity: 'error'
    });
    return;
  }

  try {
    const fileContent = await readFileAsText(file);
    const jsonData = JSON.parse(fileContent);

    if (!jsonData.medications || 
        !jsonData.medications.dispensing_bay_1 || 
        !jsonData.medications.dispensing_bay_2 || 
        !jsonData.medications.dispensing_bay_3 || 
        !jsonData.medications.dispensing_bay_4) {
      throw new Error(language === 'hu' ? 'Érvénytelen JSON formátum' : 'Invalid JSON format');
    }

    const response = await fetch('http://localhost:2076/selected_recipe', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(jsonData)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    
    setMedicationsData(jsonData);
    
    setRecipeSelected(true);
    setSnackbar({
      open: true,
      message: t.recipeUploadSuccess,
      severity: 'success'
    });

    await fetchReferenceImages(jsonData);

  } catch (error) {
    console.error('Error uploading recipe:', error);
    setSnackbar({
      open: true,
      message: t.recipeUploadError + (error instanceof Error ? error.message : 'Unknown error'),
      severity: 'error'
    });
  }
};

  const readFileAsText = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.onerror = (e) => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  };

  const handleSelectRecipeClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

   const handleSnackbarClose = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const formatPillName = (pillName: string): string => {
    return pillName
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const fetchReferenceImages = async (medicationsDataParam?: MedicationsData) => {
  const dataToUse = medicationsDataParam || medicationsData;
  if (!dataToUse) return;

  try {
    const response = await fetch('http://localhost:2076/get_recipe_reference_images', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(dataToUse)
    });

    if (response.ok) {
      const data = await response.json();
      setReferenceImages(data);
    }
  } catch (error) {
    console.error('Error fetching reference images:', error);
  }
};

const renderMedicationTable = (medications: Medication[], bayName: string) => {
  if (!medications || medications.length === 0) {
    return (
      <TableRow>
        <TableCell colSpan={3} align="center">
          {language === 'hu' ? 'Nincs adat' : 'No data'}
        </TableCell>
      </TableRow>
    );
  }

  return medications.map((medication, index) => {
    const pillImages = referenceImages[bayName]?.[index]?.images || [];
    const firstImage = pillImages[0];

    return (
      <TableRow key={index}>
        <TableCell>{formatPillName(medication.pill_name)}</TableCell>
        <TableCell align="right">{medication.count}</TableCell>
        <TableCell align="right">
          {firstImage ? (
            <img 
              src={`http://localhost:2076${firstImage}`}
              alt={medication.pill_name}
              style={{ 
                width: '50px', 
                height: '50px', 
                objectFit: 'cover',
                borderRadius: '4px'
              }}
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
          ) : (
            <span style={{ color: '#999', fontStyle: 'italic' }}>
              {language === 'hu' ? 'Nincs kép' : 'No image'}
            </span>
          )}
        </TableCell>
      </TableRow>
    );
  });
};

const handleVerifyDispenseClick = () => {
    if (imageInputRef.current) {
      imageInputRef.current.click();
    }
  };

  const handleImageSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setSnackbar({
        open: true,
        message: t.imageUploadError + (language === 'hu' ? 'Csak képfájlok engedélyezettek' : 'Only image files are allowed'),
        severity: 'error'
      });
      return;
    }

    try {
      setIsVerifying(true);
      
      const formData = new FormData();
      formData.append('image', file);

      const response = await fetch('http://localhost:2076/verify_dispense', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result: VerificationResult = await response.json();
      
      setVerificationResult(result);
      
      setSnackbar({
        open: true,
        message: result.verification_passed 
          ? (language === 'hu' ? 'Ellenőrzés sikeres' : 'Verification successful') 
          : (language === 'hu' ? 'Ellenőrzés sikertelen' : 'Verification failed'),
        severity: result.verification_passed ? 'success' : 'error'
      });

    } catch (error) {
      console.error('Error uploading image:', error);
      setSnackbar({
        open: true,
        message: t.imageUploadError + (error instanceof Error ? error.message : 'Unknown error'),
        severity: 'error'
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const renderPredictionTable = (bayName: string) => {
  if (!verificationResult) {
    return (
      <TableRow>
        <TableCell colSpan={3} align="center">
          {language === 'hu' ? 'Nincs adat' : 'No data'}
        </TableCell>
      </TableRow>
    );
  }

  const bayResult = verificationResult.bays.find(bay => bay.bay === bayName);
  
  if (!bayResult || !bayResult.found || bayResult.found.length === 0) {
    return (
      <TableRow>
        <TableCell colSpan={3} align="center">
          {language === 'hu' ? 'Nincs adat' : 'No data'}
        </TableCell>
      </TableRow>
    );
  }

  return bayResult.found.map((medication, index) => (
    <TableRow key={index}>
      <TableCell>{formatPillName(medication.pill_name)}</TableCell>
      <TableCell align="right">{medication.count}</TableCell>
      <TableCell align="right">
        <span style={{ color: '#999', fontStyle: 'italic' }}>
          {language === 'hu' ? 'Kép' : 'Image'}
        </span>
      </TableCell>
    </TableRow>
  ));
};

const getResultText = (bayName: string) => {
  if (!verificationResult) return t.result;

  const bayResult = verificationResult.bays.find(bay => bay.bay === bayName);
  if (!bayResult) return t.result;

  const resultText = bayResult.match ? t.match : t.mismatch;
  const color = bayResult.match ? '#04e762' : '#ef233c';

  return (
    <span style={{ color, fontWeight: 'bold' }}>
      {t.result.replace('-', resultText)}
    </span>
  );
};

  return (
    <ProtectedRoute allowedRoles={[ROLES.ADMIN, ROLES.TECHNICIAN, ROLES.NURSE, ROLES.DOCTOR]}>
      <div className="camera-container" style={{
        padding: '20px',
        width: '100vw',
        boxSizing: 'border-box',
        minHeight: '100vh',
        position: 'relative'
      }}>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          accept=".json"
          style={{ display: 'none' }}
        />
        <input
          type="file"
          ref={imageInputRef}
          onChange={handleImageSelect}
          accept="image/*"
          style={{ display: 'none' }}
        />
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={handleSnackbarClose}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
          <Alert onClose={handleSnackbarClose} severity={snackbar.severity as any} sx={{ width: '100%' }}>
            {snackbar.message}
          </Alert>
        </Snackbar>

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
                  <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            marginBottom: '30px',
            gap: '20px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
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
                <Button variant="contained" onClick={handleSelectRecipeClick}>
                  {t.selectRecipe}
                </Button>
                <FormControlLabel
                  control={<Checkbox checked={recipeSelected} disabled />}
                  sx={{
                    '& .MuiSvgIcon-root': {
                      color: recipeSelected ? '#04e762' : '#ef233c',
                      fontSize: 28,
                    },
                  }}
                  label={
                    <span style={{
                      color: recipeSelected ? '#04e762' : '#ef233c',
                      fontWeight: 'bold'
                    }}>
                      {t.recipe}
                    </span>
                  }
                />
              </div>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Button 
                className="verify"
                variant="contained"
                onClick={handleVerifyDispenseClick}
                disabled={isVerifying}>
                {t.verifyDispense}
              </Button>
            </div>
          </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', alignItems: 'start' }}>
          <Box ref={el => (bayRefs.current[0] = el)} sx={{ gridColumn: '1', display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Typography variant='h6' gutterBottom>{t.morning}</Typography>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.recipeLabel}</Typography>
            </div>
            
           
              <TableContainer component={Paper} sx={{ flex: 1 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {medicationsData ? renderMedicationTable(medicationsData.medications.dispensing_bay_1, 'dispensing_bay_1') : (
                      <TableRow>
                        <TableCell colSpan={3} align="center">
                          {language === 'hu' ? 'Nincs adat' : 'No data'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
          
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.predictionLabel}</Typography>
            </div>
              <TableContainer component={Paper} sx={{ flex: 1 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {renderPredictionTable('dispensing_bay_1')}
                  </TableBody>
                </Table>
              </TableContainer>
            
            <Typography gutterBottom style={{ marginTop: '10px' }}>{getResultText('dispensing_bay_1')}</Typography>
          </Box>

          <Box ref={el => (bayRefs.current[1] = el)} sx={{ gridColumn: '2', display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Typography variant='h6' gutterBottom>{t.noon}</Typography>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.recipeLabel}</Typography>
            </div>
        
              <TableContainer component={Paper} sx={{ flex: 1 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {medicationsData ? renderMedicationTable(medicationsData.medications.dispensing_bay_2, 'dispensing_bay_2') : (
                      <TableRow>
                        <TableCell colSpan={3} align="center">
                          {language === 'hu' ? 'Nincs adat' : 'No data'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>

            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.predictionLabel}</Typography>
            </div>
            
           
              <TableContainer component={Paper} sx={{ flex: 1 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {renderPredictionTable('dispensing_bay_2')}
                  </TableBody>
                </Table>
              </TableContainer>
        
            
            <Typography gutterBottom style={{ marginTop: '10px' }}>{getResultText('dispensing_bay_2')}</Typography>
          </Box>

          <Box ref={el => (bayRefs.current[2] = el)} sx={{ gridColumn: '3', display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Typography variant='h6' gutterBottom>{t.night}</Typography>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.recipeLabel}</Typography>
            </div>
            
            
              <TableContainer component={Paper} sx={{ flex: 1 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {medicationsData ? renderMedicationTable(medicationsData.medications.dispensing_bay_3, 'dispensing_bay_3') : (
                      <TableRow>
                        <TableCell colSpan={3} align="center">
                          {language === 'hu' ? 'Nincs adat' : 'No data'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
                  
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.predictionLabel}</Typography>
            </div>
            
       
              <TableContainer component={Paper} sx={{ flex: 1 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {renderPredictionTable('dispensing_bay_3')}
                  </TableBody>
                </Table>
              </TableContainer>
         
            
            <Typography gutterBottom style={{ marginTop: '10px' }}>{getResultText('dispensing_bay_3')}</Typography>
          </Box>
          <Box ref={el => (bayRefs.current[3] = el)} sx={{ gridColumn: '4', display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Typography variant='h6' gutterBottom>{t.midnight}</Typography>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.recipeLabel}</Typography>
            </div>
            
            
              <TableContainer component={Paper} sx={{ flex: 1 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {medicationsData ? renderMedicationTable(medicationsData.medications.dispensing_bay_4, 'dispensing_bay_4') : (
                      <TableRow>
                        <TableCell colSpan={3} align="center">
                          {language === 'hu' ? 'Nincs adat' : 'No data'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
    
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <Typography>{t.predictionLabel}</Typography>
            </div>
            
            
              <TableContainer component={Paper} sx={{ flex: 1 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t.pillName}</TableCell>
                      <TableCell align="right">{t.count}</TableCell>
                      <TableCell align="right">{t.referenceImage}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {renderPredictionTable('dispensing_bay_4')}
                  </TableBody>
                </Table>
              </TableContainer>
          
            
            <Typography gutterBottom style={{ marginTop: '10px' }}>{getResultText('dispensing_bay_4')}</Typography>
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
          <Link href="/mainpage" passHref>
            <Button variant="contained">{t.mainPage}</Button>
          </Link>
        </div>
      </div>
    </ProtectedRoute>
  );
};

export default CameraApp;