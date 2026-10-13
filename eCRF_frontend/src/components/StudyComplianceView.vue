<template>
  <div class="compliance-view">
    <header class="compliance-header">
      <div>
        <p class="eyebrow">Study oversight</p>
        <h2>Compliance view</h2>
        <p class="subtitle">Recruitment, visit completion, and current data-entry coverage.</p>
      </div>
      <button type="button" class="refresh-btn" :disabled="loading" @click="loadSummary">
        {{ loading ? 'Refreshing…' : 'Refresh' }}
      </button>
    </header>

    <div v-if="loading && !summary" class="state-card" role="status">Calculating study compliance…</div>
    <div v-else-if="error" class="state-card error-state" role="alert">
      <strong>Compliance statistics could not be loaded.</strong>
      <span>{{ error }}</span>
    </div>

    <template v-else-if="summary">
      <section class="kpi-grid" aria-label="Compliance key performance indicators">
        <article class="kpi-card accent-blue">
          <span class="kpi-label">Subjects enrolled with data</span>
          <strong>{{ recruitment.recruited_subjects }}</strong>
          <small>At least one visit started · {{ recruitment.active_subjects }} currently active</small>
        </article>
        <article class="kpi-card accent-rose">
          <span class="kpi-label">Dropped out</span>
          <strong>{{ recruitment.dropped_subjects }}</strong>
          <small>{{ recruitment.dropout_percent }}% of enrolled subjects with data</small>
        </article>
        <article class="kpi-card accent-teal">
          <span class="kpi-label">Data entered</span>
          <strong>{{ compliance.data_compliance_percent }}%</strong>
          <small>Across {{ compliance.expected_subject_visits }} expected subject-visits in {{ compliance.started_visits }} started visit{{ compliance.started_visits === 1 ? '' : 's' }}</small>
        </article>
        <article class="kpi-card accent-violet">
          <span class="kpi-label">Subjects complete</span>
          <strong>{{ compliance.completed_subjects }}</strong>
          <small>{{ compliance.subject_completion_percent }}% of subjects in the current scope</small>
        </article>
      </section>

      <section class="operational-grid" aria-label="Operational compliance indicators">
        <article>
          <span>Retention rate</span>
          <strong>{{ retentionPercent }}%</strong>
          <small>Subjects not dropped out</small>
        </article>
        <article>
          <span>Needs attention</span>
          <strong>{{ subjectVisitsNeedingAttention }}</strong>
          <small>Partially completed subject-visits</small>
        </article>
        <article>
          <span>Lowest coverage visit</span>
          <strong class="text-value">{{ lowestCoverageVisit?.visit_name || '—' }}</strong>
          <small v-if="lowestCoverageVisit">{{ lowestCoverageVisit.data_compliance_percent }}% average progress</small>
          <small v-else>No visit data available</small>
        </article>
      </section>

      <aside class="scope-note" aria-label="Compliance calculation scope">
        <div>
          <strong>Current compliance scope</strong>
          <span>
            {{ compliance.evaluable_subjects }} subject{{ compliance.evaluable_subjects === 1 ? '' : 's' }} with entered data
            · {{ compliance.started_visits }} started visit{{ compliance.started_visits === 1 ? '' : 's' }}
          </span>
        </div>
        <small>
          Excludes {{ compliance.excluded_not_started_subjects }} untouched subject{{ compliance.excluded_not_started_subjects === 1 ? '' : 's' }}
          and {{ compliance.excluded_not_started_visits }} future visit{{ compliance.excluded_not_started_visits === 1 ? '' : 's' }} with no data yet.
        </small>
      </aside>

      <section class="chart-card enrollment-card">
        <div class="chart-heading enrollment-heading">
          <div>
            <span class="insight-label">Enrollment monitoring</span>
            <h3>Actual enrollment over time</h3>
            <p>Based on each subject’s first qualifying data-entry date. Retained dropouts remain included.</p>
          </div>
          <span class="actual-only-badge" :class="{ planned: enrollmentPlan.configured }">{{ enrollmentPlanBadge }}</span>
        </div>

        <div class="enrollment-kpis">
          <article>
            <span>Enrolled with data</span>
            <strong>{{ enrollment.enrolled_subjects || 0 }}</strong>
            <small>of {{ enrollment.configured_subjects || 0 }} subjects in the current roster</small>
          </article>
          <article>
            <span>30-day pace</span>
            <strong>{{ enrollmentPace.subjects_per_30_days || 0 }}</strong>
            <small>subjects first entered in the last 30 days</small>
          </article>
          <article>
            <span>90-day pace</span>
            <strong>{{ enrollmentPace.subjects_per_30_days_from_90_day_window || 0 }}</strong>
            <small>subjects per 30 days · rolling 90-day average</small>
          </article>
          <article>
            <span>{{ enrollmentPlan.configured ? 'Target forecast' : 'Current-roster forecast' }}</span>
            <strong class="forecast-value">{{ enrollmentForecastLabel }}</strong>
            <small>{{ enrollmentForecastNote }}</small>
          </article>
        </div>

        <template v-if="enrollmentTimeline.length">
          <div class="enrollment-chart-block">
            <div class="enrollment-chart-header">
              <div>
                <strong>Cumulative enrollment</strong>
                <span>Total and group counts from first data entry</span>
              </div>
              <div class="enrollment-legend" aria-label="Enrollment chart legend">
                <span class="total-series"><i></i>Total</span>
                <span v-if="enrollmentPlan.enabled" class="planned-series"><i></i>Planned</span>
                <span v-for="group in enrollmentGroups" :key="`enrollment-legend-${group.group_index}`">
                  <i :style="{ backgroundColor: enrollmentColor(group.group_index) }"></i>{{ group.group_name }}
                </span>
              </div>
            </div>
            <div class="enrollment-chart-scroll">
              <svg
                class="enrollment-chart"
                viewBox="0 0 860 300"
                role="img"
                :aria-label="`Cumulative enrollment for ${enrollment.enrolled_subjects || 0} subjects`"
              >
                <g class="chart-grid">
                  <line v-for="tick in enrollmentYTicks" :key="`enrollment-y-grid-${tick.value}`" x1="62" x2="828" :y1="tick.y" :y2="tick.y" />
                </g>
                <g class="chart-axes">
                  <line x1="62" x2="828" y1="245" y2="245" />
                  <line x1="62" x2="62" y1="20" y2="245" />
                </g>
                <g class="axis-labels">
                  <text v-for="tick in enrollmentYTicks" :key="`enrollment-y-label-${tick.value}`" x="52" :y="tick.y + 4" text-anchor="end">{{ tick.value }}</text>
                  <text v-for="tick in enrollmentXTicks" :key="`enrollment-x-label-${tick.timestamp}`" :x="tick.x" y="266" :text-anchor="tick.anchor">{{ tick.label }}</text>
                  <text x="445" y="291" text-anchor="middle">First qualifying data-entry date</text>
                  <text transform="translate(16 134) rotate(-90)" text-anchor="middle">Subjects</text>
                </g>
                <polyline
                  v-for="series in enrollmentGroupSeries"
                  :key="`enrollment-series-${series.group_index}`"
                  class="enrollment-group-line"
                  :stroke="enrollmentColor(series.group_index)"
                  :points="series.points"
                />
                <polyline v-if="enrollmentPlan.enabled" class="enrollment-planned-line" :points="enrollmentPlannedPoints" />
                <polyline class="enrollment-total-line" :points="enrollmentTotalPoints" />
                <circle
                  v-for="point in enrollmentTotalChartPoints"
                  :key="`enrollment-point-${point.date}`"
                  class="enrollment-total-point"
                  :cx="point.x"
                  :cy="point.y"
                  r="4"
                >
                  <title>{{ formatDateOnly(point.date) }}: {{ point.total }} enrolled</title>
                </circle>
              </svg>
            </div>
            <div v-if="enrollmentPlan.enabled" class="plan-comparison-note" :class="enrollmentPlanVarianceClass">
              <strong>{{ enrollmentPlanVarianceLabel }}</strong>
              <span>{{ enrollment.planned_to_date }} planned by {{ formatDateOnly(enrollment.as_of) }} · target {{ enrollmentPlan.target_subjects }} subjects</span>
            </div>
          </div>

          <div class="enrollment-chart-block proportion-block">
            <div class="enrollment-chart-header">
              <div>
                <strong>Group proportions over time</strong>
                <span>Share of enrolled subjects in each group</span>
              </div>
            </div>
            <div class="enrollment-chart-scroll">
              <svg class="enrollment-proportion-chart" viewBox="0 0 860 220" role="img" aria-label="Enrollment group proportions over time">
                <g class="proportion-grid">
                  <line x1="62" x2="828" y1="20" y2="20" />
                  <line x1="62" x2="828" y1="95" y2="95" />
                  <line x1="62" x2="828" y1="170" y2="170" />
                </g>
                <polygon
                  v-for="area in enrollmentProportionAreas"
                  :key="`enrollment-area-${area.group_index}`"
                  :points="area.points"
                  :fill="enrollmentColor(area.group_index)"
                />
                <g class="chart-axes"><line x1="62" x2="828" y1="170" y2="170" /><line x1="62" x2="62" y1="20" y2="170" /></g>
                <g class="axis-labels">
                  <text x="52" y="174" text-anchor="end">0%</text><text x="52" y="99" text-anchor="end">50%</text><text x="52" y="24" text-anchor="end">100%</text>
                  <text v-for="tick in enrollmentProportionXTicks" :key="`proportion-x-${tick.timestamp}`" :x="tick.x" y="194" :text-anchor="tick.anchor">{{ tick.label }}</text>
                </g>
              </svg>
            </div>
            <div class="group-proportion-list">
              <div v-for="group in enrollmentGroups" :key="`enrollment-share-${group.group_index}`">
                <i :style="{ backgroundColor: enrollmentColor(group.group_index) }"></i>
                <span>{{ group.group_name }}</span>
                <strong>{{ group.count }} · {{ group.proportion_percent }}%</strong>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="empty-state">Enrollment history will appear after a subject has qualifying data and a recorded entry date.</div>
        <p v-if="enrollment.subjects_missing_entry_date" class="enrollment-warning">
          {{ enrollment.subjects_missing_entry_date }} enrolled subject{{ enrollment.subjects_missing_entry_date === 1 ? '' : 's' }} could not be placed on the timeline because an entry date was unavailable.
        </p>

        <form v-if="summary.can_edit_enrollment_plan" class="enrollment-plan-editor" @submit.prevent="saveEnrollmentPlan">
          <div class="plan-editor-heading">
            <div>
              <strong>Optional planned enrollment</strong>
              <p>Add a comparison line as a total target over a number of months, or enter a target for each month. Leave this off to show actual pace and a forecast against the current study roster.</p>
            </div>
            <button type="submit" class="save-plan-btn" :disabled="savingEnrollmentPlan">
              {{ savingEnrollmentPlan ? 'Saving…' : 'Save plan' }}
            </button>
          </div>
          <div class="plan-fields">
            <label>
              <span>Comparison</span>
              <select v-model="enrollmentPlanDraft.mode" @change="clearEnrollmentPlanMessage">
                <option value="none">No planned comparison</option>
                <option value="linear">Total subjects over a period</option>
                <option value="monthly">Monthly recruitment numbers</option>
              </select>
            </label>
            <template v-if="enrollmentPlanDraft.mode === 'linear'">
              <label>
                <span>Planned subjects</span>
                <input v-model.number="enrollmentPlanDraft.target_subjects" type="number" min="1" step="1" required />
              </label>
              <label>
                <span>Recruitment period (months)</span>
                <input v-model.number="enrollmentPlanDraft.duration_months" type="number" min="1" max="240" step="1" required />
              </label>
            </template>
            <label v-else-if="enrollmentPlanDraft.mode === 'monthly'" class="monthly-plan-field">
              <span>New subjects planned per month</span>
              <textarea v-model="enrollmentPlanDraft.monthlyText" rows="2" required placeholder="For example: 10, 15, 20, 20"></textarea>
              <small>Enter one number per month, separated by commas or new lines. These are monthly additions, not cumulative totals.</small>
            </label>
          </div>
          <p v-if="enrollmentPlan.configured && enrollmentPlan.waiting_for_actual" class="plan-message neutral">Plan saved. Its timeline will begin on the first qualifying data-entry date.</p>
          <p v-if="enrollmentPlanError" class="plan-message error">{{ enrollmentPlanError }}</p>
          <p v-else-if="enrollmentPlanSaved" class="plan-message success">Enrollment plan saved.</p>
        </form>
      </section>

      <section class="chart-card histogram-card">
        <div class="chart-heading">
          <div>
            <span class="insight-label">Subject progress</span>
            <h3>Subject completeness distribution</h3>
            <p>Subjects appear after they have entered data for at least one visit. Future visits with no data are excluded.</p>
          </div>
          <span class="metric-note">{{ histogramSubjectTotal }} subjects</span>
        </div>
        <div v-if="histogramSubjectTotal" class="histogram-scroll">
          <div class="histogram-plot" role="img" aria-label="Distribution of subjects by completeness range">
            <div
              v-for="bin in histogramBars"
              :key="bin.range_start"
              class="histogram-column"
              tabindex="0"
              :aria-label="`${bin.label}: ${bin.subject_count} subject${bin.subject_count === 1 ? '' : 's'}`"
            >
              <strong>{{ bin.subject_count }}</strong>
              <div class="histogram-bar-area">
                <span :style="{ height: `${bin.heightPercent}%` }"></span>
              </div>
              <small>{{ bin.label }}</small>
            </div>
          </div>
          <div class="histogram-axis-title">Subject completeness range</div>
        </div>
        <div v-else class="empty-state">No subject completeness data is available.</div>
      </section>

      <section class="insight-grid">
        <article class="insight-card primary-insight">
          <div>
            <span class="insight-label">Overall data compliance</span>
            <strong>On average, {{ compliance.data_compliance_percent }}% of expected data is entered.</strong>
            <p>
              Each expected subject-visit in the current scope contributes equally across {{ compliance.evaluable_subjects }} subjects with entered data and {{ compliance.started_visits }} started visits.
            </p>
          </div>
          <div class="radial" :style="complianceRadialStyle" role="img" :aria-label="`${compliance.data_compliance_percent}% data compliance`">
            <span>{{ compliance.data_compliance_percent }}%</span>
          </div>
        </article>

        <article class="insight-card recruitment-card">
          <div class="chart-heading">
            <div>
              <span class="insight-label">Recruitment status</span>
              <strong>{{ recruitment.recruited_subjects }} enrolled subjects with data</strong>
            </div>
          </div>
          <div class="recruitment-chart-wrap">
            <div class="donut" :style="recruitmentDonutStyle" role="img" aria-label="Subject recruitment status distribution">
              <span><strong>{{ recruitment.active_subjects }}</strong> active</span>
            </div>
            <ul class="legend-list">
              <li><i class="dot active"></i><span>Active</span><strong>{{ recruitment.active_subjects }}</strong></li>
              <li><i class="dot retained"></i><span>Dropped · retained</span><strong>{{ recruitment.dropped_data_retained }}</strong></li>
              <li><i class="dot deleted"></i><span>Dropped · deleted</span><strong>{{ recruitment.dropped_data_deleted }}</strong></li>
            </ul>
          </div>
        </article>
      </section>

      <section class="chart-card threshold-card">
        <div class="chart-heading">
          <div>
            <span class="insight-label">Subject completeness</span>
            <h3>Completeness threshold curve</h3>
          </div>
          <span class="metric-note">Current compliance scope only</span>
        </div>
        <div v-if="thresholdCurveMax" class="threshold-chart-wrap">
          <svg
            class="threshold-chart"
            viewBox="0 0 820 300"
            role="img"
            :aria-label="`Completeness threshold curve for ${thresholdCurveMax} subjects`"
          >
            <g class="chart-grid">
              <line v-for="tick in thresholdYTicks" :key="`y-grid-${tick.value}`" x1="60" x2="760" :y1="tick.y" :y2="tick.y" />
              <line v-for="tick in thresholdXTicks" :key="`x-grid-${tick.value}`" :x1="tick.x" :x2="tick.x" y1="18" y2="242" />
            </g>
            <g class="chart-axes">
              <line x1="60" x2="760" y1="242" y2="242" />
              <line x1="60" x2="60" y1="18" y2="242" />
            </g>
            <g class="axis-labels">
              <text v-for="tick in thresholdYTicks" :key="`y-label-${tick.value}`" x="51" :y="tick.y + 4" text-anchor="end">{{ tick.value }}</text>
              <text v-for="tick in thresholdXTicks" :key="`x-label-${tick.value}`" :x="tick.x" y="260" text-anchor="middle">{{ tick.value }}</text>
              <text x="410" y="286" text-anchor="middle">Data completeness threshold (%)</text>
              <text transform="translate(15 130) rotate(-90)" text-anchor="middle">Subjects at or above threshold</text>
            </g>
            <polyline class="threshold-line" :points="thresholdPolyline" />
            <circle
              v-for="point in thresholdCurvePoints"
              :key="`curve-point-${point.threshold}`"
              class="curve-hit-point"
              :cx="point.x"
              :cy="point.y"
              r="7"
            >
              <title>{{ point.threshold }}%: {{ point.subject_count }} subject{{ point.subject_count === 1 ? '' : 's' }}</title>
            </circle>
            <g v-for="marker in thresholdMarkers" :key="`marker-${marker.threshold}`" class="threshold-marker">
              <line :class="`marker-${marker.threshold}`" :x1="marker.x" :x2="marker.x" :y1="marker.y" y2="242" />
              <circle :class="`marker-${marker.threshold}`" :cx="marker.x" :cy="marker.y" r="5" />
            </g>
          </svg>
          <div class="threshold-summary" aria-label="Selected completeness thresholds">
            <article v-for="marker in thresholdMarkers" :key="`summary-${marker.threshold}`">
              <i :class="`marker-${marker.threshold}`"></i>
              <span>At least {{ marker.threshold }}% complete</span>
              <strong>{{ marker.subject_count }} subject{{ marker.subject_count === 1 ? '' : 's' }}</strong>
            </article>
          </div>
        </div>
        <div v-else class="empty-state">No subject completeness data is available.</div>
      </section>

      <section class="dashboard-grid">
        <article class="chart-card visit-card">
          <div class="chart-heading">
            <div>
              <span class="insight-label">Visit completion</span>
              <h3>Average visit progress across subjects</h3>
            </div>
            <span class="metric-note">Simple average of subject progress</span>
          </div>
          <div v-if="visitStats.length" class="bar-list">
            <div v-for="visit in visitStats" :key="visit.visit_index" class="bar-row">
              <div class="bar-meta">
                <strong>{{ visit.visit_name }}</strong>
                <span>{{ visit.completed_subjects }} of {{ visit.expected_subjects }} subjects at 100% · {{ visit.data_compliance_percent }}% average progress</span>
              </div>
              <div class="bar-track" :aria-label="`${visit.visit_name}: ${visit.data_compliance_percent}% average progress`">
                <span class="bar-fill" :style="{ width: `${visit.data_compliance_percent}%` }"></span>
              </div>
              <strong class="bar-value">{{ visit.data_compliance_percent }}%</strong>
            </div>
          </div>
          <div v-else class="empty-state">No visits with assigned fields are available.</div>
        </article>

        <article class="chart-card status-card">
          <div class="chart-heading">
            <div>
              <span class="insight-label">Subject-visit status</span>
              <h3>Data-entry distribution</h3>
            </div>
          </div>
          <div class="stacked-bar" role="img" aria-label="Subject visit completion distribution">
            <span class="complete" :style="{ width: distributionWidth('complete') }"></span>
            <span class="partial" :style="{ width: distributionWidth('partial') }"></span>
            <span class="not-started" :style="{ width: distributionWidth('not_started') }"></span>
          </div>
          <ul class="status-breakdown">
            <li><i class="dot complete"></i><span>Complete</span><strong>{{ distribution.complete }}</strong></li>
            <li><i class="dot partial"></i><span>Partial</span><strong>{{ distribution.partial }}</strong></li>
            <li><i class="dot not-started"></i><span>Not started</span><strong>{{ distribution.not_started }}</strong></li>
          </ul>
          <div class="skipped-note" :class="{ warning: compliance.skipped_fields > 0 }">
            <strong>{{ compliance.skipped_fields }}</strong> skipped required field{{ compliance.skipped_fields === 1 ? '' : 's' }}
          </div>
        </article>
      </section>

      <section v-if="groupStats.length" class="chart-card group-card">
        <div class="chart-heading">
          <div>
            <span class="insight-label">Group comparison</span>
            <h3>Data compliance by group</h3>
          </div>
        </div>
        <div class="group-grid">
          <div v-for="group in groupStats" :key="group.group_index" class="group-stat">
            <div class="group-stat-head">
              <strong>{{ group.group_name }}</strong>
              <span>{{ group.data_compliance_percent }}%</span>
            </div>
            <div class="bar-track"><span class="bar-fill group-fill" :style="{ width: `${group.data_compliance_percent}%` }"></span></div>
            <small>{{ group.recruited_subjects }} enrolled with data</small>
          </div>
        </div>
      </section>

      <section class="table-card">
        <div class="chart-heading">
          <div>
            <span class="insight-label">Visit detail</span>
            <h3>Compliance overview</h3>
          </div>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Visit</th>
                <th>Expected subjects</th>
                <th>Complete</th>
                <th>Partial</th>
                <th>Not started</th>
                <th>Data entered</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="visit in visitStats" :key="`detail-${visit.visit_index}`">
                <td><strong>{{ visit.visit_name }}</strong></td>
                <td>{{ visit.expected_subjects }}</td>
                <td>{{ visit.completed_subjects }}</td>
                <td>{{ visit.partial_subjects }}</td>
                <td>{{ visit.not_started_subjects }}</td>
                <td>
                  <span
                    class="percent-pill"
                    :class="percentClass(visit)"
                    :title="visit.skipped_fields > 0 ? `${visit.skipped_fields} required field(s) skipped` : ''"
                  >{{ visit.data_compliance_percent }}%</span>
                </td>
              </tr>
              <tr v-if="!visitStats.length"><td colspan="6" class="empty-cell">No visit statistics available.</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <footer class="method-note">
        <strong>How compliance is calculated:</strong>
        A subject is counted as enrolled/recruited only after data is entered or a required field is skipped in at least one assigned visit. Enrollment timing uses that subject’s first qualifying entry date, while group totals use the subject’s configured study group. An optional plan begins on the first actual enrollment date. The dropout percentage is the share of this enrolled-with-data cohort whose status is dropped out. A visit enters the calculation after at least one included subject starts it. Subjects with no started visits and future visits with no entered data are excluded. Within the remaining subject × visit scope, every expected subject-visit contributes equally: complete is 100%, partial uses its saved progress, and an expected visit not yet started by that subject is 0%. This prevents untouched subjects and future visits from lowering today’s compliance while still showing genuine gaps inside the active study scope. Dropped subjects whose data was deleted are excluded; retained dropouts remain included after they have started data entry.
        <span v-if="summary.generated_at">Updated {{ formatDateTime(summary.generated_at) }}.</span>
      </footer>
    </template>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StudyComplianceView",
  props: {
    studyId: { type: [String, Number], required: true },
    active: { type: Boolean, default: false },
  },
  data() {
    return {
      summary: null,
      loading: false,
      error: "",
      loadedStudyId: null,
      savingEnrollmentPlan: false,
      enrollmentPlanError: "",
      enrollmentPlanSaved: false,
      enrollmentPlanDraft: { mode: "none", target_subjects: null, duration_months: null, monthlyText: "" },
    };
  },
  computed: {
    recruitment() {
      return this.summary?.recruitment || {};
    },
    compliance() {
      return this.summary?.compliance || {};
    },
    enrollment() {
      return this.summary?.enrollment_monitoring || {};
    },
    enrollmentPace() {
      return this.enrollment?.pace || {};
    },
    enrollmentForecast() {
      return this.enrollment?.forecast || {};
    },
    enrollmentPlan() {
      return this.enrollment?.plan || { configured: false, enabled: false, mode: "none", planned_timeline: [] };
    },
    enrollmentTimeline() {
      return Array.isArray(this.enrollment?.timeline) ? this.enrollment.timeline : [];
    },
    enrollmentPlannedTimeline() {
      return Array.isArray(this.enrollmentPlan?.planned_timeline) ? this.enrollmentPlan.planned_timeline : [];
    },
    enrollmentGroups() {
      return Array.isArray(this.enrollment?.actual_by_group) ? this.enrollment.actual_by_group : [];
    },
    enrollmentMinTimestamp() {
      const dates = [...this.enrollmentTimeline, ...this.enrollmentPlannedTimeline]
        .map((point) => Date.parse(`${point.date}T00:00:00Z`))
        .filter(Number.isFinite);
      return dates.length ? Math.min(...dates) : 0;
    },
    enrollmentMaxTimestamp() {
      const dates = [...this.enrollmentTimeline, ...this.enrollmentPlannedTimeline]
        .map((point) => Date.parse(`${point.date}T00:00:00Z`))
        .filter(Number.isFinite);
      return dates.length ? Math.max(...dates) : 0;
    },
    enrollmentActualMinTimestamp() {
      if (!this.enrollmentTimeline.length) return 0;
      return Date.parse(`${this.enrollmentTimeline[0].date}T00:00:00Z`);
    },
    enrollmentActualMaxTimestamp() {
      if (!this.enrollmentTimeline.length) return 0;
      return Date.parse(`${this.enrollmentTimeline[this.enrollmentTimeline.length - 1].date}T00:00:00Z`);
    },
    enrollmentTopValue() {
      const maximum = Math.max(
        1,
        ...this.enrollmentTimeline.map((point) => Number(point.total || 0)),
        ...this.enrollmentPlannedTimeline.map((point) => Number(point.cumulative || 0))
      );
      return Math.max(4, Math.ceil(maximum / 4) * 4);
    },
    enrollmentTotalChartPoints() {
      return this.enrollmentTimeline.map((point) => ({
        ...point,
        x: this.enrollmentChartX(point.date),
        y: this.enrollmentChartY(point.total),
      }));
    },
    enrollmentTotalPoints() {
      return this.enrollmentTotalChartPoints.map((point) => `${point.x},${point.y}`).join(" ");
    },
    enrollmentPlannedPoints() {
      return this.enrollmentPlannedTimeline
        .map((point) => `${this.enrollmentChartX(point.date)},${this.enrollmentChartY(point.cumulative)}`)
        .join(" ");
    },
    enrollmentGroupSeries() {
      return this.enrollmentGroups.map((group) => ({
        ...group,
        points: this.enrollmentTimeline.map((point) => {
          const current = (point.groups || []).find((item) => Number(item.group_index) === Number(group.group_index));
          return `${this.enrollmentChartX(point.date)},${this.enrollmentChartY(current?.count || 0)}`;
        }).join(" "),
      }));
    },
    enrollmentYTicks() {
      return [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
        const value = Math.round(this.enrollmentTopValue * ratio);
        return { value, y: this.enrollmentChartY(value) };
      });
    },
    enrollmentXTicks() {
      return this.buildEnrollmentDateTicks(62, 828);
    },
    enrollmentProportionXTicks() {
      return this.buildEnrollmentDateTicks(62, 828, this.enrollmentActualMinTimestamp, this.enrollmentActualMaxTimestamp);
    },
    enrollmentProportionAreas() {
      const accumulated = this.enrollmentTimeline.map(() => 0);
      return this.enrollmentGroups.map((group) => {
        const lower = [...accumulated];
        const upper = this.enrollmentTimeline.map((point, index) => {
          const current = (point.groups || []).find((item) => Number(item.group_index) === Number(group.group_index));
          const share = Number(current?.proportion_percent || 0);
          accumulated[index] += share;
          return accumulated[index];
        });
        const upperPoints = this.enrollmentTimeline.map((point, index) => `${this.enrollmentProportionX(point.date)},${this.enrollmentProportionY(upper[index])}`);
        const lowerPoints = this.enrollmentTimeline.slice().reverse().map((point, reverseIndex) => {
          const index = this.enrollmentTimeline.length - 1 - reverseIndex;
          return `${this.enrollmentProportionX(point.date)},${this.enrollmentProportionY(lower[index])}`;
        });
        return { ...group, points: [...upperPoints, ...lowerPoints].join(" ") };
      });
    },
    enrollmentForecastLabel() {
      if (this.enrollmentForecast.available) return this.formatDateOnly(this.enrollmentForecast.projected_completion_date);
      if (this.enrollmentForecast.reason === "current_roster_complete") return "Roster complete";
      return "Not available";
    },
    enrollmentForecastNote() {
      if (this.enrollmentForecast.available) return `At ${this.enrollmentForecast.monthly_pace_used} subjects per 30 days`;
      if (this.enrollmentForecast.reason === "current_roster_complete") {
        return this.enrollmentPlan.configured ? "The planned target has been reached" : "All currently configured subjects have data";
      }
      return "Requires at least 30 days and 3 recent enrollments";
    },
    enrollmentPlanBadge() {
      if (this.enrollmentPlan.enabled) return "Actual + planned comparison";
      if (this.enrollmentPlan.configured) return "Plan saved · awaiting enrollment data";
      return "Actual only · no plan configured";
    },
    enrollmentPlanVarianceLabel() {
      const variance = Number(this.enrollment?.variance_to_plan || 0);
      if (variance === 0) return "On plan";
      return variance > 0 ? `${variance} ahead of plan` : `${Math.abs(variance)} behind plan`;
    },
    enrollmentPlanVarianceClass() {
      const variance = Number(this.enrollment?.variance_to_plan || 0);
      return variance < 0 ? "behind" : (variance > 0 ? "ahead" : "on-plan");
    },
    visitStats() {
      return this.summary?.visit_stats || [];
    },
    groupStats() {
      return this.summary?.group_stats || [];
    },
    distribution() {
      return this.summary?.subject_visit_status || { complete: 0, partial: 0, not_started: 0 };
    },
    distributionTotal() {
      return Number(this.distribution.complete || 0) + Number(this.distribution.partial || 0) + Number(this.distribution.not_started || 0);
    },
    retentionPercent() {
      const recruited = Number(this.recruitment.recruited_subjects || 0);
      if (!recruited) return 0;
      return Math.round((Number(this.recruitment.active_subjects || 0) / recruited) * 100);
    },
    subjectVisitsNeedingAttention() {
      return Number(this.distribution.partial || 0);
    },
    histogramBars() {
      const bins = this.summary?.completeness_histogram || [];
      const maximum = Math.max(0, ...bins.map((bin) => Number(bin.subject_count || 0)));
      return bins.map((bin) => ({
        ...bin,
        heightPercent: maximum ? (Number(bin.subject_count || 0) / maximum) * 100 : 0,
        label: `${bin.range_start}–${bin.range_end === 100 ? 100 : bin.range_end - 1}%`,
      }));
    },
    histogramSubjectTotal() {
      return this.histogramBars.reduce((total, bin) => total + Number(bin.subject_count || 0), 0);
    },
    thresholdCurveMax() {
      return Math.max(0, ...(this.summary?.completeness_threshold_curve || []).map((point) => Number(point.subject_count || 0)));
    },
    thresholdCurvePoints() {
      const maximum = this.thresholdCurveMax;
      if (!maximum) return [];
      return (this.summary?.completeness_threshold_curve || []).map((point) => ({
        ...point,
        x: 60 + (Number(point.threshold || 0) / 100) * 700,
        y: 18 + (1 - Number(point.subject_count || 0) / maximum) * 224,
      }));
    },
    thresholdPolyline() {
      return this.thresholdCurvePoints.map((point) => `${point.x},${point.y}`).join(" ");
    },
    thresholdXTicks() {
      return [0, 20, 40, 60, 80, 100].map((value) => ({ value, x: 60 + value * 7 }));
    },
    thresholdYTicks() {
      if (!this.thresholdCurveMax) return [];
      const values = [...new Set([0, 0.25, 0.5, 0.75, 1].map((ratio) => Math.round(this.thresholdCurveMax * ratio)))];
      return values.map((value) => ({ value, y: 18 + (1 - value / this.thresholdCurveMax) * 224 }));
    },
    thresholdMarkers() {
      return [80, 90, 95]
        .map((threshold) => this.thresholdCurvePoints.find((point) => Number(point.threshold) === threshold))
        .filter(Boolean);
    },
    lowestCoverageVisit() {
      const eligible = this.visitStats.filter((visit) => Number(visit.expected_subjects || 0) > 0);
      if (!eligible.length) return null;
      return eligible.reduce((lowest, visit) =>
        Number(visit.data_compliance_percent || 0) < Number(lowest.data_compliance_percent || 0)
          ? visit
          : lowest
      );
    },
    complianceRadialStyle() {
      const value = Math.max(0, Math.min(100, Number(this.compliance.data_compliance_percent || 0)));
      return { background: `conic-gradient(#0f766e 0 ${value}%, #dce9e7 ${value}% 100%)` };
    },
    recruitmentDonutStyle() {
      const total = Number(this.recruitment.recruited_subjects || 0);
      if (!total) return { background: "#e2e8f0" };
      const active = (Number(this.recruitment.active_subjects || 0) / total) * 100;
      const retained = active + (Number(this.recruitment.dropped_data_retained || 0) / total) * 100;
      return { background: `conic-gradient(#2563eb 0 ${active}%, #818cf8 ${active}% ${retained}%, #64748b ${retained}% 100%)` };
    },
  },
  watch: {
    active: {
      immediate: true,
      handler(value) {
        if (value && String(this.loadedStudyId) !== String(this.studyId)) this.loadSummary();
      },
    },
    studyId() {
      this.summary = null;
      this.loadedStudyId = null;
      if (this.active) this.loadSummary();
    },
  },
  methods: {
    enrollmentChartX(value) {
      const timestamp = Date.parse(`${value}T00:00:00Z`);
      const span = this.enrollmentMaxTimestamp - this.enrollmentMinTimestamp;
      if (!Number.isFinite(timestamp) || span <= 0) return 445;
      return 62 + ((timestamp - this.enrollmentMinTimestamp) / span) * 766;
    },
    enrollmentProportionX(value) {
      const timestamp = Date.parse(`${value}T00:00:00Z`);
      const span = this.enrollmentActualMaxTimestamp - this.enrollmentActualMinTimestamp;
      if (!Number.isFinite(timestamp) || span <= 0) return 445;
      return 62 + ((timestamp - this.enrollmentActualMinTimestamp) / span) * 766;
    },
    enrollmentChartY(value) {
      return 245 - (Math.max(0, Number(value || 0)) / this.enrollmentTopValue) * 225;
    },
    enrollmentProportionY(value) {
      return 170 - (Math.max(0, Math.min(100, Number(value || 0))) / 100) * 150;
    },
    enrollmentColor(index) {
      const colors = ["#2563eb", "#0f766e", "#7c3aed", "#ea580c", "#db2777", "#0891b2", "#65a30d", "#64748b"];
      return colors[Math.abs(Number(index || 0)) % colors.length];
    },
    buildEnrollmentDateTicks(left, right, minimum = this.enrollmentMinTimestamp, maximum = this.enrollmentMaxTimestamp) {
      if (!this.enrollmentTimeline.length) return [];
      if (minimum === maximum) {
        return [{ timestamp: minimum, x: (left + right) / 2, label: this.formatDateOnly(this.enrollmentTimeline[0].date), anchor: "middle" }];
      }
      return [0, 0.25, 0.5, 0.75, 1].map((ratio, index) => {
        const timestamp = minimum + (maximum - minimum) * ratio;
        return {
          timestamp,
          x: left + (right - left) * ratio,
          label: this.formatDateOnly(new Date(timestamp).toISOString().slice(0, 10)),
          anchor: index === 0 ? "start" : (index === 4 ? "end" : "middle"),
        };
      });
    },
    formatDateOnly(value) {
      if (!value) return "—";
      const date = new Date(`${String(value).slice(0, 10)}T00:00:00Z`);
      return Number.isNaN(date.getTime())
        ? String(value)
        : date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
    },
    clearEnrollmentPlanMessage() {
      this.enrollmentPlanError = "";
      this.enrollmentPlanSaved = false;
    },
    hydrateEnrollmentPlan() {
      const plan = this.enrollmentPlan || {};
      this.enrollmentPlanDraft = {
        mode: plan.configured ? plan.mode : "none",
        target_subjects: plan.target_subjects || null,
        duration_months: plan.duration_months || null,
        monthlyText: Array.isArray(plan.monthly_enrollments) ? plan.monthly_enrollments.join(", ") : "",
      };
    },
    parseMonthlyEnrollmentPlan() {
      const values = String(this.enrollmentPlanDraft.monthlyText || "")
        .split(/[\s,;]+/)
        .map((value) => value.trim())
        .filter(Boolean);
      if (!values.length || values.some((value) => !/^\d+$/.test(value))) {
        throw new Error("Enter whole, non-negative subject numbers for each month.");
      }
      const parsed = values.map(Number);
      if (!parsed.some((value) => value > 0)) throw new Error("At least one month must recruit a subject.");
      return parsed;
    },
    async saveEnrollmentPlan() {
      this.clearEnrollmentPlanMessage();
      const mode = this.enrollmentPlanDraft.mode;
      const payload = { mode, target_subjects: null, duration_months: null, monthly_enrollments: [] };
      if (mode === "linear") {
        payload.target_subjects = Number(this.enrollmentPlanDraft.target_subjects);
        payload.duration_months = Number(this.enrollmentPlanDraft.duration_months);
        if (!Number.isInteger(payload.target_subjects) || payload.target_subjects < 1 || !Number.isInteger(payload.duration_months) || payload.duration_months < 1) {
          this.enrollmentPlanError = "Enter a valid subject target and recruitment period.";
          return;
        }
      } else if (mode === "monthly") {
        try {
          payload.monthly_enrollments = this.parseMonthlyEnrollmentPlan();
        } catch (error) {
          this.enrollmentPlanError = error.message;
          return;
        }
      }

      this.savingEnrollmentPlan = true;
      try {
        await axios.put(`/forms/studies/${this.studyId}/enrollment-plan`, payload, {
          headers: { Authorization: `Bearer ${this.$store.state.token}` },
        });
        this.enrollmentPlanSaved = true;
        await this.loadSummary(true);
      } catch (error) {
        this.enrollmentPlanError = error?.response?.data?.detail || error?.message || "Could not save the enrollment plan.";
      } finally {
        this.savingEnrollmentPlan = false;
      }
    },
    async loadSummary(force = false) {
      if (!this.studyId || (this.loading && !force)) return;
      this.loading = true;
      this.error = "";
      try {
        const { data } = await axios.get(`/forms/studies/${this.studyId}/compliance-summary`, {
          headers: { Authorization: `Bearer ${this.$store.state.token}` },
        });
        this.summary = data;
        this.loadedStudyId = this.studyId;
        this.hydrateEnrollmentPlan();
      } catch (error) {
        this.error = error?.response?.data?.detail || error?.message || "Unknown error";
      } finally {
        this.loading = false;
      }
    },
    distributionWidth(key) {
      if (!this.distributionTotal) return "0%";
      return `${(Number(this.distribution[key] || 0) / this.distributionTotal) * 100}%`;
    },
    percentClass(visit) {
      if (Number(visit?.skipped_fields || 0) > 0) return "skipped";
      const number = Number(visit?.data_compliance_percent || 0);
      if (number >= 80) return "good";
      if (number >= 50) return "moderate";
      return "low";
    },
    formatDateTime(value) {
      if (!value) return "";
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
    },
  },
};
</script>

