'use server'

import { auth } from "@/auth"
import { prisma } from "@/lib/prisma"
import { revalidatePath } from "next/cache"
import { redirect } from "next/navigation"

export async function createClass(prevState: any, formData: FormData) {
    const session = await auth()
    if (!session?.user || session.user.role !== 'HOD') {
        return { error: "Unauthorized" }
    }

    // We need to fetch the user's department to know where to create the class
    const user = await prisma.user.findUnique({
        where: { email: session.user.email! },
        include: { managedDepartment: true }
    })

    if (!user?.managedDepartment) {
        return { error: "No department assigned to manage." }
    }

    const name = formData.get('name') as string
    const batch = formData.get('batch') as string

    if (!name || !batch) {
        return { error: "Missing required fields" }
    }

    try {
        await prisma.class.create({
            data: {
                name,
                batch,
                departmentId: user.managedDepartment.id
            }
        })
    } catch (error) {
        console.error("Failed to create class:", error)
        return { error: "Failed to create class. Name might be duplicate." }
    }

    revalidatePath('/dashboard/hod/classes')
    redirect('/dashboard/hod/classes')
}

export async function updateClass(prevState: any, formData: FormData) {
    const session = await auth()
    if (!session?.user || session.user.role !== 'HOD') {
        return { error: "Unauthorized" }
    }

    const classId = formData.get('classId') as string
    const name = formData.get('name') as string
    const batch = formData.get('batch') as string

    if (!classId || !name || !batch) {
        return { error: "Missing required fields" }
    }

    try {
        await prisma.class.update({
            where: { id: classId },
            data: { name, batch }
        })
    } catch (error) {
        console.error("Failed to update class:", error)
        return { error: "Failed to update class. Name might be duplicate." }
    }

    revalidatePath(`/dashboard/hod/classes/${classId}`)
    redirect(`/dashboard/hod/classes/${classId}`)
}
