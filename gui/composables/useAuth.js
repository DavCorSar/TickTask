import { jwtDecode } from 'jwt-decode'

export const useAuth = () => {
    const { $api } = useNuxtApp()

    const accessToken = useState('access_token', () => null)
    const refreshToken = useState('refresh_token', () => null)
    const user = useState('user', () => null)

    const login = async (username, password) => {
        try {
            logout()

            console.log("Login with: ", { username, password });
            const response = await $api('/auth/login', {
                method: 'POST',
                body: { username, password },
            })

            if (!response.access || !response.refresh) {
                throw new Error('Tokens where not received successfully')
            }

            accessToken.value = response.access
            refreshToken.value = response.refresh
            user.value = jwtDecode(response.access)

            localStorage.setItem('access_token', accessToken.value)
            localStorage.setItem('refresh_token', refreshToken.value)

            scheduleTokenRefresh()

            return true
        } catch (error) {
            throw new Error('Invalid user or password')
        }
    }

    const refresh = async () => {
        if (!refreshToken.value) return
        try {
            const response = await $api('/auth/refresh', {
                method: 'POST',
                body: { refresh: refreshToken.value },
            })
            accessToken.value = response.access
            user.value = jwtDecode(response.access)

            scheduleTokenRefresh()
        } catch (error) {
            console.log('Error refreshing token:', error)
            logout()
        }
    }

    const logout = () => {
        accessToken.value = null
        refreshToken.value = null
        user.value = null

        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
    }

    const isAuthenticated = computed(() => !!accessToken.value)

    const scheduleTokenRefresh = () => {
        if (!accessToken.value) return

        const decoded = jwtDecode(accessToken.value)
        const now = Math.floor(Date.now() / 1000)
        const timeLeft = decoded.exp - now

        // Refrescar 30 segundos antes de que expire el token
        setTimeout(async () => {
            refresh()
        }, (timeLeft - 30) * 1000)
    }

    return { accessToken, refreshToken, user, login, refresh, logout, isAuthenticated }
}
