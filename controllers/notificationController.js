const Notification = require('../models/Notification');

// @desc Get my notifications
exports.getNotifications = async (req, res, next) => {
    try {
        const { page = 1, limit = 20 } = req.query;
        const notifications = await Notification.find({ user: req.user._id })
            .sort('-createdAt')
            .skip((page - 1) * limit)
            .limit(parseInt(limit));
        const unreadCount = await Notification.countDocuments({ user: req.user._id, read: false });
        const total = await Notification.countDocuments({ user: req.user._id });
        res.json({ notifications, unreadCount, total, page: parseInt(page), pages: Math.ceil(total / limit) });
    } catch (error) { next(error); }
};

// @desc Mark notification as read
exports.markRead = async (req, res, next) => {
    try {
        const notification = await Notification.findByIdAndUpdate(req.params.id, { read: true }, { new: true });
        if (!notification) return res.status(404).json({ message: 'Notification not found' });
        res.json(notification);
    } catch (error) { next(error); }
};

// @desc Mark all as read
exports.markAllRead = async (req, res, next) => {
    try {
        await Notification.updateMany({ user: req.user._id, read: false }, { read: true });
        res.json({ message: 'All notifications marked as read' });
    } catch (error) { next(error); }
};

// @desc Create announcement (instructor/admin)
exports.createAnnouncement = async (req, res, next) => {
    try {
        const { userIds, title, message, link } = req.body;
        const notifications = await Promise.all(userIds.map(userId =>
            Notification.create({ user: userId, title, message, type: 'announcement', link })
        ));
        res.status(201).json({ count: notifications.length });
    } catch (error) { next(error); }
};
