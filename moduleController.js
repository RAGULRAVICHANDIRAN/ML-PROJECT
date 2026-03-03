const Module = require('../models/Module');
const Course = require('../models/Course');

// @desc Create module
exports.createModule = async (req, res, next) => {
    try {
        const course = await Course.findById(req.params.courseId);
        if (!course) return res.status(404).json({ message: 'Course not found' });
        if (course.instructor.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
            return res.status(403).json({ message: 'Not authorized' });
        }
        req.body.course = req.params.courseId;
        const moduleCount = await Module.countDocuments({ course: req.params.courseId });
        if (!req.body.order) req.body.order = moduleCount;
        const mod = await Module.create(req.body);
        res.status(201).json(mod);
    } catch (error) { next(error); }
};

// @desc Get modules for course
exports.getModules = async (req, res, next) => {
    try {
        const modules = await Module.find({ course: req.params.courseId }).sort('order');
        res.json(modules);
    } catch (error) { next(error); }
};

// @desc Update module
exports.updateModule = async (req, res, next) => {
    try {
        const mod = await Module.findByIdAndUpdate(req.params.id, req.body, { new: true, runValidators: true });
        if (!mod) return res.status(404).json({ message: 'Module not found' });
        res.json(mod);
    } catch (error) { next(error); }
};

// @desc Delete module
exports.deleteModule = async (req, res, next) => {
    try {
        const mod = await Module.findByIdAndDelete(req.params.id);
        if (!mod) return res.status(404).json({ message: 'Module not found' });
        res.json({ message: 'Module removed' });
    } catch (error) { next(error); }
};
