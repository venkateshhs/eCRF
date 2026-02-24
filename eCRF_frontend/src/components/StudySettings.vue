<template>
  <div class="settings-container">
    <h1>Study Settings</h1>
    <form @submit.prevent="saveSettings">
      <section class="setting-section">
        <h2>Measurement Preferences</h2>
        <div class="form-group">
          <label for="weightFormat">Weight Format</label>
          <select v-model="settings.weightFormat" id="weightFormat">
            <option value="kg">Kilograms (kg)</option>
            <option value="lbs">Pounds (lbs)</option>
            <option value="oz">Ounce (oz)</option>
          </select>
        </div>
        <div class="form-group">
          <label for="heightFormat">Height Format</label>
          <select v-model="settings.heightFormat" id="heightFormat">
            <option value="cm">Centimeters (cm)</option>
            <option value="m">Meters (m)</option>
            <option value="in">Inches (in)</option>
          </select>
        </div>
        <div class="form-group">
          <label for="temperatureFormat">Temperature Format</label>
          <select v-model="settings.temperatureFormat" id="temperatureFormat">
            <option value="celsius">Celsius (°C)</option>
            <option value="fahrenheit">Fahrenheit (°F)</option>
            <option value="kelvin">Kelvin (K)</option>
          </select>
        </div>
        <!-- Distance Unit -->
        <div class="form-group">
          <label for="distanceUnit">Distance Unit</label>
          <select v-model="settings.distanceUnit" id="distanceUnit">
            <option value="km">Kilometers (km)</option>
            <option value="miles">Miles</option>
          </select>
        </div>
        <!-- Liquid Unit -->
        <div class="form-group">
          <label for="liquidUnit">Liquid Unit</label>
          <select v-model="settings.liquidUnit" id="liquidUnit">
            <option value="litres">Litres (L)</option>
            <option value="gallons">Gallons</option>
          </select>
        </div>
      </section>

      <section class="setting-section">
        <h2>Date Formatting</h2>
        <div class="form-group">
          <label for="dateFormat">Date Format</label>
          <select v-model="settings.dateFormat" id="dateFormat">
            <option value="DD/MM/YYYY">DD/MM/YYYY</option>
            <option value="MM/DD/YYYY">MM/DD/YYYY</option>
            <option value="YYYY-MM-DD">YYYY-MM-DD</option>
            <option value="DD-MM-YYYY">DD-MM-YYYY</option>
            <option value="MM-DD-YYYY">MM-DD-YYYY</option>
            <option value="YYYY/MM/DD">YYYY/MM/DD</option>
            <option value="DD.MM.YYYY">DD.MM.YYYY</option>
          </select>
        </div>
      </section>

      <section class="setting-section">
        <h2>Locale & Time</h2>
        <div class="form-group">
          <label for="timezone">Timezone</label>
          <select v-model="settings.timezone" id="timezone">
            <option v-for="tz in timezones" :key="tz" :value="tz">{{ tz }}</option>
          </select>
        </div>
        <div class="form-group">
          <label for="locale">Language / Locale</label>
          <select v-model="settings.locale" id="locale">
            <option value="en-US">English</option>
            <option value="de-DE">German</option>
          </select>
        </div>
      </section>

      <section class="setting-section">
        <h2>Study Defaults & Behavior</h2>
        <div class="form-group">
          <label for="autoSaveInterval">Auto-Save Interval (minutes)</label>
          <input type="number" id="autoSaveInterval" v-model.number="settings.autoSaveInterval" min="1" />
        </div>
      </section>

      <section class="setting-section">
        <h2>Notification & UI Preferences</h2>
        <div class="form-group">
          <label>Notifications</label>
          <div>
            <label>
              <input type="checkbox" v-model="settings.notifications.email" />
              Email Notifications
            </label>
          </div>
          <div>
            <label>
              <input type="checkbox" v-model="settings.notifications.sms" />
              SMS Notifications
            </label>
          </div>
          <div>
            <label>
              <input type="checkbox" v-model="settings.notifications.push" />
              Push Notifications
            </label>
          </div>
        </div>
        <div class="form-group">
          <label for="uiTheme">UI Theme</label>
          <select v-model="settings.uiTheme" id="uiTheme">
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>
      </section>

      <div class="form-actions">
        <button type="submit" class="btn-save-settings">Save Settings</button>
        <button type="button" class="btn-restore" @click="restoreDefaults">Restore Defaults</button>
        <button type="button" class="btn-cancel" @click="cancelSettings">Cancel</button>
      </div>
    </form>
    <p v-if="saveMessage" class="message">{{ saveMessage }}</p>
    <p v-if="saveError" class="error">{{ saveError }}</p>
  </div>
