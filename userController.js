const User = require('../models/User');
const Enrollment = require('../models/Enrollment');
const Course = require('../models/Course');

// @desc Get all users (admin only)
exports.getUsers = async (req, res, next) => {
    try {
        const { page = 1, limit = 20, role, search } = req.query;
        const query = {};
        if (role) query.role = role;
        if (search) query.$or = [
            { name: { $regex: search, $options: 'i' } },
            { email: { $regex: search, $options: 'i' } }
        ];

        const users = await User.find(query)
            .sort({ createdAt: -1 })
            .skip((page - 1) * limit)
            .limit(parseInt(limit));

        const total = await User.countDocuments(query);
        res.json({ users, total, page: parseInt(page), pages: Math.ceil(total / limit) });
    } catch (error) { next(error); }
};

// @desc Get single user
exports.getUser = async (req, res, next) => {
    try {
        const user = await User.findById(req.params.id);
        if (!user) return res.status(404).json({ message: 'User not found' });
        res.json(user);
    } catch (error) { next(error); }
};

// @desc Update user (admin)
exports.updateUser = async (req, res, next) => {
    try {
        const { name, email, role } = req.body;
        const user = await User.findByIdAndUpdate(req.params.id, { name, email, role }, { new: true, runValidators: true });
        if (!user) return res.status(404).json({ message: 'User not found' });
        res.json(user);
    } catch (error) { next(error); }
};

// @desc Delete user (admin)
exports.deleteUser = async (req, res, next) => {
    try {
        const user = await User.findByIdAndDelete(req.params.id);
        if (!user) return res.status(404).json({ message: 'User not found' });
        res.json({ message: 'User removed' });
    } catch (error) { next(error); }
};

// @desc Get dashboard stats (admin)
exports.getDashboardStats = async (req, res, next) => {
    try {
        const totalUsers = await User.countDocuments();
        const totalStudents = await User.countDocuments({ role: 'student' });
        const totalInstructors = await User.countDocuments({ role: 'instructor' });
        const totalCourses = await Course.countDocuments();
        const activeEnrollments = await Enrollment.countDocuments({ status: 'active' });
        const completedEnrollments = await Enrollment.countDocuments({ status: 'completed' });
        const recentUsers = await User.find().sort({ createdAt: -1 }).limit(5);

        const enrollmentsByMonth = await Enrollment.aggregate([
            { $group: { _id: { $month: '$enrolledAt' }, count: { $sum: 1 } } },
            { $sort: { _id: 1 } }
        ]);

        res.json({
            totalUsers, totalStudents, totalInstructors, totalCourses,
            activeEnrollments, completedEnrollments, recentUsers, enrollmentsByMonth,
            completionRate: activeEnrollments + completedEnrollments > 0
                ? Math.round((completedEnrollments / (activeEnrollments + completedEnrollments)) * 100) : 0
        });
    } catch (error) { next(error); }
};
