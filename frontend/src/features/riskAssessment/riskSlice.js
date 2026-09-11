import { createSlice } from '@reduxjs/toolkit';

/**
 * riskSlice — manages the AI Copilot Risk Assessment section.
 * Populated when SSE emits a "risk_update" event.
 */

const initialState = {
  severityLevel: '',
  riskScore: null,
  recommendedAction: '',
  rootCauseHypothesis: '',
  capaRequired: null,
  regulatoryReportRequired: null,
  recallRisk: '',
  aiReasoning: '',
  capaSteps: '',
  isLoaded: false,
};

const riskSlice = createSlice({
  name: 'risk',
  initialState,

  reducers: {
    populateRiskFromAI(state, action) {
      const data = action.payload;
      // Map snake_case backend → camelCase frontend
      if (data.severity_level !== undefined) state.severityLevel = data.severity_level || '';
      if (data.risk_score !== undefined) state.riskScore = data.risk_score;
      if (data.recommended_action !== undefined) state.recommendedAction = data.recommended_action || '';
      if (data.root_cause_hypothesis !== undefined) state.rootCauseHypothesis = data.root_cause_hypothesis || '';
      if (data.capa_required !== undefined) state.capaRequired = data.capa_required;
      if (data.regulatory_report_required !== undefined) state.regulatoryReportRequired = data.regulatory_report_required;
      if (data.recall_risk !== undefined) state.recallRisk = data.recall_risk || '';
      if (data.ai_reasoning !== undefined) state.aiReasoning = data.ai_reasoning || '';
      if (data.capa_steps !== undefined) state.capaSteps = data.capa_steps || '';
      state.isLoaded = true;
    },

    resetRisk() {
      return { ...initialState };
    },
  },
});

export const { populateRiskFromAI, resetRisk } = riskSlice.actions;
export default riskSlice.reducer;
