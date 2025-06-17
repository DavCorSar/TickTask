<template>

    <v-container class="mx-auto">
        <v-row justify="center" align="center" class="text-center" no-gutters>
            <div class="text-h3 mb-10">Here goes option 1</div>
            <!-- <v-col cols="12" md="4">
                <v-btn @click="goTo('my-scenarios')" variant="text" size="200" stacked color="primary">
                    <v-icon size="150">mdi-hospital-building</v-icon>
                    <span class="mt-2 text-lg font-semibold text-gray-800">Mis escenarios</span>
                </v-btn>
            </v-col> -->

            <div class="text-h3 mb-10">Here goes option 2</div>
            <!-- <v-col cols="12" md="4">
                <v-btn @click="goTo('simulations')" variant="text" size="200" stacked color="primary">
                    <v-icon size="150">mdi-cog</v-icon>
                    <span class="mt-2 text-lg font-semibold text-gray-800">Simulaciones</span>
                </v-btn>
            </v-col> -->

            <div class="text-h3 mb-10">Here goes option 3</div>
            <!-- <v-col cols="12" md="4">
                <v-btn @click="goTo('optimizations')" variant="text" size="200" stacked color="primary">
                    <v-icon size="150">mdi-clipboard-check</v-icon>
                    <span class="mt-2 text-lg font-semibold text-gray-800">Optimizaciones</span>
                </v-btn>
            </v-col> -->
        </v-row>
    </v-container>
</template>

<script setup>
const router = useRouter()

function goTo(path) {
    router.push(`/${path}`)
}
</script>
