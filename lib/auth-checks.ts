import { auth } from "@/auth"
import { redirect } from "next/navigation"

export async function requireRole(allowedRoles: string[]) {
    const session = await auth()

    if (!session?.user) {
        redirect('/login')
    }

    const userRole = session.user.role as string

    if (!allowedRoles.includes(userRole)) {
        redirect('/dashboard') // Back to main dispatcher which will redirect to correct dashboard
    }

    return session
}
