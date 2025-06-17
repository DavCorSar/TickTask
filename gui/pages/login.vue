<template>
    <v-container class="fill-height d-flex justify-center align-center">
        <v-card class="pa-6" width="400" elevation="16">
            <v-card-title class="text-center">LogIn</v-card-title>

            <v-card-text>
                <v-form @submit.prevent="login">
                    <v-text-field v-model="username" label="User" variant="underlined" prepend-inner-icon="mdi-account"
                        autofocus></v-text-field>

                    <v-text-field v-model="password" label="Password" :type="showPassword ? 'text' : 'password'"
                        variant="underlined" prepend-inner-icon="mdi-key-variant"
                        :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                        @click:append-inner="showPassword = !showPassword"></v-text-field>

                    <v-btn color="primary" block type="submit" :loading="loading">
                        Access
                    </v-btn>

                    <v-btn color="primary" block variant="text" class="mt-4" to="/">
                        Return
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
definePageMeta({
    layout: 'blank'
})

import { useRouter } from 'vue-router'

const auth = useAuth()
const router = useRouter()

const username = ref('')
const password = ref('')
const errorMessage = ref('')

const showPassword = ref(false)

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
                router.push('/home')
            }
        } catch (error) {
            errorMessage.value = error.message || 'Incorrect user or password'
        }
    }

    loading.value = false
}
</script>