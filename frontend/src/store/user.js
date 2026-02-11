import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, getCurrentUser } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)
  const roles = ref([])

  const setToken = (newToken) => {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  const setUserInfo = (info) => {
    userInfo.value = info
    roles.value = info.roles || []
  }

  const login = async (username, password) => {
    const data = await loginApi(username, password)
    setToken(data.access_token)
    await getCurrentUserInfo()
    return data
  }

  const getCurrentUserInfo = async () => {
    const info = await getCurrentUser()
    setUserInfo(info)
    return info
  }

  const logout = () => {
    token.value = ''
    userInfo.value = null
    roles.value = []
    localStorage.removeItem('token')
  }

  const checkLogin = async () => {
    if (token.value) {
      try {
        await getCurrentUserInfo()
      } catch (error) {
        logout()
      }
    }
  }

  const hasRole = (roleName) => {
    return roles.value.includes(roleName)
  }

  const hasAnyRole = (roleNames) => {
    return roleNames.some(role => roles.value.includes(role))
  }

  return {
    token,
    userInfo,
    roles,
    setToken,
    setUserInfo,
    login,
    logout,
    getCurrentUserInfo,
    checkLogin,
    hasRole,
    hasAnyRole
  }
})
