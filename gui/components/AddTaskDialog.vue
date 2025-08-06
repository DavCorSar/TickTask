<template>
  <v-dialog v-model="dialog" max-width="500px" persistent>
    <v-card>
      <v-form ref="formRef" @submit.prevent="submitForm">
        <v-toolbar density="compact" class="bg-transparent">
          <v-toolbar-title>Crear nueva tarea</v-toolbar-title>
          <v-btn icon="mdi-close" @click="dialog = false"></v-btn>
        </v-toolbar>

        <v-card-text>
          <v-text-field
            v-model="taskName"
            label="Nombre de la tarea"
            :rules="[(v) => !!v || 'El nombre es obligatorio']"
            variant="underlined"
            dense />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" variant="flat" type="submit"> Crear </v-btn>
        </v-card-actions>
      </v-form>
    </v-card>
  </v-dialog>
</template>

<script setup>
  import { ref, watch } from "vue";

  const props = defineProps({
    modelValue: Boolean,
  });

  const emit = defineEmits(["update:modelValue", "task-created"]);

  const { $api } = useNuxtApp();

  const dialog = ref(props.modelValue);
  const formRef = ref(null);
  const taskName = ref("");

  watch(
    () => props.modelValue,
    (val) => {
      dialog.value = val;
    }
  );

  watch(dialog, (val) => {
    emit("update:modelValue", val);
  });

  async function submitForm() {
    const valid = await formRef.value.validate();
    if (!valid) return;

    try {
      const response = await $api("/ticktask/user/create-task/", {
        method: "POST",
        body: {
          name: taskName.value.trim(),
        },
      });

      emit("task-created", response);
      resetForm();
      dialog.value = false;
    } catch (error) {
      console.error("Error al crear tarea:", error);
    }
  }

  function resetForm() {
    taskName.value = "";
    formRef.value.resetValidation();
  }
</script>
