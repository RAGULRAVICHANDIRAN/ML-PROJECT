import { createTheme } from '@mui/material/styles';

const theme = createTheme({
    palette: {
        mode: 'light',
        primary: { main: '#3f51b5', light: '#7986cb', dark: '#283593', contrastText: '#fff' },
        secondary: { main: '#ff6f00', light: '#ffa040', dark: '#c43e00', contrastText: '#fff' },
        background: { default: '#f0f2f5', paper: '#ffffff' },
        success: { main: '#2e7d32' },
        warning: { main: '#ed6c02' },
        error: { main: '#d32f2f' },
        info: { main: '#0288d1' },
        text: { primary: '#1a1a2e', secondary: '#546e7a' }
    },
    typography: {
        fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
        h1: { fontWeight: 800, letterSpacing: '-0.02em' },
        h2: { fontWeight: 700, letterSpacing: '-0.01em' },
        h3: { fontWeight: 700 },
        h4: { fontWeight: 600 },
        h5: { fontWeight: 600 },
        h6: { fontWeight: 600 },
        subtitle1: { fontWeight: 500 },
        button: { fontWeight: 600, textTransform: 'none' }
    },
    shape: { borderRadius: 12 },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: 10, padding: '10px 24px', fontSize: '0.938rem',
                    boxShadow: 'none', '&:hover': { boxShadow: '0 4px 12px rgba(63,81,181,0.3)' }
                },
                contained: { background: 'linear-gradient(135deg, #3f51b5 0%, #5c6bc0 100%)' }
            }
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    borderRadius: 16, boxShadow: '0 2px 20px rgba(0,0,0,0.06)',
                    border: '1px solid rgba(0,0,0,0.05)',
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&:hover': { boxShadow: '0 8px 32px rgba(0,0,0,0.1)', transform: 'translateY(-2px)' }
                }
            }
        },
        MuiTextField: {
            styleOverrides: {
                root: { '& .MuiOutlinedInput-root': { borderRadius: 10 } }
            }
        },
        MuiChip: {
            styleOverrides: { root: { borderRadius: 8, fontWeight: 500 } }
        },
        MuiAppBar: {
            styleOverrides: {
                root: { boxShadow: '0 1px 3px rgba(0,0,0,0.08)', backdropFilter: 'blur(20px)', background: 'rgba(255,255,255,0.9)' }
            }
        },
        MuiDrawer: {
            styleOverrides: {
                paper: { border: 'none', boxShadow: '2px 0 20px rgba(0,0,0,0.05)' }
            }
        },
        MuiPaper: {
            styleOverrides: { rounded: { borderRadius: 16 } }
        }
    }
});

export default theme;
