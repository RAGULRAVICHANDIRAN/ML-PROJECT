'use server'

import { auth } from "@/auth"
import { prisma } from "@/lib/prisma" // Need to ensure singleton prisma
import { sendSMSNotification } from "@/lib/sms"
import { revalidatePath } from "next/cache"

// Singleton prisma pattern - already imported above
// import { PrismaClient } from "@prisma/client"
// const globalForPrisma = globalThis as unknown as { prisma: PrismaClient }
// const db = globalForPrisma.prisma || new PrismaClient()
// if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = db

export async function saveAttendance(classId: string, date: Date, period: number, attendanceData: Record<string, string>) {
    const session = await auth()
    if (!session?.user) throw new Error("Unauthorized")

    const recorderId = session.user.id

    // Use transaction
    await prisma.$transaction(async (tx) => {
        for (const [studentId, status] of Object.entries(attendanceData)) {
            await tx.attendance.upsert({
                where: {
                    studentId_date_period: {
                        studentId,
                        date,
                        period
                    }
                },
                update: { status, recorderId: recorderId! },
                create: {
                    studentId,
                    date,
                    period,
                    status,
                    recorderId: recorderId!
                }
            })

            if (status === 'ABSENT') {
                const student = await tx.user.findUnique({ where: { id: studentId }, include: { profile: true } })
                if (student) {
                    // Mock SMS
                    await sendSMSNotification(student.name, student.profile?.phone ?? null)
                }
            }
        }
    })

    revalidatePath(`/dashboard/staff/attendance/${classId}`)
    return { success: true }
}

export async function getAttendance(classId: string, date: Date, period: number) {
    const session = await auth()
    if (!session?.user) throw new Error("Unauthorized")

    // Ensure date is start of day for consistent querying if stored as DateTime
    // But since schema uses DateTime, we should match exactly or range.
    // The saveAttendance uses the exact date object passed.
    // Let's assume the client passes the same "start of day" date object.

    const records = await prisma.attendance.findMany({
        where: {
            student: {
                studentClassId: classId
            },
            date: date,
            period: period
        },
        select: {
            studentId: true,
            status: true
        }
    })

    const attendanceMap: Record<string, string> = {}
    records.forEach(r => {
        attendanceMap[r.studentId] = r.status
    })

    return attendanceMap
}
