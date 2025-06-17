// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',
  devtools: { enabled: true },
  modules: ['vuetify-nuxt-module'],
  ssr: false,
  vuetify: {
    moduleOptions: {
    },
    vuetifyOptions: {
      theme: {
        themes: {
          light: {
            dark: false,
            colors: {
              primary: '#007CBF',
              secondary: '#5EA611',
              error: '#D30F4B'
            }
          },
        },
      },
    }
  },
  runtimeConfig: {
    public: {
      apiBaseUrl: process.env.NUXT_PUBLIC_API_URL || '/api',
    },
  },
  router: {
    options: {
      hashMode: true,
    },
  },
  app: {
    head: {
      title: 'TickTask',
      link: [
        { rel: 'icon', type: 'image/png', href: '/favicon.png' },
      ]
    }
  }
})