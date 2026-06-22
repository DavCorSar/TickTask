<template>
  <div v-if="tasks.length" class="space-y-4">
    <div v-for="(task, index) in tasks" :key="task.task_id">
      <div class="flex items-center gap-2">
        <button
          v-if="task.subtasks.length"
          class="rounded-md p-0.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          :aria-label="
            expanded.has(task.task_id) ? 'Collapse subtasks' : 'Expand subtasks'
          "
          @click="toggle(task.task_id)">
          <Icon
            name="lucide:chevron-right"
            class="size-4 transition-transform"
            :class="{ 'rotate-90': expanded.has(task.task_id) }" />
        </button>
        <span v-else class="size-5 shrink-0"></span>

        <span
          class="size-2.5 shrink-0 rounded-full"
          :style="{ backgroundColor: chartColor(index) }"
          :class="{ 'opacity-40': task.deleted }"></span>
        <span
          class="min-w-0 flex-1 truncate text-sm font-medium"
          :class="{ 'text-muted-foreground line-through': task.deleted }">
          {{ task.task_name }}
        </span>
        <span
          v-if="task.deleted"
          class="shrink-0 rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          deleted
        </span>
        <button
          v-if="task.deleted"
          class="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-primary"
          title="Restore task"
          @click="emit('restore-task', task.task_id)">
          <Icon name="lucide:rotate-ccw" class="size-4" />
        </button>
        <span class="shrink-0 text-sm font-semibold tabular-nums">
          {{ formatHours(task.hours) }}
        </span>
      </div>

      <div class="ml-7 mt-1.5 h-2 overflow-hidden rounded-full bg-muted">
        <div
          class="h-full rounded-full transition-all"
          :style="{
            width: `${pct(task.hours)}%`,
            backgroundColor: chartColor(index),
          }"></div>
      </div>

      <div v-if="expanded.has(task.task_id)" class="ml-7 mt-2.5 space-y-2">
        <div
          v-for="subtask in task.subtasks"
          :key="subtask.subtask_id"
          class="flex items-center gap-3">
          <span
            class="min-w-0 flex-1 truncate text-xs text-muted-foreground"
            :class="{ 'line-through': subtask.deleted }">
            {{ subtask.subtask_name }}
          </span>
          <button
            v-if="subtask.deleted"
            class="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-primary"
            title="Restore subtask"
            @click="emit('restore-subtask', subtask.subtask_id)">
            <Icon name="lucide:rotate-ccw" class="size-3.5" />
          </button>
          <div
            class="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-muted">
            <div
              class="h-full rounded-full bg-muted-foreground/50"
              :style="{ width: `${pct(subtask.hours)}%` }"></div>
          </div>
          <span
            class="w-14 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
            {{ formatHours(subtask.hours) }}
          </span>
        </div>
      </div>
    </div>
  </div>

  <p v-else class="py-8 text-center text-sm text-muted-foreground">
    No tracked time in this range.
  </p>
</template>

<script setup>
  import { computed, reactive } from "vue";

  const props = defineProps({
    tasks: { type: Array, default: () => [] },
  });

  const emit = defineEmits(["restore-task", "restore-subtask"]);

  const expanded = reactive(new Set());

  const maxHours = computed(() =>
    Math.max(1, ...props.tasks.map((t) => t.hours)),
  );

  function pct(hours) {
    return Math.min(100, (hours / maxHours.value) * 100);
  }

  function toggle(taskId) {
    if (expanded.has(taskId)) expanded.delete(taskId);
    else expanded.add(taskId);
  }
</script>
