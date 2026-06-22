<template>
  <div class="mx-auto max-w-2xl space-y-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">Settings</h1>
      <p class="mt-1 text-muted-foreground">
        Configure how TickTask notifies you.
      </p>
    </div>

    <UiCard
      title="Telegram reminders"
      subtitle="Get a message when one of your calendar events is near.">
      <div
        v-if="loading"
        class="flex items-center justify-center py-10 text-muted-foreground">
        <Icon name="lucide:loader-circle" class="size-6 animate-spin" />
      </div>

      <div v-else-if="telegram" class="space-y-6">
        <!-- Connection -->
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2.5">
            <span
              class="size-2.5 rounded-full"
              :class="
                telegram.connected ? 'bg-accent' : 'bg-muted-foreground/40'
              "></span>
            <span class="text-sm font-medium">
              {{ telegram.connected ? "Connected" : "Not connected" }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <template v-if="telegram.connected">
              <UiButton
                variant="outline"
                size="sm"
                icon="lucide:send"
                :loading="testing"
                @click="sendTest">
                Send test
              </UiButton>
              <UiButton
                variant="ghost"
                size="sm"
                :loading="unlinking"
                @click="disconnect">
                Disconnect
              </UiButton>
            </template>
            <UiButton
              v-else
              size="sm"
              icon="lucide:link"
              :loading="linking"
              @click="connect">
              Connect Telegram
            </UiButton>
          </div>
        </div>

        <!-- Connect: QR for the phone + link for desktop Telegram -->
        <div
          v-if="pendingLink && !telegram.connected"
          class="rounded-xl border border-border bg-muted/40 p-4">
          <p class="text-sm font-medium">Connect from your phone</p>
          <p class="mt-1 text-sm text-muted-foreground">
            Scan this QR with your phone's camera, or open the link if you have
            Telegram here. Press <strong>Start</strong> in the chat, then
            refresh.
          </p>
          <div
            class="mt-3 flex flex-col items-center gap-4 sm:flex-row sm:items-start">
            <img
              v-if="qrDataUrl"
              :src="qrDataUrl"
              alt="Telegram connect QR code"
              class="size-44 rounded-lg bg-white p-2" />
            <div class="flex flex-col items-center gap-2 sm:items-start">
              <a
                :href="deepLink"
                target="_blank"
                rel="noopener"
                class="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
                <Icon name="lucide:external-link" class="size-4" />
                Open in Telegram
              </a>
              <button
                class="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
                @click="copyLink">
                <Icon name="lucide:copy" class="size-4" />
                Copy link
              </button>
              <UiButton
                variant="outline"
                size="sm"
                icon="lucide:refresh-cw"
                :loading="loading"
                @click="refresh">
                I've connected — refresh
              </UiButton>
            </div>
          </div>
        </div>

        <!-- Preferences -->
        <div class="space-y-4 border-t border-border pt-5">
          <label class="flex cursor-pointer items-center justify-between gap-3">
            <span class="text-sm">
              <span class="font-medium">Enable reminders</span>
              <span class="block text-muted-foreground">
                Send reminders to your Telegram.
              </span>
            </span>
            <input
              v-model="enabled"
              type="checkbox"
              class="size-4 rounded border-border accent-primary" />
          </label>

          <div class="flex items-center justify-between gap-3">
            <span class="text-sm">
              <span class="font-medium">Remind me before</span>
              <span class="block text-muted-foreground">
                Minutes before the event (plus one at the exact time). 0 = only
                at the time.
              </span>
            </span>
            <input
              v-model.number="leadMinutes"
              type="number"
              min="0"
              max="1440"
              class="h-10 w-24 rounded-xl border border-input bg-card px-3 text-foreground focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>

          <div class="flex justify-end">
            <UiButton
              size="sm"
              :loading="saving"
              :disabled="!dirty"
              @click="save">
              Save
            </UiButton>
          </div>
        </div>
      </div>
    </UiCard>
  </div>
</template>

<script setup>
  import { ref, computed, onMounted } from "vue";
  import QRCode from "qrcode";

  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });

  const {
    getTelegram,
    updateTelegram,
    linkTelegram,
    unlinkTelegram,
    testTelegram,
  } = useSettings();
  const toast = useToast();

  const telegram = ref(null);
  const loading = ref(true);
  const linking = ref(false);
  const unlinking = ref(false);
  const testing = ref(false);
  const saving = ref(false);
  const pendingLink = ref(false);
  const deepLink = ref("");
  const qrDataUrl = ref("");

  const enabled = ref(true);
  const leadMinutes = ref(15);

  const dirty = computed(
    () =>
      telegram.value &&
      (enabled.value !== telegram.value.enabled ||
        leadMinutes.value !== telegram.value.reminder_lead_minutes),
  );

  function sync(data) {
    telegram.value = data;
    enabled.value = data.enabled;
    leadMinutes.value = data.reminder_lead_minutes;
  }

  async function load() {
    loading.value = true;
    try {
      sync(await getTelegram());
    } catch (err) {
      console.error("Error loading settings:", err);
      toast.error("Couldn't load your settings.");
    } finally {
      loading.value = false;
    }
  }

  async function connect() {
    linking.value = true;
    try {
      const { deep_link } = await linkTelegram();
      deepLink.value = deep_link;
      qrDataUrl.value = await QRCode.toDataURL(deep_link, {
        margin: 1,
        width: 240,
      });
      pendingLink.value = true;
    } catch (err) {
      console.error("Error starting Telegram link:", err);
      toast.error(
        err?.data?.detail || "Couldn't start the Telegram connection.",
      );
    } finally {
      linking.value = false;
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(deepLink.value);
      toast.success("Link copied.");
    } catch {
      toast.error("Couldn't copy the link.");
    }
  }

  async function refresh() {
    await load();
    if (telegram.value?.connected) {
      pendingLink.value = false;
      toast.success("Telegram connected.");
    }
  }

  async function disconnect() {
    unlinking.value = true;
    try {
      sync(await unlinkTelegram());
      toast.success("Telegram disconnected.");
    } catch (err) {
      console.error("Error disconnecting Telegram:", err);
      toast.error("Couldn't disconnect Telegram.");
    } finally {
      unlinking.value = false;
    }
  }

  async function sendTest() {
    testing.value = true;
    try {
      await testTelegram();
      toast.success("Test message sent — check Telegram.");
    } catch (err) {
      console.error("Error sending test message:", err);
      toast.error(err?.data?.detail || "Couldn't send the test message.");
    } finally {
      testing.value = false;
    }
  }

  async function save() {
    saving.value = true;
    try {
      sync(await updateTelegram(enabled.value, leadMinutes.value));
      toast.success("Settings saved.");
    } catch (err) {
      console.error("Error saving settings:", err);
      toast.error("Couldn't save your settings.");
    } finally {
      saving.value = false;
    }
  }

  onMounted(load);
</script>
