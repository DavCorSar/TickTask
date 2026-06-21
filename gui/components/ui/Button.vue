<template>
  <component
    :is="to ? NuxtLink : 'button'"
    :to="to"
    :type="to ? undefined : type"
    :disabled="!to && (disabled || loading)"
    :class="classes">
    <Icon
      v-if="loading"
      name="lucide:loader-circle"
      class="animate-spin"
      :class="iconSize" />
    <Icon v-else-if="icon" :name="icon" :class="iconSize" />
    <span v-if="$slots.default" :class="{ 'opacity-0': loading && !icon }">
      <slot />
    </span>
  </component>
</template>

<script setup>
  import { computed } from "vue";
  import { NuxtLink } from "#components";

  const props = defineProps({
    variant: { type: String, default: "primary" }, // primary | secondary | ghost | outline | danger
    size: { type: String, default: "md" }, // sm | md | lg | icon
    icon: { type: String, default: "" },
    to: { type: [String, Object], default: null },
    type: { type: String, default: "button" },
    block: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  });

  const variants = {
    primary:
      "bg-primary text-primary-foreground hover:bg-primary/90 shadow-soft",
    secondary: "bg-muted text-foreground hover:bg-muted/70",
    ghost:
      "bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground",
    outline:
      "border border-border bg-transparent text-foreground hover:bg-muted",
    danger: "bg-danger text-danger-foreground hover:bg-danger/90 shadow-soft",
  };

  const sizes = {
    sm: "h-8 px-3 text-sm gap-1.5",
    md: "h-10 px-4 text-sm gap-2",
    lg: "h-12 px-6 text-base gap-2",
    icon: "h-10 w-10",
  };

  const iconSize = computed(() =>
    props.size === "sm" ? "size-4" : "size-[18px]",
  );

  const classes = computed(() => [
    "inline-flex items-center justify-center rounded-xl font-medium transition-colors",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:pointer-events-none disabled:opacity-50",
    variants[props.variant],
    sizes[props.size],
    props.block ? "w-full" : "",
  ]);
</script>
