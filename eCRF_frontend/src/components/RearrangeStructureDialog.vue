<template>
  <div class="dialog">
    <div class="header">
      <h3>Rearrange Structure</h3>

      <div class="header-actions">
        <button
          class="icon-btn"
          type="button"
          title="Expand all"
          @click="expandAll"
        >
          <i :class="icons.toggleDown"></i>
        </button>

        <button
          class="icon-btn"
          type="button"
          title="Collapse all"
          @click="collapseAll"
        >
          <i :class="icons.toggleUp"></i>
        </button>

        <button class="close-btn" type="button" @click="$emit('close')">✕</button>
      </div>
    </div>

    <div
      ref="scrollBody"
      class="body"
      @dragover.prevent="onBodyDragOver"
      @drop.prevent="stopAutoScroll"
      @dragleave="onBodyDragLeave"
    >
      <template v-for="(section, si) in localSections" :key="section._id">
        <!-- SECTION INSERT LINE -->
        <div
          class="section-insert-line"
          :class="{ active: isActiveSectionDrop(si) }"
          @mouseenter="onSectionInsertEnter(si)"
        ></div>

        <div class="section-node">
          <div
            class="section-row"
            :class="{
              dragging: sectionDrag.active && sectionDrag.fromIndex === si,
              'field-drop-active': isCollapsedSectionFieldDrop(si)
            }"
            @dragover.prevent="onCollapsedSectionFieldOver(si, $event)"
            @drop.prevent="dropFieldToCollapsedSection(si)"
          >
            <button
              class="icon-btn collapse-btn"
              type="button"
              :title="isExpanded(section._id) ? 'Collapse' : 'Expand'"
              @click.stop="toggleSection(section._id)"
            >
              <i :class="isExpanded(section._id) ? icons.toggleUp : icons.toggleDown"></i>
            </button>

            <span
              class="section-handle"
              title="Move section"
              @mousedown.stop.prevent="startSectionPointerDrag(si, $event)"
            >
              <i :class="icons.move || 'fas fa-grip-vertical'"></i>
            </span>

            <span class="section-label">{{ section.title }}</span>
          </div>

          <div v-if="isExpanded(section._id)" class="children">
            <template v-if="section.fields && section.fields.length">
              <template v-for="(field, fi) in section.fields" :key="field._id">
                <div
                  class="field-insert-line"
                  :class="{ active: isActiveFieldDrop(si, fi) }"
                  @dragover.prevent="onFieldInsertOver(si, fi, $event)"
                  @drop.prevent="dropFieldAt(si, fi)"
                ></div>

                <div
                  class="field-row"
                  draggable="true"
                  @dragstart.stop="startField(si, fi, $event)"
                  @dragend="resetFieldDrag"
                  @dragover.prevent="onFieldInsertOver(si, fi, $event)"
                  @drop.prevent="dropFieldAt(si, fi)"
                >
                  <span class="tree-branch">↳</span>
                  <span class="field-label">{{ field.label || field.name }}</span>
                </div>
              </template>

              <div
                class="field-insert-line end"
                :class="{ active: isActiveFieldDrop(si, section.fields.length) }"
                @dragover.prevent="onFieldInsertOver(si, section.fields.length, $event)"
                @drop.prevent="dropFieldAt(si, section.fields.length)"
              ></div>
            </template>

            <template v-else>
              <div
                class="empty-drop"
                :class="{ active: isActiveFieldDrop(si, 0) }"
                @dragover.prevent="onFieldInsertOver(si, 0, $event)"
                @drop.prevent="dropFieldAt(si, 0)"
              >
                Drop field here
              </div>
            </template>
          </div>
        </div>
      </template>

      <div
        class="section-insert-line last"
        :class="{ active: isActiveSectionDrop(localSections.length) }"
        @mouseenter="onSectionInsertEnter(localSections.length)"
      ></div>
    </div>

    <div class="footer">
      <div v-if="sectionDrag.active" class="drag-hint">
        Moving section. Release mouse to drop.
      </div>

      <div class="footer-actions">
        <button class="btn-option" type="button" @click="$emit('close')">Cancel</button>
        <button class="btn-primary" type="button" @click="save">Save</button>
      </div>
    </div>
  </div>
