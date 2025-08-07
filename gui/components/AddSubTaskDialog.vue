<template>
  <v-dialog v-model="dialog" max-width="600px" persistent>
    <v-card>
      <v-form ref="formRef" @submit.prevent="submitForm">
        <v-toolbar density="compact" class="bg-transparent">
          <v-toolbar-title>Crear nueva subtarea</v-toolbar-title>
          <v-btn icon="mdi-close" @click="dialog = false"></v-btn>
        </v-toolbar>

        <v-card-text>
          <v-text-field
            v-model="subtaskName"
            label="Nombre de la subtarea"
            :rules="[(v) => !!v || 'El nombre es obligatorio']"
            variant="underlined"
            dense />

          <v-textarea
            v-model="subtaskDescription"
            label="Descripción"
            :rules="[(v) => !!v || 'La descripción es obligatoria']"
            variant="underlined"
            rows="3"
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
    taskId: Number, // Tarea asociada
  });

  const emit = defineEmits(["update:modelValue", "subtask-created"]);

  const { $api } = useNuxtApp();

  const dialog = ref(props.modelValue);
  const formRef = ref(null);
  const subtaskName = ref("");
  const subtaskDescription = ref("");

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
      console.log("Subtask: ", {
        name: subtaskName.value.trim(),
        description: subtaskDescription.value.trim(),
        task_id: props.taskId,
      });
      const response = await $api("/ticktask/user/create-subtask/", {
        method: "POST",
        body: {
          name: subtaskName.value.trim(),
          description: subtaskDescription.value.trim(),
          task_id: props.taskId,
        },
      });

      emit("subtask-created", response);
      resetForm();
      dialog.value = false;
    } catch (error) {
      console.error("Error al crear subtarea:", error);
    }
  }

  function resetForm() {
    subtaskName.value = "";
    subtaskDescription.value = "";
    formRef.value.resetValidation();
  }
</script>
