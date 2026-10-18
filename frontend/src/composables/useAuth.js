import { ref } from 'vue'
import { api, setUnauthorizedHandler, tokenStore } from '../services/api'

const user = ref(null)
const checked = ref(false) // false until the stored token (if any) has been checked

setUnauthorizedHandler(() => {
  user.value = null
})

export function useAuth() {
  async function restore() {
    try {
      user.value = tokenStore.get() ? await api.me() : null
    } catch {
      tokenStore.clear()
      user.value = null
    } finally {
      checked.value = true
    }
  }

  async function login(username, password) {
    const { access_token: token } = await api.login(username, password)
    tokenStore.set(token)
    user.value = await api.me()
  }

  async function register(username, password) {
    await api.register(username, password)
    await login(username, password)
  }

  async function logout() {
    try {
      await api.logout()
    } finally {
      tokenStore.clear()
      user.value = null
    }
  }

  return { user, checked, restore, login, register, logout }
}