</template>

<script>
import icons from "@/assets/styles/icons";

export default {
  name: "RearrangeStructureDialog",
  props: {
    sections: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      icons,
      localSections: [],

      fieldDrag: {
        active: false,
        fromSection: null,
        fromField: null
      },
      fieldHover: {
        sectionIndex: null,
        fieldIndex: null,
        mode: null // "insert" | "collapsed-section"
      },

      sectionDrag: {
        active: false,
        fromIndex: null,
        overIndex: null
      },

      expandedSectionIds: [],

      autoScrollFrame: null,
      autoScrollDirection: 0,
      autoScrollSpeed: 14,
      lastPointerY: null
    };
  },
  mounted() {
    this.localSections = JSON.parse(JSON.stringify(this.sections || []));
    this.expandedSectionIds = this.localSections.map(s => s._id);
  },
  beforeUnmount() {
    this.cleanupSectionPointerDrag();
    this.stopAutoScroll();
  },
  methods: {
    save() {
      this.$emit("save", JSON.parse(JSON.stringify(this.localSections)));
    },

    isExpanded(sectionId) {
      return this.expandedSectionIds.includes(sectionId);
    },

    toggleSection(sectionId) {
      if (this.isExpanded(sectionId)) {
        this.expandedSectionIds = this.expandedSectionIds.filter(id => id !== sectionId);
      } else {
        this.expandedSectionIds = [...this.expandedSectionIds, sectionId];
      }
    },

    expandAll() {
      this.expandedSectionIds = this.localSections.map(s => s._id);
    },

    collapseAll() {
      this.expandedSectionIds = [];
    },

    onBodyDragOver(evt) {
      this.lastPointerY = evt.clientY;
      this.updateAutoScrollByPointer(evt.clientY);
    },

    onBodyDragLeave(evt) {
      const body = this.$refs.scrollBody;
      if (!body) return;

      const rect = body.getBoundingClientRect();
      const stillInside =
        evt.clientX >= rect.left &&
        evt.clientX <= rect.right &&
        evt.clientY >= rect.top &&
        evt.clientY <= rect.bottom;

      if (!stillInside) this.stopAutoScroll();
    },

    updateAutoScrollByPointer(clientY) {
      const body = this.$refs.scrollBody;
      if (!body) return;

      const rect = body.getBoundingClientRect();
      const threshold = 70;

      if (clientY < rect.top + threshold) {
        this.startAutoScroll(-1);
      } else if (clientY > rect.bottom - threshold) {
        this.startAutoScroll(1);
      } else {
        this.stopAutoScroll();
      }
    },

    startAutoScroll(direction) {
      if (this.autoScrollDirection === direction && this.autoScrollFrame) return;

      this.autoScrollDirection = direction;
      this.stopAutoScrollFrameOnly();

      const tick = () => {
        const body = this.$refs.scrollBody;
        if (!body || !this.autoScrollDirection) return;

        body.scrollTop += this.autoScrollSpeed * this.autoScrollDirection;
        this.autoScrollFrame = requestAnimationFrame(tick);
      };

      this.autoScrollFrame = requestAnimationFrame(tick);
    },

    stopAutoScrollFrameOnly() {
      if (this.autoScrollFrame) {
        cancelAnimationFrame(this.autoScrollFrame);
        this.autoScrollFrame = null;
      }
    },

    stopAutoScroll() {
      this.autoScrollDirection = 0;
      this.stopAutoScrollFrameOnly();
    },

    startSectionPointerDrag(si, evt) {
      this.sectionDrag = {
        active: true,
        fromIndex: si,
        overIndex: si
      };

      this.lastPointerY = evt.clientY;
      document.addEventListener("mousemove", this.onSectionPointerMove);
      document.addEventListener("mouseup", this.onSectionPointerUp);
      document.body.classList.add("no-select");
    },

    onSectionPointerMove(evt) {
      this.lastPointerY = evt.clientY;
      this.updateAutoScrollByPointer(evt.clientY);
    },

    onSectionInsertEnter(si) {
      if (!this.sectionDrag.active) return;
      this.sectionDrag.overIndex = si;
    },

    onSectionPointerUp() {
      if (!this.sectionDrag.active) {
        this.cleanupSectionPointerDrag();
        return;
      }

      const from = this.sectionDrag.fromIndex;
      let to = this.sectionDrag.overIndex;

      if (Number.isInteger(from) && Number.isInteger(to)) {
        const arr = this.localSections.slice();
        const moved = arr.splice(from, 1)[0];

        if (from < to) to -= 1;
        to = Math.max(0, Math.min(to, arr.length));

        arr.splice(to, 0, moved);
        this.localSections = arr;
      }

      this.cleanupSectionPointerDrag();
    },

    cleanupSectionPointerDrag() {
      document.removeEventListener("mousemove", this.onSectionPointerMove);
      document.removeEventListener("mouseup", this.onSectionPointerUp);
      document.body.classList.remove("no-select");

      this.sectionDrag = {
        active: false,
        fromIndex: null,
        overIndex: null
      };

      this.stopAutoScroll();
    },

    isActiveSectionDrop(si) {
      return this.sectionDrag.active && this.sectionDrag.overIndex === si;
    },

    startField(si, fi, evt) {
      this.fieldDrag = {
        active: true,
        fromSection: si,
        fromField: fi
      };

      try {
        evt.dataTransfer.effectAllowed = "move";
        evt.dataTransfer.setData("text/plain", "field");
      } catch (e) {
        console.error(e);
      }
    },

    resetFieldDrag() {
      this.fieldDrag = {
        active: false,
        fromSection: null,
        fromField: null
      };
      this.fieldHover = {
        sectionIndex: null,
        fieldIndex: null,
        mode: null
      };
      this.stopAutoScroll();
    },

    onFieldInsertOver(si, fi, evt) {
      if (!this.fieldDrag.active) return;
      evt.dataTransfer.dropEffect = "move";

      this.fieldHover = {
        sectionIndex: si,
        fieldIndex: fi,
        mode: "insert"
      };

      this.lastPointerY = evt.clientY;
      this.updateAutoScrollByPointer(evt.clientY);
    },

    onCollapsedSectionFieldOver(si, evt) {
      if (!this.fieldDrag.active) return;
      if (this.isExpanded(this.localSections[si]?._id)) return;

      evt.dataTransfer.dropEffect = "move";
      this.fieldHover = {
        sectionIndex: si,
        fieldIndex: null,
        mode: "collapsed-section"
      };

      this.lastPointerY = evt.clientY;
      this.updateAutoScrollByPointer(evt.clientY);
    },

    dropFieldAt(targetSectionIndex, targetFieldIndex) {
      if (!this.fieldDrag.active) return;

      const fromS = this.fieldDrag.fromSection;
      const fromF = this.fieldDrag.fromField;

      if (!Number.isInteger(fromS) || !Number.isInteger(fromF)) {
        this.resetFieldDrag();
        return;
      }

      const sections = this.localSections.slice();
      const sourceSection = sections[fromS];
      const targetSection = sections[targetSectionIndex];

      if (!sourceSection || !targetSection) {
        this.resetFieldDrag();
        return;
      }

      if (!Array.isArray(sourceSection.fields)) sourceSection.fields = [];
      if (!Array.isArray(targetSection.fields)) targetSection.fields = [];

      const moved = sourceSection.fields.splice(fromF, 1)[0];
      if (!moved) {
        this.resetFieldDrag();
        return;
      }

      let insertAt = targetFieldIndex;
      if (fromS === targetSectionIndex && fromF < targetFieldIndex) {
        insertAt -= 1;
      }

      insertAt = Math.max(0, Math.min(insertAt, targetSection.fields.length));
      targetSection.fields.splice(insertAt, 0, moved);

      this.localSections = sections;
      this.resetFieldDrag();
    },

    dropFieldToCollapsedSection(targetSectionIndex) {
      if (!this.fieldDrag.active) return;
      if (this.isExpanded(this.localSections[targetSectionIndex]?._id)) return;

      const fromS = this.fieldDrag.fromSection;
      const fromF = this.fieldDrag.fromField;

      if (!Number.isInteger(fromS) || !Number.isInteger(fromF)) {
        this.resetFieldDrag();
        return;
      }

      const sections = this.localSections.slice();
      const sourceSection = sections[fromS];
      const targetSection = sections[targetSectionIndex];

      if (!sourceSection || !targetSection) {
        this.resetFieldDrag();
        return;
      }

      if (!Array.isArray(sourceSection.fields)) sourceSection.fields = [];
      if (!Array.isArray(targetSection.fields)) targetSection.fields = [];

      const moved = sourceSection.fields.splice(fromF, 1)[0];
      if (!moved) {
        this.resetFieldDrag();
        return;
      }

      targetSection.fields.push(moved);

      this.localSections = sections;
      this.resetFieldDrag();
    },

    isActiveFieldDrop(si, fi) {
      return (
        this.fieldHover.sectionIndex === si &&
        this.fieldHover.fieldIndex === fi &&
        this.fieldHover.mode === "insert"
      );
    },

    isCollapsedSectionFieldDrop(si) {
      return (
        this.fieldHover.sectionIndex === si &&
        this.fieldHover.mode === "collapsed-section"
      );
    }
  }
};
</script>

