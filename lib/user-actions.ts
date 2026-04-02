'use server'

import { auth } from "@/auth"
import { prisma } from "@/lib/prisma"
import { revalidatePath } from "next/cache"
import { redirect } from "next/navigation"
import bcrypt from "bcryptjs"

export async function createUser(prevState: any, formData: FormData) {
    const session = await auth()
    if (!session?.user || session.user.role !== 'HOD') {
        return { error: "Unauthorized" }
    }

    const user = await prisma.user.findUnique({
        where: { email: session.user.email! },
        include: { managedDepartment: true }
    })

    if (!user?.managedDepartment) {
        return { error: "No department assigned to manage." }
    }

    const name = formData.get('name') as string
    const email = formData.get('email') as string
    const role = formData.get('role') as string // STAFF or STUDENT
    const password = formData.get('password') as string || 'password123'
    const classId = formData.get('classId') as string // Optional, for students

    if (!name || !email || !role) {
        return { error: "Missing required fields" }
    }

    const hashedPassword = await bcrypt.hash(password, 10)

    try {
        await prisma.user.create({
            data: {
                name,
                email,
                password: hashedPassword,
                role: role as any,
                ...(role === 'STUDENT' && classId ? { studentClassId: classId } : {}),
                ...(role === 'STAFF' && user.managedDepartment ? { departmentId: user.managedDepartment.id } : {}),
            }
        })
    } catch (error) {
        console.error("Failed to create user:", error)
        return { error: "Failed to create user. Email might be duplicate." }
    }

    if (role === 'STAFF') {
        revalidatePath('/dashboard/hod/staff')
        redirect('/dashboard/hod/staff')
    } else {
        revalidatePath('/dashboard/hod/students')
        redirect('/dashboard/hod/students')
    }
}

export async function assignAdvisor(classId: string, staffId: string) {
    const session = await auth()
    if (!session?.user || session.user.role !== 'HOD') {
        throw new Error("Unauthorized")
    }

    try {
        await prisma.class.update({
            where: { id: classId },
            data: { advisorId: staffId }
        })
        revalidatePath(`/dashboard/hod/classes/${classId}`)
        revalidatePath('/dashboard/hod/staff')
    } catch (error) {
        console.error("Failed to assign advisor:", error)
        throw new Error("Failed to assign advisor")
    }
}

export async function updateUser(prevState: any, formData: FormData) {
    const session = await auth()
    if (!session?.user || session.user.role !== 'HOD') {
        return { error: "Unauthorized" }
    }

    const userId = formData.get('userId') as string
    const name = formData.get('name') as string
    const email = formData.get('email') as string
    const role = formData.get('role') as string

    if (!userId || !name || !email) {
        return { error: "Missing required fields" }
    }

    try {
        await prisma.user.update({
            where: { id: userId },
            data: { name, email }
        })
    } catch (error) {
        console.error("Failed to update user:", error)
        return { error: "Failed to update user. Email might be in use." }
    }

    if (role === 'STAFF') {
        revalidatePath('/dashboard/hod/staff')
        redirect('/dashboard/hod/staff')
    } else {
        revalidatePath('/dashboard/hod/students')
        redirect('/dashboard/hod/students')
    }
}

export async function unassignAdvisor(classId: string) {
    const session = await auth()
    if (!session?.user || session.user.role !== 'HOD') {
        throw new Error("Unauthorized")
    }

    try {
        await prisma.class.update({
            where: { id: classId },
            data: { advisorId: null }
        })
        revalidatePath('/dashboard/hod/staff')
    } catch (error) {
        console.error("Failed to unassign advisor:", error)
        throw new Error("Failed to unassign advisor")
    }
}
