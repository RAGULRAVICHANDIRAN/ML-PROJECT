'use server'

import { auth } from "@/auth"
import { prisma } from "@/lib/prisma"
import { revalidatePath } from "next/cache"

export async function logClass(classId: string, date: Date, period: number) {
    const session = await auth()
    if (!session?.user || session.user.role !== 'STAFF') throw new Error("Unauthorized")

    const teacherId = session.user.id

    // Check for schema mismatch
    if (!(prisma as any).teachingLog) {
        throw new Error("System update required. Please restart the server.")
    }

    // Check if already logged
    const existing = await (prisma as any).teachingLog.findUnique({
        where: {
            teacherId_date_period: {
                teacherId,
                date,
                period
            }
        }
    })

    if (existing) {
        throw new Error("You have already logged a class for this date and period.")
    }

    await (prisma as any).teachingLog.create({
        data: {
            teacherId,
            classId,
            date,
            period
        }
    })

    revalidatePath('/dashboard/staff/my-logs')
    return { success: true }
}

export async function getTeachingLogs() {
    const session = await auth()
    if (!session?.user) throw new Error("Unauthorized")

    // Check for schema mismatch
    if (!(prisma as any).teachingLog) {
        return []
    }

    const logs = await (prisma as any).teachingLog.findMany({
        where: {
            teacherId: session.user.id
        },
        include: {
            class: true
        },
        orderBy: {
            date: 'desc'
        }
    })

    return logs
}
