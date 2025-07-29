import { CaptureResponse } from './apiTypes';

export const captureImage = async (): Promise<CaptureResponse> => {
  const apiUrl = process.env.NODE_ENV === 'development' 
    ? 'http://localhost:2076' 
    : 'http://biotechnica:2076';

  const response = await fetch(`${apiUrl}/capture`);
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json() as CaptureResponse;
};