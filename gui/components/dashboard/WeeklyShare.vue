<template>
  <div v-if="tasks.length" class="space-y-4">
    <div v-for="(task, index) in tasks" :key="task.task_id">
      <div class="flex items-center gap-2">
        <span
          class="size-2.5 shrink-0 rounded-full"
          :style="{ backgroundColor: chartColor(index) }"
          :class="{ 'opacity-40': task.deleted }"></span>
        <span
          class="min-w-0 flex-1 truncate text-sm font-medium"
          :class="{ 'text-muted-foreground line-through': task.deleted }">
          {{ task.task_name }}
        </span>
        <span class="shrink-0 text-sm font-semibold tabular-nums">
          {{ task.percent }}%
        </span>
        <span class="shrink-0 text-xs text-muted-foreground tabular-nums">
          {{ formatHours(task.hours) }}
        </span>
      </div>

      <div class="mt-1.5 h-2 overflow-hidden rounded-full bg-muted">
        <div
          class="h-full rounded-full transition-all"
          :style="{
            width: `${task.percent}%`,
            backgroundColor: chartColor(index),
          }"></div>
      </div>
    </div>
  </div>

  <div
    v-else
    class="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 text-center text-muted-foreground">
    <Icon name="lucide:chart-no-axes-column" class="size-7" />
    <p class="text-sm">No time tracked in the last 7 days.</p>
  </div>
</template>

<script setup>
  defineProps({
    tasks: { type: Array, default: () => [] },
  });
</script>
