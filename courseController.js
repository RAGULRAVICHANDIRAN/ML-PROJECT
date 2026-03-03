const Course = require('../models/Course');
const Module = require('../models/Module');
const Enrollment = require('../models/Enrollment');
const Notification = require('../models/Notification');

// @desc Create course
exports.createCourse = async (req, res, next) => {
    try {
        req.body.instructor = req.user._id;
        if (req.file) req.body.thumbnail = `/uploads/thumbnails/${req.file.filename}`;
        const course = await Course.create(req.body);
        res.status(201).json(course);
    } catch (error) { next(error); }
};

// @desc Get all courses / catalog
exports.getCourses = async (req, res, next) => {
    try {
        const { page = 1, limit = 12, category, search, instructor, status = 'active', sort = '-createdAt' } = req.query;
        const query = {};
        if (status) query.status = status;
        if (category) query.category = category;
        if (instructor) query.instructor = instructor;
        if (search) query.$or = [
            { title: { $regex: search, $options: 'i' } },
            { description: { $regex: search, $options: 'i' } },
            { category: { $regex: search, $options: 'i' } }
        ];

        const courses = await Course.find(query)
            .populate('instructor', 'name email avatar')
            .sort(sort)
            .skip((page - 1) * limit)
            .limit(parseInt(limit));

        const total = await Course.countDocuments(query);
        const categories = await Course.distinct('category');

        res.json({ courses, total, page: parseInt(page), pages: Math.ceil(total / limit), categories });
    } catch (error) { next(error); }
};

// @desc Get single course
exports.getCourse = async (req, res, next) => {
    try {
        const course = await Course.findById(req.params.id)
            .populate('instructor', 'name email avatar bio');
        if (!course) return res.status(404).json({ message: 'Course not found' });

        const modules = await Module.find({ course: course._id }).sort('order');
        const enrollmentCount = await Enrollment.countDocuments({ course: course._id, status: 'active' });

        let userEnrollment = null;
        if (req.user) {
            userEnrollment = await Enrollment.findOne({ course: course._id, student: req.user._id });
        }

        res.json({ ...course.toObject(), modules, enrollmentCount, userEnrollment });
    } catch (error) { next(error); }
};

// @desc Update course
exports.updateCourse = async (req, res, next) => {
    try {
        if (req.file) req.body.thumbnail = `/uploads/thumbnails/${req.file.filename}`;
        let course = await Course.findById(req.params.id);
        if (!course) return res.status(404).json({ message: 'Course not found' });
        if (course.instructor.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
            return res.status(403).json({ message: 'Not authorized to update this course' });
        }
        course = await Course.findByIdAndUpdate(req.params.id, req.body, { new: true, runValidators: true });
        res.json(course);
    } catch (error) { next(error); }
};

// @desc Delete course
exports.deleteCourse = async (req, res, next) => {
    try {
        const course = await Course.findById(req.params.id);
        if (!course) return res.status(404).json({ message: 'Course not found' });
        if (course.instructor.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
            return res.status(403).json({ message: 'Not authorized to delete this course' });
        }
        await Course.findByIdAndDelete(req.params.id);
        await Module.deleteMany({ course: req.params.id });
        res.json({ message: 'Course removed' });
    } catch (error) { next(error); }
};

// @desc Enroll in course
exports.enrollCourse = async (req, res, next) => {
    try {
        const course = await Course.findById(req.params.id);
        if (!course) return res.status(404).json({ message: 'Course not found' });

        const existing = await Enrollment.findOne({ course: course._id, student: req.user._id });
        if (existing) return res.status(400).json({ message: 'Already enrolled in this course' });

        const enrollmentCount = await Enrollment.countDocuments({ course: course._id, status: 'active' });
        if (course.capacity && enrollmentCount >= course.capacity) {
            return res.status(400).json({ message: 'Course is at full capacity' });
        }

        const status = course.enrollmentType === 'restricted' ? 'pending' : 'active';
        const enrollment = await Enrollment.create({ course: course._id, student: req.user._id, status });

        await Notification.create({
            user: req.user._id, title: 'Enrollment Confirmation',
            message: `You have been enrolled in "${course.title}"`, type: 'enrollment',
            link: `/courses/${course._id}`
        });

        await Notification.create({
            user: course.instructor, title: 'New Enrollment',
            message: `${req.user.name} has enrolled in "${course.title}"`, type: 'enrollment',
            link: `/courses/${course._id}/students`
        });

        res.status(201).json(enrollment);
    } catch (error) { next(error); }
};

// @desc Get enrolled students
exports.getCourseStudents = async (req, res, next) => {
    try {
        const enrollments = await Enrollment.find({ course: req.params.id })
            .populate('student', 'name email avatar')
            .sort('-enrolledAt');
        res.json(enrollments);
    } catch (error) { next(error); }
};

// @desc Update enrollment status
exports.updateEnrollment = async (req, res, next) => {
    try {
        const enrollment = await Enrollment.findByIdAndUpdate(req.params.enrollmentId, { status: req.body.status }, { new: true });
        if (!enrollment) return res.status(404).json({ message: 'Enrollment not found' });
        res.json(enrollment);
    } catch (error) { next(error); }
};

// @desc Get my enrolled courses (student)
exports.getMyEnrollments = async (req, res, next) => {
    try {
        const enrollments = await Enrollment.find({ student: req.user._id })
            .populate({ path: 'course', populate: { path: 'instructor', select: 'name avatar' } })
            .sort('-enrolledAt');
        res.json(enrollments);
    } catch (error) { next(error); }
};

// @desc Get instructor's courses
exports.getInstructorCourses = async (req, res, next) => {
    try {
        const courses = await Course.find({ instructor: req.user._id }).sort('-createdAt');
        const coursesWithStats = await Promise.all(courses.map(async (c) => {
            const enrollmentCount = await Enrollment.countDocuments({ course: c._id, status: 'active' });
            const completedCount = await Enrollment.countDocuments({ course: c._id, status: 'completed' });
            return { ...c.toObject(), enrollmentCount, completedCount };
        }));
        res.json(coursesWithStats);
    } catch (error) { next(error); }
};
