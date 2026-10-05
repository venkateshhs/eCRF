<template>
  <div
    v-if="visible"
    class="study-save-status"
    :class="[statusClass, { 'is-compact': compact, 'is-inline': inline }]"
    role="status"
    aria-live="polite"
  >
    <div class="study-save-status__message">
      <span class="study-save-status__dot" aria-hidden="true"></span>
      <div>
        <strong>{{ headline }}</strong>
        <span v-if="detail">{{ detail }}</span>
      </div>
    </div>

    <div v-if="showAction && dirty && !saving" class="study-save-status__actions">
      <button type="button" class="btn-option" @click="$emit('save')">
        {{ published ? "Review and save changes" : "Save and Continue" }}
      </button>
      <button
        v-if="reminderVisible"
        type="button"
        class="study-save-status__later"
        @click="remindLater"
      >
        Remind me later
      </button>
    </div>
  </div>
</template>

<script>
import { STUDY_BEFORE_IDLE_EVENT } from "@/utils/studySaveWorkflow";

export default {
  name: "StudySaveStatus",
  props: {
    dirty: { type: Boolean, default: false },
    saving: { type: Boolean, default: false },
    status: { type: String, default: "DRAFT" },
    lastSavedAt: { type: [Number, Date], default: null },
    saveError: { type: String, default: "" },
    canAutoSave: { type: Boolean, default: true },
    compact: { type: Boolean, default: false },
    inline: { type: Boolean, default: false },
    showAction: { type: Boolean, default: true },
    reminderMs: { type: Number, default: 20 * 60 * 1000 },
    remindLaterMs: { type: Number, default: 10 * 60 * 1000 },
  },
  emits: ["save", "idle-save"],
  data() {
    return {
      dirtySince: null,
      remindAfter: null,
      reminderVisible: false,
      reminderTimer: null,
    };
  },
  computed: {
    published() {
      return String(this.status || "").trim().toUpperCase() === "PUBLISHED";
    },
    visible() {
      return this.dirty || this.saving || !!this.lastSavedAt || !!this.saveError;
    },
    statusClass() {
      return {
        "is-dirty": this.dirty && !this.saveError,
        "is-saving": this.saving,
        "is-saved": !this.dirty && !this.saving && !this.saveError,
        "is-error": !!this.saveError,
        "is-reminder": this.reminderVisible,
      };
    },
    headline() {
      if (this.saving) return "Saving changes…";
      if (this.saveError) return "Changes could not be saved";
      if (this.dirty) return this.published ? "Published study has unsaved changes" : "Unsaved draft changes";
      if (this.lastSavedAt) return `Saved at ${this.formatTime(this.lastSavedAt)}`;
      return "Changes saved";
    },
    detail() {
      const lastSaved = this.lastSavedAt ? ` Last saved at ${this.formatTime(this.lastSavedAt)}.` : "";
      if (this.saving) return `Please keep this page open until saving finishes.${lastSaved}`;
      if (this.saveError) return `${this.saveError}${lastSaved}`;
      if (this.reminderVisible) {
        return this.published
          ? `Review and save explicitly. Structural changes may create a new template version.${lastSaved}`
          : `Use Save and Continue periodically to protect your work.${lastSaved}`;
      }
      if (this.dirty) {
        return this.published
          ? `Published changes are never saved automatically.${lastSaved}`
          : `Use Save and Continue periodically to protect your work.${lastSaved}`;
      }
      return "";
    },
  },
  watch: {
    dirty: {
      immediate: true,
      handler(value) {
        if (value) {
          if (!this.dirtySince) this.dirtySince = Date.now();
          if (!this.remindAfter) this.remindAfter = this.dirtySince + this.reminderMs;
        } else {
          this.resetReminder();
        }
      },
    },
    lastSavedAt() {
      if (!this.dirty) this.resetReminder();
    },
  },
  mounted() {
    this.reminderTimer = window.setInterval(this.checkReminder, 30 * 1000);
    window.addEventListener(STUDY_BEFORE_IDLE_EVENT, this.onBeforeIdle);
    this.checkReminder();
  },
  beforeUnmount() {
    if (this.reminderTimer) window.clearInterval(this.reminderTimer);
    window.removeEventListener(STUDY_BEFORE_IDLE_EVENT, this.onBeforeIdle);
  },
  methods: {
    formatTime(value) {
      const date = value instanceof Date ? value : new Date(Number(value));
      return Number.isNaN(date.getTime()) ? "just now" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    },
    checkReminder() {
      if (!this.dirty || this.saving || !this.remindAfter) return;
      if (Date.now() >= this.remindAfter) this.reminderVisible = true;
    },
    remindLater() {
      this.reminderVisible = false;
      this.remindAfter = Date.now() + this.remindLaterMs;
    },
    resetReminder() {
      this.dirtySince = null;
      this.remindAfter = null;
      this.reminderVisible = false;
    },
    onBeforeIdle() {
      if (!this.dirty || this.saving) return;
      if (!this.published && this.canAutoSave) {
        this.$emit("idle-save");
        return;
      }
      this.reminderVisible = true;
    },
  },
};
</script>

<style scoped>
.study-save-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 12px 0;
  padding: 11px 14px;
  border: 1px solid #dbe3ec;
  border-radius: 10px;
  background: #f8fafc;
  color: #334155;
}

.study-save-status__message,
.study-save-status__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.study-save-status__message strong,
.study-save-status__message span {
  display: block;
}

.study-save-status__message span {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
}

.study-save-status__dot {
  flex: 0 0 9px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #64748b;
}

.study-save-status.is-dirty,
.study-save-status.is-reminder {
  border-color: #f4c76b;
  background: #fffbeb;
}

.study-save-status.is-dirty .study-save-status__dot,
.study-save-status.is-reminder .study-save-status__dot {
  background: #d97706;
}

.study-save-status.is-saved .study-save-status__dot { background: #16803c; }
.study-save-status.is-error { border-color: #fecaca; background: #fef2f2; }
.study-save-status.is-error .study-save-status__dot { background: #dc2626; }
.study-save-status.is-saving .study-save-status__dot { background: #2563eb; }

.study-save-status.is-compact {
  width: fit-content;
  max-width: min(100%, 560px);
  margin: 6px 0 10px;
  padding: 6px 10px;
  border-radius: 7px;
  font-size: 12px;
}

.study-save-status.is-compact .study-save-status__message span {
  font-size: 11px;
}

.study-save-status.is-inline {
  align-self: center;
  flex: 0 1 auto;
  margin: 0;
  padding: 5px 8px;
}

.study-save-status__later {
  border: 0;
  background: transparent;
  color: #475569;
  cursor: pointer;
  font: inherit;
  text-decoration: underline;
}

@media (max-width: 720px) {
  .study-save-status { align-items: flex-start; flex-direction: column; }
  .study-save-status__actions { flex-wrap: wrap; }
}
</style>
