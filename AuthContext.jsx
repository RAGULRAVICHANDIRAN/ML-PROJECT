import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import API from '../api/axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const stored = localStorage.getItem('lms_user');
        if (stored) {
            const parsed = JSON.parse(stored);
            setUser(parsed);
            API.get('/auth/me').then(res => {
                const updated = { ...parsed, ...res.data };
                setUser(updated);
                localStorage.setItem('lms_user', JSON.stringify(updated));
            }).catch(() => {
                localStorage.removeItem('lms_user');
                setUser(null);
            });
        }
        setLoading(false);
    }, []);

    const login = useCallback(async (email, password) => {
        const { data } = await API.post('/auth/login', { email, password });
        setUser(data);
        localStorage.setItem('lms_user', JSON.stringify(data));
        return data;
    }, []);

    const register = useCallback(async (name, email, password) => {
        const { data } = await API.post('/auth/register', { name, email, password });
        setUser(data);
        localStorage.setItem('lms_user', JSON.stringify(data));
        return data;
    }, []);

    const logout = useCallback(() => {
        setUser(null);
        localStorage.removeItem('lms_user');
    }, []);

    const updateUser = useCallback((updates) => {
        const updated = { ...user, ...updates };
        setUser(updated);
        localStorage.setItem('lms_user', JSON.stringify(updated));
    }, [user]);

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout, updateUser }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) throw new Error('useAuth must be used within AuthProvider');
    return context;
};
