export const ROLES = {
  ADMIN: 'admin',
  NURSE: 'nurse',
  DOCTOR: 'doctor',
  TECHNICIAN: 'technician',
} as const;

export type Role = typeof ROLES[keyof typeof ROLES];