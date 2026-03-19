const Certificate = require('../models/Certificate');
const Course = require('../models/Course');
const User = require('../models/User');
const Enrollment = require('../models/Enrollment');
const Notification = require('../models/Notification');
const generateCertificatePDF = require('../utils/generateCertificate');
const { v4: uuidv4 } = require('uuid');

// @desc Generate certificate
exports.generateCertificate = async (req, res, next) => {
    try {
        const { courseId, studentId } = req.body;
        const course = await Course.findById(courseId).populate('instructor', 'name');
        const student = await User.findById(studentId);
        if (!course || !student) return res.status(404).json({ message: 'Course or student not found' });

        const existing = await Certificate.findOne({ course: courseId, student: studentId });
        if (existing) return res.status(400).json({ message: 'Certificate already issued', certificate: existing });

        const certificateId = uuidv4().split('-')[0].toUpperCase() + '-' + uuidv4().split('-')[1].toUpperCase();
        const fileUrl = await generateCertificatePDF({
            studentName: student.name, courseName: course.title,
            completionDate: new Date(), certificateId,
            instructorName: course.instructor.name
        });

        const certificate = await Certificate.create({
            student: studentId, course: courseId, certificateId, fileUrl, issuedBy: req.user._id
        });

        // Mark enrollment as completed
        await Enrollment.findOneAndUpdate(
            { course: courseId, student: studentId },
            { status: 'completed', completedAt: new Date(), progress: 100 }
        );

        await Notification.create({
            user: studentId, title: 'Certificate Earned!',
            message: `You have earned a certificate for "${course.title}"`,
            type: 'certificate', link: '/certificates'
        });

        res.status(201).json(certificate);
    } catch (error) { next(error); }
};

// @desc Get my certificates
exports.getMyCertificates = async (req, res, next) => {
    try {
        const certificates = await Certificate.find({ student: req.user._id, revoked: false })
            .populate('course', 'title category thumbnail')
            .populate('issuedBy', 'name')
            .sort('-issueDate');
        res.json(certificates);
    } catch (error) { next(error); }
};

// @desc Get all certificates (admin)
exports.getAllCertificates = async (req, res, next) => {
    try {
        const certificates = await Certificate.find()
            .populate('student', 'name email')
            .populate('course', 'title')
            .sort('-issueDate');
        res.json(certificates);
    } catch (error) { next(error); }
};

// @desc Verify certificate
exports.verifyCertificate = async (req, res, next) => {
    try {
        const certificate = await Certificate.findOne({ certificateId: req.params.certId })
            .populate('student', 'name email')
            .populate('course', 'title category');
        if (!certificate) return res.status(404).json({ message: 'Certificate not found', valid: false });
        res.json({ valid: !certificate.revoked, certificate });
    } catch (error) { next(error); }
};

// @desc Revoke certificate
exports.revokeCertificate = async (req, res, next) => {
    try {
        const certificate = await Certificate.findByIdAndUpdate(req.params.id, { revoked: true }, { new: true });
        if (!certificate) return res.status(404).json({ message: 'Certificate not found' });
        res.json(certificate);
    } catch (error) { next(error); }
};
