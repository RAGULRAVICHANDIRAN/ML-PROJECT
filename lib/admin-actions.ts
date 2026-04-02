'use server'

import { auth } from "@/auth"
import { prisma } from "@/lib/prisma"
import { revalidatePath } from "next/cache"
import bcrypt from "bcryptjs"

// ========== HELPER ==========
async function requirePrincipal() {
    const session = await auth()
    if (!session?.user || session.user.role !== 'PRINCIPAL') {
        throw new Error("Unauthorized: Only PRINCIPAL can perform this action")
    }
    return session
}

// ========== DEPARTMENT ACTIONS ==========

export async function createDepartment(prevState: any, formData: FormData) {
    try {
        await requirePrincipal()

        const name = formData.get('name') as string
        const code = formData.get('code') as string
        const hodId = formData.get('hodId') as string

        if (!name || !code) {
            return { error: "Department name and code are required." }
        }

        await prisma.department.create({
            data: {
                name,
                code: code.toUpperCase(),
                ...(hodId ? { hodId } : {}),
            }
        })

        revalidatePath('/dashboard/admin/departments')
        return { success: "Department created successfully!" }
    } catch (error: any) {
        console.error("Failed to create department:", error)
        if (error.code === 'P2002') {
            return { error: "A department with this name or code already exists." }
        }
        return { error: error.message || "Failed to create department." }
    }
}

export async function updateDepartment(prevState: any, formData: FormData) {
    try {
        await requirePrincipal()

        const id = formData.get('id') as string
        const name = formData.get('name') as string
        const code = formData.get('code') as string
        const hodId = formData.get('hodId') as string

        if (!id || !name || !code) {
            return { error: "Department ID, name, and code are required." }
        }

        await prisma.department.update({
            where: { id },
            data: {
                name,
                code: code.toUpperCase(),
                hodId: hodId || null,
            }
        })

        revalidatePath('/dashboard/admin/departments')
        return { success: "Department updated successfully!" }
    } catch (error: any) {
        console.error("Failed to update department:", error)
        if (error.code === 'P2002') {
            return { error: "A department with this name or code already exists." }
        }
        return { error: error.message || "Failed to update department." }
    }
}

export async function deleteDepartment(id: string) {
    try {
        await requirePrincipal()

        // Check for related data
        const dept = await prisma.department.findUnique({
            where: { id },
            include: {
                _count: { select: { staff: true, classes: true, subjects: true } }
            }
        })

        if (!dept) return { error: "Department not found." }

        if (dept._count.staff > 0 || dept._count.classes > 0) {
            return { error: `Cannot delete: department has ${dept._count.staff} staff and ${dept._count.classes} classes. Remove them first.` }
        }

        // Delete related subjects first
        await prisma.subject.deleteMany({ where: { departmentId: id } })

        await prisma.department.delete({ where: { id } })

        revalidatePath('/dashboard/admin/departments')
        return { success: "Department deleted successfully!" }
    } catch (error: any) {
        console.error("Failed to delete department:", error)
        return { error: error.message || "Failed to delete department." }
    }
}

// ========== STAFF ACTIONS (Principal level) ==========

export async function createStaff(prevState: any, formData: FormData) {
    try {
        await requirePrincipal()

        const name = formData.get('name') as string
        const email = formData.get('email') as string
        const password = (formData.get('password') as string) || 'password123'
        const role = (formData.get('role') as string) || 'STAFF'
        const departmentId = formData.get('departmentId') as string

        if (!name || !email) {
            return { error: "Name and email are required." }
        }

        const hashedPassword = await bcrypt.hash(password, 10)

        const data: any = {
            name,
            email,
            password: hashedPassword,
            role,
        }

        if (departmentId) {
            data.departmentId = departmentId
        }

        const newUser = await prisma.user.create({ data })

        // If creating as HOD and department selected, assign as HOD
        if (role === 'HOD' && departmentId) {
            await prisma.department.update({
                where: { id: departmentId },
                data: { hodId: newUser.id }
            })
        }

        revalidatePath('/dashboard/admin/staff')
        revalidatePath('/dashboard/admin/departments')
        revalidatePath('/dashboard/admin')
        return { success: `${role === 'HOD' ? 'HOD' : 'Staff member'} created successfully!` }
    } catch (error: any) {
        console.error("Failed to create staff:", error)
        if (error.code === 'P2002') {
            return { error: "A user with this email already exists." }
        }
        return { error: error.message || "Failed to create staff member." }
    }
}

