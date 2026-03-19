const Session = require('../models/Session');
const Attendance = require('../models/Attendance');
const Enrollment = require('../models/Enrollment');
const Course = require('../models/Course');
const Notification = require('../models/Notification');

// @desc Create session
exports.createSession = async (req, res, next) => {
    try {
        req.body.course = req.params.courseId;
        const session = await Session.create(req.body);
        res.status(201).json(session);
    } catch (error) { next(error); }
};

// @desc Get sessions for course
exports.getSessions = async (req, res, next) => {
    try {
        const sessions = await Session.find({ course: req.params.courseId }).sort('date');
        res.json(sessions);
    } catch (error) { next(error); }
};

// @desc Update session
exports.updateSession = async (req, res, next) => {
    try {
        const session = await Session.findByIdAndUpdate(req.params.id, req.body, { new: true });
        if (!session) return res.status(404).json({ message: 'Session not found' });
        res.json(session);
    } catch (error) { next(error); }
};

// @desc Delete session
exports.deleteSession = async (req, res, next) => {
    try {
        await Session.findByIdAndDelete(req.params.id);
        await Attendance.deleteMany({ session: req.params.id });
        res.json({ message: 'Session removed' });
    } catch (error) { next(error); }
};

// @desc Mark attendance (bulk)
exports.markAttendance = async (req, res, next) => {
    try {
        const { sessionId, records } = req.body;
        // records: [{ studentId, status }]
        const results = await Promise.all(records.map(async (r) => {
            return Attendance.findOneAndUpdate(
                { session: sessionId, student: r.studentId },
                { status: r.status, markedBy: req.user._id },
                { upsert: true, new: true, setDefaultsOnInsert: true }
            );
        }));
        res.json(results);
    } catch (error) { next(error); }
};

// @desc Get attendance for session
exports.getSessionAttendance = async (req, res, next) => {
    try {
        const attendance = await Attendance.find({ session: req.params.sessionId })
            .populate('student', 'name email avatar');
        res.json(attendance);
    } catch (error) { next(error); }
};

// @desc Get student attendance for a course
exports.getStudentAttendance = async (req, res, next) => {
    try {
        const sessions = await Session.find({ course: req.params.courseId });
        const sessionIds = sessions.map(s => s._id);
        const studentId = req.params.studentId || req.user._id;

        const attendance = await Attendance.find({
            session: { $in: sessionIds }, student: studentId
        }).populate('session', 'title date startTime');

        const totalSessions = sessions.length;
        const presentCount = attendance.filter(a => a.status === 'present').length;
        const lateCount = attendance.filter(a => a.status === 'late').length;
        const absentCount = totalSessions - presentCount - lateCount;

        res.json({
            attendance, totalSessions, presentCount, lateCount, absentCount,
            percentage: totalSessions > 0 ? Math.round(((presentCount + lateCount * 0.5) / totalSessions) * 100) : 0
        });
    } catch (error) { next(error); }
};

// @desc Get attendance report for course
exports.getAttendanceReport = async (req, res, next) => {
    try {
        const sessions = await Session.find({ course: req.params.courseId }).sort('date');
        const enrollments = await Enrollment.find({ course: req.params.courseId, status: 'active' })
            .populate('student', 'name email avatar');

        const report = await Promise.all(enrollments.map(async (en) => {
            const sessionIds = sessions.map(s => s._id);
            const att = await Attendance.find({ session: { $in: sessionIds }, student: en.student._id });
            const present = att.filter(a => a.status === 'present').length;
            const late = att.filter(a => a.status === 'late').length;
            return {
                student: en.student, present, late,
                absent: sessions.length - present - late,
                percentage: sessions.length > 0 ? Math.round(((present + late * 0.5) / sessions.length) * 100) : 0
            };
        }));

        res.json({ sessions: sessions.length, report });
    } catch (error) { next(error); }
};
