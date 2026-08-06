<template>
  <div class="dropout-backdrop" role="presentation" @click.self="$emit('close')">
    <section class="dropout-dialog" role="dialog" aria-modal="true" aria-labelledby="dropout-title">
      <h3 id="dropout-title">Drop out subject</h3>

      <template v-if="!mode">
        <p>How do you want to drop out this subject?</p>
        <button class="choice" type="button" @click="mode = 'keep_data'">
          <strong>Drop out and keep existing data</strong>
          <span>Existing data remains read-only. No new data can be added.</span>
        </button>
        <button class="choice danger-choice" type="button" @click="mode = 'delete_data'">
          <strong>Drop out and delete subject data</strong>
          <span>Removes data and file references from the active Case-e dataset.</span>
        </button>
      </template>

      <form v-else @submit.prevent="submit">
        <label>
          Subject ID
          <select v-model.number="subjectIndex" required>
            <option :value="null" disabled>Select a subject</option>
            <option v-for="item in activeSubjects" :key="item.index" :value="item.index">
              {{ item.id }} · {{ item.group || 'Unassigned' }}
            </option>
          </select>
        </label>

        <div v-if="selectedSubject" class="subject-facts">
          <strong>{{ selectedSubject.id }}</strong>
          <span>{{ entryCount }} data record(s) · {{ fileCount }} uploaded file/reference(s)</span>
        </div>

        <label>
          Dropout date
          <input v-model="dropoutDate" type="date" required />
        </label>

        <label>
          Dropout reason
          <select v-model="reason" required>
            <option value="" disabled>Select a reason</option>
            <option v-for="item in reasons" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>

        <label v-if="reason === 'Other'">
          Other reason
          <textarea v-model.trim="otherReason" rows="3" maxlength="1000" required></textarea>
        </label>

        <div v-if="selectedSubject" class="warning" :class="{ destructive: mode === 'delete_data' }">
          <template v-if="mode === 'keep_data'">
            Subject <strong>{{ selectedSubject.id }}</strong> will be dropped out. Existing data will remain
            available for review and export, but no data can be added, edited, imported, or uploaded.
          </template>
          <template v-else>
            Subject <strong>{{ selectedSubject.id }}</strong> will be dropped out and their data will be removed
            from the active Case-e dataset. Exports, backups, DataLad/git-annex remotes, and externally hosted
            files are not deleted.
          </template>
        </div>

        <template v-if="mode === 'delete_data' && selectedSubject">
          <label class="acknowledge">
            <input v-model="acknowledged" type="checkbox" />
            I understand that the active application data cannot be restored through Case-e.
          </label>
          <label>
            Type <strong>{{ selectedSubject.id }}</strong> to confirm
            <input v-model="confirmationId" autocomplete="off" />
          </label>
        </template>

        <p v-if="error" class="error">{{ error }}</p>
        <footer>
          <button type="button" @click="mode = ''" :disabled="saving">Back</button>
          <button type="button" @click="$emit('close')" :disabled="saving">Cancel</button>
          <button class="confirm" :class="{ danger: mode === 'delete_data' }" :disabled="!canSubmit || saving">
            {{ saving ? 'Processing…' : mode === 'delete_data' ? 'Delete subject data and drop out' : 'Confirm dropout' }}
          </button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script>
const REASONS = [
  "Withdrawal of consent", "Lost to follow-up", "Adverse event", "Investigator decision",
  "Protocol deviation", "Non-compliance", "Disease progression", "Death",
  "Administrative reason", "Other",
];

export default {
  name: "SubjectDropoutDialog",
  props: {
    subjects: { type: Array, default: () => [] },
    entries: { type: Array, default: () => [] },
    files: { type: Array, default: () => [] },
    saving: { type: Boolean, default: false },
    error: { type: String, default: "" },
  },
  emits: ["close", "submit"],
  data() {
    return {
      mode: "",
      subjectIndex: null,
      dropoutDate: new Date().toISOString().slice(0, 10),
      reason: "",
      otherReason: "",
      acknowledged: false,
      confirmationId: "",
      reasons: REASONS,
    };
  },
  computed: {
    activeSubjects() {
      return this.subjects.map((subject, index) => ({
        ...subject,
        index,
        id: String(subject?.id || subject?.subject_id || `Subject ${index + 1}`),
      })).filter((subject) => String(subject.status || "ACTIVE").toUpperCase() === "ACTIVE");
    },
    selectedSubject() {
      return this.activeSubjects.find((item) => item.index === this.subjectIndex) || null;
    },
    entryCount() {
      return this.entries.filter((item) => Number(item.subject_index) === this.subjectIndex).length;
    },
    fileCount() {
      return this.files.filter((item) => Number(item.subject_index) === this.subjectIndex).length;
    },
    canSubmit() {
      if (!this.selectedSubject || !this.dropoutDate || !this.reason) return false;
      if (this.reason === "Other" && !this.otherReason) return false;
      if (this.mode === "delete_data") {
        return this.acknowledged && this.confirmationId.trim() === this.selectedSubject.id;
      }
      return true;
    },
  },
  methods: {
    submit() {
      if (!this.canSubmit) return;
      this.$emit("submit", {
        subjectIndex: this.subjectIndex,
        mode: this.mode,
        dropout_date: this.dropoutDate,
        reason: this.reason,
        other_reason: this.reason === "Other" ? this.otherReason : null,
        confirmation_subject_id: this.mode === "delete_data" ? this.confirmationId.trim() : null,
      });
    },
  },
};
</script>

<style scoped>
.dropout-backdrop { position: fixed; inset: 0; z-index: 1200; background: rgba(15,23,42,.55); display: grid; place-items: center; padding: 24px; }
.dropout-dialog { width: min(620px, 100%); max-height: 90vh; overflow: auto; background: white; border-radius: 12px; padding: 24px; box-shadow: 0 24px 70px rgba(0,0,0,.25); }
.dropout-dialog h3 { margin-top: 0; }
.choice { width: 100%; display: flex; flex-direction: column; gap: 5px; text-align: left; padding: 14px; margin: 10px 0; border: 1px solid #cbd5e1; border-radius: 8px; background: #f8fafc; }
.danger-choice { border-color: #fca5a5; background: #fff7f7; }
label { display: grid; gap: 6px; margin: 14px 0; font-weight: 600; }
select, input, textarea { padding: 9px 10px; border: 1px solid #94a3b8; border-radius: 6px; font: inherit; }
.subject-facts { display: flex; justify-content: space-between; gap: 12px; padding: 10px; background: #f1f5f9; border-radius: 6px; }
.warning { padding: 12px; border-left: 4px solid #dc2626; background: #fff1f2; color: #991b1b; margin: 16px 0; }
.destructive { border: 1px solid #dc2626; border-left-width: 5px; }
.acknowledge { display: flex; grid-template-columns: auto 1fr; align-items: flex-start; font-weight: 500; }
.error { color: #b91c1c; }
footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
footer button { padding: 9px 13px; border-radius: 6px; border: 1px solid #94a3b8; }
.confirm { background: #9f1239; color: white; border-color: #9f1239; }
.danger { background: #b91c1c; }
button:disabled { opacity: .55; cursor: not-allowed; }
</style>