</template>

<script>
export default {
  name: "StudySettings",
  data() {
    const defaultSettings = {
      weightFormat: "kg",
      heightFormat: "cm",
      temperatureFormat: "celsius",
      distanceUnit: "km",
      liquidUnit: "litres",
      dateFormat: "YYYY-MM-DD",
      timezone: "UTC",
      locale: "en-US",
      autoSaveInterval: 5,
      notifications: {
        email: false,
        sms: false,
        push: false,
      },
      uiTheme: "light",
    };

    return {
      settings: { ...defaultSettings },
      defaultSettings,
      timezones: [],
      saveMessage: null,
      saveError: null,
    };
  },
  computed: {
    // Retrieve the user ID from Vuex store
    userId() {
      return this.$store.state.user.id;
    },
  },
  created() {
    this.fetchTimezones();
    // If userId isn't available immediately, watch for changes.
    if (this.userId) {
      this.fetchUserSettings();
    } else {
      this.$watch(
        () => this.userId,
        (newVal) => {
          if (newVal) {
            this.fetchUserSettings();
          }
        }
      );
    }
  },
  methods: {
    async fetchTimezones() {
      try {
        const response = await fetch("/api/timezones");
        const data = await response.json();
        this.timezones = data;
      } catch (error) {
        console.error("Failed to fetch timezones, using default UTC", error);
        this.timezones = ["UTC"];
      }
    },
    async fetchUserSettings() {
      try {
        const response = await fetch(`/api/settings/${this.userId}`);
        if (response.ok) {
          const data = await response.json();
          this.settings = data;
        } else if (response.status === 404) {
          console.log("No settings found, loading defaults.");
        } else {
          console.error("Error fetching settings:", response.statusText);
        }
      } catch (error) {
        console.error("Error fetching user settings:", error);
      }
    },
    async saveSettings() {
      this.saveMessage = null;
      this.saveError = null;
      try {
        const response = await fetch(`/api/settings/${this.userId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(this.settings),
        });
        if (response.ok) {
          this.saveMessage = "Settings saved successfully.";
        } else {
          this.saveError = "Failed to save settings. Please try again.";
        }
      } catch (error) {
        console.error(error);
        this.saveError = "Failed to save settings. Please try again.";
      }
    },
    restoreDefaults() {
      this.settings = { ...this.defaultSettings };
    },
    cancelSettings() {
      this.$router.push("/profile");
    },
  },
};
</script>

<style scoped>
.settings-container {
  max-width: 800px;
  margin: 20px auto;
  padding: 30px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}
h1 {
  text-align: center;
  margin-bottom: 20px;
}
.setting-section {
  margin-bottom: 25px;
}
.setting-section h2 {
  margin-bottom: 10px;
  color: #333;
}
.form-group {
  margin-bottom: 15px;
}
.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #555;
}
.form-group input,
.form-group select {
  width: 100%;
  padding: 8px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box;
}
.form-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}
.btn-save-settings,
.btn-restore,
.btn-cancel {
  padding: 10px 20px;
  font-size: 16px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}
.btn-save-settings {
  background-color: #007bff;
  color: #fff;
}
.btn-save-settings:hover {
  background-color: #0056b3;
}
.btn-restore {
  background-color: #28a745;
  color: #fff;
}
.btn-restore:hover {
  background-color: #218838;
}
.btn-cancel {
  background-color: #6c757d;
  color: #fff;
}
.btn-cancel:hover {
  background-color: #5a6268;
}
.message {
  color: green;
  text-align: center;
  margin-top: 15px;
}
.error {
  color: red;
  text-align: center;
  margin-top: 15px;
}
</style>