<style scoped>
.dialog {
  width: min(94vw, 920px);
  height: min(86vh, 760px);
  background: #fff;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.16);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
}

.header h3 {
  margin: 0;
  font-size: 16px;
  color: #111827;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}

.icon-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #4b5563;
  transition: background 0.15s ease, color 0.15s ease;
}

.icon-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #111827;
}

.close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 17px;
  color: #6b7280;
  border-radius: 8px;
  padding: 4px 8px;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.06);
}

.body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 14px 12px;
  background: linear-gradient(to bottom, #fcfcfd, #fafbfc);
}

.section-insert-line {
  height: 8px;
  margin: 1px 0 2px;
  border-radius: 999px;
}

.section-insert-line.last {
  margin-top: 4px;
}

.section-insert-line.active,
.field-insert-line.active,
.empty-drop.active,
.section-row.field-drop-active {
  background: rgba(37, 99, 235, 0.16);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.42);
}

.section-node {
  border: 1px solid #dbe2ea;
  border-radius: 10px;
  background: #fff;
  margin-bottom: 6px;
  overflow: hidden;
}

.section-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 5px 8px;
  background: #f3f6fb;
  border-bottom: 1px solid #e9eef5;
  transition: background 0.12s ease;
}

.section-row.dragging {
  background: #eaf2ff;
}

