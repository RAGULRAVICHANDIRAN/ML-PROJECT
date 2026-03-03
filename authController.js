const User = require('../models/User');
const Notification = require('../models/Notification');
const { generateToken, generateRefreshToken } = require('../utils/generateToken');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');

// @desc Register user
exports.register = async (req, res, next) => {
    try {
        const { name, email, password } = req.body;
        const existingUser = await User.findOne({ email });
        if (existingUser) return res.status(400).json({ message: 'Email already registered' });

        const user = await User.create({ name, email, password });
        const token = generateToken(user._id);
        const refreshToken = generateRefreshToken(user._id);

        await Notification.create({ user: user._id, title: 'Welcome!', message: `Welcome to LMS, ${name}!`, type: 'system' });

        res.status(201).json({
            _id: user._id, name: user.name, email: user.email, role: user.role,
            avatar: user.avatar, token, refreshToken
        });
    } catch (error) { next(error); }
};

// @desc Login user
exports.login = async (req, res, next) => {
    try {
        const { email, password } = req.body;
        if (!email || !password) return res.status(400).json({ message: 'Please provide email and password' });

        const user = await User.findOne({ email }).select('+password');
        if (!user) return res.status(401).json({ message: 'Invalid credentials' });

        const isMatch = await user.matchPassword(password);
        if (!isMatch) return res.status(401).json({ message: 'Invalid credentials' });

        const token = generateToken(user._id);
        const refreshToken = generateRefreshToken(user._id);

        res.json({
            _id: user._id, name: user.name, email: user.email, role: user.role,
            avatar: user.avatar, token, refreshToken
        });
    } catch (error) { next(error); }
};

// @desc Refresh token
exports.refreshToken = async (req, res, next) => {
    try {
        const { refreshToken } = req.body;
        if (!refreshToken) return res.status(400).json({ message: 'Refresh token required' });

        const decoded = jwt.verify(refreshToken, process.env.JWT_REFRESH_SECRET);
        const user = await User.findById(decoded.id);
        if (!user) return res.status(401).json({ message: 'User not found' });

        const token = generateToken(user._id);
        const newRefreshToken = generateRefreshToken(user._id);
        res.json({ token, refreshToken: newRefreshToken });
    } catch (error) {
        return res.status(401).json({ message: 'Invalid refresh token' });
    }
};

// @desc Get current user
exports.getMe = async (req, res) => {
    res.json(req.user);
};

// @desc Update profile
exports.updateProfile = async (req, res, next) => {
    try {
        const { name, bio, phone } = req.body;
        const updateData = {};
        if (name) updateData.name = name;
        if (bio !== undefined) updateData.bio = bio;
        if (phone !== undefined) updateData.phone = phone;
        if (req.file) updateData.avatar = `/uploads/avatars/${req.file.filename}`;

        const user = await User.findByIdAndUpdate(req.user._id, updateData, { new: true, runValidators: true });
        res.json(user);
    } catch (error) { next(error); }
};

// @desc Change password
exports.changePassword = async (req, res, next) => {
    try {
        const { currentPassword, newPassword } = req.body;
        const user = await User.findById(req.user._id).select('+password');

        const isMatch = await user.matchPassword(currentPassword);
        if (!isMatch) return res.status(400).json({ message: 'Current password is incorrect' });

        user.password = newPassword;
        await user.save();
        res.json({ message: 'Password updated successfully' });
    } catch (error) { next(error); }
};

// @desc Forgot password
exports.forgotPassword = async (req, res, next) => {
    try {
        const user = await User.findOne({ email: req.body.email });
        if (!user) return res.status(404).json({ message: 'No user with that email' });

        const resetToken = crypto.randomBytes(32).toString('hex');
        user.resetPasswordToken = crypto.createHash('sha256').update(resetToken).digest('hex');
        user.resetPasswordExpire = Date.now() + 3600000; // 1 hour
        await user.save({ validateBeforeSave: false });

        console.log(`Password reset token for ${user.email}: ${resetToken}`);
        res.json({ message: 'Password reset token generated (check server console)', resetToken });
    } catch (error) { next(error); }
};

// @desc Reset password
exports.resetPassword = async (req, res, next) => {
    try {
        const hashedToken = crypto.createHash('sha256').update(req.body.token).digest('hex');
        const user = await User.findOne({ resetPasswordToken: hashedToken, resetPasswordExpire: { $gt: Date.now() } });
        if (!user) return res.status(400).json({ message: 'Invalid or expired token' });

        user.password = req.body.password;
        user.resetPasswordToken = undefined;
        user.resetPasswordExpire = undefined;
        await user.save();

        res.json({ message: 'Password reset successful' });
    } catch (error) { next(error); }
};
