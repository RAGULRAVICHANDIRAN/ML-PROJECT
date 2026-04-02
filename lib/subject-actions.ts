'use server'

import { auth } from "@/auth"
import { prisma } from "@/lib/prisma"
import { revalidatePath } from "next/cache"

export async function createSubject(prevState: any, formData: FormData) {
    const session = await auth()
    if (!session?.user || !['PRINCIPAL', 'VP', 'HOD'].includes(session.user.role)) {
        return { error: "Unauthorized" }
    }

    const name = formData.get('name') as string
    const code = formData.get('code') as string

    if (!name || !code) {
        return { error: "Name and Code are required" }
    }

    // Get department from user
    const user = await prisma.user.findUnique({
        where: { email: session.user.email! },
        include: { managedDepartment: true }
    })

    if (!user?.managedDepartment) {
        return { error: "No department assigned to manage." }
    }

    try {
        await prisma.subject.create({
            data: {
                name,
                code,
                departmentId: user.managedDepartment.id
            }
        })
        revalidatePath('/dashboard/hod/subjects')
        return { message: "Subject created successfully" }
    } catch (error) {
        console.error("Failed to create subject:", error)
        return { error: "Failed to create subject. Code might be duplicate." }
    }
}

export async function deleteSubject(subjectId: string) {
    const session = await auth()
    if (!session?.user || !['PRINCIPAL', 'VP', 'HOD'].includes(session.user.role)) {
        return { error: "Unauthorized" }
    }

    try {
        await prisma.subject.delete({
            where: { id: subjectId }
        })
        revalidatePath('/dashboard/hod/subjects')
    } catch (error) {
        console.error("Failed to delete subject:", error)
        return { error: "Failed to delete subject." }
    }
}
