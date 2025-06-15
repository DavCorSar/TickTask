<template>
    <v-container class="fill-height d-flex justify-center align-center">
        <v-card class="pa-6" width="400" elevation="16">
            <v-card-title class="text-center">Login</v-card-title>

            <v-card-text>
                <v-form @submit.prevent="login">
                    <v-text-field v-model="username" label="User" variant="underlined" prepend-inner-icon="mdi-account"
                        autofocus></v-text-field>

                    <v-text-field v-model="password" label="Password" type="password" variant="underlined"
                        prepend-inner-icon="mdi-key-variant"></v-text-field>

                    <v-btn color="primary" block type="submit" :loading="loading">
                        Access
                    </v-btn>
                </v-form>

                <v-alert v-if="errorMessage" type="error" class="mt-3" dense>
                    {{ errorMessage }}
                </v-alert>
            </v-card-text>
        </v-card>
    </v-container>
</template>

<script setup>
import { useRouter } from 'vue-router'

const auth = useAuth()
const router = useRouter()

const username = ref('')
const password = ref('')
const errorMessage = ref('')

const loading = ref(false)

const login = async () => {
    errorMessage.value = ''
    loading.value = true

    if (!username.value || !password.value) {
        errorMessage.value = 'You must introduce user and password'
    } else {
        try {
            const success = await auth.login(username.value, password.value)
            if (success) {
                router.push('/simulation')
            }
        } catch (error) {
            errorMessage.value = error.message || 'Invalid user or password'
        }
    }

    loading.value = false
}
</script>
