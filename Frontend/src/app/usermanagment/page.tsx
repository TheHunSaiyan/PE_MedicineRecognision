"use client";

import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Link from 'next/link';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { MaterialReactTable, type MRT_ColumnDef } from 'material-react-table';
import { Box, IconButton } from '@mui/material';

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
            const response = await fetch(`/delete_user/${userId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                throw new Error('Failed to delete user');
            }
            setUsers(users.filter(user => user.user_id !== userId));
        } catch (error) {
            console.error('Error deleting user:', error);
        }
    };

    return(
        <ProtectedRoute>
        <div className="camera-container" style={{
            position: 'absolute', left: '50%', top: '50%',
            transform: 'translate(-50%, -50%)'
        }}>
            <div>
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
                    renderRowActions={({ row, table }) => (
                        <Box sx={{ display: 'flex', flexWrap: 'nowrap', gap: '8px' }}>
                            <IconButton
                                color="secondary"
                                onClick={() => {
                                    table.setEditingRow(row);
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
        </div>
        </ProtectedRoute>
    );
};

export default CameraApp;