<style scoped>
.compliance-view { box-sizing: border-box; color: #111827; padding: 0 0 40px; font-size: 14px; }
.compliance-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid #f1f1f1; }
.eyebrow { display: none; }
.insight-label { display: block; margin: 0 0 5px; color: #6b7280; font-size: 12px; font-weight: 600; text-transform: none; letter-spacing: 0; }
.compliance-header h2 { margin: 0; color: #111827; font-size: 16px; font-weight: 700; }
.subtitle { margin: 5px 0 0; color: #6b7280; font-size: 13px; }
.refresh-btn { padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 8px; background: transparent; color: #555; font-size: 14px; cursor: pointer; }
.refresh-btn:hover { background: #e8e8e8; color: #000; border-color: #d6d6d6; }
.refresh-btn:disabled { opacity: .6; cursor: wait; }
.state-card { padding: 24px; border: 1px solid #e5e7eb; border-radius: 10px; background: #f9fafb; color: #6b7280; text-align: center; }
.error-state { display: grid; gap: 5px; color: #991b1b; background: #fef2f2; border-color: #fecaca; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 12px; }
.kpi-card { min-height: 104px; padding: 14px; border: 1px solid #f1f1f1; border-radius: 10px; background: #fff; }
.kpi-label { display: block; color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.kpi-card strong { display: block; margin: 7px 0 5px; color: #111827; font-size: 26px; line-height: 1; }
.kpi-card small { color: #6b7280; font-size: 12px; line-height: 1.4; }
.operational-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 0 0 12px; padding: 12px; border: 1px solid #e5e7eb; border-radius: 12px; background: #f3f4f6; }
.operational-grid article { min-height: 72px; padding: 10px 12px; border: 1px solid #f1f1f1; border-radius: 8px; background: #fff; }
.operational-grid span { display: block; color: #6b7280; font-size: 12px; }
.operational-grid strong { display: block; margin: 5px 0 3px; color: #111827; font-size: 19px; }
.operational-grid .text-value { overflow: hidden; font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }
.operational-grid small { color: #6b7280; font-size: 11px; }
.scope-note { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin: 0 0 12px; padding: 11px 13px; border: 1px solid #bfdbfe; border-radius: 10px; background: #eff6ff; }
.scope-note div { display: grid; gap: 3px; }
.scope-note strong { color: #1e3a8a; font-size: 12px; }
.scope-note span { color: #1e40af; font-size: 12px; }
.scope-note small { max-width: 520px; color: #475569; font-size: 11px; line-height: 1.4; text-align: right; }
.insight-grid, .dashboard-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(280px, .65fr); gap: 12px; margin-bottom: 12px; }
.insight-card, .chart-card, .table-card { border: 1px solid #f1f1f1; border-radius: 12px; background: #fff; }
.insight-card { min-height: 160px; padding: 16px; }
.primary-insight { display: flex; align-items: center; justify-content: space-between; gap: 20px; background: #f9fafb; border-color: #e5e7eb; }
.primary-insight strong { display: block; max-width: 560px; margin-top: 7px; font-size: 19px; line-height: 1.35; }
.primary-insight p { margin: 8px 0 0; color: #6b7280; font-size: 13px; }
.radial { position: relative; flex: 0 0 104px; width: 104px; height: 104px; display: grid; place-items: center; border-radius: 50%; }
.radial::after, .donut::after { content: ""; position: absolute; inset: 11px; border-radius: 50%; background: #fff; }
.radial span { position: relative; z-index: 1; color: #0f766e; font-size: 21px; font-weight: 700; }
.chart-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.chart-heading h3 { margin: 2px 0 0; color: #111827; font-size: 14px; font-weight: 700; }
.chart-heading p { max-width: 680px; margin: 6px 0 0; color: #6b7280; font-size: 12px; line-height: 1.45; }
.metric-note { color: #6b7280; font-size: 11px; }
.recruitment-chart-wrap { display: flex; align-items: center; gap: 18px; margin-top: 14px; }
.donut { position: relative; flex: 0 0 104px; width: 104px; height: 104px; display: grid; place-items: center; border-radius: 50%; }
.donut span { position: relative; z-index: 1; display: grid; color: #6b7280; font-size: 10px; text-align: center; }
.donut strong { color: #111827; font-size: 20px; }
.legend-list, .status-breakdown { flex: 1; margin: 0; padding: 0; list-style: none; }
.legend-list li, .status-breakdown li { display: grid; grid-template-columns: 9px 1fr auto; align-items: center; gap: 8px; padding: 5px 0; color: #374151; font-size: 12px; }
.dot { width: 8px; height: 8px; border-radius: 50%; }.dot.active { background: #2563eb; }.dot.retained { background: #818cf8; }.dot.deleted { background: #64748b; }
.chart-card { padding: 16px; }
.enrollment-card { margin-bottom: 12px; }
.enrollment-heading { align-items: center; }
.actual-only-badge { flex: 0 0 auto; padding: 5px 9px; border: 1px solid #cbd5e1; border-radius: 999px; background: #f8fafc; color: #475569; font-size: 11px; font-weight: 600; }
.actual-only-badge.planned { border-color: #bfdbfe; background: #eff6ff; color: #1d4ed8; }
.enrollment-kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 9px; margin-top: 14px; }
.enrollment-kpis article { min-height: 84px; padding: 11px 12px; border: 1px solid #e5e7eb; border-radius: 9px; background: #f9fafb; }
.enrollment-kpis span, .enrollment-kpis small { display: block; color: #6b7280; font-size: 11px; line-height: 1.4; }
.enrollment-kpis strong { display: block; margin: 5px 0 3px; color: #111827; font-size: 21px; line-height: 1.15; }
.enrollment-kpis .forecast-value { font-size: 16px; }
.enrollment-chart-block { margin-top: 14px; padding: 12px; border: 1px solid #e5e7eb; border-radius: 10px; }
.enrollment-chart-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.enrollment-chart-header > div:first-child { display: grid; gap: 3px; }
.enrollment-chart-header strong { font-size: 12px; }
.enrollment-chart-header span { color: #6b7280; font-size: 11px; }
.enrollment-legend { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 7px 11px; }
.enrollment-legend span { display: inline-flex; align-items: center; gap: 5px; color: #475569; white-space: nowrap; }
.enrollment-legend i, .group-proportion-list i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: #111827; }
.enrollment-legend .planned-series i { width: 14px; height: 0; border-top: 2px dashed #f97316; border-radius: 0; background: transparent; }
.enrollment-chart-scroll { margin-top: 8px; overflow-x: auto; }
.enrollment-chart, .enrollment-proportion-chart { display: block; width: 100%; min-width: 700px; height: auto; }
.enrollment-total-line, .enrollment-group-line, .enrollment-planned-line { fill: none; stroke-linecap: round; stroke-linejoin: round; }
.enrollment-total-line { stroke: #111827; stroke-width: 3; }
.enrollment-group-line { stroke-width: 1.75; opacity: .72; }
.enrollment-planned-line { stroke: #f97316; stroke-width: 2.5; stroke-dasharray: 8 6; }
.enrollment-total-point { fill: #fff; stroke: #111827; stroke-width: 2; }
.proportion-grid line { stroke: #e5e7eb; stroke-width: 1; }
.enrollment-proportion-chart polygon { opacity: .72; }
.group-proportion-list { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 8px; }
.group-proportion-list div { display: grid; grid-template-columns: 9px auto auto; align-items: center; gap: 6px; color: #475569; font-size: 11px; }
.group-proportion-list strong { color: #111827; }
.plan-comparison-note { display: flex; align-items: center; gap: 8px; margin-top: 7px; padding: 7px 9px; border-radius: 7px; background: #f0fdf4; color: #166534; font-size: 11px; }
.plan-comparison-note.behind { background: #fff7ed; color: #9a3412; }
.plan-comparison-note.on-plan { background: #eff6ff; color: #1d4ed8; }
.plan-comparison-note span { color: inherit; opacity: .85; }
.enrollment-warning { margin: 10px 0 0; color: #9a3412; font-size: 11px; }
.enrollment-plan-editor { margin-top: 14px; padding: 13px; border: 1px solid #dbeafe; border-radius: 10px; background: #f8fbff; }
.plan-editor-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.plan-editor-heading strong { color: #111827; font-size: 13px; }
.plan-editor-heading p { max-width: 680px; margin: 4px 0 0; color: #64748b; font-size: 11px; line-height: 1.45; }
.save-plan-btn { flex: 0 0 auto; padding: 7px 12px; border: 1px solid #2563eb; border-radius: 7px; background: #2563eb; color: #fff; font-size: 12px; font-weight: 600; cursor: pointer; }
.save-plan-btn:disabled { opacity: .6; cursor: wait; }
.plan-fields { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
.plan-fields label { display: grid; align-content: start; gap: 5px; }
.plan-fields label > span { color: #374151; font-size: 11px; font-weight: 600; }
.plan-fields input, .plan-fields select, .plan-fields textarea { box-sizing: border-box; width: 100%; padding: 8px 9px; border: 1px solid #d1d5db; border-radius: 7px; background: #fff; color: #111827; font: inherit; font-size: 12px; }
.plan-fields textarea { resize: vertical; }
.plan-fields small { color: #64748b; font-size: 10px; line-height: 1.4; }
.monthly-plan-field { grid-column: span 2; }
.plan-message { margin: 9px 0 0; font-size: 11px; }
.plan-message.error { color: #b91c1c; }.plan-message.success { color: #166534; }.plan-message.neutral { color: #475569; }
.histogram-card { margin-bottom: 12px; }
.histogram-scroll { margin-top: 16px; overflow-x: auto; }
.histogram-plot { min-width: 620px; height: 210px; display: grid; grid-template-columns: repeat(10, minmax(48px, 1fr)); align-items: end; gap: clamp(6px, 1.4vw, 16px); padding: 12px 8px 0; border-bottom: 1px solid #9ca3af; background: repeating-linear-gradient(to top, transparent 0, transparent 49px, #eef2f7 50px); }
.histogram-column { height: 100%; min-width: 0; display: grid; grid-template-rows: 22px 1fr 30px; align-items: end; outline: none; }
.histogram-column > strong { color: #374151; font-size: 12px; text-align: center; }
.histogram-bar-area { height: 144px; display: flex; align-items: end; }
.histogram-bar-area span { width: 100%; min-height: 0; border-radius: 5px 5px 0 0; background: linear-gradient(180deg, #38bdf8, #2563eb); box-shadow: 0 1px 2px rgba(37, 99, 235, .18); transition: height .35s ease, filter .2s ease, transform .2s ease; transform-origin: bottom; }
.histogram-column:hover .histogram-bar-area span, .histogram-column:focus .histogram-bar-area span { filter: saturate(1.25); transform: scaleX(1.04); }
.histogram-column small { align-self: center; color: #6b7280; font-size: 10px; font-weight: 600; text-align: center; white-space: nowrap; }
.histogram-axis-title { padding: 8px 0 1px; color: #6b7280; font-size: 11px; text-align: center; }
.threshold-card { margin-bottom: 12px; }
.threshold-chart-wrap { width: 100%; margin-top: 12px; overflow-x: auto; }
.threshold-chart { display: block; width: 100%; min-width: 620px; height: auto; }
.chart-grid line { stroke: #e5e7eb; stroke-width: 1; }
.chart-axes line { stroke: #9ca3af; stroke-width: 1; }
.axis-labels { fill: #6b7280; font-size: 10px; }
.threshold-line { fill: none; stroke: #2563eb; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.curve-hit-point { fill: transparent; cursor: crosshair; }
.curve-hit-point:hover { fill: #2563eb; opacity: .35; }
.threshold-marker line { stroke-width: 1; stroke-dasharray: 3 4; opacity: .55; }
.threshold-marker circle { stroke: #fff; stroke-width: 2; }
.marker-80 { fill: #2563eb; stroke: #2563eb; background: #2563eb; }.marker-90 { fill: #f97316; stroke: #f97316; background: #f97316; }.marker-95 { fill: #16a34a; stroke: #16a34a; background: #16a34a; }
.threshold-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 2px 8px 4px 60px; }
.threshold-summary article { display: grid; grid-template-columns: 8px 1fr; gap: 3px 8px; padding: 9px 10px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; }
.threshold-summary i { grid-row: 1 / 3; align-self: center; width: 8px; height: 8px; border-radius: 50%; }
.threshold-summary span { color: #6b7280; font-size: 10px; }
.threshold-summary strong { color: #111827; font-size: 12px; }
.bar-list { display: grid; gap: 14px; margin-top: 16px; padding-right: 4px; }
.bar-row { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(150px, 1.4fr) 44px; align-items: center; gap: 12px; }
.bar-meta { min-width: 0; display: grid; gap: 3px; }.bar-meta strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }.bar-meta span { color: #6b7280; font-size: 11px; }
.bar-track { height: 9px; overflow: hidden; border-radius: 999px; background: #e5e7eb; }
.bar-fill { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #2563eb, #38bdf8); }
.bar-value { color: #374151; font-size: 12px; text-align: right; }
.stacked-bar { display: flex; overflow: hidden; height: 14px; margin: 20px 0 13px; border-radius: 999px; background: #e5e7eb; }
.stacked-bar span { height: 100%; }.complete, .dot.complete { background: #16a34a; }.partial, .dot.partial { background: #f59e0b; }.not-started, .dot.not-started { background: #cbd5e1; }
.status-breakdown { margin-bottom: 13px; }
.skipped-note { padding: 8px 10px; border-radius: 8px; background: #f3f4f6; color: #6b7280; font-size: 12px; }.skipped-note.warning { color: #9a3412; background: #fff7ed; }
.group-card { margin-bottom: 12px; }
.group-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; margin-top: 14px; }
.group-stat { padding: 11px; border: 1px solid #f1f1f1; border-radius: 8px; background: #f9fafb; }
.group-stat-head { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 9px; }.group-stat-head span { color: #0f766e; font-weight: 700; }
.group-fill { background: linear-gradient(90deg, #0f766e, #2dd4bf); }.group-stat small { display: block; margin-top: 7px; color: #6b7280; font-size: 11px; }
.table-card { overflow: hidden; margin-bottom: 12px; }.table-card > .chart-heading { padding: 14px 14px 10px; }
.table-scroll { overflow-x: auto; } table { width: 100%; border-collapse: collapse; background: #fff; font-size: 13px; } th { padding: 9px 10px; background: #fafafe; color: #374151; font-weight: 600; text-align: left; white-space: nowrap; } td { padding: 9px 10px; border-top: 1px solid #f5f5f5; color: #374151; } tbody tr:hover { background: #f9fafb; }
.percent-pill { display: inline-block; min-width: 46px; padding: 3px 7px; border-radius: 999px; font-weight: 700; text-align: center; }.percent-pill.good { color: #166534; background: #dcfce7; }.percent-pill.moderate { color: #92400e; background: #fef3c7; }.percent-pill.low, .percent-pill.skipped { color: #991b1b; background: #fee2e2; }.percent-pill.skipped { outline: 1px solid #fca5a5; }
.empty-state, .empty-cell { padding: 24px; color: #6b7280; text-align: center; }
.method-note { padding: 11px 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; color: #6b7280; font-size: 11px; line-height: 1.55; }.method-note span { display: block; margin-top: 4px; }.method-note::after { content: ""; display: block; height: 1px; }
@media (max-width: 1050px) { .kpi-grid, .enrollment-kpis { grid-template-columns: repeat(2, 1fr); }.insight-grid, .dashboard-grid { grid-template-columns: 1fr; } }
@media (max-width: 760px) { .operational-grid, .threshold-summary, .plan-fields { grid-template-columns: 1fr; }.monthly-plan-field { grid-column: auto; }.threshold-summary { margin-left: 0; }.chart-heading, .scope-note, .enrollment-chart-header, .plan-editor-heading { align-items: flex-start; flex-direction: column; }.scope-note small { text-align: left; }.metric-note { align-self: flex-start; }.enrollment-legend { justify-content: flex-start; } }
@media (max-width: 640px) { .compliance-header, .primary-insight { align-items: stretch; flex-direction: column; }.kpi-grid, .enrollment-kpis { grid-template-columns: 1fr; }.radial { align-self: center; }.recruitment-chart-wrap { flex-direction: column; }.bar-row { grid-template-columns: 1fr 44px; }.bar-meta { grid-column: 1 / -1; }.plan-comparison-note { align-items: flex-start; flex-direction: column; } }
</style>
