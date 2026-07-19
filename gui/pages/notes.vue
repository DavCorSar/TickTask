<template>
  <div class="mx-auto max-w-6xl space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">Notes</h1>
        <p class="mt-1 text-muted-foreground">
          Keep pending items grouped into simple checklists.
        </p>
      </div>
      <UiButton icon="lucide:folder-plus" @click="openCreateGroup">
        New group
      </UiButton>
    </div>

    <!-- Loading -->
    <UiCard v-if="loading">
      <div class="flex items-center justify-center py-12 text-muted-foreground">
        <Icon name="lucide:loader-circle" class="size-6 animate-spin" />
      </div>
    </UiCard>

    <!-- Empty -->
    <UiCard v-else-if="!groups.length">
      <div class="flex flex-col items-center gap-3 py-12 text-center">
        <div
          class="flex size-12 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
          <Icon name="lucide:notebook-pen" class="size-6" />
        </div>
        <div>
          <p class="font-medium">No notes yet</p>
          <p class="text-sm text-muted-foreground">
            Create a group to start jotting things down.
          </p>
        </div>
        <UiButton icon="lucide:folder-plus" @click="openCreateGroup">
          New group
        </UiButton>
      </div>
    </UiCard>

    <!-- Groups -->
    <div v-else class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <UiCard v-for="group in groups" :key="group.id" :padded="false">
        <!-- Group header -->
        <div class="flex items-center gap-2.5 border-b border-border px-4 py-3">
          <span
            class="size-3 shrink-0 rounded-full"
            :style="{ backgroundColor: group.color || 'var(--muted-foreground)' }"></span>
          <div class="min-w-0 flex-1">
            <p class="truncate font-semibold">{{ group.name }}</p>
            <p class="text-xs text-muted-foreground">
              {{ progressOf(group).done }}/{{ progressOf(group).total }} done
            </p>
          </div>
          <button
            class="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            title="Edit group"
            @click="openEditGroup(group)">
            <Icon name="lucide:pencil" class="size-4" />
          </button>
        </div>

        <!-- Notes -->
        <ul v-if="group.notes.length" class="divide-y divide-border">
          <li
            v-for="note in sortNotes(group.notes)"
            :key="note.id"
            class="group/note flex items-start gap-2.5 px-4 py-2.5">
            <button
              class="mt-0.5 shrink-0 transition-colors"
              :class="
                note.done
                  ? 'text-primary'
                  : 'text-muted-foreground hover:text-foreground'
              "
              :title="note.done ? 'Mark as pending' : 'Mark as done'"
              @click="toggle(note)">
              <Icon
                :name="note.done ? 'lucide:check-circle-2' : 'lucide:circle'"
                class="size-[18px]" />
            </button>
            <div class="min-w-0 flex-1">
              <p
                class="truncate text-sm font-medium"
                :class="{ 'text-muted-foreground line-through': note.done }">
                {{ note.title }}
              </p>
              <p
                v-if="note.body"
                class="mt-0.5 whitespace-pre-line break-words text-xs text-muted-foreground"
                :class="{ 'line-through': note.done }">
                {{ note.body }}
              </p>
            </div>
            <button
              class="shrink-0 rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:text-primary focus:opacity-100 group-hover/note:opacity-100"
              title="Edit note"
              @click="openEditNote(group, note)">
              <Icon name="lucide:pencil" class="size-4" />
            </button>
          </li>
        </ul>
        <p v-else class="px-4 py-4 text-sm text-muted-foreground">
          No notes in this group yet.
        </p>

        <!-- Add note -->
        <div class="border-t border-border px-2 py-2">
          <button
            class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            @click="openCreateNote(group)">
            <Icon name="lucide:plus" class="size-4" />
            Add note
          </button>
        </div>
      </UiCard>
    </div>

    <NoteGroupDialog
      v-model="groupDialogOpen"
      :group="editingGroup"
      @saved="load"
      @deleted="load" />

    <NoteDialog
      v-model="noteDialogOpen"
      :note="editingNote"
      :group-id="activeGroupId"
      @saved="load"
      @deleted="load" />
  </div>
</template>

<script setup>
  import { ref, onMounted } from "vue";

  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });

  const { getNotes, toggleNote } = useNotes();
  const toast = useToast();

  const groups = ref([]);
  const loading = ref(false);

  const groupDialogOpen = ref(false);
  const editingGroup = ref(null);
  const noteDialogOpen = ref(false);
  const editingNote = ref(null);
  const activeGroupId = ref(null);

  const progressOf = (group) => groupProgress(group.notes);

  function openCreateGroup() {
    editingGroup.value = null;
    groupDialogOpen.value = true;
  }

  function openEditGroup(group) {
    editingGroup.value = group;
    groupDialogOpen.value = true;
  }

  function openCreateNote(group) {
    editingNote.value = null;
    activeGroupId.value = group.id;
    noteDialogOpen.value = true;
  }

  function openEditNote(group, note) {
    editingNote.value = note;
    activeGroupId.value = group.id;
    noteDialogOpen.value = true;
  }

  async function toggle(note) {
    // Flip locally first so the checklist feels instant; revert on failure.
    note.done = !note.done;
    try {
      await toggleNote(note.id);
    } catch (err) {
      note.done = !note.done;
      console.error("Error toggling note:", err);
      toast.error("Couldn't update the note.");
    }
  }

  async function load() {
    loading.value = true;
    try {
      groups.value = await getNotes();
    } catch (err) {
      console.error("Error loading notes:", err);
      toast.error("Couldn't load your notes.");
    } finally {
      loading.value = false;
    }
  }

  onMounted(load);
</script>
