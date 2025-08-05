<template>
  <div class="date-picker">
    <input
      type="text"
      :value="formattedValue"
      :placeholder="format"
      @input="handleInput"
      @focus="showCalendar = true"
      @blur="handleBlur"
      class="date-input"
    />
    <div v-if="showCalendar" class="calendar-popup">
      <div class="calendar-header">
        <button @click="changeMonth(-1)" class="nav-button">&lt;</button>
        <span>{{ currentMonthYear }}</span>
        <button @click="changeMonth(1)" class="nav-button">&gt;</button>
      </div>
      <div class="calendar-grid">
        <div class="day-header" v-for="day in daysOfWeek" :key="day">{{ day }}</div>
        <div
          v-for="(day, index) in calendarDays"
          :key="index"
          class="calendar-day"
          :class="{ 'selected': isSelected(day), 'disabled': !isInCurrentMonth(day) }"
          @click="selectDate(day)"
        >
          {{ day ? day.date() : '' }}
        </div>
      </div>
    </div>
    <div v-if="error" class="error-message">{{ error }}</div>
  </div>
</template>

<script>
import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';

dayjs.extend(customParseFormat);

export default {
  name: 'DatePicker',
  props: {
    value: {
      type: String,
      default: ''
    },
    format: {
      type: String,
      default: 'DD-MM-YYYY'
    },
    constraints: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      showCalendar: false,
      currentDate: dayjs(),
      error: '',
      daysOfWeek: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    };
  },
  computed: {
    formattedValue() {
      if (!this.value) return '';
      const date = dayjs(this.value, this.format, true);
      return date.isValid() ? date.format(this.format) : this.value;
    },
    currentMonthYear() {
      return this.currentDate.format('MMMM YYYY');
    },
    calendarDays() {
      const startOfMonth = this.currentDate.startOf('month');
      const endOfMonth = this.currentDate.endOf('month');
      const startWeek = startOfMonth.startOf('week');
      const endWeek = endOfMonth.endOf('week');
      const days = [];
      let day = startWeek;
      while (day <= endWeek) {
        days.push(day);
        day = day.add(1, 'day');
      }
      return days;
    }
  },
  methods: {
    handleInput(event) {
      const input = event.target.value;
      const date = dayjs(input, this.format, true);
      if (date.isValid()) {
        const formatted = date.format(this.format);
        this.$emit('update:value', formatted);
        this.error = '';
        this.currentDate = date;
      } else {
        this.$emit('update:value', input);
        this.error = `Invalid date format. Use ${this.format}`;
      }
    },
    handleBlur() {
      setTimeout(() => {
        this.showCalendar = false;
      }, 200);
    },
    selectDate(day) {
      if (this.isInCurrentMonth(day)) {
        const formatted = day.format(this.format);
        this.$emit('update:value', formatted);
        this.error = '';
        this.currentDate = day;
      }
    },
    changeMonth(offset) {
      this.currentDate = this.currentDate.add(offset, 'month');
    },
    isInCurrentMonth(day) {
      return day.month() === this.currentDate.month() && day.year() === this.currentDate.year();
    },
    isSelected(day) {
      if (!this.value) return false;
      const selected = dayjs(this.value, this.format, true);
      return selected.isValid() && day.isSame(selected, 'day');
    }
  }
};
</script>

<style lang="scss" scoped>
.date-picker {
  position: relative;
  width: 100%;
}

.date-input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 5px;
  font-size: 14px;
}

.calendar-popup {
  position: absolute;
  top: 100%;
  left: 0;
  background: white;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
  z-index: 1000;
  padding: 10px;
  width: 250px;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.nav-button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 5px;
}

.day-header {
  text-align: center;
  font-weight: bold;
}

.calendar-day {
  text-align: center;
  padding: 5px;
  cursor: pointer;
}

.calendar-day:hover:not(.disabled) {
  background: #e3effd;
}

.calendar-day.selected {
  background: #007bff;
  color: white;
  border-radius: 3px;
}

.calendar-day.disabled {
  color: #ccc;
  cursor: not-allowed;
}

.error-message {
  color: red;
  font-size: 12px;
  margin-top: 5px;
}
</style>