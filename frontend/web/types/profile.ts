export type UserRole = 'admin' | 'trainer' | 'member'

export interface Profile {
    id: string
    full_name: string | null
    role: UserRole
    created_at: string
}