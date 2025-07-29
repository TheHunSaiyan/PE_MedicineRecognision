export interface CaptureResponse {
  status: 'success' | 'error';
  filename?: string;
  error?: string;
  path?: string;
}