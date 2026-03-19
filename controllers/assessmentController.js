const Assessment = require('../models/Assessment');
const Submission = require('../models/Submission');
const Course = require('../models/Course');
const Notification = require('../models/Notification');

// @desc Create assessment
exports.createAssessment = async (req, res, next) => {
    try {
        req.body.createdBy = req.user._id;
        const assessment = await Assessment.create(req.body);
        res.status(201).json(assessment);
    } catch (error) { next(error); }
};

// @desc Get assessments for course
exports.getAssessments = async (req, res, next) => {
    try {
        const assessments = await Assessment.find({ course: req.params.courseId }).sort('-createdAt');
        res.json(assessments);
    } catch (error) { next(error); }
};

// @desc Get single assessment
exports.getAssessment = async (req, res, next) => {
    try {
        const assessment = await Assessment.findById(req.params.id).populate('createdBy', 'name');
        if (!assessment) return res.status(404).json({ message: 'Assessment not found' });

        // Hide correct answers for students
        if (req.user.role === 'student') {
            const cleaned = assessment.toObject();
            if (cleaned.questions) {
                cleaned.questions = cleaned.questions.map(q => ({ ...q, correctAnswer: undefined }));
            }
            return res.json(cleaned);
        }
        res.json(assessment);
    } catch (error) { next(error); }
};

// @desc Update assessment
exports.updateAssessment = async (req, res, next) => {
    try {
        const assessment = await Assessment.findByIdAndUpdate(req.params.id, req.body, { new: true, runValidators: true });
        if (!assessment) return res.status(404).json({ message: 'Assessment not found' });
        res.json(assessment);
    } catch (error) { next(error); }
};

// @desc Delete assessment
exports.deleteAssessment = async (req, res, next) => {
    try {
        await Assessment.findByIdAndDelete(req.params.id);
        await Submission.deleteMany({ assessment: req.params.id });
        res.json({ message: 'Assessment removed' });
    } catch (error) { next(error); }
};

// @desc Submit assessment
exports.submitAssessment = async (req, res, next) => {
    try {
        const assessment = await Assessment.findById(req.params.id);
        if (!assessment) return res.status(404).json({ message: 'Assessment not found' });

        const existing = await Submission.findOne({ assessment: req.params.id, student: req.user._id });
        if (existing) return res.status(400).json({ message: 'Already submitted' });

        const submissionData = {
            assessment: req.params.id, student: req.user._id,
            answers: req.body.answers || [],
            textContent: req.body.textContent || ''
        };
        if (req.file) submissionData.fileUrl = `/uploads/submissions/${req.file.filename}`;

        // Auto-grade quizzes
        let autoGrade = null;
        if (assessment.type === 'quiz' && assessment.questions && assessment.questions.length > 0) {
            let correct = 0;
            let totalPts = 0;
            assessment.questions.forEach((q, i) => {
                const pts = q.points || 1;
                totalPts += pts;
                const studentAns = submissionData.answers.find(a => a.questionIndex === i);
                if (studentAns && studentAns.answer.toLowerCase().trim() === q.correctAnswer.toLowerCase().trim()) {
                    correct += pts;
                }
            });
            autoGrade = Math.round((correct / totalPts) * assessment.totalPoints);
            submissionData.grade = autoGrade;
            submissionData.status = 'graded';
            submissionData.feedback = `Auto-graded: ${correct}/${totalPts} points`;
        }

        const submission = await Submission.create(submissionData);

        await Notification.create({
            user: assessment.createdBy,
            title: 'New Submission',
            message: `${req.user.name} submitted "${assessment.title}"`,
            type: 'assessment', link: `/assessments/${assessment._id}/submissions`
        });

        if (autoGrade !== null) {
            await Notification.create({
                user: req.user._id,
                title: 'Quiz Graded',
                message: `Your quiz "${assessment.title}" scored ${autoGrade}/${assessment.totalPoints}`,
                type: 'grade'
            });
        }

        res.status(201).json(submission);
    } catch (error) { next(error); }
};

// @desc Get submissions for assessment
exports.getSubmissions = async (req, res, next) => {
    try {
        const submissions = await Submission.find({ assessment: req.params.id })
            .populate('student', 'name email avatar')
            .sort('-submittedAt');
        res.json(submissions);
    } catch (error) { next(error); }
};

// @desc Grade submission
exports.gradeSubmission = async (req, res, next) => {
    try {
        const { grade, feedback } = req.body;
        const submission = await Submission.findByIdAndUpdate(req.params.submissionId, {
            grade, feedback, gradedBy: req.user._id, gradedAt: new Date(), status: 'graded'
        }, { new: true }).populate('student', 'name email');

        if (!submission) return res.status(404).json({ message: 'Submission not found' });

        const assessment = await Assessment.findById(submission.assessment);
        await Notification.create({
            user: submission.student._id,
            title: 'Grade Posted',
            message: `You received ${grade}/${assessment.totalPoints} on "${assessment.title}"`,
            type: 'grade'
        });

        res.json(submission);
    } catch (error) { next(error); }
};

// @desc Get student gradebook
exports.getGradebook = async (req, res, next) => {
    try {
        const studentId = req.params.studentId || req.user._id;
        const assessments = await Assessment.find({ course: req.params.courseId });
        const submissions = await Submission.find({
            assessment: { $in: assessments.map(a => a._id) },
            student: studentId
        });

        const gradebook = assessments.map(a => {
            const sub = submissions.find(s => s.assessment.toString() === a._id.toString());
            return {
                assessment: { _id: a._id, title: a.title, type: a.type, totalPoints: a.totalPoints, dueDate: a.dueDate },
                submission: sub || null
            };
        });

        const totalPoints = assessments.reduce((sum, a) => sum + a.totalPoints, 0);
        const earnedPoints = submissions.filter(s => s.grade !== null).reduce((sum, s) => sum + s.grade, 0);

        res.json({ gradebook, totalPoints, earnedPoints, percentage: totalPoints > 0 ? Math.round((earnedPoints / totalPoints) * 100) : 0 });
    } catch (error) { next(error); }
};
