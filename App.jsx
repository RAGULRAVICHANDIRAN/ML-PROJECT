import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './theme';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import ChatBot from './components/ChatBot';

// Auth pages
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import ProfilePage from './pages/auth/ProfilePage';

// Dashboards
import AdminDashboard from './pages/dashboard/AdminDashboard';
import InstructorDashboard from './pages/dashboard/InstructorDashboard';
import StudentDashboard from './pages/dashboard/StudentDashboard';

// Courses
import CourseCatalog from './pages/courses/CourseCatalog';
import CourseDetail from './pages/courses/CourseDetail';
import CourseForm from './pages/courses/CourseForm';
import CourseStudents from './pages/courses/CourseStudents';

// Attendance
import MarkAttendance from './pages/attendance/MarkAttendance';
import AttendanceReport from './pages/attendance/AttendanceReport';

// Assessments
import AssessmentForm from './pages/assessments/AssessmentForm';
import TakeAssessment from './pages/assessments/TakeAssessment';
import GradeSubmissions from './pages/assessments/GradeSubmissions';
import Gradebook from './pages/assessments/Gradebook';

// Certificates
import CertificateList from './pages/certificates/CertificateList';
import VerifyCertificate from './pages/certificates/VerifyCertificate';

// Admin
import UserManagement from './pages/admin/UserManagement';

// Notifications
import NotificationsPage from './pages/notifications/NotificationsPage';

const DashboardRouter = () => {
    const { user } = useAuth();
    if (user?.role === 'admin') return <AdminDashboard />;
    if (user?.role === 'instructor') return <InstructorDashboard />;
    return <StudentDashboard />;
};

function App() {
    return (
        <ThemeProvider theme={theme}>
            <CssBaseline />
            <BrowserRouter>
                <AuthProvider>
                    <Routes>
                        {/* Public routes */}
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/register" element={<RegisterPage />} />
                        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                        <Route path="/verify-certificate" element={<VerifyCertificate />} />

                        {/* Protected routes */}
                        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                            <Route path="/dashboard" element={<DashboardRouter />} />
                            <Route path="/profile" element={<ProfilePage />} />
                            <Route path="/notifications" element={<NotificationsPage />} />

                            {/* Courses */}
                            <Route path="/courses" element={<CourseCatalog />} />
                            <Route path="/courses/new" element={
                                <ProtectedRoute roles={['admin', 'instructor']}><CourseForm /></ProtectedRoute>
                            } />
                            <Route path="/courses/:id" element={<CourseDetail />} />
                            <Route path="/courses/:id/edit" element={
                                <ProtectedRoute roles={['admin', 'instructor']}><CourseForm /></ProtectedRoute>
                            } />
                            <Route path="/courses/:id/students" element={
                                <ProtectedRoute roles={['admin', 'instructor']}><CourseStudents /></ProtectedRoute>
                            } />
                            <Route path="/my-courses" element={<CourseCatalog />} />

                            {/* Attendance */}
                            <Route path="/courses/:courseId/attendance" element={
                                <ProtectedRoute roles={['admin', 'instructor']}><AttendanceReport /></ProtectedRoute>
                            } />
                            <Route path="/courses/:courseId/attendance/:sessionId" element={
                                <ProtectedRoute roles={['admin', 'instructor']}><MarkAttendance /></ProtectedRoute>
                            } />

                            {/* Assessments */}
                            <Route path="/courses/:courseId/assessments/new" element={
                                <ProtectedRoute roles={['admin', 'instructor']}><AssessmentForm /></ProtectedRoute>
                            } />
                            <Route path="/assessments/:id/take" element={
                                <ProtectedRoute roles={['student']}><TakeAssessment /></ProtectedRoute>
                            } />
                            <Route path="/assessments/:id/submissions" element={
                                <ProtectedRoute roles={['admin', 'instructor']}><GradeSubmissions /></ProtectedRoute>
                            } />
                            <Route path="/courses/:courseId/gradebook" element={<Gradebook />} />

                            {/* Certificates */}
                            <Route path="/certificates" element={<CertificateList />} />

                            {/* Admin */}
                            <Route path="/admin/users" element={
                                <ProtectedRoute roles={['admin']}><UserManagement /></ProtectedRoute>
                            } />
                        </Route>

                        {/* Global components for authenticated users */}
                        <Route element={<ProtectedRoute><ChatBot /></ProtectedRoute>} />

                        {/* Default redirect */}
                        <Route path="/" element={<Navigate to="/dashboard" replace />} />
                        <Route path="*" element={<Navigate to="/dashboard" replace />} />
                    </Routes>
                </AuthProvider>
            </BrowserRouter>
        </ThemeProvider>
    );
}

export default App;
