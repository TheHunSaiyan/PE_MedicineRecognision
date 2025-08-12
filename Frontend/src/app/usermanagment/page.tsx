"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import { MaterialReactTable, type MRT_ColumnDef } from 'material-react-table';
import { Box, IconButton, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import {ROLES} from '../../../constans/roles';

interface User {
    user_id: number;
    first_name: string;
    last_name: string;
    email: string;
    role: string;
}

const CameraApp: React.FC = () => { 
    const [users, setUsers] = useState<User[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [currentUser, setCurrentUser] = useState<User | null>(null);
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [newUser, setNewUser] = useState({
        email: '',
        password: '',
        first_name: '',
        last_name: '',
        role: ROLES.NURSE
    });

    const roleOptions = Object.entries(ROLES).map(([key, value]) => ({
        label: key.charAt(0).toUpperCase() + key.slice(1).toLowerCase(),
        value
    }));

    useEffect(() => {
        const fetchUsers = async () => {
            try {
                const response = await fetch('http://localhost:2076/get_all_users');
                if (!response.ok) {
                    throw new Error('Failed to fetch users');
                }
                const data = await response.json();
                setUsers(data);
            } catch (error) {
                console.error('Error fetching users:', error);
            } finally {
                setIsLoading(false);
            }
        };
        
        fetchUsers();
    }, []);

    const columns = React.useMemo<MRT_ColumnDef<User>[]>(() => [
        {
            accessorKey: 'user_id',
            header: 'ID',
        },
        {
            accessorKey: 'first_name',
            header: 'First Name',
        },
        {
            accessorKey: 'last_name',
            header: 'Last Name',
        },
        {
            accessorKey: 'email',
            header: 'Email',
        },
        {
            accessorKey: 'role',
            header: 'Role',
        },
    ], []);

    const handleDeleteUser = async (userId: number) => {
        try {
            const response = await fetch(`http://localhost:2076/delete_user`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: userId }),
            });
            if (!response.ok) {
                throw new Error('Failed to delete user');
            }
            setUsers(users.filter(user => user.user_id !== userId));
        } catch (error) {
            console.error('Error deleting user:', error);
        }
    };

    const handleUpdateUser = async (user: User) => {
        try {
            const response = await fetch('http://localhost:2076/update_user', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: user.user_id,
                    first_name: user.first_name,
                    last_name: user.last_name,
                    email: user.email,
                    role: user.role
                }),
            });
            
            if (!response.ok) {
                throw new Error('Failed to update user');
            }
            
            const updatedUser = await response.json();
            setUsers(users.map(u => u.user_id === user.user_id ? updatedUser.user : u));
            setIsEditing(false);
            setCurrentUser(null);
        } catch (error) {
            console.error('Error updating user:', error);
        }
    };

    const handleCreateUser = async () => {
        try {
            const response = await fetch('http://localhost:2076/create_user', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newUser),
            });
            
            if (!response.ok) {
                throw new Error('Failed to create user');
            }
            
            const createdUser = await response.json();
            setUsers([...users, createdUser.user]);
            setIsCreateDialogOpen(false);
            setNewUser({
                email: '',
                password: '',
                first_name: '',
                last_name: '',
                role: ROLES.NURSE
            });
        } catch (error) {
            console.error('Error creating user:', error);
        }
    };

    return(
        <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
        <div className="camera-container" style={{
            position: 'absolute', left: '50%', top: '50%',
            transform: 'translate(-50%, -50%)'
        }}>
            <div style={{ margin: '20px' }}>
                {error && (
                    <div style={{ color: 'red', marginBottom: '10px' }}>
                        {error}
                        <Button onClick={() => setError(null)}>Dismiss</Button>
                    </div>
                )}
                
                <MaterialReactTable              
                    columns={columns}
                    data={users}
                    state={{ isLoading }}
                    layoutMode="grid"
                    displayColumnDefOptions={{
                        'mrt-row-actions': {
                            size: 180,
                            grow: false,
                        },
                    }}
                    enableRowActions
                    renderRowActions={({ row }) => (
                        <Box sx={{ display: 'flex', flexWrap: 'nowrap', gap: '8px' }}>
                            <IconButton
                                color="secondary"
                                onClick={() => {
                                    setCurrentUser(row.original);
                                    setIsEditing(true);
                                }}
                            >
                                <EditIcon />
                            </IconButton>
                            <IconButton
                                color="error"
                                onClick={() => handleDeleteUser(row.original.user_id)}
                            >
                                <DeleteIcon />
                            </IconButton>
                        </Box>
                    )}
                    renderTopToolbarCustomActions={() => (
                        <Tooltip title="Create New User">
                            <Button
                                color="primary"
                                onClick={() => setIsCreateDialogOpen(true)}
                                variant="contained"
                                startIcon={<AddIcon />}
                            >
                                New User
                            </Button>
                        </Tooltip>
                    )}
                />
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
                    <Button variant="contained">Main Page</Button>
                </Link>
            </div>

            <Dialog open={isEditing} onClose={() => setIsEditing(false)}>
                <DialogTitle>Edit User</DialogTitle>
                <DialogContent>
                    {currentUser && (
                        <>
                            <TextField
                                margin="dense"
                                label="First Name"
                                fullWidth
                                value={currentUser.first_name}
                                onChange={(e) => setCurrentUser({...currentUser, first_name: e.target.value})}
                                sx={{ mt: 2 }}
                            />
                            <TextField
                                margin="dense"
                                label="Last Name"
                                fullWidth
                                value={currentUser.last_name}
                                onChange={(e) => setCurrentUser({...currentUser, last_name: e.target.value})}
                                sx={{ mt: 2 }}
                            />
                            <TextField
                                margin="dense"
                                label="Email"
                                fullWidth
                                value={currentUser.email}
                                onChange={(e) => setCurrentUser({...currentUser, email: e.target.value})}
                                sx={{ mt: 2 }}
                            />
                            <FormControl fullWidth sx={{ mt: 2 }}>
                                <InputLabel>Role</InputLabel>
                                <Select
                                    value={currentUser.role}
                                    label="Role"
                                    onChange={(e) => setCurrentUser({...currentUser, role: e.target.value})}
                                >
                                    {roleOptions.map((option) => (
                                        <MenuItem key={option.value} value={option.value}>
                                            {option.label}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setIsEditing(false)}>Cancel</Button>
                    <Button onClick={() => currentUser && handleUpdateUser(currentUser)}>Save</Button>
                </DialogActions>
            </Dialog>

            {/* Create User Dialog */}
            <Dialog open={isCreateDialogOpen} onClose={() => setIsCreateDialogOpen(false)}>
                <DialogTitle>Create New User</DialogTitle>
                <DialogContent>
                    <TextField
                        margin="dense"
                        label="Email"
                        fullWidth
                        value={newUser.email}
                        onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                        sx={{ mt: 2 }}
                    />
                    <TextField
                        margin="dense"
                        label="Password"
                        type="password"
                        fullWidth
                        value={newUser.password}
                        onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                        sx={{ mt: 2 }}
                    />
                    <TextField
                        margin="dense"
                        label="First Name"
                        fullWidth
                        value={newUser.first_name}
                        onChange={(e) => setNewUser({...newUser, first_name: e.target.value})}
                        sx={{ mt: 2 }}
                    />
                    <TextField
                        margin="dense"
                        label="Last Name"
                        fullWidth
                        value={newUser.last_name}
                        onChange={(e) => setNewUser({...newUser, last_name: e.target.value})}
                        sx={{ mt: 2 }}
                    />
                    <FormControl fullWidth sx={{ mt: 2 }}>
                        <InputLabel>Role</InputLabel>
                        <Select
                            value={newUser.role}
                            label="Role"
                            onChange={(e) => setNewUser({...newUser, role: e.target.value})}
                        >
                            {roleOptions.map((option) => (
                                <MenuItem key={option.value} value={option.value}>
                                    {option.label}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setIsCreateDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleCreateUser}>Create</Button>
                </DialogActions>
            </Dialog>
        </div>
        </ProtectedRoute>
    );
};

export default CameraApp;