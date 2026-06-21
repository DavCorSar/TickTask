<template>
  <div
    class="flex items-start gap-3 rounded-xl border px-4 py-3 text-sm"
    :class="styles[variant].box">
    <Icon
      :name="styles[variant].icon"
      class="mt-0.5 size-[18px] shrink-0"
      :class="styles[variant].iconColor" />
    <div class="min-w-0">
      <slot />
    </div>
  </div>
</template>

<script setup>
  defineProps({
    variant: { type: String, default: "info" }, // info | success | danger
  });

  const styles = {
    info: {
      box: "border-primary/20 bg-primary/10 text-foreground",
      icon: "lucide:info",
      iconColor: "text-primary",
    },
    success: {
      box: "border-accent/25 bg-accent/10 text-foreground",
      icon: "lucide:circle-check",
      iconColor: "text-accent",
    },
    danger: {
      box: "border-danger/25 bg-danger/10 text-foreground",
      icon: "lucide:circle-alert",
      iconColor: "text-danger",
    },
  };
</script>
