'use server'

import { auth } from "@/auth"
import { prisma } from "@/lib/prisma"
import { revalidatePath } from "next/cache"

export async function saveTimetableEntry(
    classId: string,
    day: string,
    period: number,
    subjectId: string,
    teacherId: string
) {
    const session = await auth()
    if (!session?.user || !['PRINCIPAL', 'VP', 'HOD'].includes(session.user.role)) {
        return { error: "Unauthorized" }
    }

    if (!classId || !day || !period || !subjectId || !teacherId) {
        return { error: "All fields are required" }
    }

    try {
        await prisma.timetable.upsert({
            where: {
                classId_day_period: {
                    classId,
                    day,
                    period
                }
            },
            update: {
                subjectId,
                teacherId
            },
            create: {
                classId,
                day,
                period,
                subjectId,
                teacherId
            }
        })
        revalidatePath(`/dashboard/hod/classes/${classId}/timetable`)
        return { success: true }
    } catch (error) {
        console.error("Failed to save timetable entry:", error)
        return { error: "Failed to save entry. Teacher might be busy." }
    }
}

export async function clearTimetableEntry(classId: string, day: string, period: number) {
    const session = await auth()
    if (!session?.user || !['PRINCIPAL', 'VP', 'HOD'].includes(session.user.role)) {
        return { error: "Unauthorized" }
    }

    try {
        await prisma.timetable.delete({
            where: {
                classId_day_period: {
                    classId,
                    day,
                    period
                }
            }
        })
        revalidatePath(`/dashboard/hod/classes/${classId}/timetable`)
        return { success: true }
    } catch (error) {
        // Record might not exist, which is fine
        return { success: true }
    }
}
