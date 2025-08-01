// Import LitElement directly from the CDN for Home Assistant compatibility
import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit@2.0.0/index.js?module";

// import { LitElement, html, css } from "lit";

class MedicationTrackerPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object, attribute: false },
      narrow: { type: Object, attribute: false },
      panel: { type: Object, attribute: false },
      _medications: { type: Array, state: true },
      _loading: { type: Boolean, state: true },
      _showAddDialog: { type: Boolean, state: true },
      _showEditDialog: { type: Boolean, state: true },
      _newMedication: { type: Object, state: true },
      _editMedication: { type: Object, state: true },
      _editMedicationId: { type: String, state: true },
    };
  }

  constructor() {
    super();
    this._medications = [];
    this._loading = true;
    this._showAddDialog = false;
    this._showEditDialog = false;
    this._newMedication = {
      name: "",
      dosage: "",
      frequency: "daily",
      times: ["09:00"],
      start_date: "",
      end_date: "",
      notes: "",
    };
    this._editMedication = {
      name: "",
      dosage: "",
      frequency: "daily",
      times: ["09:00"],
      start_date: "",
      end_date: "",
      notes: "",
    };
    this._editMedicationId = "";
    this._refreshInterval = null;
    this._hassUpdateTimeout = null;
  }

  connectedCallback() {
    super.connectedCallback();
    // Set up periodic refresh every 30 seconds
    this._refreshInterval = setInterval(() => {
      if (this.hass && !this._loading) {
        this._loadMedications();
      }
    }, 30000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    // Clean up the refresh interval
    if (this._refreshInterval) {
      clearInterval(this._refreshInterval);
      this._refreshInterval = null;
    }
    // Clean up the hass update timeout
    if (this._hassUpdateTimeout) {
      clearTimeout(this._hassUpdateTimeout);
      this._hassUpdateTimeout = null;
    }
  }

  static get styles() {
    return css`
      :host {
        padding: 16px;
        display: block;
        max-width: 1200px;
        margin: 0 auto;
      }

      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--divider-color);
      }

      .title {
        font-size: 2em;
        font-weight: 300;
        color: var(--primary-text-color);
        margin: 0;
      }

      .add-button {
        background: var(--primary-color);
        color: var(--text-primary-color);
        border: none;
        border-radius: 4px;
        padding: 12px 24px;
        font-size: 14px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .add-button:hover {
        -moz-box-shadow: inset 0 0 100px 100px rgba(255, 255, 255, 0.3);
        -webkit-box-shadow: inset 0 0 100px 100px rgba(255, 255, 255, 0.3);
        box-shadow: inset 0 0 100px 100px rgba(255, 255, 255, 0.3);
      }

      .header-buttons {
        display: flex;
        gap: 12px;
        align-items: center;
      }

      .medications-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 16px;
        margin-top: 24px;
      }

      .medication-card {
        background: var(--card-background-color);
        border-radius: 8px;
        padding: 16px;
        box-shadow: var(--ha-card-box-shadow);
        border: 1px solid var(--divider-color);
      }

      .medication-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
      }

      .medication-name {
        font-size: 1.2em;
        font-weight: 500;
        color: var(--primary-text-color);
        margin: 0;
      }

      .medication-id {
        font-size: 0.8em;
        color: var(--secondary-text-color);
        background: var(--disabled-text-color);
        padding: 2px 6px;
        border-radius: 3px;
        font-family: monospace;
      }

      .medication-details {
        margin-bottom: 16px;
      }

      .medication-detail {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
        font-size: 0.9em;
      }

      .detail-label {
        color: var(--secondary-text-color);
      }

      .detail-value {
        color: var(--primary-text-color);
        font-weight: 500;
      }

      .medication-status {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: 500;
        text-transform: uppercase;
      }

      .status-due {
        background: var(--error-color);
        color: var(--text-primary-color);
      }

      .status-taken {
        background: var(--success-color);
        color: var(--text-primary-color);
      }

      .status-overdue {
        background: var(--warning-color);
        color: var(--text-primary-color);
      }

      .status-not-due {
        background: var(--disabled-text-color);
        color: var(--text-primary-color);
      }

      .status-skipped {
        background: var(--info-color);
        color: var(--text-primary-color);
      }

      .medication-actions {
        display: flex;
        gap: 8px;
        margin-top: 12px;
      }

      .action-button {
        flex: 1;
        padding: 8px 12px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.9em;
        font-weight: 500;
      }

      .action-button:hover {
        -moz-box-shadow: inset 0 0 100px 100px rgba(255, 255, 255, 0.3);
        -webkit-box-shadow: inset 0 0 100px 100px rgba(255, 255, 255, 0.3);
        box-shadow: inset 0 0 100px 100px rgba(255, 255, 255, 0.3);
      }

      .take-button {
        background: var(--success-color);
        color: var(--text-primary-color);
      }

      .skip-button {
        background: var(--warning-color);
        color: var(--text-primary-color);
      }

      .edit-button {
        background: var(--primary-color);
        color: var(--text-primary-color);
        flex: 0;
        padding: 8px;
      }

      .remove-button {
        background: var(--error-color);
        color: var(--text-primary-color);
        flex: 0;
        padding: 8px;
      }

      .dialog-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
      }

      .dialog {
        background: var(--card-background-color);
        border-radius: 8px;
        padding: 24px;
        max-width: 500px;
        width: 90%;
        max-height: 80vh;
        overflow-y: auto;
      }

      .dialog-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
      }

      .dialog-title {
        font-size: 1.5em;
        font-weight: 500;
        margin: 0;
      }

      .close-button {
        background: none;
        border: none;
        font-size: 1.5em;
        cursor: pointer;
        color: var(--secondary-text-color);
      }

      .form-field {
        margin-bottom: 16px;
      }

      .form-label {
        display: block;
        margin-bottom: 4px;
        font-weight: 500;
        color: var(--primary-text-color);
      }

      .form-input,
      .form-select,
      .form-textarea {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 14px;
        box-sizing: border-box;
      }

      .form-textarea {
        min-height: 80px;
        resize: vertical;
      }

      .times-input {
        display: flex;
        gap: 8px;
        align-items: center;
        margin-bottom: 8px;
      }

      .times-input input {
        flex: 1;
      }

      .remove-time-button {
        background: var(--error-color);
        color: var(--text-primary-color);
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
        cursor: pointer;
      }

      .add-time-button {
        background: var(--primary-color);
        color: var(--text-primary-color);
        border: none;
        border-radius: 4px;
        padding: 8px 12px;
        cursor: pointer;
        margin-top: 8px;
      }

      .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        margin-top: 24px;
      }

      .dialog-button {
        padding: 10px 20px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-weight: 500;
      }

      .cancel-button {
        background: var(--secondary-color);
        color: var(--text-primary-color);
      }

      .save-button {
        background: var(--primary-color);
        color: var(--text-primary-color);
      }

      .loading {
        text-align: center;
        padding: 48px;
        color: var(--secondary-text-color);
      }

      .empty-state {
        text-align: center;
        padding: 48px;
        color: var(--secondary-text-color);
      }

      .empty-icon {
        font-size: 4em;
        margin-bottom: 16px;
        opacity: 0.5;
      }

          .main-title {
        margin: 0 0 0 0;
        line-height: 20px;
        flex-grow: 1;
    }
            .toolbar {
        height: var(--header-height);
        display: flex;
        align-items: center;
        font-size: 20px;
        padding: 0;
        font-weight: 400;
        box-sizing: border-box;
    }
    `;
  }

  firstUpdated() {
    this._loadMedications();
  }

  willUpdate(changedProps) {
    super.willUpdate(changedProps);
    // Refresh medications when hass object changes (entity states updated)
    if (changedProps.has('hass') && this.hass && !this._loading) {
      // Debounce to avoid too frequent updates
      clearTimeout(this._hassUpdateTimeout);
      this._hassUpdateTimeout = setTimeout(() => {
        this._loadMedications();
      }, 500);
    }
  }

  async _loadMedications() {
    this._loading = true;
    try {
      // Get all entities from the medication_tracker domain
      const entities = Object.keys(this.hass.states).filter((entityId) =>
        entityId.startsWith("sensor.") && entityId.includes("_status")
      );

      console.log("Found status entities:", entities);

      // Debug: let's see what ID sensors exist
      const allIdSensors = Object.keys(this.hass.states).filter(id =>
        id.startsWith("sensor.") && id.endsWith("_id")
      );
      console.log("All ID sensors found:", allIdSensors);

      const medications = [];
      for (const entityId of entities) {
        const state = this.hass.states[entityId];
        if (state.attributes.medication_name) {
          // For duplicate names, Home Assistant generates IDs like:
          // - sensor.jklhi_status -> sensor.jklhi_status_2
          // - sensor.jklhi_id -> sensor.jklhi_id_2
          // The pattern is that the suffix (_2, _3, etc.) goes at the very end

          let baseName, suffix = "";
          const entityWithoutDomain = entityId.replace("sensor.", "");

          // Check if this is a duplicate (has _status_N pattern)
          const statusDuplicateMatch = entityWithoutDomain.match(/^(.+)_status_(\d+)$/);
          if (statusDuplicateMatch) {
            // This is a duplicate: "name_status_2" -> baseName="name", suffix="_2"
            baseName = statusDuplicateMatch[1];
            suffix = `_${statusDuplicateMatch[2]}`;
          } else {
            // This is the first instance: "name_status" -> baseName="name", suffix=""
            baseName = entityWithoutDomain.replace("_status", "");
          }

          // Construct the related entity IDs with correct suffix placement
          const idSensorId = `sensor.${baseName}_id${suffix}`;
          const adherenceSensorId = `sensor.${baseName}_adherence${suffix}`;
          const dueSensorId = `binary_sensor.${baseName}_due${suffix}`;

          console.log(`Mapping ${entityId} -> ID sensor: ${idSensorId}`);

          const idSensor = this.hass.states[idSensorId];
          const adherenceSensor = this.hass.states[adherenceSensorId];
          const dueSensor = this.hass.states[dueSensorId];

          // The actual medication ID should ALWAYS be from the ID sensor state (UUID)
          // This is critical for duplicate medication names where entity IDs get _2, _3, etc
          let actualMedicationId = idSensor?.state;

          // Only fall back if ID sensor is truly unavailable, empty, or in error state
          if (!actualMedicationId || actualMedicationId === "unknown" || actualMedicationId === "unavailable" || actualMedicationId === "null") {
            // Fallback to medication_id in the status sensor attributes, then base ID as last resort
            actualMedicationId = state.attributes.medication_id || `${baseName}${suffix}`;
            console.warn("ID sensor unavailable for", entityId, "falling back to:", actualMedicationId);
          }

          console.log("Entity:", entityId, "Base:", baseName, "Suffix:", suffix, "Actual ID:", actualMedicationId, "ID Sensor:", idSensor?.state);

          // Validate that we have a proper UUID (basic check)
          const isUUID = actualMedicationId && actualMedicationId.length > 10 && actualMedicationId.includes('-');
          if (!isUUID) {
            console.warn("Warning: Medication ID doesn't look like a UUID:", actualMedicationId, "for entity:", entityId);
          }

          medications.push({
            // Use the actual medication ID for service calls
            id: actualMedicationId, // This should be a UUID (e.g., "12345678-1234-1234-1234-123456789abc")
            displayId: idSensor?.state || actualMedicationId, // This is what we show to the user
            name: state.attributes.medication_name,
            status: state.state,
            dosage: state.attributes.dosage,
            frequency: state.attributes.frequency,
            times: state.attributes.times || [],
            adherence: adherenceSensor?.state || 0,
            due: dueSensor?.state === "on",
            start_date: state.attributes.start_date,
            end_date: state.attributes.end_date,
            notes: state.attributes.notes,
            next_due: state.attributes.next_due,
            last_taken: state.attributes.last_taken,
          });
        }
      }

      this._medications = medications;
    } catch (error) {
      console.error("Error loading medications:", error);
    } finally {
      this._loading = false;
    }

    // Force a re-render to update the UI
    this.requestUpdate();
  }

  async _refreshMedications() {
    // Manual refresh triggered by user
    console.log("Manual refresh triggered");
    await this._loadMedications();
  }

  async _takeMedication(medicationId) {
    console.log("Taking medication with ID:", medicationId);
    console.log("Current medications data:", this._medications);
    try {
      await this.hass.callService("medication_tracker", "take_medication", {
        medication_id: medicationId,
      });
      // Add a small delay to ensure the backend has processed the change
      setTimeout(() => this._loadMedications(), 500);
    } catch (error) {
      console.error("Error taking medication:", error);
    }
  }

  async _skipMedication(medicationId) {
    console.log("Skipping medication with ID:", medicationId);
    try {
      await this.hass.callService("medication_tracker", "skip_medication", {
        medication_id: medicationId,
      });
      // Add a small delay to ensure the backend has processed the change
      setTimeout(() => this._loadMedications(), 500);
    } catch (error) {
      console.error("Error skipping medication:", error);
    }
  }

  async _removeMedication(medicationId) {
    console.log("Removing medication with ID:", medicationId);
    if (!confirm("Are you sure you want to remove this medication?")) {
      return;
    }

    try {
      await this.hass.callService("medication_tracker", "remove_medication", {
        medication_id: medicationId,
      });
      // Add a small delay to ensure the backend has processed the change
      setTimeout(() => this._loadMedications(), 500);
    } catch (error) {
      console.error("Error removing medication:", error);
    }
  }

  _showAddMedicationDialog() {
    this._showAddDialog = true;
  }

  _hideAddMedicationDialog() {
    this._showAddDialog = false;
    this._resetNewMedication();
  }

  _resetNewMedication() {
    this._newMedication = {
      name: "",
      dosage: "",
      frequency: "daily",
      times: ["09:00"],
      start_date: "",
      end_date: "",
      notes: "",
    };
  }

  _updateNewMedication(field, value) {
    this._newMedication = { ...this._newMedication, [field]: value };
  }

  _addTime() {
    this._newMedication = {
      ...this._newMedication,
      times: [...this._newMedication.times, "09:00"],
    };
  }

  _removeTime(index) {
    const times = [...this._newMedication.times];
    times.splice(index, 1);
    this._newMedication = { ...this._newMedication, times };
  }

  _updateTime(index, value) {
    const times = [...this._newMedication.times];
    times[index] = value;
    this._newMedication = { ...this._newMedication, times };
  }

  async _saveMedication() {
    try {
      const data = {
        name: this._newMedication.name,
        dosage: this._newMedication.dosage,
        frequency: this._newMedication.frequency,
        times: this._newMedication.times,
        notes: this._newMedication.notes,
      };

      if (this._newMedication.start_date) {
        data.start_date = this._newMedication.start_date;
      }

      if (this._newMedication.end_date) {
        data.end_date = this._newMedication.end_date;
      }

      await this.hass.callService("medication_tracker", "add_medication", data);
      this._hideAddMedicationDialog();
      // Add a small delay to ensure the backend has processed the change
      setTimeout(() => this._loadMedications(), 500);
    } catch (error) {
      console.error("Error adding medication:", error);
    }
  }

  _showEditMedicationDialog(medicationId) {
    const medication = this._medications.find((med) => med.id === medicationId);
    if (!medication) {
      console.error("Medication not found:", medicationId);
      return;
    }

    this._editMedicationId = medicationId;
    this._editMedication = {
      name: medication.name,
      dosage: medication.dosage,
      frequency: medication.frequency,
      times: [...medication.times],
      start_date: medication.start_date || "",
      end_date: medication.end_date || "",
      notes: medication.notes || "",
    };
    this._showEditDialog = true;
  }

  _hideEditMedicationDialog() {
    this._showEditDialog = false;
    this._editMedicationId = "";
    this._resetEditMedication();
  }

  _resetEditMedication() {
    this._editMedication = {
      name: "",
      dosage: "",
      frequency: "daily",
      times: ["09:00"],
      start_date: "",
      end_date: "",
      notes: "",
    };
  }

  _updateEditMedication(field, value) {
    this._editMedication = { ...this._editMedication, [field]: value };
  }

  _addEditTime() {
    this._editMedication = {
      ...this._editMedication,
      times: [...this._editMedication.times, "09:00"],
    };
  }

  _removeEditTime(index) {
    const times = [...this._editMedication.times];
    times.splice(index, 1);
    this._editMedication = { ...this._editMedication, times };
  }

  _updateEditTime(index, value) {
    const times = [...this._editMedication.times];
    times[index] = value;
    this._editMedication = { ...this._editMedication, times };
  }

  async _updateMedication() {
    try {
      const data = {
        medication_id: this._editMedicationId,
        name: this._editMedication.name,
        dosage: this._editMedication.dosage,
        frequency: this._editMedication.frequency,
        times: this._editMedication.times,
        notes: this._editMedication.notes,
      };

      if (this._editMedication.start_date) {
        data.start_date = this._editMedication.start_date;
      }

      if (this._editMedication.end_date) {
        data.end_date = this._editMedication.end_date;
      }

      await this.hass.callService("medication_tracker", "update_medication", data);
      this._hideEditMedicationDialog();
      // Add a small delay to ensure the backend has processed the change
      setTimeout(() => this._loadMedications(), 500);
    } catch (error) {
      console.error("Error updating medication:", error);
    }
  }

  _getStatusClass(status) {
    return `medication-status status-${status.replace("_", "-")}`;
  }

  _formatDate(dateString) {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleDateString();
  }

  _formatTime(timeString) {
    if (!timeString) return "—";
    return new Date(timeString).toLocaleString();
  }

  render() {
    return html`


            <div class="header">
              <div class="toolbar">
                <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
                <div class="main-title">
                  Medication Tracker
                </div>
              </div>
              <div class="header-buttons">
                <button class="add-button" @click=${this._showAddMedicationDialog}>
                  <ha-icon icon="mdi:plus"></ha-icon>
                  Add Medication
                </button>
              </div>
            </div>

      ${this._loading
        ? html`<div class="loading">Loading medications...</div>`
        : this._medications.length === 0
          ? html`
            <div class="empty-state">
              <div class="empty-icon">💊</div>
              <h3>No medications found</h3>
              <p>Click "Add Medication" to get started.</p>
            </div>
          `
          : html`
            <div class="medications-grid">
              ${this._medications.map(
            (med) => html`
                  <div class="medication-card">
                    <div class="medication-header">
                      <h3 class="medication-name">${med.name}</h3>
                      <span class="medication-id">${med.displayId}</span>
                    </div>

                    <div class="medication-details">
                      <div class="medication-detail">
                        <span class="detail-label">Status:</span>
                        <span class="${this._getStatusClass(med.status)}"
                          >${med.status.replace("_", " ")}</span
                        >
                      </div>
                      <div class="medication-detail">
                        <span class="detail-label">Dosage:</span>
                        <span class="detail-value">${med.dosage}</span>
                      </div>
                      <div class="medication-detail">
                        <span class="detail-label">Frequency:</span>
                        <span class="detail-value">${med.frequency}</span>
                      </div>
                      <div class="medication-detail">
                        <span class="detail-label">Times:</span>
                        <span class="detail-value"
                          >${med.times.join(", ") || "—"}</span
                        >
                      </div>
                      <div class="medication-detail">
                        <span class="detail-label">Adherence:</span>
                        <span class="detail-value">${med.adherence}%</span>
                      </div>
                      <div class="medication-detail">
                        <span class="detail-label">Next Due:</span>
                        <span class="detail-value"
                          >${this._formatTime(med.next_due)}</span
                        >
                      </div>
                      <div class="medication-detail">
                        <span class="detail-label">Last Taken:</span>
                        <span class="detail-value"
                          >${this._formatTime(med.last_taken)}</span
                        >
                      </div>
                      <div class="medication-detail">
                        <span class="detail-label">Start Date:</span>
                        <span class="detail-value"
                          >${this._formatDate(med.start_date)}</span
                        >
                      </div>
                      <div class="medication-detail">
                        <span class="detail-label">End Date:</span>
                        <span class="detail-value"
                          >${this._formatDate(med.end_date)}</span
                        >
                      </div>
                    </div>

                    <div class="medication-actions">
                        ${med.due
                ? html`
                              <button
                                class="action-button take-button"
                                @click=${() => this._takeMedication(med.id)}
                              >
                                Take
                              </button>
                              <button
                                class="action-button skip-button"
                                @click=${() => this._skipMedication(med.id)}
                              >
                                Skip
                              </button>
                            `
                : html`
                              <button
                                class="action-button take-button"
                                @click=${() => this._takeMedication(med.id)}
                              >
                                Take
                              </button>
                            `}
                        <button
                          class="action-button edit-button"
                          @click=${() => this._showEditMedicationDialog(med.id)}
                          title="Edit medication"
                        >
                          <ha-icon icon="mdi:pencil"></ha-icon>
                        </button>
                        <button
                          class="action-button remove-button"
                          @click=${() => this._removeMedication(med.id)}
                          title="Remove medication"
                        >
                          <ha-icon icon="mdi:delete"></ha-icon>
                        </button>
                    </div>
                  </div>
                `
          )}
            </div>
          `}

      ${this._showAddDialog
        ? html`
            <div class="dialog-overlay" @click=${this._hideAddMedicationDialog}>
              <div class="dialog" @click=${(e) => e.stopPropagation()}>
                <div class="dialog-header">
                  <h2 class="dialog-title">Add New Medication</h2>
                  <button
                    class="close-button"
                    @click=${this._hideAddMedicationDialog}
                  >
                    ×
                  </button>
                </div>

                <div class="form-field">
                  <label class="form-label">Name</label>
                  <input
                    class="form-input"
                    type="text"
                    .value=${this._newMedication.name}
                    @input=${(e) =>
            this._updateNewMedication("name", e.target.value)}
                    placeholder="e.g., Vitamin D"
                  />
                </div>

                <div class="form-field">
                  <label class="form-label">Dosage</label>
                  <input
                    class="form-input"
                    type="text"
                    .value=${this._newMedication.dosage}
                    @input=${(e) =>
            this._updateNewMedication("dosage", e.target.value)}
                    placeholder="e.g., 1000 IU, 2 tablets"
                  />
                </div>

                <div class="form-field">
                  <label class="form-label">Frequency</label>
                  <select
                    class="form-select"
                    .value=${this._newMedication.frequency}
                    @change=${(e) =>
            this._updateNewMedication("frequency", e.target.value)}
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="as_needed">As Needed</option>
                  </select>
                </div>

                <div class="form-field">
                  <label class="form-label">Times</label>
                  ${this._newMedication.times.map(
              (time, index) => html`
                      <div class="times-input">
                        <input
                          class="form-input"
                          type="time"
                          .value=${time}
                          @input=${(e) =>
                  this._updateTime(index, e.target.value)}
                        />
                        ${this._newMedication.times.length > 1
                  ? html`
                              <button
                                class="remove-time-button"
                                @click=${() => this._removeTime(index)}
                              >
                                Remove
                              </button>
                            `
                  : ""}
                      </div>
                    `
            )}
                  <button class="add-time-button" @click=${this._addTime}>
                    Add Time
                  </button>
                </div>

                <div class="form-field">
                  <label class="form-label">Start Date (Optional)</label>
                  <input
                    class="form-input"
                    type="date"
                    .value=${this._newMedication.start_date}
                    @input=${(e) =>
            this._updateNewMedication("start_date", e.target.value)}
                  />
                </div>

                <div class="form-field">
                  <label class="form-label">End Date (Optional)</label>
                  <input
                    class="form-input"
                    type="date"
                    .value=${this._newMedication.end_date}
                    @input=${(e) =>
            this._updateNewMedication("end_date", e.target.value)}
                  />
                </div>

                <div class="form-field">
                  <label class="form-label">Notes (Optional)</label>
                  <textarea
                    class="form-textarea"
                    .value=${this._newMedication.notes}
                    @input=${(e) =>
            this._updateNewMedication("notes", e.target.value)}
                    placeholder="Additional notes or instructions"
                  ></textarea>
                </div>

                <div class="dialog-actions">
                  <button
                    class="dialog-button cancel-button"
                    @click=${this._hideAddMedicationDialog}
                  >
                    Cancel
                  </button>
                  <button
                    class="dialog-button save-button"
                    @click=${this._saveMedication}
                    ?disabled=${!this._newMedication.name ||
          !this._newMedication.dosage}
                  >
                    Add Medication
                  </button>
                </div>
              </div>
            </div>
          `
        : ""}

      ${this._showEditDialog
        ? html`
            <div class="dialog-overlay" @click=${this._hideEditMedicationDialog}>
              <div class="dialog" @click=${(e) => e.stopPropagation()}>
                <div class="dialog-header">
                  <h2 class="dialog-title">Edit Medication</h2>
                  <button
                    class="close-button"
                    @click=${this._hideEditMedicationDialog}
                  >
                    ×
                  </button>
                </div>

                <div class="form-field">
                  <label class="form-label">Name</label>
                  <input
                    class="form-input"
                    type="text"
                    .value=${this._editMedication.name}
                    @input=${(e) =>
            this._updateEditMedication("name", e.target.value)}
                    placeholder="e.g., Vitamin D"
                  />
                </div>

                <div class="form-field">
                  <label class="form-label">Dosage</label>
                  <input
                    class="form-input"
                    type="text"
                    .value=${this._editMedication.dosage}
                    @input=${(e) =>
            this._updateEditMedication("dosage", e.target.value)}
                    placeholder="e.g., 1000 IU, 2 tablets"
                  />
                </div>

                <div class="form-field">
                  <label class="form-label">Frequency</label>
                  <select
                    class="form-select"
                    .value=${this._editMedication.frequency}
                    @change=${(e) =>
            this._updateEditMedication("frequency", e.target.value)}
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="as_needed">As Needed</option>
                  </select>
                </div>

                <div class="form-field">
                  <label class="form-label">Times</label>
                  ${this._editMedication.times.map(
              (time, index) => html`
                      <div class="times-input">
                        <input
                          class="form-input"
                          type="time"
                          .value=${time}
                          @input=${(e) =>
                  this._updateEditTime(index, e.target.value)}
                        />
                        ${this._editMedication.times.length > 1
                  ? html`
                              <button
                                class="remove-time-button"
                                @click=${() => this._removeEditTime(index)}
                              >
                                Remove
                              </button>
                            `
                  : ""}
                      </div>
                    `
            )}
                  <button class="add-time-button" @click=${this._addEditTime}>
                    Add Time
                  </button>
                </div>

                <div class="form-field">
                  <label class="form-label">Start Date (Optional)</label>
                  <input
                    class="form-input"
                    type="date"
                    .value=${this._editMedication.start_date}
                    @input=${(e) =>
            this._updateEditMedication("start_date", e.target.value)}
                  />
                </div>

                <div class="form-field">
                  <label class="form-label">End Date (Optional)</label>
                  <input
                    class="form-input"
                    type="date"
                    .value=${this._editMedication.end_date}
                    @input=${(e) =>
            this._updateEditMedication("end_date", e.target.value)}
                  />
                </div>

                <div class="form-field">
                  <label class="form-label">Notes (Optional)</label>
                  <textarea
                    class="form-textarea"
                    .value=${this._editMedication.notes}
                    @input=${(e) =>
            this._updateEditMedication("notes", e.target.value)}
                    placeholder="Additional notes or instructions"
                  ></textarea>
                </div>

                <div class="dialog-actions">
                  <button
                    class="dialog-button cancel-button"
                    @click=${this._hideEditMedicationDialog}
                  >
                    Cancel
                  </button>
                  <button
                    class="dialog-button save-button"
                    @click=${this._updateMedication}
                    ?disabled=${!this._editMedication.name ||
          !this._editMedication.dosage}
                  >
                    Update Medication
                  </button>
                </div>
              </div>
            </div>
          `
        : ""}
    `;
  }
}

// Register the custom element
customElements.define("medication-tracker-panel", MedicationTrackerPanel);
