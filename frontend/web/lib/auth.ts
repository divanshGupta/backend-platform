import { supabase } from './supabase';

export interface SignUpInput {
  email: string
  password: string
  fullName: string
}

export interface LoginInput {
  email: string
  password: string
}

export const signUp = async ({
  email,
  password,
  fullName
}: SignUpInput) => {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName
      }
    }
  })

  if (error) throw error
  return data
}

export const login = async ({ email, password }: LoginInput) => {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password
  })

  if (error) throw error
  return data
}

export const logout = async () => {
  const { error } = await supabase.auth.signOut()
  if (error) throw error
}