.collapse-btn {
  flex: 0 0 auto;
}

.section-handle {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  cursor: grab;
  border-radius: 6px;
  flex: 0 0 auto;
  transition: background 0.15s ease, color 0.15s ease;
}

.section-handle:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #111827;
}

.section-label {
  font-weight: 700;
  font-size: 13px;
  color: #111827;
  line-height: 1.15;
}

.children {
  padding: 2px 8px 4px 18px;
}

.field-insert-line {
  height: 4px;
  margin: 0;
  border-radius: 999px;
}

.field-insert-line.end {
  margin-top: 1px;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 20px;
  padding: 0;
  cursor: grab;
  user-select: none;
}

.field-row:active {
  cursor: grabbing;
}

.tree-branch {
  color: #94a3b8;
  font-size: 11px;
  width: 12px;
  flex: 0 0 12px;
  text-align: center;
  line-height: 1;
}

.field-label {
  font-size: 12px;
  line-height: 1.05;
  color: #374151;
  padding: 0;
  margin: 0;
}

.field-row:hover .field-label {
  color: #111827;
}

.empty-drop {
  min-height: 24px;
  display: flex;
  align-items: center;
  padding-left: 16px;
  color: #94a3b8;
  font-size: 11px;
  border-radius: 6px;
}

.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

.drag-hint {
  font-size: 12px;
  color: #6b7280;
}

.footer-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.btn-option {
  border: 1px solid #d1d5db;
  background: #f8fafc;
  color: #374151;
  padding: 7px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}

.btn-primary {
  border: none;
  background: #2563eb;
  color: #fff;
  padding: 7px 13px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}

.btn-option:hover {
  background: #f1f5f9;
}

.btn-primary:hover {
  background: #1d4ed8;
}
</style>