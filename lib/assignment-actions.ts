'use server'

import { auth } from "@/auth"
import { prisma } from "@/lib/prisma"
import { revalidatePath } from "next/cache"
import { redirect } from "next/navigation"

export async function createAssignment(classId: string, formData: FormData) {
    const session = await auth()
    if (!session?.user) throw new Error("Unauthorized")

    const title = formData.get('title') as string
    const description = formData.get('description') as string
    const dueDateStr = formData.get('dueDate') as string

    if (!title || !dueDateStr) {
        throw new Error("Missing required fields")
    }

    const dueDate = new Date(dueDateStr)

    try {
        await prisma.assignment.create({
            data: {
                title,
                description,
                dueDate,
                classId,
            }
        })
    } catch (error) {
        console.error("Failed to create assignment:", error)
        return { error: "Failed to create assignment" }
    }

    revalidatePath(`/dashboard/staff/assignments/${classId}`)
    redirect(`/dashboard/staff/assignments/${classId}`)
}