export async function updateStaff(prevState: any, formData: FormData) {
    try {
        await requirePrincipal()

        const id = formData.get('id') as string
        const name = formData.get('name') as string
        const email = formData.get('email') as string
        const departmentId = formData.get('departmentId') as string

        if (!id || !name || !email) {
            return { error: "ID, name, and email are required." }
        }

        await prisma.user.update({
            where: { id },
            data: {
                name,
                email,
                departmentId: departmentId || null,
            }
        })

        revalidatePath('/dashboard/admin/staff')
        revalidatePath('/dashboard/admin/departments')
        revalidatePath('/dashboard/admin')
        return { success: "Staff member updated successfully!" }
    } catch (error: any) {
        console.error("Failed to update staff:", error)
        if (error.code === 'P2002') {
            return { error: "A user with this email already exists." }
        }
        return { error: error.message || "Failed to update staff." }
    }
}

export async function deleteStaff(id: string) {
    try {
        await requirePrincipal()

        const user = await prisma.user.findUnique({
            where: { id },
            include: { managedDepartment: true }
        })

        if (!user) return { error: "User not found." }

        // Unassign as HOD if applicable
        if (user.managedDepartment) {
            await prisma.department.update({
                where: { id: user.managedDepartment.id },
                data: { hodId: null }
            })
        }

        // Unassign from classes
        await prisma.class.updateMany({
            where: { advisorId: id },
            data: { advisorId: null }
        })

        // Delete profile if exists
        await prisma.profile.deleteMany({ where: { userId: id } })

        await prisma.user.delete({ where: { id } })

        revalidatePath('/dashboard/admin/staff')
        revalidatePath('/dashboard/admin/departments')
        revalidatePath('/dashboard/admin')
        return { success: "Staff member deleted successfully!" }
    } catch (error: any) {
        console.error("Failed to delete staff:", error)
        return { error: error.message || "Failed to delete staff." }
    }
}

// ========== STUDENT ACTIONS (Principal level) ==========

export async function createStudent(prevState: any, formData: FormData) {
    try {
        await requirePrincipal()

        const name = formData.get('name') as string
        const email = formData.get('email') as string
        const password = (formData.get('password') as string) || 'password123'
        const classId = formData.get('classId') as string

        if (!name || !email) {
            return { error: "Name and email are required." }
        }

        const hashedPassword = await bcrypt.hash(password, 10)

        await prisma.user.create({
            data: {
                name,
                email,
                password: hashedPassword,
                role: 'STUDENT',
                ...(classId ? { studentClassId: classId } : {}),
            }
        })

        revalidatePath('/dashboard/admin/students')
        revalidatePath('/dashboard/admin')
        return { success: "Student created successfully!" }
    } catch (error: any) {
        console.error("Failed to create student:", error)
        if (error.code === 'P2002') {
            return { error: "A student with this email already exists." }
        }
        return { error: error.message || "Failed to create student." }
    }
}

export async function updateStudent(prevState: any, formData: FormData) {
    try {
        await requirePrincipal()

        const id = formData.get('id') as string
        const name = formData.get('name') as string
        const email = formData.get('email') as string
        const classId = formData.get('classId') as string

        if (!id || !name || !email) {
            return { error: "ID, name, and email are required." }
        }

        await prisma.user.update({
            where: { id },
            data: {
                name,
                email,
                studentClassId: classId || null,
            }
        })

        revalidatePath('/dashboard/admin/students')
        revalidatePath('/dashboard/admin')
        return { success: "Student updated successfully!" }
    } catch (error: any) {
        console.error("Failed to update student:", error)
        if (error.code === 'P2002') {
            return { error: "A user with this email already exists." }
        }
        return { error: error.message || "Failed to update student." }
    }
}

export async function deleteStudent(id: string) {
    try {
        await requirePrincipal()

        // Delete related data
        await prisma.attendance.deleteMany({ where: { studentId: id } })
        await prisma.mark.deleteMany({ where: { studentId: id } })
        await prisma.submission.deleteMany({ where: { studentId: id } })
        await prisma.profile.deleteMany({ where: { userId: id } })

        await prisma.user.delete({ where: { id } })

        revalidatePath('/dashboard/admin/students')
        revalidatePath('/dashboard/admin')
        return { success: "Student deleted successfully!" }
    } catch (error: any) {
        console.error("Failed to delete student:", error)
        return { error: error.message || "Failed to delete student." }
    }
}
