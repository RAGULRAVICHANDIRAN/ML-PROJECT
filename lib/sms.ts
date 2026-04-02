export async function sendSMSNotification(studentName: string, parentPhone: string | null) {
    // In a real app, integrate with Twilio/SNS
    console.log(`[SMS MOCK] Sending to ${parentPhone || 'Parent'}: Your ward ${studentName} is absent for this period.`)
    return true
}
